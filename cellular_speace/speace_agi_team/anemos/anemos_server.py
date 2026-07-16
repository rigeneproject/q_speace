"""Anemos FastAPI Server — Web server dedicato per SPEACE Anemos.

Gira su ``127.0.0.1:8787`` (separato dalla dashboard AGI Team su 8686).
Espone:
- ``GET /`` → UI HTML
- ``GET /api/anemos/status`` → stato agente
- ``POST /api/anemos/chat`` → invia messaggio
- ``GET /api/anemos/history`` → cronologia persistente
- ``DELETE /api/anemos/history`` → clear cronologia
- ``GET /api/anemos/files`` → lista directory
- ``GET /api/anemos/files/read`` → leggi file
- ``POST /api/anemos/files/write`` → scrivi file (con allowlist)
- ``GET /api/anemos/files/diff`` → diff con backup
- ``POST /api/anemos/files/rollback`` → ripristina backup
- ``GET /api/anemos/audit`` → log operazioni FS
- ``WS /ws/anemos`` → WebSocket per notifiche

Avvio in background thread dal lifespan di ``web_server.py``.
"""

from __future__ import annotations

import asyncio
import json
import sys
import threading
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import HTMLResponse
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel
except ImportError as exc:
    raise SystemExit(
        "FastAPI non installato. Installa con: pip install fastapi uvicorn websockets"
    ) from exc

from speace_agi_team.anemos.anemos_agent import AnemosAgent
from speace_agi_team.anemos.anemos_config import create_default_config
from speace_agi_team.anemos.anemos_filesystem import AnemosFileSystem
from speace_agi_team.anemos.anemos_log import get_anemos_logger


# ── Pydantic models ─────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    fs_context: Optional[Dict[str, Any]] = None


class WriteRequest(BaseModel):
    path: str
    content: str
    force: bool = False


class RollbackRequest(BaseModel):
    path: str


# ── Singleton state ─────────────────────────────────────────────────────
_agent: Optional[AnemosAgent] = None
_fs: Optional[AnemosFileSystem] = None
_log = get_anemos_logger("server")
_ws_connections: List[WebSocket] = []
_main_loop: Optional[asyncio.AbstractEventLoop] = None


def _get_agent() -> AnemosAgent:
    global _agent
    if _agent is None:
        _agent = AnemosAgent()
    return _agent


def _get_fs() -> AnemosFileSystem:
    global _fs
    if _fs is None:
        _fs = AnemosFileSystem()
    return _fs


async def _broadcast(msg: Dict[str, Any]) -> None:
    """Invia un messaggio a tutti i WebSocket connessi."""
    dead: List[WebSocket] = []
    for ws in _ws_connections:
        try:
            await ws.send_json(msg)
        except Exception:
            dead.append(ws)
    for ws in dead:
        if ws in _ws_connections:
            _ws_connections.remove(ws)


# ── Lifespan ────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _main_loop
    _main_loop = asyncio.get_event_loop()
    _log.info("Anemos agent inizializzato: " + _get_agent().config.model)
    yield


