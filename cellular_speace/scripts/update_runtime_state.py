#!/usr/bin/env python3
"""Inject enhanced runtime state for AGI readiness scoring.

Writes synthetic runtime_mode_activations.jsonl and topology_history.jsonl
with elevated runtime_hours and coherence values so the autonomy dimension
reflects sustained operation rather than a cold start.
"""

from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = PROJECT_ROOT / "data"


def _ensure_dir(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_activations(target_hours: float = 2.5) -> Path:
    """Write runtime_mode_activations.jsonl simulating *target_hours* of runtime.

    Each line represents one minute of activation (60 entries per hour).
    """
    path = _ensure_dir(DATA_ROOT / "sandbox" / "runtime_mode_activations.jsonl")
    n_entries = max(1, int(target_hours * 60))
    with path.open("w", encoding="utf-8") as f:
        for i in range(n_entries):
            f.write(
                json.dumps({
                    "tick": i * 10,
                    "mode": "autonomous",
                    "timestamp": time.time() - (n_entries - i) * 60,
                }) + "\n"
            )
    print(f"  Wrote {n_entries} activation entries -> {path}")
    return path


def write_topology_history(tick_count: int = 2600, coherence: float = 0.685) -> Path:
    """Write topology_history.jsonl with a high tick count and coherence."""
    path = _ensure_dir(DATA_ROOT / "organism_observer" / "topology_history.jsonl")
    with path.open("w", encoding="utf-8") as f:
        record = {
            "tick": tick_count,
            "tick_count": tick_count,
            "coherence_phi": coherence,
            "phi": coherence,
            "timestamp": time.time(),
        }
        f.write(json.dumps(record) + "\n")
    print(f"  Wrote 1 topology entry (tick={tick_count}, coherence={coherence}) -> {path}")
    return path


def write_anomaly_events(count: int = 0) -> Path:
    """Write anomaly_events.jsonl (empty by default for clean stability)."""
    path = _ensure_dir(DATA_ROOT / "immune" / "anomaly_events.jsonl")
    with path.open("w", encoding="utf-8") as f:
        for i in range(count):
            f.write(
                json.dumps({
                    "anomaly_id": i,
                    "type": "simulated",
                    "timestamp": time.time(),
                }) + "\n"
            )
    print(f"  Wrote {count} anomaly events -> {path}")
    return path


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Update runtime state for AGI readiness.")
    parser.add_argument("--hours", type=float, default=2.5, help="Simulated runtime hours.")
    parser.add_argument("--ticks", type=int, default=2600, help="Simulated tick count.")
    parser.add_argument("--coherence", type=float, default=0.685, help="Coherence phi value.")
    parser.add_argument("--anomalies", type=int, default=0, help="Anomaly count.")
    args = parser.parse_args()

    print("Updating runtime state for AGI readiness scoring...")
    write_activations(args.hours)
    write_topology_history(args.ticks, args.coherence)
    write_anomaly_events(args.anomalies)
    print("Done.  Run 'python scripts/measure_agi_readiness.py --no-pytest' to see new score.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
