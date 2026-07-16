"""Log embodiment sensor state to environment_state.jsonl for AGI readiness."""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

DATA_ROOT = Path(__file__).resolve().parent.parent / "data"
ENV_STATE_PATH = DATA_ROOT / "embodiment" / "environment_state.jsonl"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from speace_core.cellular_brain.embodiment.cyber_physical_sensor_array import (
        CyberPhysicalSensorArray,
    )
except ImportError as e:
    logger.warning("Failed to import CyberPhysicalSensorArray: %s", e)
    sys.exit(1)


def _normalize(value, min_val=0.0, max_val=100.0):
    if value is None:
        return None
    if max_val == min_val:
        return 0.0
    return max(0.0, min(1.0, (value - min_val) / (max_val - min_val)))


def extract_features(snapshot: dict) -> list[dict]:
    sensors = []

    cpu = snapshot.get("cpu", {})
    sensors.append({
        "name": "cpu_usage",
        "value": _normalize(cpu.get("usage_percent"), 0.0, 100.0),
        "raw": cpu.get("usage_percent"),
    })
    sensors.append({
        "name": "cpu_frequency",
        "value": _normalize(cpu.get("frequency_mhz"), 0.0, 5000.0),
        "raw": cpu.get("frequency_mhz"),
    })

    mem = snapshot.get("memory", {})
    sensors.append({
        "name": "memory_usage",
        "value": _normalize(mem.get("percent"), 0.0, 100.0),
        "raw": mem.get("percent"),
    })

    disk = snapshot.get("disk", {})
    drives = disk.get("drives", [])
    if drives:
        disk_pct = drives[0].get("percent", 0)
    else:
        disk_pct = 0
    sensors.append({
        "name": "disk_usage",
        "value": _normalize(disk_pct, 0.0, 100.0),
        "raw": disk_pct,
    })

    net = snapshot.get("network", {})
    max_net = 1_000_000_000
    sensors.append({
        "name": "network_in",
        "value": _normalize(net.get("bytes_received"), 0.0, float(max_net)),
        "raw": net.get("bytes_received"),
    })
    sensors.append({
        "name": "network_out",
        "value": _normalize(net.get("bytes_sent"), 0.0, float(max_net)),
        "raw": net.get("bytes_sent"),
    })

    proc = snapshot.get("process", {})
    sensors.append({
        "name": "process_count",
        "value": _normalize(proc.get("process_count"), 0.0, 500.0),
        "raw": proc.get("process_count"),
    })

    power = snapshot.get("power", {})
    sensors.append({
        "name": "battery",
        "value": _normalize(power.get("battery_percent"), 0.0, 100.0),
        "raw": power.get("battery_percent"),
    })

    temp = snapshot.get("temperature", {})
    sensors.append({
        "name": "temperature_cpu",
        "value": _normalize(temp.get("cpu_celsius"), 20.0, 100.0),
        "raw": temp.get("cpu_celsius"),
    })

    return sensors


def main():
    ENV_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)

    sensor_array = CyberPhysicalSensorArray()
    snapshot = sensor_array.read_all()

    sensors = extract_features(snapshot)

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sensors": sensors,
    }

    with ENV_STATE_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    logger.info("Logged %d sensors to %s", len(sensors), ENV_STATE_PATH)


if __name__ == "__main__":
    main()
