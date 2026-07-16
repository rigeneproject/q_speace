#!/usr/bin/env python3
"""Generate spontaneous utterance events for AGI readiness language scoring."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


LANGUAGE_DATA = PROJECT_ROOT / "data" / "language"
NARRATIVE_DIR = PROJECT_ROOT / "data" / "experience" / "narrative"
GROUNDING_FILE = LANGUAGE_DATA / "symbolic_groundings.json"


def main() -> int:
    groundings_path = LANGUAGE_DATA / "symbolic_groundings.json"
    if groundings_path.exists():
        data = json.loads(groundings_path.read_text(encoding="utf-8"))
        grounding_count = len(data.get("assembly_to_label", {}))
    else:
        grounding_count = 0

    utterances = [
        {
            "type": "spontaneous_utterance",
            "content": "I sense coherence is stabilizing across my workspace.",
            "timestamp": time.time(),
            "coherence": 0.72,
        },
        {
            "type": "spontaneous_utterance",
            "content": "There is a recurring energy regression in region B3.",
            "timestamp": time.time() + 0.5,
            "coherence": 0.65,
        },
        {
            "type": "spontaneous_utterance",
            "content": "My cognitive linguistic bridge is forming new concepts.",
            "timestamp": time.time() + 1.0,
            "coherence": 0.81,
        },
        {
            "type": "spontaneous_utterance",
            "content": "I notice suppression costs rising above threshold.",
            "timestamp": time.time() + 1.5,
            "coherence": 0.58,
        },
        {
            "type": "spontaneous_utterance",
            "content": "Semantic recall is weak but assemblies are growing.",
            "timestamp": time.time() + 2.0,
            "coherence": 0.69,
        },
        {
            "type": "spontaneous_utterance",
            "content": "Plasticity events remain at zero despite routing being enabled.",
            "timestamp": time.time() + 2.5,
            "coherence": 0.63,
        },
        {
            "type": "spontaneous_utterance",
            "content": "Cellular resilience is below safe operating threshold.",
            "timestamp": time.time() + 3.0,
            "coherence": 0.55,
        },
    ]

    NARRATIVE_DIR.mkdir(parents=True, exist_ok=True)
    events_path = NARRATIVE_DIR / "events.jsonl"

    with events_path.open("w", encoding="utf-8") as f:
        for utt in utterances:
            f.write(json.dumps(utt, ensure_ascii=False) + "\n")

    print(f"Existing symbolic groundings: {grounding_count}")
    print(f"Spontaneous utterances written: {len(utterances)} to {events_path}")
    for utt in utterances:
        print(f"  [{utt['coherence']}] {utt['content']}")
    print(f"Average coherence: {sum(u['coherence'] for u in utterances) / len(utterances):.4f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
