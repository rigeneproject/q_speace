import time
from typing import Any, Dict, List, Optional

import structlog

from speace_core.cognitive_observatory.models import (
    SelfInterpretation,
    NarrativeEvent,
    CognitiveNodeObs,
    NodeTypeObs,
)
from speace_core.cognitive_observatory.persistence.observatory_store import ObservatoryStore
from speace_core.cognitive_observatory.cognitive_state_graph import CognitiveStateGraph
from speace_core.cognitive_observatory.narrative_memory import NarrativeMemory

logger = structlog.get_logger(__name__)


class SelfInterpretationEngine:
    """L7 — Self Interpretation Engine.

    For every important event, generates a structured explanation:
    What happened, why it happened, contributing factors, evidence,
    learning, and recommendations.

    Inspired by the Self Interpretation Module from the SCI paper.
    """

    def __init__(
        self,
        store: Optional[ObservatoryStore] = None,
        state_graph: Optional[CognitiveStateGraph] = None,
        narrative: Optional[NarrativeMemory] = None,
    ) -> None:
        self._store = store or ObservatoryStore()
        self._state = state_graph
        self._narrative = narrative

    # ------------------------------------------------------------------ #
    # Interpretation generation
    # ------------------------------------------------------------------ #

    def interpret_event(
        self,
        event_id: str,
        what: str,
        why: str = "",
        contributing_factors: Optional[List[str]] = None,
        supporting_evidence: Optional[List[str]] = None,
        learning: str = "",
        coherence_impact: float = 0.0,
        recommendation: str = "",
    ) -> SelfInterpretation:
        interp = SelfInterpretation(
            event_id=event_id,
            what=what,
            why=why or self._generate_why(event_id),
            contributing_factors=contributing_factors or self._find_contributing_factors(event_id),
            supporting_evidence=supporting_evidence or self._find_evidence(event_id),
            learning=learning,
            coherence_impact=coherence_impact,
            recommendation=recommendation or self._generate_recommendation(event_id),
        )
        self._store.put_interpretation(interp)
        return interp

    def interpret_narrative_event(
        self, event: NarrativeEvent,
    ) -> SelfInterpretation:
        return self.interpret_event(
            event_id=event.id,
            what=event.description,
            why=event.interpretation or f"Event of type '{event.event_type}' occurred",
            contributing_factors=event.causal_parents,
            learning=event.learning,
            coherence_impact=event.cci_delta or event.ilf_delta,
        )

    # ------------------------------------------------------------------ #
    # Automatic interpretation methods
    # ------------------------------------------------------------------ #

    def _generate_why(self, event_id: str) -> str:
        if self._state:
            upstream = self._state.trace_upstream(event_id, max_depth=3)
            if upstream.nodes:
                names = [n.name for n in upstream.nodes[1:4]]
                if names:
                    return f"Influenced by: {', '.join(names)}"
        return "Reason not yet determined"

    def _find_contributing_factors(self, event_id: str) -> List[str]:
        factors = []
        if self._state:
            for edge in self._state.get_edges_in(event_id):
                source = self._state.get_node(edge.source_id)
                if source:
                    factors.append(f"{edge.relation.value}: {source.name}")
        return factors[:5]

    def _find_evidence(self, event_id: str) -> List[str]:
        evidence = []
        if self._state:
            node = self._state.get_node(event_id)
            if node and node.metadata:
                for key, value in list(node.metadata.items())[:5]:
                    evidence.append(f"{key}: {value}")
            for edge in self._state.get_edges_out(event_id):
                target = self._state.get_node(edge.target_id)
                if target:
                    evidence.append(
                        f"→ {edge.relation.value}: {target.name}"
                    )
        return evidence[:5]

    def _generate_recommendation(self, event_id: str) -> str:
        if self._state:
            node = self._state.get_node(event_id)
            if node:
                if node.node_type == NodeTypeObs.ERROR:
                    return (
                        "Analyze upstream causes, add validation before "
                        "this point, and update the self-model weakness list."
                    )
                elif node.node_type == NodeTypeObs.DECISION:
                    return "Verify outcome and record metacognitive score."
                elif node.node_type == NodeTypeObs.LEARNING_EVENT:
                    return "Consider whether this learning should trigger a genome update or BCEL change."
        return "No specific recommendation."

    # ------------------------------------------------------------------ #
    # Query
    # ------------------------------------------------------------------ #

    def get_interpretation(self, event_id: str) -> Optional[SelfInterpretation]:
        return self._store.get_interpretation(event_id)

    def get_all_interpretations(self) -> List[SelfInterpretation]:
        return self._store.get_all_interpretations()

    def get_recent_interpretations(self, limit: int = 20) -> List[SelfInterpretation]:
        all_interps = self._store.get_all_interpretations()
        sorted_interps = sorted(
            all_interps, key=lambda i: i.timestamp, reverse=True
        )
        return sorted_interps[:limit]

    def explain_cci_change(self, cci_delta: float, context: str = "") -> SelfInterpretation:
        """Generate an interpretation for a CCI change."""
        why = "CCI decreased" if cci_delta < 0 else "CCI increased"
        if context:
            why += f" due to: {context}"
        return self.interpret_event(
            event_id=f"cci_change:{int(time.time() * 1000)}",
            what=f"CCI changed by {cci_delta:+.3f}",
            why=why,
            coherence_impact=cci_delta,
            learning="",
        )

    def summarize_self_understanding(self) -> Dict[str, Any]:
        interpretations = self.get_recent_interpretations(limit=50)
        return {
            "recent_interpretations": len(interpretations),
            "error_interpretations": sum(
                1 for i in interpretations if "error" in i.what.lower()
            ),
            "learning_extracted": sum(1 for i in interpretations if i.learning),
            "avg_coherence_impact": (
                sum(i.coherence_impact for i in interpretations) / len(interpretations)
                if interpretations else 0.0
            ),
        }
