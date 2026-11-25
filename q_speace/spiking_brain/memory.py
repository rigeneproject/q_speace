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

import hashlib
import json
import math
import os
import re
import sqlite3
import time
from collections import deque
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol, runtime_checkable

import numpy as np

from .types import ThinkResult

_TOKEN_RE = re.compile(r"[a-z0-9_]+")


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

    async def get_relevant(self, query: str, k: int = 4) -> Sequence[ThinkResult]:
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

    async def get_relevant(self, query: str, k: int = 4) -> Sequence[ThinkResult]:
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
        return [_dict_to_minimal_result(json.loads(line)) for line in lines]

    async def get_relevant(self, query: str, k: int = 4) -> Sequence[ThinkResult]:
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


def embed_text_hashed(text: str, dim: int = 128) -> np.ndarray:
    """Deterministic signed feature-hash L2 unit vector (word tokens + char 3-grams, T248).

    Synthesized via BCEL from ``GTP SPEACE`` ``SemanticStore``: requires only
    stdlib ``hashlib.blake2b`` + ``numpy`` (zero external ML/daemon dependencies).
    """
    if dim < 8:
        raise ValueError("dim must be >= 8")
    vec = np.zeros(dim, dtype=np.float64)
    normalized = text.lower().strip()
    if not normalized:
        return vec

    features: list[tuple[str, float]] = []
    tokens = _TOKEN_RE.findall(normalized)
    for tok in tokens:
        features.append((f"tok:{tok}", 1.0))
        if len(tok) >= 3:
            for idx in range(len(tok) - 2):
                features.append((f"tri:{tok[idx : idx + 3]}", 0.35))
    if not features:
        compact = re.sub(r"\s+", "", normalized)
        for idx in range(max(len(compact) - 2, 1)):
            features.append((f"raw:{compact[idx : idx + 3]}", 0.5))

    for feat, weight in features:
        digest = hashlib.blake2b(feat.encode("utf-8"), digest_size=8).digest()
        bucket = int.from_bytes(digest[:4], "big") % dim
        sign = 1.0 if (digest[4] % 2 == 0) else -1.0
        vec[bucket] += sign * weight

    norm = float(np.linalg.norm(vec))
    if norm > 1e-12:
        vec /= norm
    return vec


