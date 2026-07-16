"""T172 — Tests for the Information Value Omni-RAG collector + motivation audit."""

import pytest

from speace_core.omni_rag.collectors import InformationValueCollector, motivation_audit
from speace_core.omni_rag.graph import CognitiveGraph
from speace_core.omni_rag.models import NodeType, RelationType


def _seed_graph() -> CognitiveGraph:
    """Build a fresh CognitiveGraph that contains ONLY the snapshot nodes.

    The on-disk persisted graph can contain stale nodes from previous
    runs. To make the test deterministic we copy out only the nodes
    and edges we just produced.
    """
    base = CognitiveGraph()
    snapshot_nodes, snapshot_edges = [], []
    c = InformationValueCollector()
    nodes, edges = c.collect_snapshot(
        {
            "prediction_error": 0.42,
            "novelty": 0.55,
            "informational_entropy": 0.5,
            "signal_diversity": 0.6,
            "surprise": 0.3,
        },
        {
            "energy": 0.7,
            "coherence": 0.6,
            "novelty": 0.55,
        },
    )
    snapshot_nodes = nodes
    snapshot_edges = edges

    g = CognitiveGraph()
    g.clear()
    for n in snapshot_nodes:
        g.add_node(n)
    for e in snapshot_edges:
        g.add_edge(e)
    return g


class TestInformationValueCollector:
    def test_collect_snapshot_returns_nodes_and_edges(self):
        g = CognitiveGraph()
        c = InformationValueCollector()
        nodes, edges = c.collect_snapshot(
            {"prediction_error": 0.4, "novelty": 0.5, "informational_entropy": 0.5},
            {"energy": 0.7, "coherence": 0.7},
        )
        assert len(nodes) >= 3  # H + V + proposal + 4 bcel
        assert len(edges) >= 3

    def test_emits_one_metric_for_entropy(self):
        g = _seed_graph()
        entropy_metrics = [
            n for n in g.get_nodes_by_type(NodeType.METRIC)
            if "perceived_entropy" in (n.tags or [])
            or "perceived_entropy" in (n.name or "")
        ]
        assert len(entropy_metrics) == 1

    def test_emits_value_metric(self):
        g = _seed_graph()
        value_metrics = [
            n for n in g.get_nodes_by_type(NodeType.METRIC)
            if "informational_value" in (n.tags or [])
            or "informational_value" in (n.name or "")
        ]
        assert len(value_metrics) == 1

    def test_emits_decision_proposal(self):
        g = _seed_graph()
        decisions = [
            n for n in g.get_nodes_by_type(NodeType.DECISION)
            if "proposal:" in (n.name or "")
        ]
        assert len(decisions) == 1

    def test_emits_four_bcel_mappings(self):
        g = _seed_graph()
        bcel = g.get_nodes_by_type(NodeType.BCEL_MAPPING)
        expected = {
            "motivational_dopaminergic_loop",
            "curiosity_rnd_signal",
            "free_energy_active_inference",
            "inverted_u_value_function",
        }
        names = {n.name for n in bcel}
        assert expected.issubset(names)


class TestMotivationAudit:
    def test_audit_passes_after_seed(self):
        g = _seed_graph()
        report = motivation_audit(g)
        assert report["pass"] is True
        assert report["perceived_entropy_present"] is True
        assert report["informational_value_present"] is True
        assert report["proposal_present"] is True
        assert report["v_to_decision_edge_present"] is True
        assert all(report["bcel_coverage"].values())
        assert report["missing_bcel"] == []

    def test_audit_fails_when_missing_value(self):
        # Build a fresh, *empty* CognitiveGraph and add only non-value
        # nodes from a snapshot — this proves the audit detects the gap.
        c = InformationValueCollector()
        nodes, edges = c.collect_snapshot(
            {"prediction_error": 0.4, "novelty": 0.5, "informational_entropy": 0.5},
            {"energy": 0.7, "coherence": 0.7},
        )
        g = CognitiveGraph()
        g.clear()
        for n in nodes:
            if n.id.split(".", 1)[-1].split(".", 1)[0] != "value_function":
                g.add_node(n)
        for e in edges:
            if not e.source_id.startswith("iv.value_function.") and \
               not e.target_id.startswith("iv.value_function."):
                g.add_edge(e)
        report = motivation_audit(g)
        assert report["pass"] is False
        assert report["informational_value_present"] is False

    def test_audit_works_on_disk_loaded_graph(self):
        # The CognitiveGraph loads from disk on instantiation. We just
        # verify that the audit function does not raise on the loaded
        # baseline graph (which obviously lacks our new nodes).
        g = CognitiveGraph()
        # Should not raise, even if it reports pass=False.
        report = motivation_audit(g)
        assert isinstance(report, dict)
        assert "pass" in report