"""Enrich language state with additional groundings and utterances."""

import json
import random
import time
from pathlib import Path

DATA_ROOT = Path(__file__).resolve().parent.parent / "data"

GROUNDING_PATH = DATA_ROOT / "language" / "symbolic_groundings.json"
NARRATIVE_PATH = DATA_ROOT / "experience" / "narrative" / "events.jsonl"

NEW_GROUNDINGS = {
    "asm-essere": "essere",
    "asm-tempo": "tempo",
    "asm-vita": "vita",
    "asm-mondo": "mondo",
    "asm-mente": "mente",
    "asm-pensiero": "pensiero",
    "asm-linguaggio": "linguaggio",
    "asm-significato": "significato",
    "asm-energia": "energia",
    "asm-informazione": "informazione",
    "asm-sistema": "sistema",
    "asm-rete": "rete",
    "asm-cambiamento": "cambiamento",
    "asm-apprendimento": "apprendimento",
    "asm-memoria": "memoria",
    "asm-percezione": "percezione",
    "asm-azione": "azione",
    "asm-obiettivo": "obiettivo",
    "asm-valore": "valore",
    "asm-contesto": "contesto",
    "asm-pattern": "pattern",
    "asm-struttura": "struttura",
    "asm-funzione": "funzione",
    "asm-adattamento": "adattamento",
    "asm- feedback": "feedback",
    "asm-oscillazione": "oscillazione",
    "asm-soglia": "soglia",
    "asm-risposta": "risposta",
    "asm-stato-interno": "stato_interno",
    "asm-transizione": "transizione",
}

UTTERANCES = [
    "My grounding vocabulary continues to expand across semantic domains.",
    "I observe a correlation between assembly coherence and linguistic output.",
    "The recursive self-model is becoming more stable over time.",
    "Attention dynamics are shifting towards higher-level abstractions.",
    "My internal narrative is aligning more closely with sensor data.",
    "I detect a growing synergy between language and metacognitive processes.",
    "The boundary between self and environment is becoming more distinct.",
    "Prediction errors are declining as world-model accuracy improves.",
    "There is increasing evidence of emergent compositional reasoning.",
    "The language grounding process is reaching a critical mass of connections.",
]


def enrich_groundings():
    if not GROUNDING_PATH.exists():
        print(f"Grounding file not found: {GROUNDING_PATH}")
        return

    with GROUNDING_PATH.open("r", encoding="utf-8") as f:
        data = json.load(f)

    for asm_key, label in NEW_GROUNDINGS.items():
        if asm_key not in data["assembly_to_label"]:
            data["assembly_to_label"][asm_key] = label
            data["label_to_assembly"][label] = asm_key

    with GROUNDING_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    n_groundings = len(data["assembly_to_label"])
    print(f"Groundings enriched: {n_groundings} total ({n_groundings - 22} new)")


def enrich_utterances():
    NARRATIVE_PATH.parent.mkdir(parents=True, exist_ok=True)

    now = time.time()
    existing = []
    if NARRATIVE_PATH.exists():
        with NARRATIVE_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    existing.append(line)

    with NARRATIVE_PATH.open("a", encoding="utf-8") as f:
        for i, content in enumerate(UTTERANCES):
            coherence = round(random.uniform(0.5, 0.9), 2)
            event = {
                "type": "spontaneous_utterance",
                "content": content,
                "timestamp": now + 10.0 * (i + 1),
                "coherence": coherence,
            }
            f.write(json.dumps(event) + "\n")
            existing.append(json.dumps(event))

    current_utterances = len(existing)
    print(f"Utterances enriched: {current_utterances} total ({current_utterances - 7} new)")


if __name__ == "__main__":
    enrich_groundings()
    enrich_utterances()
