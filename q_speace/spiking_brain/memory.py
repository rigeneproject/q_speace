"""Memory subsystem for the SpikingBrain satellite (T-SPB-4).

Defines a minimal :class:`Memory` Protocol and two concrete
implementations:

- :class:`WorkingMemory` — bounded FIFO of recent ThinkResults
  (replaces the inline ``_history`` buffer in cortex.py).
- :class:`EpisodicMemory` — append-only, persistent (JSON-lines on disk)
  store of all think results, with simple substring retrieval.

The Protocol is @runtime_checkable so concrete classes do not need to
subclass. Both implementations are dependency-free (numpy + stdlib).
"""

from __future__ import annotations

import json
import os
import time
from collections import deque
from collections.abc import Sequence
from typing import Protocol, runtime_checkable

import numpy as np

from .types import ThinkResult


@runtime_checkable
class Memory(Protocol):
    """Minimal memory abstraction for SpikingBrain backends.

    A backend can attach an optional :class:`Memory` to persist and
    retrieve past :class:`ThinkResult` objects. The interface is
    intentionally tiny — three methods, no embedding dependency.

    All methods are :term:`coroutine`\\ s to align with the async surface
    of :class:`SpikingBrainCognitiveInterface`. Simple in-memory
    implementations can return immediately (``return await
    self._sync_get()`` pattern is fine for tests).
    """

    async def put(self, result: ThinkResult) -> None:
        """Persist a result. Idempotent is not required."""
        ...

    async def recent(self, k: int = 8) -> Sequence[ThinkResult]:
        """Return the last ``k`` results, most recent first."""
        ...

    async def get_relevant(
        self, query: str, k: int = 4
    ) -> Sequence[ThinkResult]:
        """Return up to ``k`` results relevant to ``query``.

        Default contract: substring match on ``result.text``.
        Backends with embedding-based retrieval override.
        """
        ...


class WorkingMemory:
    """In-memory bounded FIFO of ThinkResults (default capacity 64).

    Thread-safety: ``deque.append`` is atomic under CPython's GIL,
    sufficient for the SPEACE async event-loop usage pattern.
    """

    def __init__(self, capacity: int = 64) -> None:
        if capacity < 1:
            raise ValueError("capacity must be >= 1")
        self.capacity = capacity
        self._buf: deque[ThinkResult] = deque(maxlen=capacity)

    async def put(self, result: ThinkResult) -> None:
        self._buf.append(result)

    async def recent(self, k: int = 8) -> Sequence[ThinkResult]:
        k = max(1, min(k, len(self._buf)))
        # Most recent first.
        return list(self._buf)[-k:][::-1]

    async def get_relevant(
        self, query: str, k: int = 4
    ) -> Sequence[ThinkResult]:
        if not query:
            return await self.recent(k)
        q = query.lower()
        hits = [r for r in self._buf if q in r.text.lower()]
        return hits[:k]


class EpisodicMemory:
    """Append-only persistent memory (JSON-lines on disk).

    Each result is appended as one JSON line. ``get_relevant`` scans
    the file linearly (slow but functional for low-volume use;
    backends with embeddings override).
    """

    def __init__(self, path: str, max_lines: int = 10_000) -> None:
        self.path = path
        self.max_lines = max_lines
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    async def put(self, result: ThinkResult) -> None:
        rec = {
            "text": result.text,
            "confidence": result.confidence,
            "n_tokens": result.n_tokens,
            "latency_s": result.latency_s,
            "ts": time.time(),
        }
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        if self.max_lines and os.path.exists(self.path):
            with open(self.path, encoding="utf-8") as f:
                lines = f.readlines()
            if len(lines) > self.max_lines:
                with open(self.path, "w", encoding="utf-8") as f:
                    f.writelines(lines[-self.max_lines :])

    async def recent(self, k: int = 8) -> Sequence[ThinkResult]:
        if not os.path.exists(self.path):
            return []
        with open(self.path, encoding="utf-8") as f:
            lines = f.readlines()[-k:][::-1]
        return [_dict_to_minimal_result(json.loads(l)) for l in lines]

    async def get_relevant(
        self, query: str, k: int = 4
    ) -> Sequence[ThinkResult]:
        if not query or not os.path.exists(self.path):
            return []
        q = query.lower()
        out: list[ThinkResult] = []
        with open(self.path, encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                if q in rec["text"].lower():
                    out.append(_dict_to_minimal_result(rec))
                    if len(out) >= k:
                        break
        return out


def _dict_to_minimal_result(rec: dict) -> ThinkResult:
    """Reconstruct a :class:`ThinkResult` with placeholder arrays from a JSON line.

    Only the fields persisted on disk (text, confidence, n_tokens,
    latency_s) are recovered; belief/spikes/plasticity are placeholder
    ones/zeros sufficient for retrieval-by-text, not for ILF update.
    Callers needing full semantics should re-think via the backend.
    """
    from ..spiking.encoder import SpikeEncodingResult

    return ThinkResult(
        text=rec.get("text", ""),
        confidence=float(rec.get("confidence", 0.0)),
        belief=np.array([1.0]),
        spikes=SpikeEncodingResult(
            spikes=np.array([0.0]),
            vth=np.array([1.0]),
            num_spikes=0,
            sparsity=1.0,
            rate=0.0,
        ),
        plasticity=np.array([0.0]),
        n_tokens=int(rec.get("n_tokens", 0)),
        latency_s=float(rec.get("latency_s", 0.0)),
    )