class SemanticEpisodicMemory:
    """Zero-daemon SQLite + feature-hashed hybrid episodic memory (T248).

    Implements the :class:`Memory` Protocol with:
    - Hybrid lexical token overlap (or FTS5 when enabled) + 128-D ``blake2b``
      cosine similarity ranking.
    - Non-destructive TTL expiration (``archive_expired``).
    - Deterministic offline deduplication (``consolidate``).
    """

    def __init__(
        self,
        db_path: str | Path,
        *,
        max_entries: int = 10_000,
        ttl_seconds: float | None = None,
        dim: int = 128,
    ) -> None:
        if max_entries < 1:
            raise ValueError("max_entries must be >= 1")
        if ttl_seconds is not None and (not math.isfinite(ttl_seconds) or ttl_seconds <= 0.0):
            raise ValueError("ttl_seconds must be finite and > 0 when provided")
        if dim < 8:
            raise ValueError("dim must be >= 8")

        self.db_path = Path(db_path)
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self.dim = dim
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._fts_enabled = False
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self._conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                text_hash TEXT NOT NULL,
                confidence REAL NOT NULL,
                n_tokens INTEGER NOT NULL,
                latency_s REAL NOT NULL,
                ts REAL NOT NULL,
                archived INTEGER NOT NULL DEFAULT 0,
                embedding BLOB NOT NULL
            )
            """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_episodes_active_ts ON episodes(archived, ts)")
        try:
            cur.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS episodes_fts USING fts5(text, content='')"
            )
            self._fts_enabled = True
        except sqlite3.OperationalError:
            self._fts_enabled = False
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    async def put(self, result: ThinkResult) -> None:
        if not math.isfinite(result.confidence) or not math.isfinite(result.latency_s):
            raise ValueError("ThinkResult confidence and latency_s must be finite")
        now = time.time()
        vec = embed_text_hashed(result.text, dim=self.dim)
        norm_text = re.sub(r"\s+", " ", result.text.strip().lower())
        text_hash = hashlib.sha256(norm_text.encode("utf-8")).hexdigest()
        cur = self._conn.cursor()
        cur.execute(
            """
            INSERT INTO episodes (text, text_hash, confidence, n_tokens, latency_s, ts, archived, embedding)
            VALUES (?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (
                result.text,
                text_hash,
                float(result.confidence),
                int(result.n_tokens),
                float(result.latency_s),
                now,
                vec.astype(np.float32).tobytes(),
            ),
        )
        rowid = cur.lastrowid
        if self._fts_enabled and rowid is not None:
            cur.execute("INSERT INTO episodes_fts(rowid, text) VALUES (?, ?)", (rowid, result.text))
        # Enforce bounded active row cap
        cur.execute(
            """
            UPDATE episodes SET archived = 1
            WHERE archived = 0 AND id NOT IN (
                SELECT id FROM episodes WHERE archived = 0 ORDER BY id DESC LIMIT ?
            )
            """,
            (self.max_entries,),
        )
        self._conn.commit()

    def archive_expired(self, now: float | None = None) -> int:
        """Archive active entries older than ``ttl_seconds``; returns archived count."""
        if self.ttl_seconds is None:
            return 0
        ref_now = time.time() if now is None else float(now)
        if not math.isfinite(ref_now):
            raise ValueError("now must be finite")
        cutoff = ref_now - self.ttl_seconds
        cur = self._conn.cursor()
        cur.execute(
            "UPDATE episodes SET archived = 1 WHERE archived = 0 AND ts < ?",
            (cutoff,),
        )
        changed = cur.rowcount if cur.rowcount is not None and cur.rowcount > 0 else 0
        self._conn.commit()
        return int(changed)

    def consolidate(self) -> int:
        """Deduplicate active episodes sharing normalized ``text_hash`` (keeps highest confidence)."""
        cur = self._conn.cursor()
        cur.execute("""
            UPDATE episodes SET archived = 1
            WHERE archived = 0 AND id NOT IN (
                SELECT id FROM (
                    SELECT id,
                           ROW_NUMBER() OVER (
                               PARTITION BY text_hash
                               ORDER BY confidence DESC, id DESC
                           ) AS rn
                    FROM episodes
                    WHERE archived = 0
                ) WHERE rn = 1
            )
            """)
        removed = cur.rowcount if cur.rowcount is not None and cur.rowcount > 0 else 0
        self._conn.commit()
        return int(removed)

    async def recent(self, k: int = 8) -> Sequence[ThinkResult]:
        if k < 1:
            return []
        self.archive_expired()
        cur = self._conn.cursor()
        rows = cur.execute(
            """
            SELECT text, confidence, n_tokens, latency_s
            FROM episodes
            WHERE archived = 0
            ORDER BY id DESC
            LIMIT ?
            """,
            (k,),
        ).fetchall()
        return [
            _dict_to_minimal_result(
                {"text": r[0], "confidence": r[1], "n_tokens": r[2], "latency_s": r[3]}
            )
            for r in rows
        ]

    async def get_relevant(self, query: str, k: int = 4) -> Sequence[ThinkResult]:
        if k < 1:
            return []
        self.archive_expired()
        if not query.strip():
            return await self.recent(k)

        q_vec = embed_text_hashed(query, dim=self.dim)
        q_tokens = set(_TOKEN_RE.findall(query.lower()))

        fts_boost_ids: set[int] = set()
        if self._fts_enabled and q_tokens:
            fts_query = " OR ".join(sorted(q_tokens))
            try:
                fts_rows = self._conn.execute(
                    "SELECT rowid FROM episodes_fts WHERE episodes_fts MATCH ? LIMIT 64",
                    (fts_query,),
                ).fetchall()
                fts_boost_ids = {int(r[0]) for r in fts_rows}
            except sqlite3.OperationalError:
                fts_boost_ids = set()

        rows = self._conn.execute("""
            SELECT id, text, confidence, n_tokens, latency_s, embedding
            FROM episodes
            WHERE archived = 0
            ORDER BY id DESC
            """).fetchall()

        scored: list[tuple[float, int, dict[str, object]]] = []
        for row_id, text, conf, n_tok, lat, emb_bytes in rows:
            doc_tokens = set(_TOKEN_RE.findall(str(text).lower()))
            lexical = len(q_tokens & doc_tokens) / max(len(q_tokens), 1) if q_tokens else 0.0
            if int(row_id) in fts_boost_ids:
                lexical = min(1.0, lexical + 0.15)
            d_vec = np.frombuffer(emb_bytes, dtype=np.float32).astype(np.float64)
            cosine = float(np.dot(q_vec, d_vec)) if d_vec.size == self.dim else 0.0
            score = 0.65 * lexical + 0.35 * max(0.0, cosine)
            if score > 0.05:
                scored.append(
                    (
                        score,
                        int(row_id),
                        {
                            "text": text,
                            "confidence": conf,
                            "n_tokens": n_tok,
                            "latency_s": lat,
                        },
                    )
                )
        scored.sort(key=lambda item: (-item[0], -item[1]))
        return [_dict_to_minimal_result(item[2]) for item in scored[:k]]
