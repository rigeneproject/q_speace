"""Epigenetic tag system — reversible -> permanent mutations (T37)."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto


class EpigeneticMarker(Enum):
    PROMOTING = auto()
    SUPPRESSING = auto()
    NEUTRAL = auto()


@dataclass
class EpigeneticTag:
    marker: EpigeneticMarker
    expression: float = 1.0
    timestamp: float = 0.0
    confidence: float = 0.0
    source: str = ""


@dataclass
class EpigeneticState:
    mutation_id: str
    promotion_count: int = 0
    suppression_count: int = 0
    observation_window: int = 10
    tags: list[EpigeneticTag] = field(default_factory=list)
    consolidated: bool = False
    created_at: float = 0.0
    last_promoted: float = 0.0

    @property
    def stability_ratio(self) -> float:
        total = self.promotion_count + self.suppression_count
        if total == 0:
            return 0.0
        return self.promotion_count / total

    @property
    def ready_for_consolidation(self) -> bool:
        return (
            self.promotion_count >= 3
            and self.stability_ratio >= 0.7
            and not self.consolidated
        )

    @property
    def ready_for_rollback(self) -> bool:
        return (
            self.suppression_count >= 2
            and self.stability_ratio < 0.3
        )


class EpigeneticEngine:
    """Manages the lifecycle of epigenetic tags and consolidation."""

    def __init__(self, min_promotions: int = 3, stability_threshold: float = 0.7) -> None:
        self._states: dict[str, EpigeneticState] = {}
        self._min_promotions = min_promotions
        self._stability_threshold = stability_threshold

    def register(self, mutation_id: str) -> EpigeneticState:
        state = EpigeneticState(
            mutation_id=mutation_id,
            created_at=time.time(),
        )
        self._states[mutation_id] = state
        return state

    def promote(self, mutation_id: str, confidence: float = 0.0, source: str = "") -> EpigeneticTag:
        state = self._states.setdefault(
            mutation_id,
            EpigeneticState(mutation_id=mutation_id, created_at=time.time()),
        )
        state.promotion_count += 1
        state.last_promoted = time.time()
        tag = EpigeneticTag(
            marker=EpigeneticMarker.PROMOTING,
            expression=min(1.0, confidence + 0.1 * state.promotion_count),
            timestamp=time.time(),
            confidence=confidence,
            source=source,
        )
        state.tags.append(tag)
        self._check_consolidation(state)
        return tag

    def suppress(self, mutation_id: str, confidence: float = 0.0, source: str = "") -> EpigeneticTag:
        state = self._states.setdefault(
            mutation_id,
            EpigeneticState(mutation_id=mutation_id, created_at=time.time()),
        )
        state.suppression_count += 1
        tag = EpigeneticTag(
            marker=EpigeneticMarker.SUPPRESSING,
            expression=max(0.0, 1.0 - confidence),
            timestamp=time.time(),
            confidence=confidence,
            source=source,
        )
        state.tags.append(tag)
        return tag

    def _check_consolidation(self, state: EpigeneticState) -> None:
        if state.ready_for_consolidation:
            state.consolidated = True

    def consolidate(self, mutation_id: str) -> bool:
        state = self._states.get(mutation_id)
        if state is None:
            return False
        if state.ready_for_consolidation:
            state.consolidated = True
            return True
        return False

    def should_rollback(self, mutation_id: str) -> bool:
        state = self._states.get(mutation_id)
        return state is not None and state.ready_for_rollback

    def state_of(self, mutation_id: str) -> EpigeneticState | None:
        return self._states.get(mutation_id)

    def all_consolidated(self) -> list[str]:
        return [mid for mid, s in self._states.items() if s.consolidated]

    def clear(self) -> None:
        self._states.clear()
