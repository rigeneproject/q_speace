"""Run a single self-improvement detection cycle and verify persistence.

Usage:
    python scripts/run_self_improvement_cycle.py
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from speace_core.cellular_brain.self_improvement import SelfImprovementLoop


DATA_ROOT = PROJECT_ROOT / "data" / "self_improvement"
PROPOSALS_PATH = DATA_ROOT / "proposals.jsonl"


def count_accepted_proposals() -> int:
    if not PROPOSALS_PATH.exists():
        return 0
    count = 0
    with open(PROPOSALS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                if record.get("status") == "accepted":
                    count += 1
            except json.JSONDecodeError:
                continue
    return count


def main() -> None:
    print(f"Accepted proposals before cycle: {count_accepted_proposals()}")

    loop = SelfImprovementLoop()
    metrics = {
        "semantic_association_score": 0.0,
        "assembly_count": 3,
        "association_count": 0,
        "recall_diversity": 0.0,
        "memory_integration": 0.0,
    }

    result = loop.run_detection_cycle(metrics)

    print(f"Cycle ID: {result.cycle_id}")
    print(f"Final verdict: {result.final_verdict}")
    print(f"Proposals generated: {len(result.proposals)}")
    print(f"Proposals accepted: {len(result.accepted_proposals)}")
    print(f"Proposals rejected: {len(result.rejected_proposals)}")

    accepted_after = count_accepted_proposals()
    print(f"Accepted proposals after cycle: {accepted_after}")
    print(f"Accepted > 0: {accepted_after > 0}")

    if result.accepted_proposals:
        for pid in result.accepted_proposals:
            with open(PROPOSALS_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        if record.get("id") == pid:
                            print(f"  {pid}: status={record.get('status')}")
                            break
                    except json.JSONDecodeError:
                        continue


if __name__ == "__main__":
    main()
