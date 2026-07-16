import time
from typing import Dict, List, Optional

import structlog

from speace_core.cognitive_observatory.models import CCIComponents
from speace_core.cognitive_observatory.persistence.observatory_store import ObservatoryStore
from speace_core.cognitive_observatory.self_model import SelfModelEngine
from speace_core.cognitive_observatory.narrative_memory import NarrativeMemory
from speace_core.cognitive_observatory.metacognitive_engine import MetacognitiveEngine

logger = structlog.get_logger(__name__)


class CoherenceEngine:
    """L4 — Cognitive Coherence Engine.

    Computes the Cognitive Coherence Index (CCI) from six dimensions:
    C_memory, C_identity, C_reasoning, C_learning, C_prediction, C_traceability.
    """

    def __init__(
        self,
        store: Optional[ObservatoryStore] = None,
        self_model: Optional[SelfModelEngine] = None,
        narrative_memory: Optional[NarrativeMemory] = None,
        metacognitive: Optional[MetacognitiveEngine] = None,
    ) -> None:
        self._store = store or ObservatoryStore()
        self._self_model = self_model
        self._narrative = narrative_memory
        self._metacognitive = metacognitive
        self._last_cci: float = 0.5
        self._history: List[CCIComponents] = []

    # ------------------------------------------------------------------ #
    # CCI Computation
    # ------------------------------------------------------------------ #

    def compute_cci(self) -> CCIComponents:
        components = CCIComponents()

        # C_memory: coherence between memory and events
        components.c_memory = self._compute_memory_coherence()

        # C_identity: coherence with species orientation
        components.c_identity = self._compute_identity_coherence()

        # C_reasoning: coherence between decisions and goals
        components.c_reasoning = self._compute_reasoning_coherence()

        # C_learning: ability to learn from errors
        components.c_learning = self._compute_learning_effectiveness()

        # C_prediction: prediction accuracy
        components.c_prediction = self._compute_prediction_accuracy()

        # C_traceability: explainability of decisions
        components.c_traceability = self._compute_traceability()

        self._last_cci = components.compute()
        self._store.put_cci_snapshot(components)
        self._history.append(components)

        logger.info("coherence_engine.computed", cci=round(self._last_cci, 4))
        return components

    def get_current_cci(self) -> float:
        return self._last_cci

    def get_cci_history(self, limit: int = 100) -> List[CCIComponents]:
        return self._store.get_cci_history(limit=limit)

    def get_cci_trend(self, window: int = 10) -> float:
        return self._store.get_cci_trend(window=window)

    # ------------------------------------------------------------------ #
    # Component computations
    # ------------------------------------------------------------------ #

    def _compute_memory_coherence(self) -> float:
        if not self._narrative:
            return 0.5
        effectiveness = self._narrative.get_learning_effectiveness(window=50)
        return max(0.0, min(1.0, effectiveness))

    def _compute_identity_coherence(self) -> float:
        if not self._self_model:
            return 0.5
        return self._self_model.get_identity_consistency()

    def _compute_reasoning_coherence(self) -> float:
        if not self._metacognitive:
            return 0.5
        recent = self._metacognitive.get_recent_scores(limit=20)
        if not recent:
            return 0.5
        # Consistency: how often do confidence and accuracy align
        alignments = sum(
            1 - abs(s.confidence - s.accuracy) for s in recent
            if s.accuracy > 0
        )
        n = sum(1 for s in recent if s.accuracy > 0)
        return max(0.0, min(1.0, alignments / max(n, 1)))

    def _compute_learning_effectiveness(self) -> float:
        if not self._narrative:
            return 0.5
        effectiveness = self._narrative.get_learning_effectiveness(window=100)
        error_rate = 0.0
        errors = self._narrative.get_recent_errors(limit=50)
        if errors:
            has_learning = sum(1 for e in errors if e.learning)
            error_rate = has_learning / len(errors)
        return max(0.0, min(1.0, (effectiveness + error_rate) / 2))

    def _compute_prediction_accuracy(self) -> float:
        if not self._metacognitive:
            return 0.5
        recent = self._metacognitive.get_recent_scores(limit=30)
        if not recent:
            return 0.5
        with_outcome = [s for s in recent if s.accuracy > 0]
        if not with_outcome:
            return 0.5
        avg_accuracy = sum(s.accuracy for s in with_outcome) / len(with_outcome)
        return max(0.0, min(1.0, avg_accuracy))

    def _compute_traceability(self) -> float:
        if not self._narrative:
            return 0.5
        events = self._narrative.get_timeline(limit=100)
        if not events:
            return 0.5
        has_interpretation = sum(1 for e in events if e.interpretation)
        return max(0.0, min(1.0, has_interpretation / len(events)))
