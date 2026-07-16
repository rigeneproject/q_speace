"""Migrate existing proposals: update status from cycle verdicts in cycles.jsonl.

Reads cycles.jsonl to find accepted/rejected proposal IDs, then updates
proposals.jsonl to set matching status fields.
"""

import json
from collections import Counter
from pathlib import Path

CYCLES_PATH = Path("data/self_improvement/cycles.jsonl")
PROPOSALS_PATH = Path("data/self_improvement/proposals.jsonl")


def load_cycle_verdicts() -> tuple[set[str], set[str]]:
    """Return (accepted_ids, rejected_ids) from all cycles."""
    accepted: set[str] = set()
    rejected: set[str] = set()
    if not CYCLES_PATH.exists():
        return accepted, rejected
    with open(CYCLES_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            for pid in record.get("accepted_proposals") or []:
                accepted.add(pid)
            for pid in record.get("rejected_proposals") or []:
                rejected.add(pid)
    return accepted, rejected


def main() -> None:
    accepted_ids, rejected_ids = load_cycle_verdicts()
    print(f"Cycle verdicts: {len(accepted_ids)} accepted, {len(rejected_ids)} rejected")

    if not PROPOSALS_PATH.exists():
        print("No proposals.jsonl found")
        return

    lines = []
    stats: Counter[str] = Counter()
    with open(PROPOSALS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            pid = record.get("id", "")
            old_status = record.get("status", "")
            if pid in accepted_ids:
                record["status"] = "accepted"
            elif pid in rejected_ids:
                record["status"] = "rejected"
            new_status = record.get("status", "")
            if old_status != new_status:
                stats[new_status] += 1
                stats["total_updated"] += 1
            lines.append(json.dumps(record, ensure_ascii=False))

    if stats["total_updated"] > 0:
        with open(PROPOSALS_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

    print(f"Total proposals read: {len(lines)}")
    print(f"Updated to accepted: {stats.get('accepted', 0)}")
    print(f"Updated to rejected: {stats.get('rejected', 0)}")
    print(f"Total updated: {stats.get('total_updated', 0)}")


if __name__ == "__main__":
    main()
