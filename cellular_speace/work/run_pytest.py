"""Final pytest with timeouts. Show summary."""
import json, subprocess, time
from pathlib import Path

REPORT_DIR = Path(r"C:\cellular_speace\reports\actions\06_test_results")
existing = json.loads((REPORT_DIR / "pytest_results.json").read_text(encoding="utf-8")) if (REPORT_DIR / "pytest_results.json").exists() else {"targets": []}

# Add a sweep with --collect-only to count total available tests
try:
    proc = subprocess.run(
        ["python", "-m", "pytest", "--collect-only", "-q", "tests/test_event_bus.py", "tests/test_digital_cell.py", "tests/test_cell_factory.py", "tests/cells"],
        cwd=r"C:\cellular_speace",
        capture_output=True, text=True, timeout=10,
    )
    existing["collect_only"] = {
        "exit": proc.returncode,
        "tail": proc.stdout.splitlines()[-10:],
    }
    print("collect-only exit={}".format(proc.returncode))
except subprocess.TimeoutExpired:
    existing["collect_only"] = {"timeout": True}

# Compute aggregate across all targets
total_ok = sum(1 for r in existing["targets"] if r.get("exit_code") == 0)
total_fail = sum(1 for r in existing["targets"] if r.get("exit_code") not in (0, None))
total_timeouts = sum(1 for r in existing["targets"] if r.get("timeout"))
existing["summary"] = {
    "targets": len(existing["targets"]),
    "passed": total_ok,
    "failed": total_fail,
    "timeouts": total_timeouts,
    "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
}
(REPORT_DIR / "pytest_results.json").write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
print("\nFinal summary: {}".format(existing["summary"]))
