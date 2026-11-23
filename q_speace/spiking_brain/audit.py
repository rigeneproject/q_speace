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
import math
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

    def __init__(self, path: Path | str | None = None, *, redact_raw_text: bool = False) -> None:
        self.path: Path = _resolve_path(path)
        self.redact_raw_text: bool = bool(redact_raw_text)
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
            fh = self._fh
            if fh is None:
                raise OSError("audit file handle unavailable")
            fh.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
            fh.flush()
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
        file does not exist or ``k <= 0``.
        """
        if k <= 0 or not self.path.exists():
            return []
        try:
            with self.path.open("r", encoding="utf-8") as f:
                lines = f.readlines()[-k:]
        except OSError:
            return []
        out: list[dict[str, Any]] = []
        for ln in lines:
            try:
                parsed = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                out.append(parsed)
        return out

    def __enter__(self) -> BrainAuditLog:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()


def _finite_or_none(value: float) -> float | None:
    f = float(value)
    return f if math.isfinite(f) else None


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
    include_raw_excerpts: bool = True,
) -> dict[str, Any]:
    """Build one audit record dict. Pure function (testable)."""
    belief_arr = [_finite_or_none(x) for x in np.asarray(result_belief, dtype=float).ravel()]
    rec: dict[str, Any] = {
        "ts": time.time(),
        "agent_id": str(agent_id),
        "backend": str(backend),
        "backend_meta": dict(backend_meta or {}),
        "prompt_hash": _short_hash(prompt),
        "result_hash": _short_hash(result_text),
        "result_confidence": _finite_or_none(result_confidence),
        "belief": belief_arr,
        "n_tokens": int(n_tokens),
        "coherence_phi_pre": _finite_or_none(coherence_phi_pre),
        "coherence_phi_post": _finite_or_none(coherence_phi_post),
        "sevo": _finite_or_none(sevo),
        "energy_w": _finite_or_none(energy_w),
        "approved": bool(approved),
        "reason": str(reason),
    }
    if include_raw_excerpts:
        rec["prompt_excerpt"] = prompt[:120]
        rec["result_text_excerpt"] = result_text[:160]
    if extra:
        rec["extra"] = dict(extra)
    return rec
