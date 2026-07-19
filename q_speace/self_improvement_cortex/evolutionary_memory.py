"""EvolutionaryMemory — stores and retrieves past mutation outcomes (T38)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MemoryEntry:
    mutation_id: str
    context_signature: str
    reason: str
    level: int
    target: str
    metrics_before: dict[str, float]
    metrics_after: dict[str, float]
    outcome: float  # positive = successful
    timestamp: float = 0.0
    tags: list[str] = field(default_factory=list)

    @property
    def net_impact(self) -> float:
        avg_before = sum(self.metrics_before.values()) / max(len(self.metrics_before), 1)
        avg_after = sum(self.metrics_after.values()) / max(len(self.metrics_after), 1)
        return avg_after - avg_before


class EvolutionaryMemory:
    """Long-term storage of evolutionary experiments."""

    def __init__(self, max_entries: int = 10000) -> None:
        self._entries: list[MemoryEntry] = []
        self._max_entries = max_entries

    def store(self, entry: MemoryEntry) -> None:
        self._entries.append(entry)
        if len(self._entries) > self._max_entries:
            self._entries.pop(0)

    def find_similar(self, context_signature: str, top_k: int = 5) -> list[MemoryEntry]:
        candidates = [
            e for e in self._entries
            if e.context_signature == context_signature
        ]
        candidates.sort(key=lambda e: abs(e.outcome), reverse=True)
        return candidates[:top_k]

    def best_for_level(self, level: int, top_k: int = 3) -> list[MemoryEntry]:
        candidates = [e for e in self._entries if e.level == level]
        candidates.sort(key=lambda e: e.net_impact, reverse=True)
        return candidates[:top_k]

    def has_failed_before(self, context_signature: str, target: str) -> bool:
        return any(
            e.context_signature == context_signature
            and e.target == target
            and e.net_impact < 0
            for e in self._entries
        )

    def success_rate(self, level: int | None = None) -> float:
        pool = self._entries if level is None else [e for e in self._entries if e.level == level]
        if not pool:
            return 0.0
        successful = sum(1 for e in pool if e.net_impact > 0)
        return successful / len(pool)

    def all(self) -> list[MemoryEntry]:
        return list(self._entries)

    def count(self) -> int:
        return len(self._entries)

    def clear(self) -> None:
        self._entries.clear()
