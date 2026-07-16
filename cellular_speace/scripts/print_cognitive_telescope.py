"""Cognitive Factors Telescope — T172/B2 smoke runner.

Reads ten cognitive factors from existing SPEACE modules (no writes,
no spawning) and prints a single JSON snapshot to stdout.

Usage:
    python scripts/print_cognitive_telescope.py
    python scripts/print_cognitive_telescope.py --output reports/cognitive_telescope/smoke_<ts>.json

Output: JSON object with 10 keys, one per factor, in this shape:

    {
      "wm": {"value": 0.0, "healthy_range": [0.4, 0.8], "tag": "cognitive_factor:wm", ...},
      "speed": {...},
      ...
    }

This script is **read-only** with respect to the organism. It does not
spawn any background process. It only inspects in-memory state and the
live genome / YAML configuration files.

Related: docs/T172_COGNITIVE_FACTORS_TELESCOPE_SPEC.md
"""

from __future__ import annotations

import json
import pathlib
import sys
import time
from typing import Any, Dict, Optional

# Make repo importable when running as `python scripts/...`
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


# --------------------------------------------------------------------------- #
# Lazy imports of in-tree modules (no production side-effects at import time)
# --------------------------------------------------------------------------- #


def _imports() -> Dict[str, Any]:
    """Lazy imports. We hold them in a dict so callers can override for tests."""
    from speace_core.cellular_brain.cognition.subgrid_attention_working_memory import (
        SubgridAttentionWorkingMemory,
    )
    from speace_core.cellular_brain.metabolism.cognitive_cost_model import (
        CognitiveCostModel,
    )
    from speace_core.cellular_brain.cognition.hierarchical_concept_abstraction_layer import (
        HierarchicalConceptAbstractionLayer,
    )
    from speace_core.cellular_brain.cognition.temporal_causal_reasoning_layer import (
        TemporalCausalReasoningLayer,
    )
    from speace_core.cellular_brain.regions.thalamic_relay_engine import (
        ThalamicRelayEngine,
        ThalamicRelayMode,
    )

    return {
        "SubgridAttentionWorkingMemory": SubgridAttentionWorkingMemory,
        "CognitiveCostModel": CognitiveCostModel,
        "HierarchicalConceptAbstractionLayer": HierarchicalConceptAbstractionLayer,
        "TemporalCausalReasoningLayer": TemporalCausalReasoningLayer,
        "ThalamicRelayEngine": ThalamicRelayEngine,
        "ThalamicRelayMode": ThalamicRelayMode,
    }


# --------------------------------------------------------------------------- #
# The ten factor probes
# --------------------------------------------------------------------------- #


def probe_wm(libs: Dict[str, Any]) -> Dict[str, Any]:
    """Factor 1 — Working memory slot utilization."""
    cls = libs["SubgridAttentionWorkingMemory"]
    wm = cls(max_slots=4)
    # No active task → utilization is 0. Healthy when a real task is loaded.
    return {
        "value": len(wm.slots) / max(1, wm.max_slots),
        "max_slots": wm.max_slots,
        "healthy_range": [0.4, 0.8],
        "tag": "cognitive_factor:wm",
        "module": "cognition.subgrid_attention_working_memory.SubgridAttentionWorkingMemory",
    }


def probe_speed(libs: Dict[str, Any]) -> Dict[str, Any]:
    """Factor 2 — Processing speed (rolling cognitive cost / tick)."""
    cls = libs["CognitiveCostModel"]
    cm = cls()
    total = cm.compute_total_cognitive_cost()
    n_modules = len(cm.list_profiles())
    avg = total / max(1, n_modules)
    return {
        "value": round(avg, 6),
        "total_cost": round(total, 6),
        "n_modules": n_modules,
        "healthy_range": [0.0, 0.5],
        "tag": "cognitive_factor:speed",
        "module": "metabolism.cognitive_cost_model.CognitiveCostModel",
    }


def probe_pattern(libs: Dict[str, Any]) -> Dict[str, Any]:
    """Factor 3 — Pattern recognition compression ratio.

    We do not spin up a ConceptGraph instance (cost); we report the
    *baseline* ratio the catalog enforces (1 / n_distinct_concepts).
    A populated graph would replace this with the real measurement.
    """
    return {
        "value": 0.0,
        "note": "empty (no live concept graph in this snapshot)",
        "healthy_range": [0.05, 1.0],
        "tag": "cognitive_factor:pattern",
        "module": "cognition.concept_graph + cognition.arc_primitive_discovery_engine",
    }


def probe_knowledge(libs: Dict[str, Any]) -> Dict[str, Any]:
    """Factor 4 — Memory link density.

    Empty at smoke time; the telescope records 0.0 + a note.
    A populated semantic store would replace these.
    """
    return {
        "value": 0.0,
        "note": "empty (no live semantic store in this snapshot)",
        "healthy_range": [0.0, 1.0],
        "tag": "cognitive_factor:knowledge",
        "module": "evolutionary_memory + memory.semantic.semantic_memory_store",
    }


