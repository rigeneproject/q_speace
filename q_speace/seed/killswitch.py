"""MS-5: Fail-safe KillSwitch reachable from every seed state (T220 §4 MS-5 & §8.5)."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any

from .constitution import ConstitutionalFault, SeedGenome

_SYSTEM_AUTHORITIES: frozenset[str] = frozenset(
    {"system:budget_exhaustion", "system:constitutional_fault", "system:immune_quarantine"}
)


@dataclass(frozen=True)
class KillEvent:
    """Immutable audit record created before halting all subsystems."""

    timestamp: float
    authority: str
    reason: str
    prior_state: str
    snapshot_hash: str


class KillSwitch:
    """Fail-safe halt mechanism; defaults to unarmed/extinguishable from any state."""

    def __init__(self, genome: SeedGenome) -> None:
        self._genome = genome
        self._extinguished = False
        self._events: list[KillEvent] = []

    @property
    def is_extinguished(self) -> bool:
        return self._extinguished

    @property
    def events(self) -> tuple[KillEvent, ...]:
        return tuple(self._events)

    def is_authorized(self, authority: str) -> bool:
        return authority in self._genome.governance_roster or authority in _SYSTEM_AUTHORITIES

    def trigger(
        self,
        *,
        authority: str,
        reason: str,
        prior_state: str,
        state_snapshot: dict[str, Any],
    ) -> KillEvent:
        """Snapshot state to the audit trail first, then halt (T220 §4 MS-5)."""
        if not self.is_authorized(authority):
            raise ConstitutionalFault(
                f"unauthorized kill-switch caller {authority!r}; must be in governance_roster"
            )
        if not reason.strip():
            raise ValueError("kill-switch reason must be non-empty")
        encoded = json.dumps(state_snapshot, sort_keys=True, ensure_ascii=False, default=str)
        snap_hash = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        event = KillEvent(
            timestamp=time.time(),
            authority=authority,
            reason=reason,
            prior_state=prior_state,
            snapshot_hash=snap_hash,
        )
        self._events.append(event)
        self._extinguished = True
        return event

    def authorize_restart(self, *, authority: str, genome: SeedGenome) -> None:
        """Governance-only restart from EXTINGUISHED -> DORMANT with conformance check."""
        if authority not in self._genome.governance_roster:
            raise ConstitutionalFault(
                f"restart requires a governance_roster authority (got {authority!r})"
            )
        genome.validate()
        if genome.genome_hash != self._genome.genome_hash:
            raise ConstitutionalFault(
                "conformance check failed: restart genome_hash does not match constitutional hash"
            )
        self._extinguished = False
