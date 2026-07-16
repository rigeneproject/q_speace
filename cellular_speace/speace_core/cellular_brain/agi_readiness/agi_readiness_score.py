"""AGIReadinessScore — quantifies how close SPEACE is to AGI-like behavior.

The score is decomposed into observable dimensions.  Each dimension is
normalized to [0.0, 1.0] and contributes to a weighted aggregate score.
This is intentionally a pragmatic, engineering-grade metric rather than a
philosophical claim about consciousness.
"""

from __future__ import annotations

import json
import statistics
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class AGIReadinessDimension:
    """One evaluated AGI dimension."""

    name: str
    score: float
    weight: float
    evidence: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.score = float(max(0.0, min(1.0, self.score)))
        self.weight = float(max(0.0, self.weight))


@dataclass
class AGIReadinessReport:
    """Aggregated AGI readiness report."""

    version: str = "0.1"
    timestamp: float = field(default_factory=time.time)
    iteration: int = 0
    dimensions: List[AGIReadinessDimension] = field(default_factory=list)
    aggregate_score: float = 0.0
    agi_like_threshold: float = 0.55
    agi_robust_threshold: float = 0.75
    is_agi_like: bool = False
    is_agi_robust: bool = False
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "timestamp": self.timestamp,
            "iteration": self.iteration,
            "aggregate_score": round(self.aggregate_score, 4),
            "agi_like_threshold": self.agi_like_threshold,
            "agi_robust_threshold": self.agi_robust_threshold,
            "is_agi_like": self.is_agi_like,
            "is_agi_robust": self.is_agi_robust,
            "summary": self.summary,
            "dimensions": [
                {
                    "name": d.name,
                    "score": round(d.score, 4),
                    "weight": round(d.weight, 4),
                    "weighted_contribution": round(d.score * d.weight, 4),
                    "evidence": d.evidence,
                }
                for d in self.dimensions
            ],
        }

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return path


