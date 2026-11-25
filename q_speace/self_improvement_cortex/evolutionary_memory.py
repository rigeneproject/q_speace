"""EvolutionaryMemory — stores and retrieves past mutation outcomes (T38)."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import numpy as np


def _require_finite(name: str, val: float) -> float:
    fval = float(val)
    if not math.isfinite(fval):
        raise ValueError(f"{name} must be finite (got {val!r})")
    return fval


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

    def __post_init__(self) -> None:
        _require_finite("outcome", self.outcome)
        _require_finite("timestamp", self.timestamp)
        for k, v in self.metrics_before.items():
            _require_finite(f"metrics_before[{k!r}]", v)
        for k, v in self.metrics_after.items():
            _require_finite(f"metrics_after[{k!r}]", v)

    @property
    def net_impact(self) -> float:
        if not self.metrics_after:
            return float(self.outcome)
        avg_before = sum(self.metrics_before.values()) / max(len(self.metrics_before), 1)
        avg_after = sum(self.metrics_after.values()) / max(len(self.metrics_after), 1)
        return avg_after - avg_before


class EvolutionaryMemory:
    """Long-term storage of evolutionary experiments."""

    def __init__(self, max_entries: int = 10000) -> None:
        if max_entries < 1:
            raise ValueError(f"max_entries must be >= 1 (got {max_entries})")
        self._entries: list[MemoryEntry] = []
        self._max_entries = max_entries

    def store(self, entry: MemoryEntry) -> None:
        self._entries.append(entry)
        if len(self._entries) > self._max_entries:
            self._entries.pop(0)

    def find_similar(self, context_signature: str, top_k: int = 5) -> list[MemoryEntry]:
        candidates = [e for e in self._entries if e.context_signature == context_signature]
        candidates.sort(key=lambda e: abs(e.outcome), reverse=True)
        return candidates[:top_k]

    def find_similar_metrics(
        self,
        metrics: Mapping[str, float],
        *,
        tags: Sequence[str] | None = None,
        top_k: int = 5,
        min_similarity: float = 0.0,
    ) -> list[MemoryEntry]:
        """Continuous metric-cosine + Jaccard tag recall (T248, fixes float-string jitter)."""
        if top_k < 1:
            return []
        if not math.isfinite(min_similarity):
            raise ValueError("min_similarity must be finite")
        clean_query: dict[str, float] = {}
        for k, v in metrics.items():
            clean_query[k] = _require_finite(f"metrics[{k!r}]", v)
        query_tags = set(tags) if tags is not None else set()

        scored: list[tuple[float, int, MemoryEntry]] = []
        for idx, entry in enumerate(self._entries):
            keys = sorted(set(clean_query.keys()) | set(entry.metrics_before.keys()))
            cos_sim = 0.0
            if keys and clean_query and entry.metrics_before:
                q_vec = np.array([clean_query.get(k, 0.0) for k in keys], dtype=np.float64)
                e_vec = np.array([entry.metrics_before.get(k, 0.0) for k in keys], dtype=np.float64)
                denom = float(np.linalg.norm(q_vec) * np.linalg.norm(e_vec))
                if denom > 1e-12:
                    cos_sim = float(np.dot(q_vec, e_vec) / denom)
                elif np.allclose(q_vec, e_vec):
                    cos_sim = 1.0

            entry_tags = set(entry.tags)
            union_tags = query_tags | entry_tags
            jaccard = len(query_tags & entry_tags) / len(union_tags) if union_tags else 0.0
            sim = (0.75 * max(0.0, cos_sim) + 0.25 * jaccard) if union_tags else max(0.0, cos_sim)
            if sim >= min_similarity:
                scored.append((sim, idx, entry))

        scored.sort(key=lambda item: (-item[0], -abs(item[2].outcome), -item[1]))
        return [item[2] for item in scored[:top_k]]

    def best_for_level(self, level: int, top_k: int = 3) -> list[MemoryEntry]:
        candidates = [e for e in self._entries if e.level == level]
        candidates.sort(key=lambda e: e.net_impact, reverse=True)
        return candidates[:top_k]

    def has_failed_before(self, context_signature: str, target: str) -> bool:
        return any(
            e.context_signature == context_signature and e.target == target and e.net_impact < 0
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
