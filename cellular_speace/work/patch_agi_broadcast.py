"""Patch /api/broadcast to be parallel via asyncio.to_thread and add per-agent duration metrics."""
import re
from pathlib import Path

WS = Path(r"C:\cellular_speace\speace_agi_team\web_server.py")
text = WS.read_text(encoding="utf-8")

old = (
    '@app.post("/api/broadcast")\n'
    'async def api_broadcast(body: BroadcastRequest):\n'
    '    message = body.message\n'
    '    if not message:\n'
    '        raise HTTPException(400, "Message is required")\n'
    '    responses = {}\n'
    '    for aid, agent in _agents.items():\n'
    '        resp = agent.chat(message)\n'
    '        responses[aid] = resp\n'
    '    await _broadcast({\n'
    '        "type": "broadcast",\n'
    '        "message": message,\n'
    '        "responses": responses,\n'
    '    })\n'
    '    return {"responses": responses}\n'
)

new = (
    '@app.post("/api/broadcast")\n'
    'async def api_broadcast(body: BroadcastRequest):\n'
    '    """Send the same message to every agent in parallel.\n'
    '\n'
    '    Uses asyncio.to_thread to offload each blocking LLM chat to a worker\n'
    '    thread, so the 20-agent broadcast finishes in roughly the time of a\n'
    '    single chat rather than 20x serial. Per-agent timing is included in\n'
    '    the response payload so callers can compute per-agent latency.\n'
    '    """\n'
    '    message = body.message\n'
    '    if not message:\n'
    '        raise HTTPException(400, "Message is required")\n'
    '    t0 = time.perf_counter()\n'
    '\n'
    '    async def _one(aid: str, agent):\n'
    '        s = time.perf_counter()\n'
    '        try:\n'
    '            resp = await asyncio.to_thread(agent.chat, message)\n'
    '            return aid, {"response": resp, "duration_sec": round(time.perf_counter() - s, 3), "ok": True}\n'
    '        except Exception as exc:\n'
    '            return aid, {"response": "ERRORE: " + repr(exc), "duration_sec": round(time.perf_counter() - s, 3), "ok": False}\n'
    '\n'
    '    pairs = await asyncio.gather(*(_one(aid, agent) for aid, agent in _agents.items()))\n'
    '    responses = {aid: payload for aid, payload in pairs}\n'
    '    total_sec = round(time.perf_counter() - t0, 3)\n'
    '    await _broadcast({\n'
    '        "type": "broadcast",\n'
    '        "message": message,\n'
    '        "responses": responses,\n'
    '        "total_sec": total_sec,\n'
    '        "agent_count": len(responses),\n'
    '    })\n'
    '    return {"responses": responses, "total_sec": total_sec, "agent_count": len(responses)}\n'
)

if old in text:
    text = text.replace(old, new, 1)
    WS.write_text(text, encoding="utf-8")
    print("OK: patched /api/broadcast to use asyncio.to_thread + gather + per-agent duration metrics")
else:
    print("SKIP: /api/broadcast body did not match the expected template (already patched or modified)")
