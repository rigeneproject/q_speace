"""Tests for Cognitive Self Observatory data models."""

import pytest

from speace_core.cognitive_observatory.models import (
    CognitiveNodeObs,
    CognitiveEdgeObs,
    NodeTypeObs,
    RelationTypeObs,
    SelfModel,
    NarrativeEvent,
    MetacognitiveScore,
    CCIComponents,
    SelfInterpretation,
    CausalPath,
)


class TestNodeTypeObs:
    def test_values(self):
        assert NodeTypeObs.THOUGHT.value == "thought"
        assert NodeTypeObs.DECISION.value == "decision"
        assert NodeTypeObs.GOAL.value == "goal"
        assert NodeTypeObs.ERROR.value == "error"
        assert NodeTypeObs.LEARNING_EVENT.value == "learning_event"

    def test_all_types_present(self):
        expected = {
            "thought", "decision", "goal", "memory_state", "belief",
            "hypothesis", "mutation_event", "action", "error",
            "learning_event", "narrative_event",
        }
        actual = {t.value for t in NodeTypeObs}
        assert actual == expected


class TestCognitiveNodeObs:
    def test_create_minimal(self):
        node = CognitiveNodeObs(id="test:1", node_type=NodeTypeObs.THOUGHT, name="Test")
        assert node.id == "test:1"
        assert node.name == "Test"
        assert node.node_type == NodeTypeObs.THOUGHT

    def test_default_timestamp(self):
        node = CognitiveNodeObs(id="t:1", node_type=NodeTypeObs.DECISION, name="D")
        assert node.timestamp > 0

    def test_source_subsystem(self):
        node = CognitiveNodeObs(
            id="t:1", node_type=NodeTypeObs.ERROR, name="E", source_subsystem="test",
        )
        assert node.source_subsystem == "test"


class TestCognitiveEdgeObs:
    def test_create(self):
        edge = CognitiveEdgeObs(
            source_id="src:1", target_id="tgt:1", relation=RelationTypeObs.CAUSED,
        )
        assert edge.source_id == "src:1"
        assert edge.target_id == "tgt:1"
        assert edge.relation == RelationTypeObs.CAUSED
        assert edge.weight == 1.0

    def test_custom_weight(self):
        edge = CognitiveEdgeObs(
            source_id="a", target_id="b", relation=RelationTypeObs.INFLUENCED, weight=0.5,
        )
        assert edge.weight == 0.5


class TestSelfModel:
    def test_empty(self):
        m = SelfModel()
        assert m.identity == {}
        assert m.active_goals == []
        assert m.capabilities == {}

    def test_with_data(self):
        m = SelfModel(
            identity={"entity_name": "SPEACE"},
            active_goals=[{"name": "test_goal"}],
            capabilities={"reasoning": 0.8},
            known_weaknesses=["poor_memory"],
        )
        assert m.identity["entity_name"] == "SPEACE"
        assert len(m.active_goals) == 1
        assert m.capabilities["reasoning"] == 0.8


class TestNarrativeEvent:
    def test_create(self):
        e = NarrativeEvent(
            id="n:1",
            event_type="decision",
            description="Test decision",
            interpretation="Because X",
            consequence="Result Y",
            learning="Learned Z",
        )
        assert e.id == "n:1"
        assert e.event_type == "decision"
        assert e.learning == "Learned Z"

    def test_causal_parents(self):
        e = NarrativeEvent(id="n:1", event_type="error", description="err")
        assert e.causal_parents == []
        e.causal_parents = ["n:0"]
        assert len(e.causal_parents) == 1


class TestCCIComponents:
    def test_default_values(self):
        c = CCIComponents()
        assert c.c_memory == 0.5
        assert c.c_identity == 0.5
        assert c.compute() == pytest.approx(0.5)  # all equal weights * 0.5

    def test_compute_max(self):
        c = CCIComponents(
            c_memory=1.0, c_identity=1.0, c_reasoning=1.0,
            c_learning=1.0, c_prediction=1.0, c_traceability=1.0,
        )
        assert c.compute() == pytest.approx(1.0)

    def test_compute_min(self):
        c = CCIComponents(
            c_memory=0.0, c_identity=0.0, c_reasoning=0.0,
            c_learning=0.0, c_prediction=0.0, c_traceability=0.0,
        )
        assert c.compute() == pytest.approx(0.0)

    def test_clamped(self):
        c = CCIComponents(c_memory=-0.5, c_identity=1.5)
        val = c.compute()
        assert 0.0 <= val <= 1.0


class TestMetacognitiveScore:
    def test_create(self):
        s = MetacognitiveScore(
            decision_id="d:1",
            confidence=0.8,
            accuracy=0.7,
            context_completeness=0.9,
        )
        assert s.decision_id == "d:1"
        assert s.confidence == 0.8
        assert s.accuracy == 0.7

    def test_defaults(self):
        s = MetacognitiveScore(decision_id="d:1")
        assert s.confidence == 0.0
        assert s.subsequent_errors == 0


class TestSelfInterpretation:
    def test_create(self):
        i = SelfInterpretation(
            event_id="e:1",
            what="Something happened",
            why="Because of X",
            learning="Do Y next time",
            coherence_impact=-0.1,
            recommendation="Add validation",
        )
        assert i.event_id == "e:1"
        assert i.coherence_impact == -0.1
        assert "validation" in i.recommendation


class TestCausalPath:
    def test_empty(self):
        p = CausalPath(start_id="s:1", end_id="t:1")
        assert p.nodes == []
        assert p.edges == []
        assert p.depth == 0

    def test_with_path(self):
        n1 = CognitiveNodeObs(id="s:1", node_type=NodeTypeObs.THOUGHT, name="start")
        n2 = CognitiveNodeObs(id="t:1", node_type=NodeTypeObs.THOUGHT, name="end")
        e1 = CognitiveEdgeObs(
            source_id="s:1", target_id="t:1", relation=RelationTypeObs.CAUSED,
        )
        p = CausalPath(
            nodes=[n1, n2], edges=[e1], start_id="s:1", end_id="t:1", depth=1,
            description="test path",
        )
        assert len(p.nodes) == 2
        assert len(p.edges) == 1
        assert p.description == "test path"
