"""Failure memory scaffolding.

A lightweight structured log of task/cognitive failures that other SPEACE
subsystems (self-improvement, FSPI, planning) can query to avoid repeating
the same mistakes.
"""
from __future__ import annotations
import datetime
import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class FailureRecord:
    """A single failure event with structured context."""

    __slots__ = ("timestamp", "subsystem", "task", "context", "error", "severity", "tags")

    def __init__(
        self,
        subsystem: str,
        task: str,
        error: str,
        context: Optional[Dict[str, Any]] = None,
        severity: float = 0.5,
        tags: Optional[List[str]] = None,
        timestamp: Optional[float] = None,
    ):
        self.timestamp = timestamp or datetime.datetime.now(datetime.UTC).timestamp()
        self.subsystem = subsystem
        self.task = task
        self.context = context or {}
        self.error = error
        self.severity = float(severity)
        self.tags = list(tags or [])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "subsystem": self.subsystem,
            "task": self.task,
            "context": self.context,
            "error": self.error,
            "severity": self.severity,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FailureRecord":
        return cls(
            subsystem=d.get("subsystem", ""),
            task=d.get("task", ""),
            error=d.get("error", ""),
            context=d.get("context") or {},
            severity=float(d.get("severity", 0.5)),
            tags=list(d.get("tags") or []),
            timestamp=d.get("timestamp"),
        )


class FailureMemory:
    """In-memory failure store with optional JSONL persistence and context retrieval.

    The store is intentionally simple: append, query by subsystem/tag, and retrieve
    top-k most similar records using a token overlap heuristic. This is enough to
    bootstrap a 'did we already fail at this?' signal for self-improvement loops.
    """

    def __init__(self, persist_path: Optional[Path] = None, max_records: int = 10_000):
        self._records: List[FailureRecord] = []
        self._persist_path = Path(persist_path) if persist_path else None
        self._max_records = max_records
        self._lock = threading.Lock()
        if self._persist_path and self._persist_path.exists():
            self._load()

    # ── core API ────────────────────────────────────────────────────────
    def record(self, failure: FailureRecord) -> None:
        with self._lock:
            self._records.append(failure)
            if len(self._records) > self._max_records:
                self._records = self._records[-self._max_records:]
            if self._persist_path:
                self._persist_path.parent.mkdir(parents=True, exist_ok=True)
                with self._persist_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(failure.to_dict(), ensure_ascii=False) + "\n")

    def by_subsystem(self, subsystem: str, limit: int = 50) -> List[FailureRecord]:
        out = [r for r in self._records if r.subsystem == subsystem]
        return out[-limit:][::-1]

    def by_tag(self, tag: str, limit: int = 50) -> List[FailureRecord]:
        out = [r for r in self._records if tag in r.tags]
        return out[-limit:][::-1]

    def similar(self, query: str, k: int = 5) -> List[Tuple[FailureRecord, float]]:
        """Return top-k FailureRecord most similar to a free-text query.

        Similarity is a simple Jaccard score over whitespace-tokenised lowercased
        words. Good enough for the bootstrap; replace with embeddings later.
        """
        q = set((query or "").lower().split())
        scored: List[Tuple[FailureRecord, float]] = []
        if not q:
            return scored
        for r in self._records:
            hay = " ".join([
                r.task or "", r.error or "",
                " ".join(r.tags or []),
                json.dumps(r.context, ensure_ascii=False),
            ]).lower().split()
            t = set(hay)
            inter = len(q & t)
            union = len(q | t) or 1
            scored.append((r, inter / union))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]

    def stats(self) -> Dict[str, Any]:
        by_sub: Dict[str, int] = {}
        for r in self._records:
            by_sub[r.subsystem] = by_sub.get(r.subsystem, 0) + 1
        return {
            "total": len(self._records),
            "by_subsystem": by_sub,
            "max_severity": max((r.severity for r in self._records), default=0.0),
            "persist_path": str(self._persist_path) if self._persist_path else None,
        }

    def _load(self) -> None:
        try:
            with self._persist_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        d = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    self._records.append(FailureRecord.from_dict(d))
        except OSError:
            pass
