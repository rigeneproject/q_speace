"""Tests for Omni-RAG query engine."""

import pytest

from speace_core.omni_rag.query_engine import OmniQueryEngine
from speace_core.omni_rag.graph import CognitiveGraph
from speace_core.omni_rag.models import (
    CognitiveNode,
    CognitiveEdge,
    NodeType,
    RelationType,
    OmniQuery,
    LayerFilter,
)


@pytest.fixture
def engine() -> OmniQueryEngine:
    g = CognitiveGraph()
    nodes = [
        CognitiveNode(id="m:main", node_type=NodeType.MODULE, name="MainModule", description="Main test module"),
        CognitiveNode(id="m:helper", node_type=NodeType.MODULE, name="Helper", description="Helper module"),
        CognitiveNode(id="c:MainClass", node_type=NodeType.CLASS, name="MainClass", description="Main test class"),
        CognitiveNode(id="g:test_gene", node_type=NodeType.GENE, name="TEST_GENE", description="Test gene for memory"),
        CognitiveNode(id="b:mem_bcel", node_type=NodeType.BCEL_MAPPING, name="Memory BCEL", description="BCEL mapping for memory"),
        CognitiveNode(id="e:event1", node_type=NodeType.RUNTIME_EVENT, name="Event 1", description="Test runtime event"),
    ]
    for n in nodes:
        g.add_node(n)

    edges = [
        CognitiveEdge(source_id="m:main", target_id="m:helper", relation=RelationType.IMPORTS),
        CognitiveEdge(source_id="m:main", target_id="c:MainClass", relation=RelationType.CONTAINS),
        CognitiveEdge(source_id="g:test_gene", target_id="m:main", relation=RelationType.REGULATES),
        CognitiveEdge(source_id="b:mem_bcel", target_id="m:main", relation=RelationType.IMPLEMENTS),
    ]
    for e in edges:
        g.add_edge(e)

    return OmniQueryEngine(graph=g)


class TestOmniQueryEngine:
    def test_basic_query(self, engine: OmniQueryEngine):
        result = engine.query_text(
            "MainModule",
            layers=[LayerFilter.ARCH],
        )
        assert result.total_count >= 1
        assert any("MainModule" in n.name for n in result.nodes)

    def test_multi_layer_query(self, engine: OmniQueryEngine):
        result = engine.query_text(
            "test",
            layers=[LayerFilter.ARCH, LayerFilter.DNA, LayerFilter.BCEL],
        )
        assert result.total_count >= 1

    def test_impact_analysis(self, engine: OmniQueryEngine):
        result = engine.get_impact_analysis("m:main", depth=2)
        assert result.total_count >= 1
        assert len(result.nodes) >= 1

    def test_root_cause_analysis(self, engine: OmniQueryEngine):
        result = engine.get_root_cause_analysis("m:main", depth=3)
        assert result.total_count >= 1

    def test_dependency_analysis(self, engine: OmniQueryEngine):
        result = engine.get_dependency_analysis("m:main", depth=2)
        assert result.total_count >= 1

    def test_nonexistent_node(self, engine: OmniQueryEngine):
        result = engine.get_impact_analysis("nonexistent", depth=2)
        assert result.total_count == 0
        assert "not found" in result.explanation.lower()

    def test_query_with_node_ids(self, engine: OmniQueryEngine):
        q = OmniQuery(
            text="",
            node_ids=["g:test_gene"],
            layers=[LayerFilter.ARCH, LayerFilter.DNA],
        )
        result = engine.query(q)
        assert result.total_count >= 1
        assert any(n.id == "g:test_gene" for n in result.nodes)

    def test_query_latency_measured(self, engine: OmniQueryEngine):
        result = engine.query_text("test", layers=[LayerFilter.ARCH])
        assert result.latency_ms > 0
