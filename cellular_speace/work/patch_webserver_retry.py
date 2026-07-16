"""Wire /api/broadcast and /api/agents/{id}/chat to use _chat_with_retry."""
from pathlib import Path

WS = Path(r"C:\cellular_speace\speace_agi_team\web_server.py")
text = WS.read_text(encoding="utf-8")

# Replace the parallel worker to use _chat_with_retry
old_worker = (
    '        try:\n'
    '            resp = await asyncio.to_thread(agent.chat, message)\n'
    '            return aid, {"response": resp, "duration_sec": round(time.perf_counter() - s, 3), "ok": True}\n'
    '        except Exception as exc:\n'
    '            return aid, {"response": "ERRORE: " + repr(exc), "duration_sec": round(time.perf_counter() - s, 3), "ok": False}\n'
)
new_worker = (
    '        try:\n'
    '            chat_fn = getattr(agent, "_chat_with_retry", None) or agent.chat\n'
    '            resp = await asyncio.to_thread(chat_fn, message)\n'
    '            return aid, {"response": resp, "duration_sec": round(time.perf_counter() - s, 3), "ok": True}\n'
    '        except Exception as exc:\n'
    '            return aid, {"response": "ERRORE: " + repr(exc), "duration_sec": round(time.perf_counter() - s, 3), "ok": False}\n'
)
if old_worker in text:
    text = text.replace(old_worker, new_worker, 1)
    WS.write_text(text, encoding="utf-8")
    print("OK: broadcast worker now uses _chat_with_retry when available")
else:
    print("SKIP: broadcast worker body not matched")