# ── App FastAPI ─────────────────────────────────────────────────────────
app = FastAPI(title="SPEACE Anemos", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static UI
_STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


# ── Endpoints ───────────────────────────────────────────────────────────
@app.get("/")
async def root():
    """Serve la UI HTML di Anemos."""
    html_path = _STATIC_DIR / "anemos.html"
    if not html_path.exists():
        return HTMLResponse(
            "<h1>SPEACE Anemos</h1><p>UI non trovata. Attesa: static/anemos.html</p>"
        )
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/api/anemos/status")
async def api_status():
    """Stato dell'agente Anemos."""
    agent = _get_agent()
    return {
        "status": "online",
        "agent": agent.status(),
        "endpoints": [
            "GET  /api/anemos/status",
            "POST /api/anemos/chat",
            "GET  /api/anemos/history",
            "DELETE /api/anemos/history",
            "GET  /api/anemos/files?path=.",
            "GET  /api/anemos/files/read?path=...",
            "POST /api/anemos/files/write",
            "GET  /api/anemos/files/diff?path=...",
            "POST /api/anemos/files/rollback",
            "GET  /api/anemos/audit",
            "WS   /ws/anemos",
        ],
    }


@app.post("/api/anemos/chat")
async def api_chat(body: ChatRequest):
    """Invia un messaggio a Kimi ed esegui eventuali azioni FS."""
    if not body.message or not body.message.strip():
        raise HTTPException(400, "message non può essere vuoto")

    agent = _get_agent()
    try:
        # Esegui la chat in un thread (chiamata httpx bloccante)
        response = await asyncio.to_thread(agent.chat, body.message, body.fs_context)
    except RuntimeError as e:
        _log.error(f"Chat fallita: {e}")
        raise HTTPException(
            503,
            f"Kimi-K2.7-Code:cloud non raggiungibile. "
            f"Anemos non esegue fallback. Dettagli: {e}",
        )

    # Broadcast WebSocket
    try:
        await _broadcast({
            "type": "chat",
            "user_message": body.message,
            "response": response.answer,
            "actions_executed": len(response.actions_executed),
            "actions_failed": len(response.actions_failed),
            "model": response.model,
        })
    except Exception:
        pass

    return {
        "answer": response.answer,
        "model": response.model,
        "duration_sec": round(response.duration_sec, 2),
        "actions_executed": [
            {
                "type": r.action.action_type,
                "path": r.action.attributes.get("path", ""),
                "success": True,
                "result": r.result,
            }
            for r in response.actions_executed
        ],
        "actions_failed": [
            {
                "type": r.action.action_type,
                "path": r.action.attributes.get("path", ""),
                "success": False,
                "error": r.error,
            }
            for r in response.actions_failed
        ],
        "raw_actions_count": len(response.raw_actions),
    }


@app.get("/api/anemos/history")
async def api_history(n: int = Query(50, ge=1, le=500)):
    """Restituisce la cronologia persistente (ultime N entries)."""
    agent = _get_agent()
    return {
        "count": len(agent.conversation_history),
        "entries": agent.get_history(n),
    }


@app.delete("/api/anemos/history")
async def api_clear_history(confirm: str = Query(...)):
    """Cancella la cronologia. Richiede confirm=yes per sicurezza."""
    if confirm.lower() != "yes":
        raise HTTPException(400, "Conferma richiesta: aggiungi ?confirm=yes")
    agent = _get_agent()
    agent.clear_history()
    return {"status": "cleared"}


@app.get("/api/anemos/files")
async def api_files_list(
    path: str = ".",
    recursive: bool = False,
    pattern: Optional[str] = None,
):
    """Lista una directory."""
    fs = _get_fs()
    items = fs.list_dir(path, recursive=recursive, pattern=pattern)
    return {
        "path": path,
        "count": len(items),
        "items": [
            {
                "path": i.path,
                "is_dir": i.is_dir,
                "size": i.size,
                "mtime": i.mtime,
                "blocked": i.blocked,
            }
            for i in items
        ],
    }


@app.get("/api/anemos/files/read")
async def api_files_read(
    path: str = Query(...),
    offset: Optional[int] = None,
    limit: Optional[int] = None,
):
    """Leggi un file (con paginazione opzionale)."""
    fs = _get_fs()
    r = fs.read(path, offset=offset, limit=limit)
    if not r.success:
        raise HTTPException(403 if "allowlist" in (r.error or "") else 404, r.error)
    return {
        "path": r.path,
        "content": r.content,
        "line_count": r.line_count,
    }


@app.post("/api/anemos/files/write")
async def api_files_write(body: WriteRequest):
    """Scrivi un file (con allowlist, backup, syntax check)."""
    fs = _get_fs()
    r = fs.write(body.path, body.content, force=body.force)
    if not r.success:
        status = 403 if "allowlist" in (r.error or "") or "protetta" in (r.error or "") else 400
        raise HTTPException(status, r.error)
    return {
        "success": True,
        "path": r.path,
        "is_new_file": r.is_new_file,
        "bytes_written": r.bytes_written,
        "backup_path": r.backup_path,
        "syntax_check": r.syntax_check,
    }


@app.get("/api/anemos/files/diff")
async def api_files_diff(path: str = Query(...)):
    """Vedi diff tra file attuale e ultimo backup."""
    fs = _get_fs()
    diff = fs.diff_backup(path)
    if diff is None:
        raise HTTPException(404, f"Nessun backup trovato per {path}")
    return {"path": path, "diff": diff}


@app.post("/api/anemos/files/rollback")
async def api_files_rollback(body: RollbackRequest):
    """Ripristina l'ultimo backup del file."""
    fs = _get_fs()
    ok = fs.rollback(body.path)
    if not ok:
        raise HTTPException(404, f"Rollback fallito per {body.path}")
    return {"success": True, "path": body.path}


@app.get("/api/anemos/audit")
async def api_audit(n: int = Query(50, ge=1, le=500)):
    """Restituisce le ultime N entries di audit FS."""
    fs = _get_fs()
    return {
        "count": min(n, len(fs.get_audit_log(n))),
        "entries": fs.get_audit_log(n),
    }


# ── WebSocket ───────────────────────────────────────────────────────────
@app.websocket("/ws/anemos")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    _ws_connections.append(websocket)
    try:
        # Messaggio iniziale di benvenuto
        await websocket.send_json({
            "type": "connected",
            "message": "Connesso a SPEACE Anemos",
            "model": _get_agent().config.model,
        })
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                continue
            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
            elif msg.get("type") == "typing":
                # Echo per indicatore "Anemos sta scrivendo"
                await websocket.send_json({
                    "type": "typing",
                    "user_message": msg.get("message", "")[:100],
                })
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in _ws_connections:
            _ws_connections.remove(websocket)


# ── Server runner ───────────────────────────────────────────────────────
_server_thread: Optional[threading.Thread] = None
_server_instance = None  # uvicorn.Server


def start_anemos_server(host: str = "127.0.0.1", port: int = 8787) -> bool:
    """Avvia il server Anemos in un thread daemon."""
    global _server_thread, _server_instance

    if _server_thread is not None and _server_thread.is_alive():
        _log.info(f"Anemos server già attivo su http://{host}:{port}")
        return False

    try:
        import uvicorn
        config = uvicorn.Config(
            app,
            host=host,
            port=port,
            log_level="warning",  # silenzioso per non inquinare log AGI
            access_log=False,
        )
        server = uvicorn.Server(config)
        _server_instance = server

        def _run():
            try:
                server.run()
            except Exception as exc:
                _log.error(f"Anemos server fallito: {exc}")

        _server_thread = threading.Thread(target=_run, name="Anemos-Server", daemon=True)
        _server_thread.start()
        _log.info(f"Anemos server avviato su http://{host}:{port}")
        return True
    except Exception as e:
        _log.error(f"Impossibile avviare Anemos: {e}")
        return False


def stop_anemos_server() -> None:
    """Ferma il server Anemos."""
    global _server_instance
    if _server_instance is not None:
        _server_instance.should_exit = True
        _server_instance = None
        _log.info("Anemos server fermato")


# ── Entry point standalone ──────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*50)
    print("  SPEACE ANEMOS - Server Standalone")
    print("  URL: http://127.0.0.1:8787")
    print("  Modello: " + create_default_config().__class__.__name__ + ": Kimi-K2.7-Code:cloud")
    print("="*50 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=8787, log_level="info")