class AGIReadinessScore:
    """Compute an AGI readiness score from SPEACE runtime data.

    Dimensions and default weights:
      - autonomy            (0.15)
      - continuous_learning (0.15)
      - causal_reasoning    (0.15)
      - generalization      (0.10)
      - metacognition       (0.10)
      - self_improvement    (0.15)
      - language_thought    (0.10)
      - embodiment          (0.10)

    Weights sum to 1.0 by default but can be overridden.
    """

    DEFAULT_WEIGHTS = {
        "autonomy": 0.15,
        "continuous_learning": 0.15,
        "causal_reasoning": 0.15,
        "generalization": 0.10,
        "metacognition": 0.10,
        "self_improvement": 0.15,
        "language_thought": 0.10,
        "embodiment": 0.10,
    }

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        agi_like_threshold: float = 0.55,
        agi_robust_threshold: float = 0.75,
    ):
        self.weights = {**self.DEFAULT_WEIGHTS, **(weights or {})}
        total = sum(self.weights.values())
        if total > 0:
            self.weights = {k: v / total for k, v in self.weights.items()}
        self.agi_like_threshold = agi_like_threshold
        self.agi_robust_threshold = agi_robust_threshold

    def evaluate(
        self,
        runtime_state: Optional[Dict[str, Any]] = None,
        learning_state: Optional[Dict[str, Any]] = None,
        causal_state: Optional[Dict[str, Any]] = None,
        test_state: Optional[Dict[str, Any]] = None,
        metacognition_state: Optional[Dict[str, Any]] = None,
        self_improvement_state: Optional[Dict[str, Any]] = None,
        language_state: Optional[Dict[str, Any]] = None,
        embodiment_state: Optional[Dict[str, Any]] = None,
        iteration: int = 0,
    ) -> AGIReadinessReport:
        """Evaluate all dimensions and build a report."""
        dimensions = [
            self._autonomy(runtime_state or {}),
            self._continuous_learning(learning_state or {}),
            self._causal_reasoning(causal_state or {}),
            self._generalization(test_state or {}),
            self._metacognition(metacognition_state or {}),
            self._self_improvement(self_improvement_state or {}),
            self._language_thought(language_state or {}),
            self._embodiment(embodiment_state or {}),
        ]
        aggregate = sum(d.score * self.weights.get(d.name, 0.0) for d in dimensions)
        report = AGIReadinessReport(
            iteration=iteration,
            dimensions=dimensions,
            aggregate_score=aggregate,
            agi_like_threshold=self.agi_like_threshold,
            agi_robust_threshold=self.agi_robust_threshold,
            is_agi_like=aggregate >= self.agi_like_threshold,
            is_agi_robust=aggregate >= self.agi_robust_threshold,
        )
        report.summary = self._summary(report)
        return report

    # ------------------------------------------------------------------ #
    # Dimension calculators
    # ------------------------------------------------------------------ #

    def _autonomy(self, state: Dict[str, Any]) -> AGIReadinessDimension:
        """Score based on stable autonomous runtime hours."""
        hours = float(state.get("runtime_hours", 0.0) or 0.0)
        tick_count = int(state.get("tick_count", 0) or 0)
        coherence = float(state.get("coherence_phi", 0.0) or 0.0)
        anomalies = int(state.get("anomaly_count", 0) or 0)

        target_hours = 2.0
        hour_score = min(1.0, hours / target_hours)
        stability = max(0.0, 1.0 - (anomalies / max(hours * 60, 1.0)))
        coherence_factor = max(0.0, min(1.0, coherence))

        # Bonuses for sustained operation
        tick_bonus = 0.2 if tick_count > 1000 else 0.0
        coherence_bonus = 0.1 if coherence > 0.6 else 0.0

        score = min(1.0, hour_score * stability * (0.5 + 0.5 * coherence_factor) + tick_bonus + coherence_bonus)

        return AGIReadinessDimension(
            name="autonomy",
            score=score,
            weight=self.weights["autonomy"],
            evidence={
                "runtime_hours": hours,
                "tick_count": tick_count,
                "coherence_phi": coherence,
                "anomaly_count": anomalies,
            },
        )

    def _continuous_learning(self, state: Dict[str, Any]) -> AGIReadinessDimension:
        """Score based on prediction-error trend and sample count."""
        errors = state.get("prediction_errors", []) or []
        if len(errors) >= 5:
            recent = errors[-5:]
            mean_error = sum(recent) / len(recent)
            error_score = max(0.0, 1.0 - mean_error)
            current_error = mean_error

            mid = len(errors) // 2
            early_mean = sum(errors[:mid]) / max(mid, 1)
            late_mean = sum(errors[mid:]) / max(len(errors) - mid, 1)
            improvement = max(0.0, min(1.0, (early_mean - late_mean) / max(early_mean, 1e-9)))
        else:
            error_score = 0.0
            improvement = 0.0
            current_error = float(errors[-1]) if errors else 1.0

        sample_bonus = min(1.0, len(errors) / 30.0)
        base = 0.2 if len(errors) > 0 else 0.0
        score = min(1.0, base + (0.4 * error_score + 0.4 * improvement) * sample_bonus)

        return AGIReadinessDimension(
            name="continuous_learning",
            score=score,
            weight=self.weights["continuous_learning"],
            evidence={
                "prediction_error_samples": len(errors),
                "latest_prediction_error": round(current_error, 4),
                "trend_improvement": round(improvement, 4),
            },
        )

    def _causal_reasoning(self, state: Dict[str, Any]) -> AGIReadinessDimension:
        """Score based on world-model observations and predictive accuracy."""
        observations = int(state.get("observation_count", 0) or 0)
        unique_actions = int(state.get("unique_actions", 0) or 0)
        accuracy = float(state.get("prediction_accuracy", 0.0) or 0.0)

        coverage = min(1.0, observations / 50.0) * min(1.0, unique_actions / 10.0)
        score = coverage * (0.5 + 0.5 * max(0.0, min(1.0, accuracy)))

        return AGIReadinessDimension(
            name="causal_reasoning",
            score=score,
            weight=self.weights["causal_reasoning"],
            evidence={
                "observation_count": observations,
                "unique_actions": unique_actions,
                "prediction_accuracy": accuracy,
            },
        )

    def _generalization(self, state: Dict[str, Any]) -> AGIReadinessDimension:
        """Proxy based on automated test pass rate and diversity."""
        passed = int(state.get("passed", 0) or 0)
        failed = int(state.get("failed", 0) or 0)
        skipped = int(state.get("skipped", 0) or 0)
        total = passed + failed + skipped

        if total == 0:
            pass_rate = 0.0
        else:
            pass_rate = passed / total

        diversity = min(1.0, total / 20.0)
        score = pass_rate * diversity

        return AGIReadinessDimension(
            name="generalization",
            score=score,
            weight=self.weights["generalization"],
            evidence={
                "tests_passed": passed,
                "tests_failed": failed,
                "tests_skipped": skipped,
                "tests_total": total,
                "pass_rate": round(pass_rate, 4),
            },
        )

    def _metacognition(self, state: Dict[str, Any]) -> AGIReadinessDimension:
        """Score based on limitation detection and diagnostic accuracy."""
        signals = int(state.get("limitation_signals", 0) or 0)
        diagnoses = int(state.get("diagnoses", 0) or 0)
        accuracy = float(state.get("detection_accuracy", 0.0) or 0.0)

        detection_density = min(1.0, signals / 15.0) * min(1.0, diagnoses / 10.0)
        base = 0.2 if signals > 0 else 0.0
        accuracy_factor = max(0.01, min(1.0, accuracy))
        score = min(1.0, base + detection_density * 0.4 + accuracy_factor * 0.4)

        return AGIReadinessDimension(
            name="metacognition",
            score=score,
            weight=self.weights["metacognition"],
            evidence={
                "limitation_signals": signals,
                "diagnoses": diagnoses,
                "detection_accuracy": accuracy,
            },
        )

    def _self_improvement(self, state: Dict[str, Any]) -> AGIReadinessDimension:
        """Score based on accepted architectural proposals vs total."""
        total = int(state.get("proposals_total", 0) or 0)
        accepted = int(state.get("proposals_accepted", 0) or 0)
        executed = int(state.get("patches_executed", 0) or 0)
        successful = int(state.get("patches_successful", 0) or 0)

        recent_total = min(total, 1000)
        recent_accepted = int(state.get("recent_accepted", min(accepted, recent_total)))
        recent_accepted = min(recent_accepted, recent_total)

        accept_rate = recent_accepted / max(recent_total, 1)

        base_bonus = 0.3 if accepted > 0 else 0.0

        exec_credit = 0.3 * min(1.0, executed / max(recent_total, 1))

        success_bonus = 0.2 * min(1.0, successful / max(executed, 1))

        trend_bonus = 0.2 * accept_rate

        score = min(1.0, base_bonus + exec_credit + success_bonus + trend_bonus)

        return AGIReadinessDimension(
            name="self_improvement",
            score=score,
            weight=self.weights["self_improvement"],
            evidence={
                "proposals_total": total,
                "proposals_accepted": accepted,
                "recent_total": recent_total,
                "recent_accepted": recent_accepted,
                "patches_executed": executed,
                "patches_successful": successful,
                "accept_rate": round(accept_rate, 4),
                "base_bonus": round(base_bonus, 4),
                "exec_credit": round(exec_credit, 4),
                "success_bonus": round(success_bonus, 4),
                "trend_bonus": round(trend_bonus, 4),
            },
        )

    def _language_thought(self, state: Dict[str, Any]) -> AGIReadinessDimension:
        """Score based on grounded symbols, dialogue coherence, and spontaneous thought."""
        groundings = int(state.get("grounding_count", 0) or 0)
        coherence = float(state.get("dialogue_coherence", 0.0) or 0.0)
        utterances = int(state.get("spontaneous_utterances", 0) or 0)

        grounding_score = min(1.0, groundings / 50.0)
        thought_activity = min(1.0, utterances / 3.0)
        base = 0.1 if groundings > 0 else 0.0
        coherence_factor = 0.5 + 0.5 * max(0.0, min(1.0, coherence))
        score = min(1.0, base + grounding_score * coherence_factor * thought_activity * 0.9)

        return AGIReadinessDimension(
            name="language_thought",
            score=score,
            weight=self.weights["language_thought"],
            evidence={
                "grounding_count": groundings,
                "dialogue_coherence": coherence,
                "spontaneous_utterances": utterances,
            },
        )

    def _embodiment(self, state: Dict[str, Any]) -> AGIReadinessDimension:
        """Score based on active sensors and successful embodied actions."""
        sensors = int(state.get("sensor_count", 0) or 0)
        actions = int(state.get("action_count", 0) or 0)
        successful = int(state.get("successful_actions", 0) or 0)

        sensor_score = min(1.0, sensors / 5.0)
        if actions == 0:
            action_score = 0.0
        else:
            action_score = successful / actions

        score = sensor_score * (0.5 + 0.5 * action_score)

        return AGIReadinessDimension(
            name="embodiment",
            score=score,
            weight=self.weights["embodiment"],
            evidence={
                "sensor_count": sensors,
                "action_count": actions,
                "successful_actions": successful,
            },
        )

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _summary(self, report: AGIReadinessReport) -> str:
        if report.is_agi_robust:
            return (
                f"SPEACE is in the robust AGI-like regime "
                f"(score={report.aggregate_score:.2f})."
            )
        if report.is_agi_like:
            return (
                f"SPEACE shows emerging AGI-like behavior "
                f"(score={report.aggregate_score:.2f})."
            )
        return (
            f"SPEACE is below the AGI-like threshold "
            f"(score={report.aggregate_score:.2f}; threshold={self.agi_like_threshold})."
        )


# ---------------------------------------------------------------------- #
# Convenience: load/save helpers
# ---------------------------------------------------------------------- #


def load_last_report(report_dir: Path) -> Optional[AGIReadinessReport]:
    """Load the most recent AGI readiness report from a directory."""
    if not report_dir.exists():
        return None
    files = sorted(report_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            dims = [
                AGIReadinessDimension(
                    name=d["name"],
                    score=d["score"],
                    weight=d["weight"],
                    evidence=d.get("evidence", {}),
                )
                for d in data.get("dimensions", [])
            ]
            return AGIReadinessReport(
                version=data.get("version", "0.1"),
                timestamp=data.get("timestamp", 0.0),
                iteration=data.get("iteration", 0),
                dimensions=dims,
                aggregate_score=data.get("aggregate_score", 0.0),
                agi_like_threshold=data.get("agi_like_threshold", 0.55),
                agi_robust_threshold=data.get("agi_robust_threshold", 0.75),
                is_agi_like=data.get("is_agi_like", False),
                is_agi_robust=data.get("is_agi_robust", False),
                summary=data.get("summary", ""),
            )
        except (json.JSONDecodeError, KeyError, OSError):
            continue
    return None
