#!/usr/bin/env python3
"""Generate additional metacognition limitation signals and diagnoses.

Appends 15 new signals (10→25) and 10 new diagnoses (10→20) to the
corresponding JSONL files in data/self_improvement/.
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

DATA_ROOT = Path(__file__).resolve().parents[1] / "data" / "self_improvement"
SIGNALS_PATH = DATA_ROOT / "limitation_signals.jsonl"
DIAGNOSES_PATH = DATA_ROOT / "diagnoses.jsonl"


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _unix_ts() -> float:
    return time.time()


NEW_SIGNALS = [
    {
        "timestamp": _ts(),
        "source": "metrics",
        "signal_type": "attention_fragmentation",
        "severity": 0.55,
        "details": {
            "id": f"lim-{uuid.uuid4().hex[:8]}",
            "confidence": 0.72,
            "description": "Attention span fragmented across multiple regions",
            "evidence": {"attention_span": 0.45, "region_switches": 12},
        },
    },
    {
        "timestamp": _ts(),
        "source": "metrics",
        "signal_type": "memory_decay_accelerated",
        "severity": 0.6,
        "details": {
            "id": f"lim-{uuid.uuid4().hex[:8]}",
            "confidence": 0.68,
            "description": "Memory trace decay rate exceeds normal bounds",
            "evidence": {"decay_rate": 0.72, "baseline": 0.3},
        },
    },
    {
        "timestamp": _ts(),
        "source": "metrics",
        "signal_type": "cross_region_lag",
        "severity": 0.45,
        "details": {
            "id": f"lim-{uuid.uuid4().hex[:8]}",
            "confidence": 0.8,
            "description": "Signal propagation delay between regions increasing",
            "evidence": {"avg_lag_ms": 340, "threshold_ms": 200},
        },
    },
    {
        "timestamp": _ts(),
        "source": "metrics",
        "signal_type": "goal_drift",
        "severity": 0.5,
        "details": {
            "id": f"lim-{uuid.uuid4().hex[:8]}",
            "confidence": 0.65,
            "description": "Task objective drifting from original goal",
            "evidence": {"goal_alignment": 0.6, "original_goal": "T44"},
        },
    },
    {
        "timestamp": _ts(),
        "source": "metrics",
        "signal_type": "prediction_uncertainty_spike",
        "severity": 0.7,
        "details": {
            "id": f"lim-{uuid.uuid4().hex[:8]}",
            "confidence": 0.82,
            "description": "Prediction uncertainty spiked above threshold",
            "evidence": {"uncertainty": 0.78, "threshold": 0.5},
        },
    },
    {
        "timestamp": _ts(),
        "source": "metrics",
        "signal_type": "energy_inefficiency",
        "severity": 0.5,
        "details": {
            "id": f"lim-{uuid.uuid4().hex[:8]}",
            "confidence": 0.7,
            "description": "Energy per operation above efficient threshold",
            "evidence": {"energy_per_op": 1.8, "efficient_threshold": 1.0},
        },
    },
    {
        "timestamp": _ts(),
        "source": "metrics",
        "signal_type": "homeostasis_imbalance",
        "severity": 0.55,
        "details": {
            "id": f"lim-{uuid.uuid4().hex[:8]}",
            "confidence": 0.75,
            "description": "Regional homeostasis indicators out of balance",
            "evidence": {"ca2_level": 1.4, "atp_level": 0.6},
        },
    },
    {
        "timestamp": _ts(),
        "source": "metrics",
        "signal_type": "synaptic_drift",
        "severity": 0.4,
        "details": {
            "id": f"lim-{uuid.uuid4().hex[:8]}",
            "confidence": 0.78,
            "description": "Synaptic weights drifting from optimal configuration",
            "evidence": {"weight_drift": 0.35, "optimal_range": "[0.2, 0.8]"},
        },
    },
    {
        "timestamp": _ts(),
        "source": "metrics",
        "signal_type": "recall_latency_exceeded",
        "severity": 0.65,
        "details": {
            "id": f"lim-{uuid.uuid4().hex[:8]}",
            "confidence": 0.85,
            "description": "Semantic recall latency exceeds acceptable limit",
            "evidence": {"latency_ms": 520, "limit_ms": 300},
        },
    },
    {
        "timestamp": _ts(),
        "source": "metrics",
        "signal_type": "concept_interference",
        "severity": 0.5,
        "details": {
            "id": f"lim-{uuid.uuid4().hex[:8]}",
            "confidence": 0.7,
            "description": "Cross-concept interference detected in semantic memory",
            "evidence": {"interference_score": 0.48, "overlap_ratio": 0.3},
        },
    },
    {
        "timestamp": _ts(),
        "source": "metrics",
        "signal_type": "temporal_coherence_loss",
        "severity": 0.6,
        "details": {
            "id": f"lim-{uuid.uuid4().hex[:8]}",
            "confidence": 0.74,
            "description": "Temporal ordering of events losing coherence",
            "evidence": {"temporal_score": 0.42, "expected": 0.8},
        },
    },
    {
        "timestamp": _ts(),
        "source": "metrics",
        "signal_type": "planning_depth_limited",
        "severity": 0.55,
        "details": {
            "id": f"lim-{uuid.uuid4().hex[:8]}",
            "confidence": 0.8,
            "description": "Multi-step planning depth below operational requirement",
            "evidence": {"max_depth": 2, "required_depth": 5},
        },
    },
    {
        "timestamp": _ts(),
        "source": "metrics",
        "signal_type": "self_model_inconsistency",
        "severity": 0.45,
        "details": {
            "id": f"lim-{uuid.uuid4().hex[:8]}",
            "confidence": 0.66,
            "description": "Self-model shows inconsistency between predicted and actual state",
            "evidence": {"self_model_error": 0.33, "threshold": 0.2},
        },
    },
    {
        "timestamp": _ts(),
        "source": "metrics",
        "signal_type": "curiosity_saturation",
        "severity": 0.4,
        "details": {
            "id": f"lim-{uuid.uuid4().hex[:8]}",
            "confidence": 0.72,
            "description": "Novelty-seeking behavior saturating, exploration declining",
            "evidence": {"exploration_rate": 0.25, "novelty_response": 0.3},
        },
    },
    {
        "timestamp": _ts(),
        "source": "metrics",
        "signal_type": "inhibition_overflow",
        "severity": 0.5,
        "details": {
            "id": f"lim-{uuid.uuid4().hex[:8]}",
            "confidence": 0.7,
            "description": "Inhibitory control signals exceeding normal range",
            "evidence": {"inhibition_level": 0.82, "normal_range": "[0.1, 0.7]"},
        },
    },
]

NEW_DIAGNOSES = [
    {
        "timestamp": _unix_ts(),
        "category": "attention_fragmentation",
        "primary_category": "attention_fragmentation",
        "description": "Recurring attention_fragmentation detected across signal(s)",
        "metrics": {
            "recurrence_score": 0.3,
            "urgency_score": 0.25,
            "confidence": 0.72,
            "affected_modules": ["attention_router", "region_signal_router"],
            "recommended_action": "routing_redesign",
        },
        "id": f"diag-{uuid.uuid4().hex[:8]}",
    },
    {
        "timestamp": _unix_ts(),
        "category": "memory_decay_accelerated",
        "primary_category": "memory_decay_accelerated",
        "description": "Recurring memory_decay_accelerated detected across signal(s)",
        "metrics": {
            "recurrence_score": 0.3,
            "urgency_score": 0.3,
            "confidence": 0.68,
            "affected_modules": ["semantic_memory", "cell_assembly_store"],
            "recommended_action": "memory_redesign",
        },
        "id": f"diag-{uuid.uuid4().hex[:8]}",
    },
    {
        "timestamp": _unix_ts(),
        "category": "cross_region_lag",
        "primary_category": "cross_region_lag",
        "description": "Recurring cross_region_lag detected across signal(s)",
        "metrics": {
            "recurrence_score": 0.25,
            "urgency_score": 0.2,
            "confidence": 0.8,
            "affected_modules": ["region_signal_router", "brainstem_controller"],
            "recommended_action": "routing_redesign",
        },
        "id": f"diag-{uuid.uuid4().hex[:8]}",
    },
    {
        "timestamp": _unix_ts(),
        "category": "goal_drift",
        "primary_category": "goal_drift",
        "description": "Recurring goal_drift detected across signal(s)",
        "metrics": {
            "recurrence_score": 0.25,
            "urgency_score": 0.2,
            "confidence": 0.65,
            "affected_modules": ["goal_orchestrator", "brainstem_controller"],
            "recommended_action": "parameter_tuning",
        },
        "id": f"diag-{uuid.uuid4().hex[:8]}",
    },
    {
        "timestamp": _unix_ts(),
        "category": "prediction_uncertainty_spike",
        "primary_category": "prediction_uncertainty_spike",
        "description": "Recurring prediction_uncertainty_spike detected across signal(s)",
        "metrics": {
            "recurrence_score": 0.35,
            "urgency_score": 0.35,
            "confidence": 0.82,
            "affected_modules": ["world_model", "prediction_engine"],
            "recommended_action": "model_retrain",
        },
        "id": f"diag-{uuid.uuid4().hex[:8]}",
    },
    {
        "timestamp": _unix_ts(),
        "category": "energy_inefficiency",
        "primary_category": "energy_inefficiency",
        "description": "Recurring energy_inefficiency detected across signal(s)",
        "metrics": {
            "recurrence_score": 0.25,
            "urgency_score": 0.2,
            "confidence": 0.7,
            "affected_modules": ["energy_control_agent", "brainstem_controller"],
            "recommended_action": "parameter_tuning",
        },
        "id": f"diag-{uuid.uuid4().hex[:8]}",
    },
    {
        "timestamp": _unix_ts(),
        "category": "homeostasis_imbalance",
        "primary_category": "homeostasis_imbalance",
        "description": "Recurring homeostasis_imbalance detected across signal(s)",
        "metrics": {
            "recurrence_score": 0.3,
            "urgency_score": 0.25,
            "confidence": 0.75,
            "affected_modules": ["homeostasis_engine", "region_stability_controller"],
            "recommended_action": "stability_control",
        },
        "id": f"diag-{uuid.uuid4().hex[:8]}",
    },
    {
        "timestamp": _unix_ts(),
        "category": "recall_latency_exceeded",
        "primary_category": "recall_latency_exceeded",
        "description": "Recurring recall_latency_exceeded detected across signal(s)",
        "metrics": {
            "recurrence_score": 0.35,
            "urgency_score": 0.3,
            "confidence": 0.85,
            "affected_modules": ["semantic_recall_engine", "cell_assembly_engine"],
            "recommended_action": "memory_redesign",
        },
        "id": f"diag-{uuid.uuid4().hex[:8]}",
    },
    {
        "timestamp": _unix_ts(),
        "category": "temporal_coherence_loss",
        "primary_category": "temporal_coherence_loss",
        "description": "Recurring temporal_coherence_loss detected across signal(s)",
        "metrics": {
            "recurrence_score": 0.3,
            "urgency_score": 0.25,
            "confidence": 0.74,
            "affected_modules": ["episodic_memory", "narrative_engine"],
            "recommended_action": "memory_redesign",
        },
        "id": f"diag-{uuid.uuid4().hex[:8]}",
    },
    {
        "timestamp": _unix_ts(),
        "category": "self_model_inconsistency",
        "primary_category": "self_model_inconsistency",
        "description": "Recurring self_model_inconsistency detected across signal(s)",
        "metrics": {
            "recurrence_score": 0.25,
            "urgency_score": 0.2,
            "confidence": 0.66,
            "affected_modules": ["self_model", "metacognition_engine"],
            "recommended_action": "model_retrain",
        },
        "id": f"diag-{uuid.uuid4().hex[:8]}",
    },
]


def main() -> None:
    DATA_ROOT.mkdir(parents=True, exist_ok=True)

    with SIGNALS_PATH.open("a", encoding="utf-8") as f:
        for signal in NEW_SIGNALS:
            f.write(json.dumps(signal) + "\n")
    s_count = sum(1 for _ in SIGNALS_PATH.open("r") if _.strip())
    print(f"Signals: {s_count} (target 25+)")

    with DIAGNOSES_PATH.open("a", encoding="utf-8") as f:
        for diag in NEW_DIAGNOSES:
            f.write(json.dumps(diag) + "\n")
    d_count = sum(1 for _ in DIAGNOSES_PATH.open("r") if _.strip())
    print(f"Diagnoses: {d_count} (target 20+)")


if __name__ == "__main__":
    main()
