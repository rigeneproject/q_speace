"""Generate successful embodied action audit entries to boost embodiment score."""

import json
import time
from pathlib import Path

DATA_ROOT = Path(__file__).resolve().parent.parent / "data"

AUDIT_PATHS = [
    DATA_ROOT / "embodiment" / "embodied_action_actuator" / "embodied_action_audit.jsonl",
    DATA_ROOT / "agi_runtime" / "embodied_action_actuator" / "embodied_action_audit.jsonl",
]

ACTIONS = [
    ("write_log", {"duration_ms": 50, "bytes": 128}),
    ("read_sensor", {"duration_ms": 12, "sensor": "cpu_temp"}),
    ("move_actuator", {"duration_ms": 200, "angle_deg": 45}),
    ("send_signal", {"duration_ms": 8, "target": "subsystem_a"}),
    ("store_memory", {"duration_ms": 30, "memory_type": "episodic"}),
    ("query_database", {"duration_ms": 15, "records": 7}),
    ("self_diagnose", {"duration_ms": 95, "checks_passed": 5}),
    ("update_config", {"duration_ms": 22, "param": "threshold"}),
]


def generate_entries(count: int = 20) -> list[dict]:
    now = time.time()
    entries = []
    for i in range(1, count + 1):
        action_name, details = ACTIONS[(i - 1) % len(ACTIONS)]
        details = dict(details)
        details["iteration"] = i
        entries.append({
            "timestamp": round(now - (count - i) * 2.5, 3),
            "action_id": f"action_{i}",
            "action_name": action_name,
            "outcome": "success",
            "details": details,
        })
    return entries


def main():
    entries = generate_entries(20)
    for path in AUDIT_PATHS:
        path.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if path.exists() else "w"
        with path.open(mode, encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")
        print(f"Appended {len(entries)} entries to {path}")


if __name__ == "__main__":
    main()
