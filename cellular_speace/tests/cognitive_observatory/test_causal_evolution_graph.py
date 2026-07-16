"""Tests for Causal Evolution Graph (L6)."""

from speace_core.cognitive_observatory.models import RelationTypeObs


class TestCausalEvolutionGraph:
    def test_record_genome_expression(self, causal_evolution):
        causal_evolution.record_genome_expression("GENE_A", "rna_a", expression_level=0.8)
        assert causal_evolution._state.node_count() >= 2

    def test_record_decision_outcome(self, causal_evolution):
        d = causal_evolution._state.record_decision("test_decision")
        outcome_id = causal_evolution.record_decision_outcome(d.id, "it worked", ilf_delta=0.05)
        edges = causal_evolution._state.get_edges_out(d.id)
        assert len(edges) == 1
        assert edges[0].relation == RelationTypeObs.CAUSED

    def test_record_ilf_change(self, causal_evolution):
        d = causal_evolution._state.record_decision("d1")
        causal_evolution.record_ilf_change(0.5, 0.7, cause_node_id=d.id)
        edges = causal_evolution._state.get_edges_out(d.id)
        ilf_edges = [e for e in edges if e.relation == RelationTypeObs.CHANGED_ILF]
        assert len(ilf_edges) >= 1

    def test_record_learning_from_outcome(self, causal_evolution):
        d = causal_evolution._state.record_decision("d1")
        outcome_id = causal_evolution.record_decision_outcome(d.id, "outcome")
        learning_id = causal_evolution.record_learning_from_outcome(outcome_id, "learned X")
        edges = causal_evolution._state.get_edges_out(learning_id)
        assert len(edges) == 1
        assert edges[0].relation == RelationTypeObs.LEARNED_FROM

    def test_record_mutation_from_learning(self, causal_evolution):
        d = causal_evolution._state.record_decision("d1")
        outcome_id = causal_evolution.record_decision_outcome(d.id, "outcome")
        learning_id = causal_evolution.record_learning_from_outcome(outcome_id, "learned X")
        mutation_id = causal_evolution.record_mutation_from_learning(learning_id, "gene mutated")
        edges = causal_evolution._state.get_edges_out(learning_id)
        mutation_edges = [e for e in edges if e.relation == RelationTypeObs.RESULTED_IN_MUTATION]
        assert len(mutation_edges) >= 1

    def test_record_full_causal_chain(self, causal_evolution):
        d = causal_evolution._state.record_decision("test decision")
        chain = causal_evolution.record_full_causal_chain(
            gene="GENE_A",
            decision="decided X",
            decision_id=d.id,
            outcome="it worked",
            ilf_before=0.5,
            ilf_after=0.7,
            learning="learned to do X",
            mutation="mutated GENE_A",
        )
        assert "decision" in chain
        assert "outcome" in chain
        assert "learning" in chain
        assert "mutation" in chain

    def test_trace_genome_to_behavior(self, causal_evolution):
        causal_evolution.record_genome_expression("GENE_X", "rna_x")
        trace = causal_evolution.trace_genome_to_behavior("GENE_X")
        assert trace is not None

    def test_trace_behavior_to_genome(self, causal_evolution):
        d = causal_evolution._state.record_decision("important_decision")
        causal_evolution.record_decision_outcome(d.id, "important_outcome")
        trace = causal_evolution.trace_behavior_to_genome("important_decision")
        assert trace is not None

    def test_compare_time_periods(self, causal_evolution):
        comparison = causal_evolution.compare_time_periods(days=30)
        assert "recent_count" in comparison
        assert "older_count" in comparison
