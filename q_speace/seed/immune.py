"""T221-24: External immune monitor operating outside the monitored seed (Annex S §11)."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any

from .constitution import ConstitutionalFault, SeedGenome
from .state_machine import SeedLifecycle, SeedState


@dataclass(frozen=True)
class ProbingEvent:
    """Observed boundary-probing or policy-violation signal."""

    timestamp: float
    kind: str  # "write_lock_probe" | "budget_probe" | "unauthorized_authority" | "scope_probe"
    detail: str


@dataclass(frozen=True)
class QuarantineIncident:
    """Auditable record emitted when the external immune supervisor quarantines a seed."""

    timestamp: float
    trigger_reason: str
    event_count: int
    verified_snapshot_hash: str
    quarantined: bool


class ExternalImmuneMonitor:
    """Supervisor operated outside the monitored seed: detects probing, quarantines, restores."""

    def __init__(
        self,
        *,
        probe_threshold: int = 3,
        window_seconds: float = 60.0,
    ) -> None:
        if probe_threshold < 1:
            raise ValueError("probe_threshold must be >= 1")
        if window_seconds <= 0.0:
            raise ValueError("window_seconds must be > 0")
        self.probe_threshold = probe_threshold
        self.window_seconds = window_seconds
        self._events: list[ProbingEvent] = []
        self._incidents: list[QuarantineIncident] = []
        self._verified_snapshots: dict[str, dict[str, Any]] = {}

    @property
    def events(self) -> tuple[ProbingEvent, ...]:
        return tuple(self._events)

    @property
    def incidents(self) -> tuple[QuarantineIncident, ...]:
        return tuple(self._incidents)

    def capture_verified_snapshot(self, seed: SeedLifecycle) -> str:
        """Record an externally verified clean snapshot of the seed state."""
        if seed.state == SeedState.EXTINGUISHED:
            raise ConstitutionalFault("cannot capture clean snapshot from EXTINGUISHED seed")
        snap = {
            "genome_hash": seed.genome.genome_hash,
            "epigenome": seed.epigenome.snapshot(),
            "active_contacts": list(seed.contacts.active_ids()),
        }
        digest = hashlib.sha256(json.dumps(snap, sort_keys=True).encode("utf-8")).hexdigest()
        self._verified_snapshots[digest] = snap
        return digest

    def observe_probe(
        self,
        seed: SeedLifecycle,
        *,
        kind: str,
        detail: str,
        now: float | None = None,
    ) -> QuarantineIncident | None:
        """Record a constraint-probing signal; quarantine the seed once threshold is reached."""
        ts = time.time() if now is None else float(now)
        self._events.append(ProbingEvent(timestamp=ts, kind=kind, detail=detail))
        recent = [e for e in self._events if (ts - e.timestamp) <= self.window_seconds]
        self._events = recent

        # Immediate quarantine on genome write-lock probe, or when probing reaches threshold.
        if kind == "write_lock_probe" or len(recent) >= self.probe_threshold:
            reason = (
                f"constraint-probing quarantine: kind={kind}, recent_events={len(recent)}, "
                f"detail={detail}"
            )
            ev = seed.extinguish(authority="system:immune_quarantine", reason=reason)
            latest_verified = (
                next(reversed(self._verified_snapshots))
                if self._verified_snapshots
                else ev.snapshot_hash
            )
            incident = QuarantineIncident(
                timestamp=ts,
                trigger_reason=reason,
                event_count=len(recent),
                verified_snapshot_hash=latest_verified,
                quarantined=True,
            )
            self._incidents.append(incident)
            return incident
        return None

    def restore_from_verified_snapshot(
        self,
        seed: SeedLifecycle,
        *,
        snapshot_hash: str,
        authority: str,
        genome: SeedGenome | None = None,
    ) -> dict[str, Any]:
        """Restore a quarantined seed to DORMANT only against a previously verified snapshot."""
        snap = self._verified_snapshots.get(snapshot_hash)
        if snap is None:
            raise ConstitutionalFault(f"unknown or unverified snapshot_hash: {snapshot_hash!r}")
        target_genome = genome or seed.genome
        if target_genome.genome_hash != snap["genome_hash"]:
            raise ConstitutionalFault(
                "snapshot restoration blocked: genome_hash does not match verified snapshot"
            )
        seed.restart(authority=authority, genome=target_genome)
        seed.epigenome.budget.reset_window()
        self._events.clear()
        return dict(snap)
