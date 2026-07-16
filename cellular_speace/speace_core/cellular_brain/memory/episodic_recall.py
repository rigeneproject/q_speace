import math
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from speace_core.cellular_brain.memory.episodic_memory import Episode, EpisodicMemory
from speace_core.cellular_brain.memory.morphology_events import MorphologyEvent, MorphologyEventType


class EpisodicRecallResult(BaseModel):
    query: str
    matched_episodes: List[Episode] = Field(default_factory=list)
    similarity_scores: List[float] = Field(default_factory=list)
    recurring_patterns: List[str] = Field(default_factory=list)
    recommended_context: Dict[str, Any] = Field(default_factory=dict)


class EpisodicRecall:
    """T47 — Recall and pattern detection from episodic memory."""

    def __init__(
        self,
        episodic_memory: Optional[EpisodicMemory] = None,
        memory=None,
    ):
        self.episodic_memory = episodic_memory
        self.memory = memory

    # ------------------------------------------------------------------ #
    # Recall by outcome
    # ------------------------------------------------------------------ #

    def recall_by_outcome(self, outcome: str) -> List[Episode]:
        if self.episodic_memory is None:
            return []
        episodes = self.episodic_memory.load_episodes()
        results = [ep for ep in episodes if ep.outcome == outcome]
        self._log_event(
            MorphologyEventType.EPISODE_RECALLED,
            {
                "query_type": "outcome",
                "query": outcome,
                "matched_count": len(results),
            },
        )
        return results

    # ------------------------------------------------------------------ #
    # Similarity recall
    # ------------------------------------------------------------------ #

    def recall_similar_metrics(
        self,
        metrics: Dict[str, float],
        top_k: int = 5,
    ) -> EpisodicRecallResult:
        if self.episodic_memory is None:
            return EpisodicRecallResult(query="similar_metrics")

        episodes = self.episodic_memory.load_episodes()
        scored = []
        for ep in episodes:
            score = self._compute_metric_similarity(metrics, ep.final_metrics)
            scored.append((score, ep))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:top_k]

        self._log_event(
            MorphologyEventType.EPISODE_RECALLED,
            {
                "query_type": "similar_metrics",
                "top_k": top_k,
                "matched_count": len(top),
            },
        )

        return EpisodicRecallResult(
            query="similar_metrics",
            matched_episodes=[ep for _, ep in top],
            similarity_scores=[round(s, 4) for s, _ in top],
        )

    @staticmethod
    def _compute_metric_similarity(
        query: Dict[str, float],
        candidate: Dict[str, float],
    ) -> float:
        if not query or not candidate:
            return 0.0
        keys = set(query.keys()) & set(candidate.keys())
        if not keys:
            return 0.0
        # Cosine similarity over shared keys
        dot = sum(query[k] * candidate[k] for k in keys)
        norm_q = math.sqrt(sum(v * v for v in query.values()))
        norm_c = math.sqrt(sum(candidate[k] * candidate[k] for k in keys))
        if norm_q == 0 or norm_c == 0:
            return 0.0
        return dot / (norm_q * norm_c)

    # ------------------------------------------------------------------ #
    # Pattern detection
    # ------------------------------------------------------------------ #

    def find_regression_precursors(self) -> List[str]:
        if self.episodic_memory is None:
            return []
        episodes = self.episodic_memory.load_episodes()
        precursors: List[str] = []
        for ep in episodes:
            if ep.outcome == "regression" or ep.cognitive_delta < -0.03 or ep.phi_delta < -0.03:
                for ev in ep.events:
                    if ev.event_type not in precursors:
                        precursors.append(ev.event_type)
        self._log_event(
            MorphologyEventType.EPISODE_REGRESSION_PRECURSOR_FOUND,
            {"precursor_count": len(precursors)},
        )
        return precursors

    def find_recovery_patterns(self) -> List[str]:
        if self.episodic_memory is None:
            return []
        episodes = self.episodic_memory.load_episodes()
        patterns: List[str] = []
        for ep in episodes:
            if ep.outcome == "recovery" or ep.cognitive_delta > 0 or ep.phi_delta > 0.02:
                for ev in ep.events:
                    if ev.event_type not in patterns:
                        patterns.append(ev.event_type)
        self._log_event(
            MorphologyEventType.EPISODE_RECOVERY_PATTERN_FOUND,
            {"pattern_count": len(patterns)},
        )
        return patterns

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _log_event(
        self,
        event_type: MorphologyEventType,
        metadata: Dict[str, Any],
    ) -> None:
        if self.memory is None or not hasattr(self.memory, "log_event"):
            return
        try:
            event = MorphologyEvent(
                event_id=f"evt-{__import__('uuid').uuid4().hex[:8]}",
                event_type=event_type,
                timestamp=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).timestamp(),
                metadata=metadata,
            )
            self.memory.log_event(event)
        except Exception:
            pass
