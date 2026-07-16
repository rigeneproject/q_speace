#!/usr/bin/env python3
"""Run LimitationDetector and persist signals + diagnoses for AGI readiness scoring."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from speace_core.cellular_brain.self_improvement.limitation_detector import (
    LimitationDetector,
)

DATA_SELF_IMPROVEMENT = PROJECT_ROOT / "data" / "self_improvement"


def main() -> int:
    detector = LimitationDetector()

    metrics = {
        "coherence_phi": 0.6,
        "mean_energy": 0.7,
        "noise_level": 0.2,
        "tick": 1000,
        "cognitive_delta": -0.05,
        "phi_delta": -0.04,
        "energy_delta": -0.06,
        "semantic_recall_success_rate": 0.15,
        "semantic_memory_enabled": True,
        "semantic_assembly_count": 5,
        "semantic_association_count": 0,
        "region_signal_routing_enabled": True,
        "regional_signal_flow_score": 0.0,
        "inter_region_plasticity_enabled": True,
        "inter_region_plasticity_events": 0,
        "brainstem_suppression_cost": 0.25,
        "cellular_resilience_score": 0.35,
        "benchmark_stagnation_score": 0.85,
    }

    signals = detector.detect_from_metrics(metrics)
    diagnoses = detector.aggregate_signals(signals)

    DATA_SELF_IMPROVEMENT.mkdir(parents=True, exist_ok=True)
    signals_path = DATA_SELF_IMPROVEMENT / "limitation_signals.jsonl"
    diagnoses_path = DATA_SELF_IMPROVEMENT / "diagnoses.jsonl"

    with signals_path.open("w", encoding="utf-8") as sf, \
         diagnoses_path.open("w", encoding="utf-8") as df:
        for sig in signals:
            record = {
                "timestamp": sig.detected_at,
                "source": sig.source,
                "signal_type": sig.category,
                "severity": round(sig.severity, 4),
                "details": {
                    "id": sig.id,
                    "confidence": sig.confidence,
                    "description": sig.description,
                    "evidence": sig.evidence,
                },
            }
            sf.write(json.dumps(record, ensure_ascii=False) + "\n")

        for diag in diagnoses:
            record = {
                "timestamp": time.time(),
                "category": diag.primary_category,
                "primary_category": diag.primary_category,
                "description": diag.root_cause_hypothesis,
                "metrics": {
                    "recurrence_score": round(diag.recurrence_score, 4),
                    "urgency_score": round(diag.urgency_score, 4),
                    "confidence": round(diag.confidence, 4),
                    "affected_modules": diag.affected_modules,
                    "recommended_action": diag.recommended_action_type,
                },
                "id": diag.id,
            }
            df.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Signals written: {len(signals)} to {signals_path}")
    print(f"Diagnoses written: {len(diagnoses)} to {diagnoses_path}")
    for diag in diagnoses:
        print(f"  Diagnosis: {diag.primary_category} (urgency={diag.urgency_score:.4f}, "
              f"action={diag.recommended_action_type})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
