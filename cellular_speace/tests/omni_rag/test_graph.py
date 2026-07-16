"""Tests for Omni-RAG CognitiveGraph."""

import tempfile
from pathlib import Path

import pytest

from speace_core.omni_rag.graph import CognitiveGraph
from speace_core.omni_rag.models import (
    CognitiveNode,
    CognitiveEdge,
    NodeType,
    RelationType,
)
from speace_core.omni_rag.persistence.graph_store import GraphStore


@pytest.fixture
def graph() -> CognitiveGraph:
    store = GraphStore(data_dir="data/omni_rag_test")
    store.clear()
    return CognitiveGraph(store=store)


@pytest.fixture
def populated_graph() -> CognitiveGraph:
    store = GraphStore(data_dir="data/omni_rag_test")
    store.clear()
    g = CognitiveGraph(store=store)
    # Add nodes
    nodes = [
        CognitiveNode(id="m:orchestrator", node_type=NodeType.MODULE, name="orchestrator"),
        CognitiveNode(id="m:dna", node_type=NodeType.MODULE, name="dna"),
        CognitiveNode(id="m:bcel", node_type=NodeType.MODULE, name="bcel"),
        CognitiveNode(id="c:Orchestrator", node_type=NodeType.CLASS, name="CellularBrainOrchestrator"),
        CognitiveNode(id="f:build_mvp", node_type=NodeType.FUNCTION, name="build_mvp"),
        CognitiveNode(id="g:test_gene", node_type=NodeType.GENE, name="TEST_GENE_1"),
    ]
    for n in nodes:
        g.add_node(n)

    # Add edges
    edges = [
        CognitiveEdge(source_id="m:orchestrator", target_id="m:dna", relation=RelationType.IMPORTS),
        CognitiveEdge(source_id="m:orchestrator", target_id="m:bcel", relation=RelationType.IMPORTS),
        CognitiveEdge(source_id="m:orchestrator", target_id="c:Orchestrator", relation=RelationType.CONTAINS),
        CognitiveEdge(source_id="c:Orchestrator", target_id="f:build_mvp", relation=RelationType.CONTAINS),
        CognitiveEdge(source_id="m:dna", target_id="g:test_gene", relation=RelationType.CONTAINS),
    ]
    for e in edges:
        g.add_edge(e)

    return g


class TestCognitiveGraph:
    def test_empty_graph(self, graph: CognitiveGraph):
        assert graph.node_count() == 0
        assert graph.edge_count() == 0

    def test_add_node(self, graph: CognitiveGraph):
        node = CognitiveNode(id="test:1", name="Test")
        graph.add_node(node)
        assert graph.node_count() == 1
        assert graph.has_node("test:1")

    def test_get_node(self, graph: CognitiveGraph):
        node = CognitiveNode(id="test:1", name="Test")
        graph.add_node(node)
        assert graph.get_node("test:1") is node
        assert graph.get_node("nonexistent") is None

    def test_add_edge(self, populated_graph: CognitiveGraph):
        assert populated_graph.edge_count() == 5

    def test_get_edges_out(self, populated_graph: CognitiveGraph):
        edges = populated_graph.get_edges_out("m:orchestrator")
        assert len(edges) == 3

    def test_get_edges_in(self, populated_graph: CognitiveGraph):
        edges = populated_graph.get_edges_in("m:dna")
        assert len(edges) == 1

    def test_get_edges_between(self, populated_graph: CognitiveGraph):
        edges = populated_graph.get_edges_between("m:orchestrator", "m:dna")
        assert len(edges) == 1
        assert edges[0].relation == RelationType.IMPORTS

    def test_get_nodes_by_type(self, populated_graph: CognitiveGraph):
        modules = populated_graph.get_nodes_by_type(NodeType.MODULE)
        assert len(modules) == 3
        classes = populated_graph.get_nodes_by_type(NodeType.CLASS)
        assert len(classes) == 1

    def test_search_nodes(self, populated_graph: CognitiveGraph):
        results = populated_graph.search_nodes("orchestrator")
        assert len(results) == 2  # module + class

    def test_bfs_traversal(self, populated_graph: CognitiveGraph):
        results = populated_graph.traverse_bfs("m:orchestrator", max_depth=2)
        assert len(results) >= 3

    def test_find_paths(self, populated_graph: CognitiveGraph):
        paths = populated_graph.find_paths("m:orchestrator", "g:test_gene", max_depth=5)
        assert len(paths) >= 1

    def test_get_subgraph(self, populated_graph: CognitiveGraph):
        sub = populated_graph.get_subgraph({"m:orchestrator"}, depth=1)
        assert sub.node_count() >= 1
        assert sub.edge_count() >= 1

    def test_clear(self, graph: CognitiveGraph):
        node = CognitiveNode(id="test:1", name="Test")
        graph.add_node(node)
        graph.clear()
        assert graph.node_count() == 0

    def test_persist_and_reload(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = GraphStore(data_dir=str(Path(tmpdir) / "omni_rag"))
            g = CognitiveGraph(store=store)
            n1 = CognitiveNode(id="p:n1", name="Persistent Node 1")
            n2 = CognitiveNode(id="p:n2", name="Persistent Node 2")
            g.add_node(n1)
            g.add_node(n2)
            g.add_edge_simple("p:n1", "p:n2", RelationType.DEPENDS_ON)

            # Persist
            g.persist()

            # Reload into new graph
            store2 = GraphStore(data_dir=str(Path(tmpdir) / "omni_rag"))
            g2 = CognitiveGraph(store=store2)
            assert g2.node_count() == 2
            assert g2.edge_count() >= 1

    def test_relation_chain(self, populated_graph: CognitiveGraph):
        # Add more DNA-like nodes
        rna = CognitiveNode(id="r:test_rna", node_type=NodeType.RNA, name="test_rna")
        populated_graph.add_node(rna)
        populated_graph.add_edge_simple("g:test_gene", "r:test_rna", RelationType.EXPRESSES)

        behavior = CognitiveNode(id="b:test_behavior", node_type=NodeType.BEHAVIOR, name="test_behavior")
        populated_graph.add_node(behavior)
        populated_graph.add_edge_simple("r:test_rna", "b:test_behavior", RelationType.REGULATES)

        chains = populated_graph.get_relation_chain(NodeType.GENE, NodeType.BEHAVIOR, max_depth=5)
        assert len(chains) >= 1
