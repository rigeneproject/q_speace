"""Generate additional prediction-error samples with a decreasing trend."""

import json
import random
import time
from pathlib import Path

DATA_ROOT = Path(__file__).resolve().parent.parent / "data"

ERRORS_PATH = DATA_ROOT / "agi_runtime" / "prediction_errors.jsonl"


def enrich_prediction_errors():
    ERRORS_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Determine the last tick
    existing_lines = []
    last_tick = -1
    if ERRORS_PATH.exists():
        with ERRORS_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    existing_lines.append(line)
                    try:
                        obj = json.loads(line)
                        tick = obj.get("tick", -1)
                        if tick > last_tick:
                            last_tick = tick
                    except (json.JSONDecodeError, TypeError):
                        pass

    now = time.time()
    # Starting from ~0.25 error, gradually decrease to ~0.05 with noise
    start_error = 0.25
    end_error = 0.05

    with ERRORS_PATH.open("a", encoding="utf-8") as f:
        for i in range(100):
            tick = last_tick + 1 + i
            progress = (i + 1) / 100.0
            target = start_error - (start_error - end_error) * progress
            noise = random.uniform(-0.02, 0.02)
            error = max(0.0, min(1.0, target + noise))
            event = {
                "tick": tick,
                "prediction_error": round(error, 6),
                "timestamp": now + 5.0 * (i + 1),
            }
            f.write(json.dumps(event) + "\n")

    total = len(existing_lines) + 100
    print(f"Prediction errors enriched: {total} total (100 new)")


if __name__ == "__main__":
    enrich_prediction_errors()
