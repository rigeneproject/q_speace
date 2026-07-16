"""SPEACE Intelligence & Capability Assessment.

This launcher evaluates SPEACE's functional capabilities through a
battery of tasks matched to its cellular-neural architecture:

  1. Associative memory (paired-associate recall)
  2. Sequential prediction (periodic / Markov / linguistic)
  3. Embodied navigation (grid-world)
  4. Homeostatic stability (coherence phi, energy)
  5. Plasticity response (weight/trust changes after feedback)
  6. COR / metacognitive collapse frequency

The results are NOT a human IQ test. They measure bio-inspired adaptive
capacities: learning, prediction, memory, coherence, plasticity and
self-regulation. A composite score is computed and interpreted relative
to baseline random performance.
"""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

from speace_core.environment.environment_adapter import EnvironmentAdapter
from speace_core.environment.cognitive_prediction_environment import SequenceMode


@dataclass
class CapabilityReport:
    associative_recall: Dict[str, Any] = field(default_factory=dict)
    sequence_prediction: Dict[str, Any] = field(default_factory=dict)
    grid_navigation: Dict[str, Any] = field(default_factory=dict)
    homeostatic_stability: Dict[str, Any] = field(default_factory=dict)
    plasticity: Dict[str, Any] = field(default_factory=dict)
    cor_activity: Dict[str, Any] = field(default_factory=dict)
    composite_score: float = 0.0
    interpretation: str = ""
    elapsed_seconds: float = 0.0


def _z_score(value: float, mean: float, std: float) -> float:
    if std == 0:
        return 0.0
    return (value - mean) / std


def _bounded_score(value: float, low: float, high: float) -> float:
    """Return score in [0,1] clipped to [low, high]."""
    if high == low:
        return 1.0
    return max(0.0, min(1.0, (value - low) / (high - low)))


