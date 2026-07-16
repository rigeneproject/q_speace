import time
from typing import Any, Dict, List, Optional

import structlog

from speace_core.cognitive_observatory.models import (
    NarrativeEvent,
    CognitiveNodeObs,
    NodeTypeObs,
    RelationTypeObs,
)
from speace_core.cognitive_observatory.persistence.observatory_store import ObservatoryStore

logger = structlog.get_logger(__name__)


class NarrativeMemory:
    """L3 — Narrative Memory.

    Each significant event produces: event → interpretation → consequence → learning.
    Maintains a causally-linked timeline of the organism's history.
    """

    def __init__(self, store: Optional[ObservatoryStore] = None) -> None:
        self._store = store or ObservatoryStore()

    # ------------------------------------------------------------------ #
    # Recording
    # ------------------------------------------------------------------ #

    def record_event(
        self,
        event_type: str,
        description: str,
        interpretation: str = "",
        consequence: str = "",
        learning: str = "",
        causal_parents: Optional[List[str]] = None,
        evidence_refs: Optional[List[str]] = None,
        ilf_delta: float = 0.0,
        cci_delta: float = 0.0,
        subsystem: str = "",
    ) -> NarrativeEvent:
        event = NarrativeEvent(
            id=f"narrative:{int(time.time() * 1000)}:{hash(description) % 100000}",
            event_type=event_type,
            description=description,
            interpretation=interpretation,
            consequence=consequence,
            learning=learning,
            causal_parents=causal_parents or [],
            evidence_refs=evidence_refs or [],
            ilf_delta=ilf_delta,
            cci_delta=cci_delta,
            subsystem=subsystem,
        )
        self._store.put_narrative_event(event)
        return event

    def record_mutation_event(
        self,
        description: str,
        interpretation: str = "",
        consequence: str = "",
        learning: str = "",
        ilf_delta: float = 0.0,
    ) -> NarrativeEvent:
        return self.record_event(
            event_type="mutation",
            description=description,
            interpretation=interpretation,
            consequence=consequence,
            learning=learning,
            ilf_delta=ilf_delta,
            subsystem="evolution",
        )

    def record_decision_event(
        self,
        description: str,
        interpretation: str = "",
        consequence: str = "",
        learning: str = "",
        cci_delta: float = 0.0,
    ) -> NarrativeEvent:
        return self.record_event(
            event_type="decision",
            description=description,
            interpretation=interpretation,
            consequence=consequence,
            learning=learning,
            cci_delta=cci_delta,
            subsystem="cognitive",
        )

    def record_error_event(
        self,
        description: str,
        interpretation: str = "",
        consequence: str = "",
        learning: str = "",
        ilf_delta: float = 0.0,
    ) -> NarrativeEvent:
        return self.record_event(
            event_type="error",
            description=description,
            interpretation=interpretation,
            consequence=consequence,
            learning=learning,
            ilf_delta=ilf_delta,
            subsystem="monitoring",
        )

    def record_learning_event(
        self,
        description: str,
        interpretation: str = "",
        consequence: str = "",
        learning: str = "",
        cci_delta: float = 0.0,
    ) -> NarrativeEvent:
        return self.record_event(
            event_type="learning",
            description=description,
            interpretation=interpretation,
            consequence=consequence,
            learning=learning,
            cci_delta=cci_delta,
            subsystem="metacognitive",
        )

    def record_adaptation_event(
        self,
        description: str,
        interpretation: str = "",
        consequence: str = "",
        learning: str = "",
        ilf_delta: float = 0.0,
    ) -> NarrativeEvent:
        return self.record_event(
            event_type="adaptation",
            description=description,
            interpretation=interpretation,
            consequence=consequence,
            learning=learning,
            ilf_delta=ilf_delta,
            subsystem="ilf",
        )

    # ------------------------------------------------------------------ #
    # Query
    # ------------------------------------------------------------------ #

    def get_timeline(
        self, limit: int = 100, event_type: Optional[str] = None,
    ) -> List[NarrativeEvent]:
        return self._store.get_narrative_timeline(limit=limit, event_type=event_type)

    def get_events_by_type(self, event_type: str) -> List[NarrativeEvent]:
        return self._store.get_narrative_timeline(limit=1000, event_type=event_type)

    def get_recent_errors(self, limit: int = 20) -> List[NarrativeEvent]:
        return self._store.get_narrative_timeline(limit=limit, event_type="error")

    def get_event(self, event_id: str) -> Optional[NarrativeEvent]:
        return self._store.get_narrative_event(event_id)

    def get_causal_chain(self, event_id: str, max_depth: int = 5) -> List[NarrativeEvent]:
        """Get the causal chain starting from an event (follow causal_parents)."""
        chain: List[NarrativeEvent] = []
        current_id = event_id
        for _ in range(max_depth):
            event = self.get_event(current_id)
            if not event:
                break
            chain.append(event)
            if event.causal_parents:
                current_id = event.causal_parents[0]
            else:
                break
        return chain

    # ------------------------------------------------------------------ #
    # Analysis
    # ------------------------------------------------------------------ #

    def get_learning_effectiveness(self, window: int = 50) -> float:
        """Proportion of events that produced learning."""
        events = self._store.get_narrative_timeline(limit=window)
        if not events:
            return 0.5
        has_learning = sum(1 for e in events if e.learning)
        return has_learning / len(events)

    def get_event_count_by_type(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for event in self._store.get_all_narrative_events():
            counts[event.event_type] = counts.get(event.event_type, 0) + 1
        return counts

    def clear(self) -> None:
        pass  # Events are managed by store
