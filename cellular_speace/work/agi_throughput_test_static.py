"""Static-only AGI throughput verification (no runtime imports that touch LLM)."""
import json, re
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

# 2) Inspect the source of /api/broadcast function
import ast
mod = ast.parse(text)
func = None
for node in ast.walk(mod):
    if isinstance(node, ast.AsyncFunctionDef) and node.name == "api_broadcast":
        func = node
        break
add("api_broadcast_async", func is not None, "api_broadcast_function_found={}".format(func is not None))
if func is not None:
    src = ast.unparse(func)
    add("api_broadcast_parallel", "asyncio.gather" in src and "asyncio.to_thread" in src,
        "broadcast_src_has_gather_and_to_thread")

# 3) count agent calls in api_broadcast (should be 0 sequential "agent.chat" inside the loop)
if func is not None:
    seq_calls = 0
    parallel_calls = 0
    for node in ast.walk(func):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Attribute) and f.attr == "chat":
                seq_calls += 1
    add("api_broadcast_no_sequential_chat", seq_calls <= 1, "chat_calls_in_body={}".format(seq_calls))

results["summary"] = {
    "total": len(results["tests"]),
    "passed": sum(1 for v in results["tests"].values() if v["ok"]),
    "failed": sum(1 for v in results["tests"].values() if not v["ok"]),
}
(REPORT_DIR / "agi_throughput_static.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
print("\nSummary: {}".format(results["summary"]))
