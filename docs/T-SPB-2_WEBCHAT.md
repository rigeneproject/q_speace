# T-SPB-2-WEBCHAT — browser chat interface for Qwen sidecar

**Status**: SHIPPED — single-page chat UI backed by Qwen2.5-3B-Instruct NF4 sidecar.

## What this is

A thin FastAPI app (`spiking_brain_server/webchat_server.py`) plus a
single-page HTML UI (`webchat_index.html`) that lets you drive the
Qwen instruction sidecar from a browser. The interface shows
**text + confidence + belief vector + latency + sidecar status**, with
a `coherence_phi` knob and `n_tokens` slider.

The chat does NOT route through `SpikingBrainCortex.tick()`. It is a
**manual testing surface for the raw sidecar contract**. To exercise
the full Sevo/coherence/ILF pipeline, use `qspace brain tick` from the
CLI; that runs `cortex.tick()` and produces `CortexReport`.

## How to run

Two services must be up:

1. **Qwen sidecar** (port 8002) — already running if you followed
   T-SPB-2-INSTRUCT validation.
2. **Webchat server** (port 8088):

```bash
wsl -d Ubuntu -- bash -c 'source ~/.venvs/spikingbrain/bin/activate \
  && cd /mnt/c/Users/rober/Desktop/Q-SPEACE/q_speace \
  && python -m spiking_brain_server.webchat_server'
```

Then open in a browser:
- **From WSL**: `http://127.0.0.1:8088/`
- **From Windows**: `http://localhost:8088/` (Windows 11 auto-maps WSL ports)

## Endpoints

| route | method | purpose |
| --- | --- | --- |
| `/` | GET | HTML chat UI |
| `/api/health` | GET | sidecar health snapshot |
| `/api/chat` | POST | send a message, get assistant reply + history |
| `/api/reset` | POST | clear a session |
| `/api/sessions` | GET | list active session IDs |

## Schema

```json
POST /api/chat
{
  "session_id": "optional, auto-generated if absent",
  "message": "free text",
  "n_tokens": 64,
  "coherence_phi": 1.0
}
```

Response:
```json
{
  "session_id": "33b61bc0fb284510babd122bd6a87a5f",
  "assistant": {
    "role": "assistant",
    "text": "...",
    "confidence": 0.694,
    "belief": [0.45, 0.07, 0.50],
    "sevo": null,
    "energy_w": null,
    "approved": null,
    "latency_s": 1.81,
    "ts": 1787470459.95
  },
  "history": [ {role, text, ts, ...}, ... ]
}
```

`sevo`, `energy_w`, `approved` are **always null** in this surface
because they are computed by `SpikingBrainCortex.tick()`, not by the
raw sidecar. To see them populated, send the same prompt through
`qspace brain tick "..."` with `Q_SPEACE_BRAIN_ENDPOINT` set.

## Session persistence

- In-memory deque (maxlen 32 turns) per session, keyed by `session_id`.
- On shutdown or after 1 h idle, the session is snapshotted to
  `spiking_brain_server/webchat_history/<sid>.jsonl`.
- History sent to the sidecar is capped at the **last 8 turns** to
  match the contract.

## Validation performed

| test | result |
| --- | --- |
| `GET /` | 200, serves HTML |
| `GET /api/health` | returns `{"ready":true,"model":"Qwen/Qwen2.5-3B-Instruct"}` |
| `POST /api/chat` (turn 1) | Italian reply, conf 0.914, belief [0.46, 0.04, 0.50] |
| `POST /api/chat` (turn 2, same session) | model recalls name "Roberto", conf 0.694, history_len=4 |
| WSL → Windows browser mapping | works on Windows 11 (auto port-forward) |

## Files added

- `spiking_brain_server/webchat_server.py` — FastAPI app, ~140 LOC
- `spiking_brain_server/webchat_index.html` — single-page UI, dark/light
  via `prefers-color-scheme`, belief rendered as colored bar
- `spiking_brain_server/webchat_history/` — created at runtime, JSONL
  snapshots per session

## Caveats / known limits

- **No system prompt customization** — Qwen's instruction template is
  used as-is. If you want a custom persona, edit
  `instruction_server.py` (the `apply_chat_template` call) and restart.
- **Single sidecar only** — the chat hardcodes
  `SIDECAR_URL = "http://127.0.0.1:8002"`. To point at a different
  sidecar, set the `Q_SPEACE_SIDECAR_URL` env var (TODO: read it in
  `webchat_server.py`).
- **No streaming** — replies arrive atomically. Qwen 3B at 1–3 s/prompt
  is fast enough that this is fine for manual testing.
- **Sevo/coherence gates not applied** — by design. The browser
  surface is for *raw LLM behaviour* testing; use the CLI for the
  full pipeline.

## Next step (proposed)

- Read `Q_SPEACE_SIDECAR_URL` from env in `webchat_server.py`.
- Add an `/api/tick` route that wraps `SpikingBrainCortex.tick()` so
  the browser can also see sevo/energy/approved.
- Add a "thinking trace" panel showing per-token greedy probabilities
  (already available in the sidecar's `metadata`).