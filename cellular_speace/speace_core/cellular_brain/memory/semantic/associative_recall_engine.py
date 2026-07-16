import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from speace_core.cellular_brain.memory.morphological_memory import MorphologicalMemory
from speace_core.cellular_brain.memory.morphology_events import MorphologyEvent, MorphologyEventType
from speace_core.cellular_brain.memory.semantic.assembly_association import (
    AssemblyAssociation,
    AssociativeRecallResult,
)
from speace_core.cellular_brain.memory.semantic.associative_learning_engine import (
    AssociativeLearningEngine,
)
from speace_core.cellular_brain.memory.semantic.semantic_memory_store import (
    SemanticMemoryStore,
)


class AssociativeRecallEngine:
    """T44 — Recall assemblies linked via associations from a cue assembly or pattern."""

    def __init__(
        self,
        association_engine: AssociativeLearningEngine,
        assembly_store: Optional[SemanticMemoryStore] = None,
        memory: Optional[MorphologicalMemory] = None,
        recall_threshold: float = 0.25,
        max_recall: int = 3,
    ):
        self.association_engine = association_engine
        self.assembly_store = assembly_store
        self.memory = memory
        self.recall_threshold = recall_threshold
        self.max_recall = max_recall

    # ------------------------------------------------------------------ #
    # Recall
    # ------------------------------------------------------------------ #

    def recall_from_assembly(
        self, cue_assembly_id: str
    ) -> AssociativeRecallResult:
        candidates = self.association_engine.get_associations_for_source(
            cue_assembly_id
        )
        scored = [(a, self.score_association(a)) for a in candidates]
        scored.sort(key=lambda x: x[1], reverse=True)

        recalled_ids: List[str] = []
        recall_scores: Dict[str, float] = {}
        best_match_id: Optional[str] = None
        best_match_score = 0.0

        for assoc, score in scored[: self.max_recall]:
            if score < self.recall_threshold:
                continue
            target = (
                assoc.target_assembly_id
                if assoc.source_assembly_id == cue_assembly_id
                else assoc.source_assembly_id
            )
            recalled_ids.append(target)
            recall_scores[target] = score
            if score > best_match_score:
                best_match_score = score
                best_match_id = target

        success = best_match_score >= self.recall_threshold
        partial = len(recalled_ids) > 0 and not success

        # Update association success/failure counts
        for assoc, score in scored:
            target = (
                assoc.target_assembly_id
                if assoc.source_assembly_id == cue_assembly_id
                else assoc.source_assembly_id
            )
            if target in recalled_ids:
                assoc.recall_success_count += 1
            else:
                # Only count as failure if it was a candidate above a low bar
                if score >= self.recall_threshold * 0.5:
                    assoc.recall_failure_count += 1

        result = AssociativeRecallResult(
            cue_assembly_id=cue_assembly_id,
            recalled_assembly_ids=recalled_ids,
            recall_scores=recall_scores,
            best_match_id=best_match_id,
            best_match_score=best_match_score,
            success=success,
            partial_success=partial,
        )

        self._log_recall_event(result)
        return result

    def recall_from_pattern(
        self,
        pattern: List[float],
        semantic_recall_engine=None,
    ) -> AssociativeRecallResult:
        """First do semantic recall to find a cue assembly, then associative recall."""
        if semantic_recall_engine is None:
            return AssociativeRecallResult(
                cue_assembly_id="",
                success=False,
                partial_success=False,
            )
        semantic_result = semantic_recall_engine.recall(pattern)
        if not semantic_result.recall_success or not semantic_result.best_match_id:
            return AssociativeRecallResult(
                cue_assembly_id="",
                success=False,
                partial_success=False,
            )
        return self.recall_from_assembly(semantic_result.best_match_id)

    # ------------------------------------------------------------------ #
    # Scoring
    # ------------------------------------------------------------------ #

    @staticmethod
    def score_association(association: AssemblyAssociation) -> float:
        total_recalls = max(
            1, association.recall_success_count + association.recall_failure_count
        )
        normalized_success = association.recall_success_count / total_recalls
        normalized_failure = association.recall_failure_count / total_recalls
        score = (
            0.50 * association.strength
            + 0.25 * association.confidence
            + 0.15 * normalized_success
            - 0.10 * normalized_failure
        )
        return max(0.0, min(1.0, score))

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _log_recall_event(self, result: AssociativeRecallResult) -> None:
        if self.memory is None or not hasattr(self.memory, "log_event"):
            return
        event_type = (
            MorphologyEventType.ASSOCIATIVE_RECALL_SUCCEEDED
            if result.success
            else MorphologyEventType.ASSOCIATIVE_RECALL_FAILED
            if not result.partial_success
            else MorphologyEventType.ASSOCIATIVE_RECALL_ATTEMPTED
        )
        try:
            event = MorphologyEvent(
                event_id=f"evt-{uuid.uuid4().hex[:8]}",
                event_type=event_type,
                timestamp=datetime.now(timezone.utc).timestamp(),
                metadata={
                    "cue_assembly_id": result.cue_assembly_id,
                    "recalled_assembly_ids": result.recalled_assembly_ids,
                    "best_match_id": result.best_match_id,
                    "best_match_score": result.best_match_score,
                    "recall_score": result.best_match_score,
                    "success": result.success,
                    "partial_success": result.partial_success,
                },
            )
            self.memory.log_event(event)
        except Exception:
            pass