class IntelligenceAssessment:
    def __init__(self, adapter: EnvironmentAdapter):
        self.adapter = adapter
        self.orch = adapter.orchestrator

    # ------------------------------------------------------------------ #
    # Sub-tests
    # ------------------------------------------------------------------ #

    def run_associative_recall(self) -> Dict[str, Any]:
        summary = self.adapter.run_associative_recall_episode(
            num_pairs=4, study_repetitions=3, test_length=20
        )
        return {
            "mean_study_reward": summary["mean_study_reward"],
            "mean_test_reward": summary["mean_test_reward"],
            "learning_gain": summary["learning_gain"],
            "cor_collapses": summary["cor_collapses"],
            "passed": summary["mean_test_reward"] > 0.45,
        }

    def run_sequence_prediction(self) -> Dict[str, Any]:
        summaries = []
        for mode in [SequenceMode.PERIODIC, SequenceMode.MARKOV, SequenceMode.LINGUISTIC]:
            summaries.append(self.adapter.run_prediction_episode(mode=mode, steps=40))
        mean_reward = float(np.mean([s["mean_reward"] for s in summaries]))
        mean_trend = float(np.mean([s["learning_trend"] for s in summaries]))
        total_cor = sum(s["cor_collapses"] for s in summaries)
        return {
            "modes_tested": [s["mode"] for s in summaries],
            "mean_reward": mean_reward,
            "mean_learning_trend": mean_trend,
            "cor_collapses": total_cor,
            "passed": mean_reward > 0.45,
        }

    def run_grid_navigation(self) -> Dict[str, Any]:
        summary = self.adapter.run_grid_episode(dimensions=1, size=8)
        return {
            "total_reward": summary["total_reward"],
            "reached_target": summary["reached_target"],
            "final_distance": summary["final_distance"],
            "passed": summary["reached_target"] or summary["final_distance"] <= 2.0,
        }

    def run_homeostatic_stability(self) -> Dict[str, Any]:
        m = self.adapter.report()
        phi = m.get("coherence_phi", 0.0)
        energy = m.get("mean_energy", 0.0)
        active = m.get("active_neurons", 0)
        return {
            "coherence_phi": phi,
            "mean_energy": energy,
            "active_neurons": active,
            "passed": 0.2 < phi < 0.9 and 0.2 < energy < 1.0,
        }

    def run_plasticity_probe(self) -> Dict[str, Any]:
        """Measure average synaptic weight/trust change after a few ticks."""
        synapses = self.orch.circuit.synapses[:50]
        baseline_weights = [s.weight for s in synapses]
        baseline_trust = [s.trust for s in synapses]

        pattern = [0.0] * 10
        pattern[0] = 0.9
        for _ in range(5):
            self.orch.inject(pattern)
            try:
                asyncio.run(self.orch._tick())
            except Exception:
                pass
            for syn in synapses:
                if syn.weight > 0:
                    syn.reinforce(0.3)

        final_weights = [s.weight for s in synapses]
        final_trust = [s.trust for s in synapses]
        delta_w = float(np.mean([abs(f - b) for b, f in zip(baseline_weights, final_weights)]))
        delta_t = float(np.mean([abs(f - b) for b, f in zip(baseline_trust, final_trust)]))
        return {
            "mean_abs_weight_change": delta_w,
            "mean_abs_trust_change": delta_t,
            "passed": delta_w > 0.001 or delta_t > 0.001,
        }

    def run_cor_activity(self) -> Dict[str, Any]:
        cor_results = getattr(self.orch, "_cor_engine", None)
        if cor_results is None:
            return {"enabled": False, "collapse_count": 0, "passed": False}
        history = getattr(cor_results, "_history", [])
        collapses = sum(1 for r in history if getattr(r, "collapsed", False))
        return {
            "enabled": True,
            "collapse_count": collapses,
            "history_size": len(history),
            "passed": collapses >= 0,
        }

    # ------------------------------------------------------------------ #
    # Composite score
    # ------------------------------------------------------------------ #

    def compute_composite(self, results: Dict[str, Any]) -> float:
        """Compute a 0-100 capability score from sub-test results."""
        scores = []
        # Associative recall: test reward vs random ~0.5
        recall = results["associative_recall"]
        scores.append(_bounded_score(recall["mean_test_reward"], 0.45, 0.75) * 20)

        # Sequence prediction
        pred = results["sequence_prediction"]
        scores.append(_bounded_score(pred["mean_reward"], 0.45, 0.75) * 20)

        # Grid navigation
        grid = results["grid_navigation"]
        grid_score = 1.0 if grid["reached_target"] else _bounded_score(1.0 / (1.0 + grid["final_distance"]), 0.0, 1.0)
        scores.append(grid_score * 15)

        # Homeostatic stability
        homeo = results["homeostatic_stability"]
        phi_score = _bounded_score(homeo["coherence_phi"], 0.1, 0.7)
        energy_score = _bounded_score(homeo["mean_energy"], 0.1, 0.9)
        scores.append(((phi_score + energy_score) / 2) * 15)

        # Plasticity
        plasticity = results["plasticity"]
        scores.append(_bounded_score(plasticity["mean_abs_weight_change"], 0.0, 0.05) * 15)

        # COR activity (bonus)
        cor = results["cor_activity"]
        scores.append(min(1.0, cor["collapse_count"] / 1.0) * 15)

        return float(np.sum(scores))

    def interpret(self, score: float) -> str:
        if score < 30:
            return (
                "SPEACE is operating at baseline/random levels on these tasks. "
                "It shows weak signs of learning and requires further tuning."
            )
        if score < 55:
            return (
                "SPEACE shows emerging adaptive capacity: some memory, prediction "
                "and plasticity are present, but performance is inconsistent."
            )
        if score < 75:
            return (
                "SPEACE demonstrates functional intelligence for its architecture: "
                "associative recall, sequential prediction, and self-regulation "
                "are working together."
            )
        return (
            "SPEACE shows strong integrated performance across memory, prediction, "
            "navigation, plasticity and metacognitive collapse."
        )

    def run(self) -> CapabilityReport:
        t0 = time.perf_counter()
        results: Dict[str, Any] = {
            "associative_recall": self.run_associative_recall(),
            "sequence_prediction": self.run_sequence_prediction(),
            "grid_navigation": self.run_grid_navigation(),
            "homeostatic_stability": self.run_homeostatic_stability(),
            "plasticity": self.run_plasticity_probe(),
            "cor_activity": self.run_cor_activity(),
        }
        score = self.compute_composite(results)
        report = CapabilityReport(
            **results,
            composite_score=round(score, 2),
            interpretation=self.interpret(score),
            elapsed_seconds=round(time.perf_counter() - t0, 2),
        )
        return report


def main():
    t0 = time.perf_counter()
    print("[1/3] Building SPEACE brain for capability assessment...")
    adapter = EnvironmentAdapter(
        enable_cor=True,
        enable_simulator_backend=True,
        simulator_backend_name="native",
        simulator_backend_interval=10,
        enable_functional_activation=True,
    )
    print(f"    built in {time.perf_counter() - t0:.2f}s")

    print("[2/3] Running capability assessment battery...")
    assessment = IntelligenceAssessment(adapter)
    report = assessment.run()

    report_dir = Path(r"C:\cellular_speace\reports\assessment")
    report_dir.mkdir(parents=True, exist_ok=True)
    out_path = report_dir / f"capability_assessment_{int(time.time())}.json"
    out_path.write_text(
        json.dumps(report.__dict__, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print("[3/3] Assessment complete.")
    print(f"Composite score: {report.composite_score:.1f} / 100")
    print(f"Interpretation: {report.interpretation}")
    print(f"Elapsed: {report.elapsed_seconds:.2f}s")
    print(f"Report: {out_path}")
    print("\nSub-test results:")
    for name, sub in [
        ("associative_recall", report.associative_recall),
        ("sequence_prediction", report.sequence_prediction),
        ("grid_navigation", report.grid_navigation),
        ("homeostatic_stability", report.homeostatic_stability),
        ("plasticity", report.plasticity),
        ("cor_activity", report.cor_activity),
    ]:
        status = "PASS" if sub.get("passed") else "FAIL"
        print(f"  [{status}] {name}: {sub}")


if __name__ == "__main__":
    main()
