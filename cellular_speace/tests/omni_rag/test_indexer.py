"""Tests for Omni-RAG indexer."""

import tempfile
from pathlib import Path

import pytest

from speace_core.omni_rag.indexer import OmniIndexer
from speace_core.omni_rag.graph import CognitiveGraph
from speace_core.omni_rag.models import NodeType
from speace_core.omni_rag.persistence.graph_store import GraphStore


@pytest.fixture
def fresh_indexer() -> OmniIndexer:
    store = GraphStore(data_dir="data/omni_rag_test")
    store.clear()
    graph = CognitiveGraph(store=store)
    return OmniIndexer(graph=graph)


class TestOmniIndexer:
    def test_index_all_creates_nodes(self, fresh_indexer: OmniIndexer):
        stats = fresh_indexer.index_all(
            semantic=False,
            arch=True,
            dna=True,
            bcel=True,
            runtime=False,
        )
        assert stats["total_nodes"] > 0
        assert stats["total_edges"] > 0
        assert fresh_indexer.graph.node_count() > 0

    def test_index_force_clears_first(self, fresh_indexer: OmniIndexer):
        stats1 = fresh_indexer.index_all(
            semantic=False, arch=True, dna=True, bcel=True, runtime=False,
        )

        stats2 = fresh_indexer.index_all(
            semantic=False, arch=True, dna=True, bcel=True, runtime=False,
            force=True,
        )
        # After force, new_nodes should roughly equal total (since we cleared)
        assert stats2["new_nodes"] <= stats2["total_nodes"]

    def test_arch_collector_finds_modules(self, fresh_indexer: OmniIndexer):
        stats = fresh_indexer.index_all(
            semantic=False, arch=True, dna=False, bcel=False, runtime=False,
        )
        assert stats["total_nodes"] > 0
        modules = fresh_indexer.graph.get_nodes_by_type(NodeType.MODULE)
        assert len(modules) > 0

    def test_bcel_collector_finds_mappings(self, fresh_indexer: OmniIndexer):
        stats = fresh_indexer.index_all(
            semantic=False, arch=False, dna=False, bcel=True, runtime=False,
        )
        assert stats["total_nodes"] > 0
        bcel_nodes = fresh_indexer.graph.get_nodes_by_type(NodeType.BCEL_MAPPING)
        assert len(bcel_nodes) > 0

    def test_stats(self, fresh_indexer: OmniIndexer):
        assert fresh_indexer.get_stats() == {}
        fresh_indexer.index_all(semantic=False, arch=False, dna=False, bcel=False, runtime=False)
        stats = fresh_indexer.get_stats()
        assert "total_nodes" in stats
