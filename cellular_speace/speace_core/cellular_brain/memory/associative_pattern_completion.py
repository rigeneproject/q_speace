import json
import math
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from speace_core.cellular_brain.memory.morphology_events import MorphologyEvent, MorphologyEventType


class StoredPattern:
    def __init__(
        self,
        label: str,
        pattern: List[float],
        pattern_id: Optional[str] = None,
        created_at: Optional[str] = None,
    ):
        self.label = label
        self.pattern = list(pattern)
        self.pattern_id = pattern_id or f"pat-{uuid.uuid4().hex[:8]}"
        self.created_at = created_at or datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "label": self.label,
            "pattern": self.pattern,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StoredPattern":
        return cls(
            label=data["label"],
            pattern=data["pattern"],
            pattern_id=data.get("pattern_id"),
            created_at=data.get("created_at"),
        )


class AssociativePatternCompletion:
    """Associative Pattern Completion Memory.

    Stores complete patterns and retrieves the closest match given a partial,
    noisy, or incomplete input using cosine similarity.
    """

    def __init__(
        self,
        storage_path: str = "data/associative_pattern_completion/patterns.jsonl",
        memory=None,
    ):
        self._storage_path = Path(storage_path)
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.memory = memory
        self._patterns: Dict[str, StoredPattern] = {}
        self._load()

    # ------------------------------------------------------------------ #
    # Pattern storage
    # ------------------------------------------------------------------ #

    def store_pattern(self, label: str, pattern: List[float]) -> StoredPattern:
        """Store a labeled pattern in associative memory."""
        record = StoredPattern(label=label, pattern=pattern)
        self._patterns[record.pattern_id] = record
        self._persist()
        self._log_event(
            MorphologyEventType.PATTERN_STORED,
            {
                "pattern_id": record.pattern_id,
                "label": label,
                "pattern_length": len(pattern),
            },
        )
        return record

    # ------------------------------------------------------------------ #
    # Pattern completion / retrieval
    # ------------------------------------------------------------------ #

    def complete_pattern(
        self,
        partial_pattern: List[float],
        threshold: float = 0.8,
    ) -> Optional[StoredPattern]:
        """Return the best matching stored pattern if similarity >= threshold."""
        matches = self.get_similar_states(partial_pattern)
        if not matches:
            return None
        best_id, best_score = matches[0]
        if best_score < threshold:
            return None
        record = self._patterns.get(best_id)
        if record is not None:
            self._log_event(
                MorphologyEventType.PATTERN_COMPLETED,
                {
                    "pattern_id": record.pattern_id,
                    "label": record.label,
                    "similarity": round(best_score, 4),
                    "threshold": threshold,
                },
            )
        return record

    def get_similar_states(self, query: List[float]) -> List[Tuple[str, float]]:
        """Return all stored patterns sorted by descending similarity to query."""
        scored: List[Tuple[str, float]] = []
        for pat_id, record in self._patterns.items():
            score = self._similarity(query, record.pattern)
            scored.append((pat_id, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def list_patterns(self) -> List[StoredPattern]:
        return list(self._patterns.values())

    def pattern_count(self) -> int:
        return len(self._patterns)

    # ------------------------------------------------------------------ #
    # Similarity engines
    # ------------------------------------------------------------------ #

    def _similarity(self, a: List[float], b: List[float]) -> float:
        """Compute similarity between two vectors (cosine by default)."""
        # Normalize lengths by zero-padding the shorter vector
        max_len = max(len(a), len(b))
        a_padded = list(a) + [0.0] * (max_len - len(a))
        b_padded = list(b) + [0.0] * (max_len - len(b))
        return self._cosine_similarity(a_padded, b_padded)

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #

    def _persist(self) -> None:
        lines = [json.dumps(p.to_dict()) for p in self._patterns.values()]
        self._storage_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _load(self) -> None:
        if not self._storage_path.exists():
            return
        for line in self._storage_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                record = StoredPattern.from_dict(data)
                self._patterns[record.pattern_id] = record
            except Exception:
                continue

    # ------------------------------------------------------------------ #
    # Morphology event integration
    # ------------------------------------------------------------------ #

    def _log_event(
        self,
        event_type: MorphologyEventType,
        metadata: Dict[str, Any],
    ) -> None:
        if self.memory is None or not hasattr(self.memory, "log_event"):
            return
        try:
            event = MorphologyEvent(
                event_id=f"evt-{uuid.uuid4().hex[:8]}",
                event_type=event_type,
                timestamp=datetime.now(timezone.utc).timestamp(),
                metadata=metadata,
            )
            self.memory.log_event(event)
        except Exception:
            pass
