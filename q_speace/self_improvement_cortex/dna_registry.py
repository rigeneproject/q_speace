"""DNA Mutation Registry — records every evolutionary change (T36)."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from .epigenetics import EpigeneticMarker, EpigeneticTag


@dataclass
class DNAMutationRecord:
    mutation_id: str
    reason: str
    level: int
    target: str
    metrics_before: dict[str, float]
    metrics_after: dict[str, float]
    rollback: str | None = None
    approved_by: str = "evolution_council"
    confidence: float = 0.0
    epigenetic_markers: list[EpigeneticMarker] = field(default_factory=list)
    plasticity_score: float = 0.0
    timestamp: float = 0.0
    active: bool = True
    tags: list[EpigeneticTag] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "mutation_id": self.mutation_id,
            "reason": self.reason,
            "level": self.level,
            "target": self.target,
            "metrics_before": self.metrics_before,
            "metrics_after": self.metrics_after,
            "rollback": self.rollback,
            "approved_by": self.approved_by,
            "confidence": self.confidence,
            "plasticity_score": self.plasticity_score,
            "timestamp": self.timestamp,
            "active": self.active,
            "num_markers": len(self.epigenetic_markers),
            "num_tags": len(self.tags),
        }


class MutationRegistry:
    """Persistent record of every mutation applied to the organism."""

    def __init__(self) -> None:
        self._records: list[DNAMutationRecord] = []

    def record(
        self,
        reason: str,
        level: int,
        target: str,
        metrics_before: dict[str, float],
        metrics_after: dict[str, float],
        approved_by: str = "evolution_council",
        confidence: float = 0.0,
        rollback: str | None = None,
    ) -> DNAMutationRecord:
        record = DNAMutationRecord(
            mutation_id=uuid.uuid4().hex[:12],
            reason=reason,
            level=level,
            target=target,
            metrics_before=metrics_before,
            metrics_after=metrics_after,
            rollback=rollback,
            approved_by=approved_by,
            confidence=confidence,
            timestamp=time.time(),
        )
        self._records.append(record)
        return record

    def all(self) -> list[DNAMutationRecord]:
        return list(self._records)

    def by_level(self, level: int) -> list[DNAMutationRecord]:
        return [r for r in self._records if r.level == level]

    def recent(self, n: int = 10) -> list[DNAMutationRecord]:
        return self._records[-n:]

    def successful(self, min_delta: float = 0.0) -> list[DNAMutationRecord]:
        result = []
        for r in self._records:
            if r.rollback is None:
                avg_before = sum(r.metrics_before.values()) / max(len(r.metrics_before), 1)
                avg_after = sum(r.metrics_after.values()) / max(len(r.metrics_after), 1)
                if avg_after - avg_before >= min_delta:
                    result.append(r)
        return result

    def count(self) -> int:
        return len(self._records)
