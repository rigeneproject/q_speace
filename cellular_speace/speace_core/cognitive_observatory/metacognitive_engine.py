import time
from typing import Any, Dict, List, Optional

import structlog

from speace_core.cognitive_observatory.models import MetacognitiveScore
from speace_core.cognitive_observatory.persistence.observatory_store import ObservatoryStore

logger = structlog.get_logger(__name__)


class MetacognitiveEngine:
    """L5 — Metacognitive Engine.

    Evaluates decision quality by tracking confidence, accuracy,
    context completeness, evidence quality, hypotheses considered,
    and subsequent errors.
    """

    def __init__(self, store: Optional[ObservatoryStore] = None) -> None:
        self._store = store or ObservatoryStore()

    # ------------------------------------------------------------------ #
    # Recording
    # ------------------------------------------------------------------ #

    def record_decision_quality(
        self,
        decision_id: str,
        confidence: float = 0.0,
        context_completeness: float = 0.0,
        evidence_quality: float = 0.0,
        hypotheses_considered: int = 0,
        subsystem: str = "",
    ) -> MetacognitiveScore:
        score = MetacognitiveScore(
            decision_id=decision_id,
            confidence=max(0.0, min(1.0, confidence)),
            context_completeness=max(0.0, min(1.0, context_completeness)),
            evidence_quality=max(0.0, min(1.0, evidence_quality)),
            hypotheses_considered=hypotheses_considered,
            subsystem=subsystem,
        )
        self._store.put_metacognitive_score(score)
        return score

    def record_outcome(
        self, decision_id: str, accuracy: float,
        subsequent_errors: int = 0, prediction_outcome_diff: float = 0.0,
    ) -> None:
        """Update an existing decision record with outcome data."""
        recent = self._store.get_recent_metacognitive_scores(limit=200)
        for score in recent:
            if score.decision_id == decision_id:
                score.accuracy = max(0.0, min(1.0, accuracy))
                score.subsequent_errors = subsequent_errors
                score.prediction_outcome_diff = abs(prediction_outcome_diff)
                return
        # If not found, create a new record with outcome only
        score = MetacognitiveScore(
            decision_id=decision_id,
            accuracy=max(0.0, min(1.0, accuracy)),
            subsequent_errors=subsequent_errors,
            prediction_outcome_diff=abs(prediction_outcome_diff),
        )
        self._store.put_metacognitive_score(score)

    # ------------------------------------------------------------------ #
    # Query
    # ------------------------------------------------------------------ #

    def get_recent_scores(self, limit: int = 50) -> List[MetacognitiveScore]:
        return self._store.get_recent_metacognitive_scores(limit=limit)

    def get_decision_scores(self, decision_id: str) -> List[MetacognitiveScore]:
        all_scores = self._store.get_recent_metacognitive_scores(limit=1000)
        return [s for s in all_scores if s.decision_id == decision_id]

    # ------------------------------------------------------------------ #
    # Analysis
    # ------------------------------------------------------------------ #

    def get_average_confidence(self, window: int = 50) -> float:
        recent = self._store.get_recent_metacognitive_scores(limit=window)
        if not recent:
            return 0.5
        return sum(s.confidence for s in recent) / len(recent)

    def get_average_accuracy(self, window: int = 50) -> float:
        recent = self._store.get_recent_metacognitive_scores(limit=window)
        with_outcome = [s for s in recent if s.accuracy > 0]
        if not with_outcome:
            return 0.5
        return sum(s.accuracy for s in with_outcome) / len(with_outcome)

    def get_calibration_error(self, window: int = 50) -> float:
        """How well does confidence predict accuracy? Lower is better."""
        recent = self._store.get_recent_metacognitive_scores(limit=window)
        with_outcome = [s for s in recent if s.accuracy > 0]
        if not with_outcome:
            return 0.5
        errors = [abs(s.confidence - s.accuracy) for s in with_outcome]
        return sum(errors) / len(errors)

    def get_average_context_completeness(self, window: int = 50) -> float:
        recent = self._store.get_recent_metacognitive_scores(limit=window)
        if not recent:
            return 0.5
        return sum(s.context_completeness for s in recent) / len(recent)

    def get_recurring_error_patterns(self, min_frequency: int = 2) -> List[Dict[str, Any]]:
        """Identify recurring error patterns by subsystem."""
        all_scores = self._store.get_recent_metacognitive_scores(limit=1000)
        subsystem_errors: Dict[str, int] = {}
        for s in all_scores:
            if s.subsequent_errors > 0:
                sub = s.subsystem or "unknown"
                subsystem_errors[sub] = subsystem_errors.get(sub, 0) + 1
        return [
            {"subsystem": sub, "error_count": count}
            for sub, count in subsystem_errors.items()
            if count >= min_frequency
        ]

    def get_comprehensive_metacognitive_report(self) -> Dict[str, Any]:
        recent = self._store.get_recent_metacognitive_scores(limit=100)
        return {
            "average_confidence": round(self.get_average_confidence(), 4),
            "average_accuracy": round(self.get_average_accuracy(), 4),
            "calibration_error": round(self.get_calibration_error(), 4),
            "average_context_completeness": round(self.get_average_context_completeness(), 4),
            "recent_decisions": len(recent),
            "recurring_error_patterns": self.get_recurring_error_patterns(),
        }
