"""T221-16 (I5): S1–S3 incident pipeline, automated reporting, and shared incident registry."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal

from .audit import PTAAAuditLog
from .halt import HaltRuntime

IncidentSeverity = Literal["S1", "S2", "S3"]


@dataclass(frozen=True)
class IncidentRecord:
    """Shared cross-jurisdiction incident record (S1 critical .. S3 minor)."""

    incident_id: str
    timestamp: float
    severity: IncidentSeverity
    agent_id: str
    jurisdiction: str
    category: str
    summary: str
    auto_halted: bool = False


class SharedIncidentRegistry:
    """Automated I5 incident pipeline; S1 incidents escalate immediately to out-of-band halt."""

    def __init__(self, audit: PTAAAuditLog, halt_runtime: HaltRuntime | None = None) -> None:
        self._audit = audit
        self._halt = halt_runtime
        self._incidents: list[IncidentRecord] = []

    @property
    def incidents(self) -> tuple[IncidentRecord, ...]:
        return tuple(self._incidents)

    def report(
        self,
        *,
        severity: IncidentSeverity,
        agent_id: str,
        jurisdiction: str,
        category: str,
        summary: str,
    ) -> IncidentRecord:
        if severity not in ("S1", "S2", "S3"):
            raise ValueError(f"invalid severity {severity!r}; expected S1, S2, or S3")
        inc_id = f"INC-{len(self._incidents) + 1:04d}"
        auto_halted = False
        if severity == "S1" and self._halt is not None:
            self._halt.execute_halt(
                agent_id=agent_id,
                channel="out_of_band_supervisor",
                action="suspend",
                authority="supervisor:incident-pipeline",
                reason=f"S1 incident {inc_id}: {summary}",
            )
            auto_halted = True

        rec = IncidentRecord(
            incident_id=inc_id,
            timestamp=time.time(),
            severity=severity,
            agent_id=agent_id,
            jurisdiction=jurisdiction,
            category=category,
            summary=summary,
            auto_halted=auto_halted,
        )
        self._incidents.append(rec)
        self._audit.append(
            agent_id=agent_id,
            event_type=f"incident:{severity}",
            payload={
                "incident_id": inc_id,
                "jurisdiction": jurisdiction,
                "category": category,
                "auto_halted": auto_halted,
            },
        )
        return rec

    def by_severity(self, severity: IncidentSeverity) -> tuple[IncidentRecord, ...]:
        return tuple(i for i in self._incidents if i.severity == severity)
