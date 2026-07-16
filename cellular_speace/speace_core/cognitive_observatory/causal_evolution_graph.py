import time
from typing import Any, Dict, List, Optional

import structlog

from speace_core.cognitive_observatory.models import (
    CognitiveNodeObs,
    CognitiveEdgeObs,
    NodeTypeObs,
    RelationTypeObs,
    CausalPath,
)
from speace_core.cognitive_observatory.cognitive_state_graph import CognitiveStateGraph

logger = structlog.get_logger(__name__)


class CausalEvolutionGraph:
    """L6 — Causal Evolution Graph.

    Traces the full causal chain: Genome → Expression → Decision → Action →
    Outcome → ILF Change → Learning → Mutation.

    Answers: "Why am I behaving differently than 30 days ago?"
    """

    def __init__(self, state_graph: CognitiveStateGraph) -> None:
        self._state = state_graph

    # ------------------------------------------------------------------ #
    # Recording causal chains
    # ------------------------------------------------------------------ #

    def record_genome_expression(
        self, gene_name: str, rna_name: str, expression_level: float = 1.0,
    ) -> None:
        gene_node = self._state.record_thought(
            name=f"Gene: {gene_name}",
            description=f"Gene {gene_name} expressed",
            metadata={"gene": gene_name, "expression_level": expression_level},
            subsystem="genome",
        )
        rna_node = self._state.record_thought(
            name=f"RNA: {rna_name}",
            description=f"RNA transcript {rna_name}",
            metadata={"rna": rna_name},
            subsystem="digital_rna",
        )
        self._state.link_generated(gene_node.id, rna_node.id)

    def record_decision_outcome(
        self, decision_node_id: str, outcome_description: str,
        ilf_delta: float = 0.0,
    ) -> str:
        outcome = self._state.record_thought(
            name=f"Outcome: {outcome_description[:50]}",
            description=outcome_description,
            metadata={"ilf_delta": ilf_delta},
            subsystem="outcome",
        )
        self._state.link_causal(decision_node_id, outcome.id)
        return outcome.id

    def record_ilf_change(
        self, previous_value: float, new_value: float,
        cause_node_id: Optional[str] = None,
    ) -> None:
        delta = new_value - previous_value
        ilf_node = self._state.record_thought(
            name=f"ILF: {previous_value:.3f} → {new_value:.3f}",
            description=f"ILF changed by {delta:+.3f}",
            metadata={"previous": previous_value, "new": new_value, "delta": delta},
            subsystem="ilf",
        )
        if cause_node_id:
            self._state.relate(cause_node_id, ilf_node.id, RelationTypeObs.CHANGED_ILF)

    def record_learning_from_outcome(
        self, outcome_node_id: str, learning_description: str,
    ) -> str:
        learning = self._state.record_learning(
            name=learning_description[:50],
            description=learning_description,
            subsystem="evolution",
        )
        self._state.link_learned_from(learning.id, outcome_node_id)
        return learning.id

    def record_mutation_from_learning(
        self, learning_node_id: str, mutation_description: str,
    ) -> str:
        mutation = self._state.record_thought(
            name=f"Mutation: {mutation_description[:50]}",
            description=mutation_description,
            node_type=NodeTypeObs.MUTATION_EVENT,
            subsystem="evolution",
        )
        self._state.relate(
            learning_node_id, mutation.id, RelationTypeObs.RESULTED_IN_MUTATION
        )
        return mutation.id

    # ------------------------------------------------------------------ #
    # Full causal chain recording
    # ------------------------------------------------------------------ #

    def record_full_causal_chain(
        self,
        gene: str,
        decision: str,
        decision_id: str,
        outcome: str,
        ilf_before: float,
        ilf_after: float,
        learning: str,
        mutation: Optional[str] = None,
    ) -> Dict[str, str]:
        """Record a complete genome→expression→decision→outcome→ILF→learning→mutation chain."""
        chain = {}
        chain["decision"] = decision_id
        outcome_id = self.record_decision_outcome(decision_id, outcome, ilf_after - ilf_before)
        chain["outcome"] = outcome_id
        self.record_ilf_change(ilf_before, ilf_after, outcome_id)
        learning_id = self.record_learning_from_outcome(outcome_id, learning)
        chain["learning"] = learning_id
        if mutation:
            mutation_id = self.record_mutation_from_learning(learning_id, mutation)
            chain["mutation"] = mutation_id
        return chain

    # ------------------------------------------------------------------ #
    # Queries
    # ------------------------------------------------------------------ #

    def trace_genome_to_behavior(
        self, gene_name: str, max_depth: int = 10,
    ) -> Optional[CausalPath]:
        """Trace from a gene name to its behavioral effects."""
        for node in self._state.search_nodes(gene_name):
            if node.node_type in {NodeTypeObs.THOUGHT, NodeTypeObs.MUTATION_EVENT}:
                return self._state.trace_downstream(node.id, max_depth=max_depth)
        return None

    def trace_behavior_to_genome(
        self, behavior_keyword: str, max_depth: int = 10,
    ) -> Optional[CausalPath]:
        """Trace from a behavior/outcome back to its genome origins."""
        for node in self._state.search_nodes(behavior_keyword):
            return self._state.trace_upstream(node.id, max_depth=max_depth)
        return None

    def compare_time_periods(self, days: int = 30) -> Dict[str, Any]:
        """Compare current behavior patterns with an earlier period."""
        now = time.time()
        past = now - (days * 86400)
        recent_nodes = [
            n for n in self._state.get_recent_nodes(limit=500)
            if n.timestamp > past
        ]
        older_nodes = [
            n for n in self._state.get_recent_nodes(limit=500)
            if n.timestamp <= past
        ]
        return {
            "recent_count": len(recent_nodes),
            "older_count": len(older_nodes),
            "recent_errors": sum(1 for n in recent_nodes if n.node_type == NodeTypeObs.ERROR),
            "older_errors": sum(1 for n in older_nodes if n.node_type == NodeTypeObs.ERROR),
            "recent_learnings": sum(1 for n in recent_nodes if n.node_type == NodeTypeObs.LEARNING_EVENT),
            "older_learnings": sum(1 for n in older_nodes if n.node_type == NodeTypeObs.LEARNING_EVENT),
            "period_days": days,
        }
