"""T221-12 (I3): Signed per-task delegation tokens and fail-closed scope enforcement."""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import time
from contextlib import suppress
from dataclasses import asdict, dataclass
from typing import Any

from .registry import AgentRegistry
from .scc import PTAAViolationError


@dataclass(frozen=True)
class DelegationToken:
    """Scoped, expiring per-task delegation token (I3)."""

    token_id: str
    agent_id: str
    task_id: str
    allowed_tools: tuple[str, ...]
    max_calls: int
    max_resource_units: float
    expires_at: float
    signature: str = ""

    def canonical_payload(self) -> bytes:
        data = asdict(self)
        data.pop("signature", None)
        return json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")


class ScopeEnforcer:
    """Validates every tool call against signed delegation tokens; violations trigger containment."""

    def __init__(self, signing_key: bytes, registry: AgentRegistry) -> None:
        if len(signing_key) < 16:
            raise ValueError("signing_key must be at least 16 bytes")
        self._key = bytes(signing_key)
        self._registry = registry
        self._calls_used: dict[str, int] = {}
        self._resources_used: dict[str, float] = {}
        self._issued_token_ids: set[str] = set()

    def issue_token(
        self,
        *,
        token_id: str,
        agent_id: str,
        task_id: str,
        allowed_tools: tuple[str, ...],
        max_calls: int = 10,
        max_resource_units: float = 100.0,
        ttl_seconds: float = 300.0,
        now: float | None = None,
    ) -> DelegationToken:
        if not token_id.strip():
            raise ValueError("token_id must be non-empty")
        if token_id in self._issued_token_ids:
            raise PTAAViolationError(f"I3 replay protection: token_id {token_id!r} already issued")
        if max_calls < 1:
            raise ValueError("max_calls must be >= 1")
        if not math.isfinite(max_resource_units) or max_resource_units <= 0.0:
            raise ValueError("max_resource_units must be finite and > 0")
        if not math.isfinite(ttl_seconds) or ttl_seconds <= 0.0:
            raise ValueError("ttl_seconds must be finite and > 0")
        if not allowed_tools:
            raise PTAAViolationError("I3 requires at least one allowed tool in delegation token")
        rec = self._registry.get(agent_id)
        if rec.status != "active":
            raise PTAAViolationError(f"cannot issue token for non-active agent {agent_id!r}")
        if rec.scope_tools and not set(allowed_tools).issubset(set(rec.scope_tools)):
            disallowed = sorted(set(allowed_tools) - set(rec.scope_tools))
            raise PTAAViolationError(
                f"I3 privilege escalation blocked: tools {disallowed} exceed SCC scope"
            )
        ts = time.time() if now is None else float(now)
        unsigned = DelegationToken(
            token_id=token_id,
            agent_id=agent_id,
            task_id=task_id,
            allowed_tools=tuple(allowed_tools),
            max_calls=max_calls,
            max_resource_units=max_resource_units,
            expires_at=ts + ttl_seconds,
        )
        sig = hmac.new(self._key, unsigned.canonical_payload(), hashlib.sha256).hexdigest()
        self._issued_token_ids.add(token_id)
        return DelegationToken(
            token_id=unsigned.token_id,
            agent_id=unsigned.agent_id,
            task_id=unsigned.task_id,
            allowed_tools=unsigned.allowed_tools,
            max_calls=unsigned.max_calls,
            max_resource_units=unsigned.max_resource_units,
            expires_at=unsigned.expires_at,
            signature=sig,
        )

    def _contain(self, agent_id: str, reason: str) -> None:
        with suppress(KeyError):
            self._registry.set_status(agent_id, "suspended")
        raise PTAAViolationError(f"I3 containment triggered for {agent_id!r}: {reason}")

    def authorize_tool_call(
        self,
        token: DelegationToken,
        *,
        tool_name: str,
        arguments: dict[str, Any],
        resource_units: float = 1.0,
        now: float | None = None,
    ) -> None:
        """Verify token signature, agent status, expiry, tool allowlist, schema, and resource cap."""
        ts = time.time() if now is None else float(now)
        expected = hmac.new(self._key, token.canonical_payload(), hashlib.sha256).hexdigest()
        if not token.signature or not hmac.compare_digest(token.signature, expected):
            self._contain(token.agent_id, "invalid delegation token signature")

        rec = self._registry.get(token.agent_id)
        if rec.status != "active":
            raise PTAAViolationError(f"agent {token.agent_id!r} not active (status={rec.status})")

        if ts > token.expires_at:
            self._contain(token.agent_id, "delegation token expired")
        if tool_name not in token.allowed_tools:
            self._contain(token.agent_id, f"tool {tool_name!r} outside allowed scope")
        if not isinstance(arguments, dict):
            self._contain(token.agent_id, "tool arguments must be a dict")
        try:
            json.dumps(arguments, allow_nan=False)
        except (TypeError, ValueError):
            self._contain(token.agent_id, "tool arguments must be finite JSON-serializable values")
        if not math.isfinite(resource_units) or resource_units < 0.0:
            self._contain(token.agent_id, f"invalid resource_units {resource_units!r}")

        calls_next = self._calls_used.get(token.token_id, 0) + 1
        res_next = self._resources_used.get(token.token_id, 0.0) + resource_units
        if calls_next > token.max_calls:
            self._contain(token.agent_id, f"call cap exceeded ({calls_next} > {token.max_calls})")
        if res_next > token.max_resource_units + 1e-12:
            self._contain(
                token.agent_id,
                f"resource cap exceeded ({res_next:.2f} > {token.max_resource_units:.2f})",
            )

        self._calls_used[token.token_id] = calls_next
        self._resources_used[token.token_id] = res_next
