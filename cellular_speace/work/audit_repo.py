import json, datetime
from pathlib import Path
from collections import defaultdict, Counter
import re

ROOT = Path(r"C:\cellular_speace")
out = ROOT/"reports"/"actions"/"01_repo_audit"
out.mkdir(parents=True, exist_ok=True)
now = datetime.datetime.now(datetime.UTC).isoformat()
report = {"generated_at_utc": now, "root": str(ROOT)}

EXCLUDE = (".git","__pycache__",".claude","root_link","reports","node_modules","work")

ext_counts, ext_sizes = Counter(), defaultdict(int)
total_size = 0
total_files = 0
for p in ROOT.rglob("*"):
    if not p.is_file():
        continue
    if any(seg in p.parts for seg in EXCLUDE):
        continue
    sz = p.stat().st_size
    total_size += sz
    total_files += 1
    ext = p.suffix.lower() or "(none)"
    ext_counts[ext] += 1
    ext_sizes[ext] += sz

MB = 1024 * 1024
report["totals"] = {"files": total_files, "size_mb": round(total_size / MB, 2)}
report["by_extension"] = {
    e: {"count": ext_counts[e], "size_mb": round(ext_sizes[e] / MB, 2)}
    for e in sorted(ext_counts, key=lambda x: -ext_counts[x])
}

py_files = [p for p in ROOT.rglob("*.py") if all(seg not in p.parts for seg in ("__pycache__",".claude","work"))]
py_total = sum(p.stat().st_size for p in py_files)
report["python"] = {
    "files": len(py_files),
    "size_mb": round(py_total / MB, 2),
    "largest": [
        {"path": str(p.relative_to(ROOT)), "kb": round(p.stat().st_size / 1024, 1)}
        for p in sorted(py_files, key=lambda x: -x.stat().st_size)[:15]
    ],
}
report["pydantic_legacy_class_config"] = [
    str(p.relative_to(ROOT))
    for p in py_files
    if re.search(r"^\s*class Config\s*:", p.read_text(encoding="utf-8", errors="ignore"), re.MULTILINE)
]
report["datetime_utcnow_usage"] = [
    str(p.relative_to(ROOT))
    for p in py_files
    if ("datetime.utcnow" in p.read_text(encoding="utf-8", errors="ignore"))
]
report["silent_except_pass"] = [
    str(p.relative_to(ROOT))
    for p in py_files
    if re.search(r"except[^\n]*:\s*\n\s*pass\b", p.read_text(encoding="utf-8", errors="ignore"))
]
report["tests"] = {"count": len([p for p in py_files if "tests" in p.parts])}

md_files = [p for p in ROOT.rglob("*.md") if all(seg not in p.parts for seg in (".claude","work","reports"))]
md_total = sum(p.stat().st_size for p in md_files)
report["markdown"] = {
    "files": len(md_files),
    "size_mb": round(md_total / MB, 2),
    "largest": [
        {"path": str(p.relative_to(ROOT)), "kb": round(p.stat().st_size / 1024, 1)}
        for p in sorted(md_files, key=lambda x: -x.stat().st_size)[:10]
    ],
}

large = []
for p in ROOT.rglob("*"):
    if not p.is_file():
        continue
    if any(seg in p.parts for seg in EXCLUDE):
        continue
    sz = p.stat().st_size
    if sz > 1_000_000:
        large.append({"path": str(p.relative_to(ROOT)), "mb": round(sz / MB, 2)})
report["large_files_over_1mb"] = sorted(large, key=lambda x: -x["mb"])[:25]
report["top_level_dirs"] = sorted([d.name for d in ROOT.iterdir() if d.is_dir() and not d.name.startswith(".")])

agi_ws = ROOT/"speace_agi_team"/"web_server.py"
if agi_ws.exists():
    txt = agi_ws.read_text(encoding="utf-8", errors="ignore")
    report["agi_broadcast_serial"] = ("for aid, agent in self.agents.items():" in txt) and ("agent.chat(message)" in txt)
    report["agi_broadcast_uses_gather"] = "asyncio.gather" in txt

(out/"audit_summary.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps({k: report[k] for k in ("totals","python","markdown","tests","agi_broadcast_serial","agi_broadcast_uses_gather")}, indent=2, ensure_ascii=False))
