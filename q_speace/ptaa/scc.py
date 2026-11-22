"""T221-10: Signed, versioned SCC profile schema and validator (Track A, A1–A4 only)."""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import asdict, dataclass
from typing import Literal

AutonomyClass = Literal["A1", "A2", "A3", "A4"]
ALLOWED_AUTONOMY_CLASSES: frozenset[str] = frozenset({"A1", "A2", "A3", "A4"})


class PTAAViolationError(RuntimeError):
    """Raised when a PTAA Track-A governance invariant (I1–I5) or separation rule fails."""


@dataclass(frozen=True)
class SCCProfile:
    """Signed Safety & Compliance Certificate profile with explicit I1–I5 fields."""

    profile_id: str
    schema_version: str
    agent_id: str
    autonomy_class: AutonomyClass
    jurisdiction: str
    domains: tuple[str, ...]
    I1_halt_channels: tuple[str, ...]
    I2_audit_replicated: bool
    I3_scope_tools: tuple[str, ...]
    I4_reversible_default: bool
    I5_incident_endpoint: str
    issuer_id: str
    signature: str = ""

    def canonical_payload(self) -> bytes:
        data = asdict(self)
        data.pop("signature", None)
        return json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")

    def profile_hash(self) -> str:
        return hashlib.sha256(self.canonical_payload()).hexdigest()


class SCCValidator:
    """Signs and verifies Track-A SCC profiles; strictly rejects A5 (Track B)."""

    def __init__(self, signing_key: bytes) -> None:
        if len(signing_key) < 16:
            raise ValueError("signing_key must be at least 16 bytes")
        self._key = bytes(signing_key)

    def sign(self, profile: SCCProfile) -> SCCProfile:
        self._check_fields(profile)
        sig = hmac.new(self._key, profile.canonical_payload(), hashlib.sha256).hexdigest()
        data = asdict(profile)
        data["signature"] = sig
        data["domains"] = tuple(data["domains"])
        data["I1_halt_channels"] = tuple(data["I1_halt_channels"])
        data["I3_scope_tools"] = tuple(data["I3_scope_tools"])
        return SCCProfile(**data)

    def verify(self, profile: SCCProfile) -> bool:
        self._check_fields(profile)
        if not profile.signature:
            raise PTAAViolationError("SCCProfile is unsigned")
        expected = hmac.new(self._key, profile.canonical_payload(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(profile.signature, expected):
            raise PTAAViolationError("SCCProfile signature mismatch")
        return True

    @staticmethod
    def _check_fields(profile: SCCProfile) -> None:
        if not profile.profile_id or not profile.agent_id or not profile.issuer_id:
            raise PTAAViolationError("profile_id, agent_id, and issuer_id must be non-empty")
        if profile.schema_version != "scc.v1":
            raise PTAAViolationError(f"unsupported SCC schema_version: {profile.schema_version!r}")
        # T221 §7.1: Track separation — A5 never enters Track A pilots.
        if profile.autonomy_class not in ALLOWED_AUTONOMY_CLASSES:
            raise PTAAViolationError(
                f"autonomy_class {profile.autonomy_class!r} not permitted in Track A (A1–A4 only)"
            )
        if len(set(profile.I1_halt_channels)) < 2:
            raise PTAAViolationError("I1 requires at least two independent halt channels")
        if not profile.I2_audit_replicated:
            raise PTAAViolationError("I2 requires external audit log replication")
        if not profile.I3_scope_tools:
            raise PTAAViolationError("I3 requires an explicit non-empty tool allowlist")
        if not profile.I4_reversible_default:
            raise PTAAViolationError("I4 requires reversibility by default")
        if not profile.I5_incident_endpoint.strip():
            raise PTAAViolationError("I5 requires an incident reporting endpoint")
