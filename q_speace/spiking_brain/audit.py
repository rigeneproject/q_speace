"""T-SPB-3-C — persistent audit trail for SpikingBrainCortex apply events.

Every call to :meth:`SpikingBrainCortex.apply_to_ilf` writes one JSONL
record to a file. Each record contains enough provenance to
reconstruct who said what, when, with which model, and what the
gate decisions were:

- ``ts``           — wall-clock timestamp (seconds since epoch)
- ``agent_id``     — which ILF agent was updated
- ``backend``      — backend name (e.g. ``"http:..."``, ``"stub"``)
- ``backend_meta`` — backend metadata (model, sidecar URL, …)
- ``prompt_hash``  — first 16 hex chars of SHA-256(prompt)
- ``n_tokens``     — token count the backend reported
- ``confidence``   — backend-reported confidence
- ``belief``       — full belief vector
- ``coherence_phi_pre``  — ILF coherence_phi BEFORE apply
- ``coherence_phi_post`` — ILF coherence_phi AFTER apply
- ``sevo``         — Sevo gate value at apply time
- ``energy_w``     — energy model output (W)
- ``approved``     — whether the cortex approved the apply
- ``reason``       — cortex reason string (for rejections)

The audit log is **append-only** and lives at
``~/.q_speace/brain_audit.jsonl`` by default. Override with the
constructor ``path`` argument or set ``Q_SPEACE_BRAIN_AUDIT_PATH``
in the environment. Writes are best-effort: a failure to write is
logged to stderr but does not raise (the audit trail must never
break a live cognition cycle).
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any, TextIO

import numpy as np

DEFAULT_AUDIT_PATH = Path.home() / ".q_speace" / "brain_audit.jsonl"
ENV_AUDIT_PATH = "Q_SPEACE_BRAIN_AUDIT_PATH"


def _resolve_path(path: Path | str | None) -> Path:
    """Resolve the audit path: explicit arg > env var > default."""
    if path is not None:
        return Path(path).expanduser()
    env = os.environ.get(ENV_AUDIT_PATH)
    if env:
        return Path(env).expanduser()
    return DEFAULT_AUDIT_PATH


def _short_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


class BrainAuditLog:
    """Append-only JSONL writer for :class:`SpikingBrainCortex` events.

    Thread-safety: a single :class:`BrainAuditLog` instance is intended
    for use from one async event loop. Multiple instances may share a
    file path (the format is line-oriented, so writes interleave safely
    at OS level).
    """

    def __init__(self, path: Path | str | None = None) -> None:
        self.path: Path = _resolve_path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # File handle is opened on first write for low overhead; a fresh
        # ``_open()`` is also exposed for tests that want explicit flush.
        self._fh: TextIO | None = None

    def _open(self) -> None:
        if self._fh is None:
            self._fh = self.path.open("a", encoding="utf-8")

    def write(self, record: dict[str, Any]) -> None:
        """Append one record as a JSON line.

        Best-effort: any OSError or encoding error is logged to stderr
        but never raised.
        """
        try:
            self._open()
            assert self._fh is not None
            self._fh.write(json.dumps(record, ensure_ascii=False) + "\n")
            self._fh.flush()
        except (OSError, TypeError, ValueError) as exc:
            print(
                f"[brain-audit] write failed: {exc.__class__.__name__}: {exc}",
                file=sys.stderr,
            )

    def close(self) -> None:
        if self._fh is not None:
            try:
                self._fh.flush()
                self._fh.close()
            except OSError:
                pass
            self._fh = None

    def recent(self, k: int = 20) -> list[dict[str, Any]]:
        """Return the last ``k`` records (most recent last).

        Reads from disk so it works across restarts. Empty list if the
        file does not exist.
        """
        if not self.path.exists():
            return []
        try:
            with self.path.open("r", encoding="utf-8") as f:
                lines = f.readlines()[-k:]
        except OSError:
            return []
        out: list[dict[str, Any]] = []
        for ln in lines:
            try:
                out.append(json.loads(ln))
            except json.JSONDecodeError:
                continue
        return out

    def __enter__(self) -> BrainAuditLog:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()


def make_apply_record(
    *,
    agent_id: str,
    backend: str,
    backend_meta: dict[str, Any],
    prompt: str,
    result_text: str,
    result_confidence: float,
    result_belief: np.ndarray | Iterable[float],
    n_tokens: int,
    coherence_phi_pre: float,
    coherence_phi_post: float,
    sevo: float,
    energy_w: float,
    approved: bool,
    reason: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one audit record dict. Pure function (testable)."""
    belief_arr = np.asarray(result_belief, dtype=float).ravel().tolist()
    rec: dict[str, Any] = {
        "ts": time.time(),
        "agent_id": str(agent_id),
        "backend": str(backend),
        "backend_meta": dict(backend_meta or {}),
        "prompt_hash": _short_hash(prompt),
        "prompt_excerpt": prompt[:120],
        "result_text_excerpt": result_text[:160],
        "result_confidence": float(result_confidence),
        "belief": belief_arr,
        "n_tokens": int(n_tokens),
        "coherence_phi_pre": float(coherence_phi_pre),
        "coherence_phi_post": float(coherence_phi_post),
        "sevo": float(sevo) if sevo != float("-inf") else None,
        "energy_w": float(energy_w),
        "approved": bool(approved),
        "reason": str(reason),
    }
    if extra:
        rec["extra"] = dict(extra)
    return rec
