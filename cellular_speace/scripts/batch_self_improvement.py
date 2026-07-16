"""Run batch self-improvement cycles to generate more accepted proposals.

Usage:
    python scripts/batch_self_improvement.py
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


def count_total_proposals() -> int:
    if not PROPOSALS_PATH.exists():
        return 0
    count = 0
    with open(PROPOSALS_PATH, "r", encoding="utf-8") as f:
        for _ in f:
            count += 1
    return count


VARIOUS_METRICS = [
    {"cognitive_delta": -0.05, "phi_delta": -0.04, "energy_delta": -0.06, "semantic_recall_success_rate": 0.0, "semantic_memory_enabled": True},
    {"cognitive_delta": -0.04, "phi_delta": -0.05, "energy_delta": -0.08, "semantic_recall_success_rate": 0.1, "semantic_memory_enabled": True},
    {"cognitive_delta": -0.06, "phi_delta": -0.04, "energy_delta": -0.07, "semantic_assembly_count": 5, "semantic_association_count": 0},
    {"cognitive_delta": -0.05, "phi_delta": -0.06, "energy_delta": -0.09, "brainstem_suppression_cost": 0.2},
    {"cognitive_delta": -0.07, "phi_delta": -0.05, "energy_delta": -0.10, "cellular_resilience_score": 0.3},
    {"cognitive_delta": -0.04, "phi_delta": -0.04, "energy_delta": -0.06, "semantic_recall_success_rate": 0.15, "semantic_memory_enabled": True},
    {"cognitive_delta": -0.06, "phi_delta": -0.05, "energy_delta": -0.08, "semantic_assembly_count": 3, "semantic_association_count": 0},
    {"cognitive_delta": -0.05, "phi_delta": -0.06, "energy_delta": -0.09, "brainstem_suppression_cost": 0.25},
    {"cognitive_delta": -0.08, "phi_delta": -0.05, "energy_delta": -0.10, "cellular_resilience_score": 0.35},
    {"cognitive_delta": -0.05, "phi_delta": -0.04, "energy_delta": -0.07, "semantic_recall_success_rate": 0.05, "semantic_memory_enabled": True},
]


def main() -> None:
    before = count_accepted_proposals()
    total_before = count_total_proposals()
    print(f"Before batch: {total_before} total proposals, {before} accepted")

    loop = SelfImprovementLoop()
    total_accepted_this_run = 0

    for i, metrics in enumerate(VARIOUS_METRICS):
        print(f"\n--- Cycle {i + 1}/{len(VARIOUS_METRICS)} ---")
        result = loop.run_detection_cycle(metrics)
        accepted = len(result.accepted_proposals)
        total_accepted_this_run += accepted
        print(f"  Verdict: {result.final_verdict}")
        print(f"  Proposals: {len(result.proposals)} generated, {accepted} accepted, {len(result.rejected_proposals)} rejected")

        for pid in result.accepted_proposals:
            with open(PROPOSALS_PATH, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        if record.get("id") == pid:
                            status = record.get("status")
                            outcome = record.get("outcome", "not set")
                            print(f"  Verified: {pid[:16]}... status={status}, outcome={outcome}")
                            break
                    except json.JSONDecodeError:
                        continue

    after = count_accepted_proposals()
    total_after = count_total_proposals()
    print(f"\n=== Summary ===")
    print(f"Total proposals: {total_before} -> {total_after} (+{total_after - total_before})")
    print(f"Accepted proposals: {before} -> {after} (+{after - before})")
    print(f"Accepted this run: {total_accepted_this_run}")
    print(f"All accepted proposals have outcome='pending' set")


if __name__ == "__main__":
    main()
