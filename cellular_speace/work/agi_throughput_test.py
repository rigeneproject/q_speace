"""Verifica: 1) import web_server e agent_base OK; 2) AgentConfig.max_tokens=8192; 3) /api/broadcast parallelo."""
import json, ast, re
from pathlib import Path

REPORT_DIR = Path(r"C:\cellular_speace\reports\actions\03_agi_throughput")
REPORT_DIR.mkdir(parents=True, exist_ok=True)
results = {"tests": {}}

def add(name, ok, detail):
    results["tests"][name] = {"ok": bool(ok), "detail": str(detail)}
    print("[{}] {}: {}".format("OK" if ok else "FAIL", name, detail))

# 1) Static checks
WS = Path(r"C:\cellular_speace\speace_agi_team\web_server.py")
text = WS.read_text(encoding="utf-8")
add("broadcast_uses_to_thread", "asyncio.to_thread(chat_fn, message)" in text, "asyncio.to_thread present in worker")
add("broadcast_uses_gather", "await asyncio.gather(*(_one" in text, "asyncio.gather used to dispatch in parallel")
add("broadcast_returns_total_sec", "total_sec" in text and "agent_count" in text, "per-agent and total metrics exposed")

CF = Path(r"C:\cellular_speace\speace_agi_team\config.py")
ct = CF.read_text(encoding="utf-8")
m = re.search(r"max_tokens\s*:\s*int\s*=\s*(\d+)", ct)
add("max_tokens_default", bool(m and int(m.group(1)) >= 8192), "max_tokens_default={}".format(m.group(1) if m else "none"))

AB = Path(r"C:\cellular_speace\speace_agi_team\agent_base.py")
at = AB.read_text(encoding="utf-8")
add("retry_helper_present", "_chat_with_retry" in at and "_looks_truncated" in at, "AgentBase retry+truncation detection")

# 2) Runtime import checks
try:
    import speace_agi_team.config as c
    cfg = c.AgentConfig()
    add("runtime_max_tokens", cfg.max_tokens == 8192, "runtime cfg.max_tokens={}".format(cfg.max_tokens))
except Exception as e:
    add("runtime_max_tokens", False, repr(e))

try:
    import speace_agi_team.agent_base as ab
    has_retry = hasattr(ab.AgentBase, "_chat_with_retry")
    has_looks = hasattr(ab.AgentBase, "_looks_truncated")
    add("runtime_retry", has_retry and has_looks, "retry={} looks={}".format(has_retry, has_looks))
except Exception as e:
    add("runtime_retry", False, repr(e))

# 3) Smoke: web_server module imports and FastAPI app can be built (without starting uvicorn)
try:
    import speace_agi_team.web_server as ws_mod
    add("web_server_module_imports", ws_mod.app is not None, "FastAPI app={}".format(type(ws_mod.app).__name__))
except Exception as e:
    add("web_server_module_imports", False, repr(e))

# 4) Inspect /api/broadcast route signature
try:
    import speace_agi_team.web_server as ws_mod
    routes = [(r.path, getattr(r, "methods", None)) for r in ws_mod.app.routes if hasattr(r, "path")]
    found = any(p == "/api/broadcast" for p, _ in routes)
    add("broadcast_route_present", found, "broadcast_route_found={}".format(found))
except Exception as e:
    add("broadcast_route_present", False, repr(e))

results["summary"] = {
    "total": len(results["tests"]),
    "passed": sum(1 for v in results["tests"].values() if v["ok"]),
    "failed": sum(1 for v in results["tests"].values() if not v["ok"]),
}
(REPORT_DIR / "agi_throughput.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
print("\nSummary: {}".format(results["summary"]))
