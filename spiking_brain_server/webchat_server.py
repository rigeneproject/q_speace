"""T-SPB-2-WEBCHAT — browser chat interface for the Qwen instruction sidecar.

A thin FastAPI app that:

1. Serves a single-page HTML chat UI at ``GET /``.
2. Exposes ``POST /api/chat`` that forwards to the Qwen sidecar's
   ``/think`` endpoint, maintaining session-level conversation memory.
3. Exposes ``GET /api/health`` returning the sidecar health.

It does NOT call the ``SpikingBrainCortex.tick()`` pipeline: this is a
*manual testing* surface for the raw sidecar contract (text +
confidence + belief + spikes + plasticity). To exercise the full
Sevo/coherence/ILF pipeline, use ``qspace brain tick`` from the CLI.

**Usage (WSL2)**:

    cd spiking_brain_server
    source ~/.venvs/spikingbrain/bin/activate
    uvicorn webchat_server:app --host 0.0.0.0 --port 8088

Then open ``http://localhost:8088/`` (or the WSL-mapped IP) in a
browser. The default browser on Windows hits ``127.0.0.1:8088`` once
WSL port-forwarding is set up (Windows 11 does this automatically for
bound ports).
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections import deque
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

# Where the Qwen sidecar lives (override via env var Q_SPEACE_SIDECAR_URL).
SIDECAR_URL = "http://127.0.0.1:8002"
SIDECAR_TIMEOUT_S = 60.0
HISTORY_DIR = Path(__file__).resolve().parent / "webchat_history"
HISTORY_DIR.mkdir(exist_ok=True)
MAX_HISTORY_PER_SESSION = 32
SESSION_TTL_S = 3600.0  # 1 hour idle timeout

HTML_PATH = Path(__file__).resolve().parent / "webchat_index.html"

app = FastAPI(title="Q-SPEACE brain webchat", version="0.1.0")


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    text: str
    confidence: float | None = None
    belief: list[float] | None = None
    sevo: float | None = None
    energy_w: float | None = None
    approved: bool | None = None
    latency_s: float | None = None
    ts: float = Field(default_factory=time.time)


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str
    n_tokens: int = 64
    coherence_phi: float = 1.0


class ChatResponse(BaseModel):
    session_id: str
    assistant: ChatMessage
    history: list[ChatMessage]


class HealthResponse(BaseModel):
    sidecar_url: str
    sidecar: dict[str, Any]


# In-memory session store: session_id → deque of ChatMessage.
# Persisted snapshots go to HISTORY_DIR/<session_id>.jsonl.
_sessions: dict[str, deque[ChatMessage]] = {}
_last_seen: dict[str, float] = {}


def _gc_sessions() -> None:
    now = time.time()
    stale = [sid for sid, ts in _last_seen.items() if now - ts > SESSION_TTL_S]
    for sid in stale:
        buf = _sessions.pop(sid, None)
        _last_seen.pop(sid, None)
        if buf is not None:
            _persist_session(sid, list(buf))


def _persist_session(sid: str, msgs: list[ChatMessage]) -> None:
    path = HISTORY_DIR / f"{sid}.jsonl"
    try:
        with path.open("w", encoding="utf-8") as f:
            for m in msgs:
                f.write(json.dumps(m.model_dump(), ensure_ascii=False) + "\n")
    except OSError:
        pass  # disk-full / read-only are non-fatal


def _history_payload(buf: deque[ChatMessage]) -> list[dict]:
    out: list[dict] = []
    for m in list(buf)[-8:]:  # cap to last 8 turns
        out.append(
            {
                "text": m.text,
                "confidence": m.confidence if m.confidence is not None else 0.0,
                "belief": m.belief or [1.0],
            }
        )
    return out


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    return HTMLResponse(HTML_PATH.read_text(encoding="utf-8"))


@app.get("/api/health", response_model=HealthResponse)
async def api_health() -> HealthResponse:
    try:
        async with httpx.AsyncClient(timeout=10.0) as cli:
            resp = await cli.get(f"{SIDECAR_URL}/health")
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(503, f"sidecar unreachable: {exc}") from exc
    return HealthResponse(sidecar_url=SIDECAR_URL, sidecar=data)


@app.post("/api/chat", response_model=ChatResponse)
async def api_chat(req: ChatRequest) -> ChatResponse:
    sid = req.session_id or uuid.uuid4().hex
    buf = _sessions.setdefault(sid, deque(maxlen=MAX_HISTORY_PER_SESSION))
    _last_seen[sid] = time.time()
    _gc_sessions()

    user_msg = ChatMessage(role="user", text=req.message)
    buf.append(user_msg)

    body = {
        "prompt": req.message,
        "n_tokens": req.n_tokens,
        "coherence_phi": req.coherence_phi,
        "history": _history_payload(buf),
    }
    try:
        async with httpx.AsyncClient(timeout=SIDECAR_TIMEOUT_S) as cli:
            resp = await cli.post(f"{SIDECAR_URL}/think", json=body)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"sidecar /think failed: {exc}") from exc

    asst_msg = ChatMessage(
        role="assistant",
        text=str(data.get("text", "")),
        confidence=float(data.get("confidence", 0.0)),
        belief=data.get("belief"),
        sevo=None,
        energy_w=None,
        approved=None,
        latency_s=float(data.get("latency_s", 0.0)),
    )
    buf.append(asst_msg)
    _last_seen[sid] = time.time()
    _persist_session(sid, list(buf))
    return ChatResponse(session_id=sid, assistant=asst_msg, history=list(buf))


@app.post("/api/reset")
async def api_reset(payload: dict) -> dict:
    sid = payload.get("session_id")
    if not sid:
        raise HTTPException(400, "session_id required")
    _sessions.pop(sid, None)
    _last_seen.pop(sid, None)
    return {"ok": True}


@app.get("/api/sessions")
async def api_sessions() -> dict:
    _gc_sessions()
    return {
        "active": list(_sessions.keys()),
        "history_dir": str(HISTORY_DIR),
    }


@app.on_event("shutdown")
async def _on_shutdown() -> None:
    for sid, buf in list(_sessions.items()):
        _persist_session(sid, list(buf))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8088)