def probe_abstraction(libs: Dict[str, Any]) -> Dict[str, Any]:
    """Factor 5 — Distinct abstraction levels currently active."""
    # Two levels is the baseline: flat concepts (level-1) always exist;
    # level-2 (categories) is created by the HierarchicalConceptAbstractionLayer
    # when at least one observation pair has been ingested. With no
    # observations, the layer is empty — count = 1 (level-1 only).
    cls = libs["HierarchicalConceptAbstractionLayer"]
    layer = cls()
    # Flat-concepts only → one active level. Categories/schema are
    # populated only by ingest(); we report the structurally guaranteed
    # baseline.
    return {
        "value": 1,
        "healthy_range": [2, 5],
        "tag": "cognitive_factor:abstraction",
        "module": "cognition.hierarchical_concept_abstraction_layer",
        "note": "baseline (1 = flat concepts only)",
    }


def probe_relational(libs: Dict[str, Any]) -> Dict[str, Any]:
    """Factor 6 — Cycles detected in the causal temporal graph."""
    cls = libs["TemporalCausalReasoningLayer"]
    layer = cls()
    # Sequences dict is empty until ingest(); 0 cycles is the baseline.
    return {
        "value": 0,
        "healthy_range": [1, 1000000],
        "tag": "cognitive_factor:relational",
        "module": "cognition.temporal_causal_reasoning_layer",
        "note": "baseline (no live observations)",
    }


def probe_metacognition(libs: Dict[str, Any]) -> Dict[str, Any]:
    """Factor 7 — Metacognitive probes per minute.

    Without an active run, this is 0. The Ispettore loop populates this.
    """
    return {
        "value": 0.0,
        "healthy_range": [0.1, 1000.0],
        "tag": "cognitive_factor:metacognition",
        "module": "metacognition.metacognitive_monitor",
        "note": "baseline (no active metacognitive monitor)",
    }


def probe_attention(libs: Dict[str, Any]) -> Dict[str, Any]:
    """Factor 8 — Sustained attention gap count (burst→tonic transitions)."""
    cls = libs["ThalamicRelayEngine"]
    ThalamicRelayMode = libs["ThalamicRelayMode"]
    engine = cls()
    # No feedback has been processed → mode is TONIC, no burst-gap occurred.
    mode = engine.state.mode
    in_burst = 1 if mode == ThalamicRelayMode.BURST else 0
    return {
        "value": in_burst,
        "healthy_range": [0, 2],
        "tag": "cognitive_factor:attention",
        "module": "regions.thalamic_relay_engine.ThalamicRelayEngine",
        "note": "0 = tonic (sustained attention); 1 = currently in burst (gap)",
    }


def probe_motivation() -> Dict[str, Any]:
    """Factor 9 — Maximum drive setpoint across the seven autonomous drives."""
    import yaml

    p = pathlib.Path("speace_core/dna/genome/morphology/autonomous_drives.yaml")
    raw = yaml.safe_load(p.read_text(encoding="utf-8"))
    drives = raw["autonomous_drives"]["parameters"]["drives"]
    setpoints = {name: float(spec.get("setpoint", 0.0)) for name, spec in drives.items()}
    return {
        "value": max(setpoints.values()) if setpoints else 0.0,
        "setpoints": setpoints,
        "healthy_range": [0.0, 0.8],
        "tag": "cognitive_factor:motivation",
        "module": "dna.genome.morphology.autonomous_drives",
    }


def probe_flexibility() -> Dict[str, Any]:
    """Factor 10 — Perspective switches per minute.

    The mmapr_council runs on demand; there is no background counter.
    We report 0 with a note.
    """
    return {
        "value": 0.0,
        "healthy_range": [0.2, 100.0],
        "tag": "cognitive_factor:flexibility",
        "module": "cognition.mmapr_council",
        "note": "baseline (no background perspective-switch counter)",
    }


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #


def collect_snapshot() -> Dict[str, Any]:
    libs = _imports()
    snapshot = {
        "timestamp": time.time(),
        "factors": {
            "wm": probe_wm(libs),
            "speed": probe_speed(libs),
            "pattern": probe_pattern(libs),
            "knowledge": probe_knowledge(libs),
            "abstraction": probe_abstraction(libs),
            "relational": probe_relational(libs),
            "metacognition": probe_metacognition(libs),
            "attention": probe_attention(libs),
            "motivation": probe_motivation(),
            "flexibility": probe_flexibility(),
        },
    }
    return snapshot


def main(argv: Optional[list] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Cognitive Factors Telescope smoke runner.")
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=None,
        help="If given, also write the JSON snapshot to this path.",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="json",
        help="Output format on stdout (default: json).",
    )
    args = parser.parse_args(argv)

    snapshot = collect_snapshot()

    if args.format == "json":
        sys.stdout.write(json.dumps(snapshot, indent=2, ensure_ascii=False))
        sys.stdout.write("\n")
    else:
        sys.stdout.write("Cognitive Factors Telescope\n")
        sys.stdout.write("=" * 32 + "\n")
        for name, payload in snapshot["factors"].items():
            sys.stdout.write(
                f"  {name:14s} = {payload.get('value')!r:>8}  "
                f"healthy {payload.get('healthy_range')}  "
                f"[{payload.get('tag')}]\n"
            )

    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
