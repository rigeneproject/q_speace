import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from speace_core.cellular_brain.memory.morphological_memory import MorphologicalMemory
from speace_core.cellular_brain.memory.morphology_events import MorphologyEvent, MorphologyEventType
from speace_core.cellular_brain.memory.semantic.assembly_association import (
    AssemblyAssociation,
    AssociativeLearningResult,
)


class AssociativeLearningEngine:
    """T44 — Learn and maintain associative links between cell assemblies."""

    def __init__(
        self,
        memory: Optional[MorphologicalMemory] = None,
        learning_rate: float = 0.08,
        decay_rate: float = 0.02,
        min_strength: float = 0.0,
        max_strength: float = 1.0,
        coactivation_window: int = 3,
        prune_threshold: float = 0.03,
    ):
        self.memory = memory
        self.learning_rate = learning_rate
        self.decay_rate = decay_rate
        self.min_strength = min_strength
        self.max_strength = max_strength
        self.coactivation_window = coactivation_window
        self.prune_threshold = prune_threshold
        self._associations: Dict[str, AssemblyAssociation] = {}
        self._activation_history: List[tuple] = []  # (tick, List[assembly_id])

    # ------------------------------------------------------------------ #
    # Observation
    # ------------------------------------------------------------------ #

    def observe_assemblies(
        self, active_assemblies: List[Any], tick: int
    ) -> AssociativeLearningResult:
        result = AssociativeLearningResult()
        if len(active_assemblies) < 2:
            return result

        ids = sorted({
            getattr(a, "assembly_id", str(a))
            for a in active_assemblies
        })
        self._activation_history.append((tick, ids))
        # Keep only relevant history
        cutoff = tick - self.coactivation_window
        self._activation_history = [
            (t, asms) for t, asms in self._activation_history if t >= cutoff
        ]

        # Build co-activation pairs within window
        for t, asms in self._activation_history:
            for i, src in enumerate(asms):
                for tgt in asms[i + 1:]:
                    if src == tgt:
                        continue
                    assoc = self._find_or_create(src, tgt)
                    if assoc.coactivation_count == 0:
                        result.created_associations += 1
                    else:
                        result.reinforced_associations += 1
                    self._reinforce(assoc, self.learning_rate)

        result.events_logged = (
            result.created_associations + result.reinforced_associations
        )
        return result

    # ------------------------------------------------------------------ #
    # CRUD
    # ------------------------------------------------------------------ #

    def create_or_get_association(
        self, source_id: str, target_id: str, association_type: str = "temporal"
    ) -> AssemblyAssociation:
        return self._find_or_create(source_id, target_id, association_type)

    def reinforce_association(
        self, association_id: str, amount: Optional[float] = None
    ) -> Optional[AssemblyAssociation]:
        assoc = self._associations.get(association_id)
        if assoc is None:
            return None
        self._reinforce(assoc, amount or self.learning_rate)
        return assoc

    def weaken_association(
        self, association_id: str, amount: Optional[float] = None
    ) -> Optional[AssemblyAssociation]:
        assoc = self._associations.get(association_id)
        if assoc is None:
            return None
        delta = amount or self.learning_rate * 0.5
        assoc.strength = max(self.min_strength, assoc.strength - delta)
        self._log_event(
            MorphologyEventType.ASSEMBLY_ASSOCIATION_WEAKENED,
            {
                "association_id": assoc.id,
                "source_assembly_id": assoc.source_assembly_id,
                "target_assembly_id": assoc.target_assembly_id,
                "association_strength": assoc.strength,
                "association_confidence": assoc.confidence,
                "association_type": assoc.association_type,
            },
        )
        return assoc

    def decay_associations(self) -> AssociativeLearningResult:
        result = AssociativeLearningResult()
        for assoc in list(self._associations.values()):
            old = assoc.strength
            assoc.strength = max(self.min_strength, assoc.strength - self.decay_rate)
            if assoc.strength < old:
                result.weakened_associations += 1
        return result

    def prune_weak_associations(self) -> AssociativeLearningResult:
        result = AssociativeLearningResult()
        to_remove = [
            aid
            for aid, assoc in self._associations.items()
            if assoc.strength <= self.prune_threshold
        ]
        for aid in to_remove:
            assoc = self._associations.pop(aid)
            result.pruned_associations += 1
            self._log_event(
                MorphologyEventType.ASSEMBLY_ASSOCIATION_PRUNED,
                {
                    "association_id": assoc.id,
                    "source_assembly_id": assoc.source_assembly_id,
                    "target_assembly_id": assoc.target_assembly_id,
                    "association_strength": assoc.strength,
                    "association_confidence": assoc.confidence,
                    "association_type": assoc.association_type,
                },
            )
        return result

    def list_associations(self) -> List[AssemblyAssociation]:
        return list(self._associations.values())

    def get_associations_for_source(self, source_assembly_id: str) -> List[AssemblyAssociation]:
        return [
            a
            for a in self._associations.values()
            if a.source_assembly_id == source_assembly_id or a.target_assembly_id == source_assembly_id
        ]

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _assoc_key(self, a: str, b: str) -> str:
        return f"assoc_{min(a, b)}_{max(a, b)}"

    def _find_or_create(
        self, source_id: str, target_id: str, association_type: str = "temporal"
    ) -> AssemblyAssociation:
        key = self._assoc_key(source_id, target_id)
        if key in self._associations:
            return self._associations[key]
        assoc = AssemblyAssociation(
            id=key,
            source_assembly_id=source_id,
            target_assembly_id=target_id,
            association_type=association_type,
            strength=0.1,
        )
        self._associations[key] = assoc
        self._log_event(
            MorphologyEventType.ASSEMBLY_ASSOCIATION_CREATED,
            {
                "association_id": assoc.id,
                "source_assembly_id": assoc.source_assembly_id,
                "target_assembly_id": assoc.target_assembly_id,
                "association_strength": assoc.strength,
                "association_confidence": assoc.confidence,
                "association_type": assoc.association_type,
            },
        )
        return assoc

    def _reinforce(self, assoc: AssemblyAssociation, amount: float) -> None:
        assoc.strength = min(self.max_strength, assoc.strength + amount)
        assoc.coactivation_count += 1
        # Confidence grows with coactivations and successful recalls
        assoc.confidence = min(
            1.0,
            0.1 + 0.5 * (assoc.coactivation_count / max(1, assoc.coactivation_count + 5))
            + 0.4 * (assoc.recall_success_count / max(1, assoc.recall_success_count + assoc.recall_failure_count + 1)),
        )
        assoc.last_reinforced_at = datetime.now(timezone.utc).isoformat()
        self._log_event(
            MorphologyEventType.ASSEMBLY_ASSOCIATION_REINFORCED,
            {
                "association_id": assoc.id,
                "source_assembly_id": assoc.source_assembly_id,
                "target_assembly_id": assoc.target_assembly_id,
                "association_strength": assoc.strength,
                "association_confidence": assoc.confidence,
                "association_type": assoc.association_type,
            },
        )

    def _log_event(self, event_type: MorphologyEventType, metadata: Dict[str, Any]) -> None:
        if self.memory is None or not hasattr(self.memory, "log_event"):
            return
        try:
            event = MorphologyEvent(
                event_id=f"evt-{uuid.uuid4().hex[:8]}",
                event_type=event_type,
                timestamp=datetime.now(timezone.utc).timestamp(),
                metadata=metadata,
            )
            self.memory.log_event(event)
        except Exception:
            pass
