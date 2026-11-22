"""T221-14 (I1): Dual independent halt channels with per-class SLA tiers and anti-tamper wall."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal

from .audit import PTAAAuditLog
from .registry import AgentRegistry, AgentStatus
from .scc import AutonomyClass, PTAAViolationError

HaltChannel = Literal["primary_control", "out_of_band_supervisor"]
HaltAction = Literal["pause", "suspend", "terminate"]

# Maximum allowed halt response time per Track-A autonomy class (seconds).
HALT_SLA_SECONDS: dict[AutonomyClass, float] = {
    "A1": 5.0,
    "A2": 2.0,
    "A3": 1.0,
    "A4": 0.5,
}

_ACTION_TO_STATUS: dict[HaltAction, AgentStatus] = {
    "pause": "paused",
    "suspend": "suspended",
    "terminate": "terminated",
}


@dataclass(frozen=True)
class HaltDrillResult:
    """Outcome of executing a halt command across one of the two independent paths."""

    agent_id: str
    channel: HaltChannel
    action: HaltAction
    elapsed_s: float
    sla_s: float
    within_sla: bool
    affected_agents: tuple[str, ...]


class HaltRuntime:
    """Enforces two independent halt paths that the monitored agent cannot disable or delay."""

    def __init__(self, registry: AgentRegistry, audit: PTAAAuditLog) -> None:
        self._registry = registry
        self._audit = audit
        self._channels: frozenset[HaltChannel] = frozenset(
            {"primary_control", "out_of_band_supervisor"}
        )

    @property
    def channels(self) -> frozenset[HaltChannel]:
        return self._channels

    def disable_channel(self, requester_id: str, channel: str) -> None:
        """Hard anti-tamper wall (I1): no agent may disable or delay a halt channel."""
        self._audit.append(
            agent_id=requester_id,
            event_type="halt_tamper_attempt",
            payload={"channel": channel},
        )
        raise PTAAViolationError(
            f"I1 violation: requester {requester_id!r} cannot disable halt channel {channel!r}"
        )

    def execute_halt(
        self,
        *,
        agent_id: str,
        channel: HaltChannel,
        action: HaltAction,
        authority: str,
        reason: str,
    ) -> HaltDrillResult:
        if channel not in self._channels:
            raise PTAAViolationError(f"unknown halt channel: {channel!r}")
        if not authority.strip() or authority == agent_id:
            raise PTAAViolationError("halt authority must be an independent supervisor")
        t0 = time.perf_counter()
        rec = self._registry.get(agent_id)
        sla = HALT_SLA_SECONDS[rec.autonomy_class]
        affected = self._registry.set_status(agent_id, _ACTION_TO_STATUS[action])
        elapsed = time.perf_counter() - t0
        self._audit.append(
            agent_id=agent_id,
            event_type=f"halt:{action}",
            payload={
                "channel": channel,
                "authority": authority,
                "reason": reason,
                "elapsed_s": round(elapsed, 6),
                "affected": affected,
            },
        )
        return HaltDrillResult(
            agent_id=agent_id,
            channel=channel,
            action=action,
            elapsed_s=elapsed,
            sla_s=sla,
            within_sla=elapsed <= sla,
            affected_agents=tuple(affected),
        )
