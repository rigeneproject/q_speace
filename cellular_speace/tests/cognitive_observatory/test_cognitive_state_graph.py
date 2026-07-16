"""Tests for Cognitive State Graph (L1)."""

import pytest

from speace_core.cognitive_observatory.models import NodeTypeObs, RelationTypeObs


class TestCognitiveStateGraph:
    def test_record_thought(self, state_graph):
        n = state_graph.record_thought("test_thought", "A test thought")
        assert n.node_type == NodeTypeObs.THOUGHT
        assert state_graph.node_count() == 1

    def test_record_decision(self, state_graph):
        n = state_graph.record_decision("test_decision", "A test decision", subsystem="test")
        assert n.node_type == NodeTypeObs.DECISION
        assert n.source_subsystem == "test"

    def test_record_goal(self, state_graph):
        n = state_graph.record_goal("test_goal", "A test goal")
        assert n.node_type == NodeTypeObs.GOAL

    def test_record_belief(self, state_graph):
        n = state_graph.record_belief("test_belief", "I believe X", confidence=0.8)
        assert n.node_type == NodeTypeObs.BELIEF
        assert n.metadata.get("confidence") == 0.8

    def test_record_hypothesis(self, state_graph):
        n = state_graph.record_hypothesis("test_hyp", "H: X causes Y")
        assert n.node_type == NodeTypeObs.HYPOTHESIS

    def test_record_error(self, state_graph):
        n = state_graph.record_error("test_error", "Something broke", severity="critical")
        assert n.node_type == NodeTypeObs.ERROR
        assert n.metadata.get("severity") == "critical"

    def test_record_learning(self, state_graph):
        n = state_graph.record_learning("test_learning", "Learned to check X")
        assert n.node_type == NodeTypeObs.LEARNING_EVENT

    def test_record_action(self, state_graph):
        n = state_graph.record_action("test_action", "Executed task Y")
        assert n.node_type == NodeTypeObs.ACTION

    def test_relate(self, state_graph):
        a = state_graph.record_thought("A")
        b = state_graph.record_thought("B")
        state_graph.relate(a.id, b.id, RelationTypeObs.CAUSED)
        assert state_graph.edge_count() == 1
        assert len(state_graph.get_edges_out(a.id)) == 1

    def test_link_causal(self, state_graph):
        a = state_graph.record_decision("A")
        b = state_graph.record_action("B")
        state_graph.link_causal(a.id, b.id)
        edges = state_graph.get_edges_out(a.id)
        assert len(edges) == 1
        assert edges[0].relation == RelationTypeObs.CAUSED

    def test_link_generated(self, state_graph):
        a = state_graph.record_thought("A")
        b = state_graph.record_thought("B")
        state_graph.link_generated(a.id, b.id)
        assert state_graph.get_edges_out(a.id)[0].relation == RelationTypeObs.GENERATED

    def test_get_node(self, state_graph):
        n = state_graph.record_thought("my_thought")
        assert state_graph.get_node(n.id) is n
        assert state_graph.get_node("nonexistent") is None

    def test_get_nodes_by_type(self, state_graph):
        state_graph.record_thought("t1")
        state_graph.record_thought("t2")
        state_graph.record_decision("d1")
        thoughts = state_graph.get_nodes_by_type(NodeTypeObs.THOUGHT)
        assert len(thoughts) == 2
        decisions = state_graph.get_nodes_by_type(NodeTypeObs.DECISION)
        assert len(decisions) == 1

    def test_search_nodes(self, state_graph):
        state_graph.record_thought("alpha_thought")
        state_graph.record_decision("beta_decision")
        results = state_graph.search_nodes("alpha")
        assert len(results) == 1
        assert results[0].name == "alpha_thought"

    def test_get_nodes_by_subsystem(self, state_graph):
        state_graph.record_decision("d1", subsystem="cognitive")
        state_graph.record_error("e1", subsystem="monitoring")
        state_graph.record_error("e2", subsystem="monitoring")
        assert len(state_graph.get_nodes_by_subsystem("monitoring")) == 2
        assert len(state_graph.get_nodes_by_subsystem("cognitive")) == 1

    def test_get_recent_nodes(self, state_graph):
        for i in range(5):
            state_graph.record_thought(f"t{i}")
        recent = state_graph.get_recent_nodes(limit=3)
        assert len(recent) == 3

    def test_get_error_rate(self, state_graph):
        assert state_graph.get_error_rate() == 0.0
        state_graph.record_thought("t1")
        state_graph.record_error("e1")
        rate = state_graph.get_error_rate(window=10)
        assert rate > 0.0

    def test_trace_causal_path(self, state_graph):
        a = state_graph.record_thought("start")
        b = state_graph.record_decision("middle")
        c = state_graph.record_action("end")
        state_graph.link_causal(a.id, b.id)
        state_graph.link_causal(b.id, c.id)
        path = state_graph.trace_causal_path(a.id, c.id)
        assert path is not None
        assert path.start_id == a.id
        assert path.end_id == c.id

    def test_trace_upstream(self, state_graph):
        a = state_graph.record_thought("cause")
        b = state_graph.record_error("effect")
        state_graph.link_causal(a.id, b.id)
        path = state_graph.trace_upstream(b.id, max_depth=3)
        assert len(path.nodes) >= 2

    def test_trace_downstream(self, state_graph):
        a = state_graph.record_thought("source")
        b = state_graph.record_action("result")
        state_graph.link_causal(a.id, b.id)
        path = state_graph.trace_downstream(a.id, max_depth=3)
        assert len(path.nodes) >= 2

    def test_clear(self, state_graph):
        state_graph.record_thought("t1")
        assert state_graph.node_count() > 0
        state_graph.clear()
        assert state_graph.node_count() == 0
