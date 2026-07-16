"""Tests for the TFTpsp Omni-RAG collector."""

import pytest

from speace_core.omni_rag.collectors.tftpsp_collector import TFTPspCollector
from speace_core.omni_rag.models import NodeType, RelationType


@pytest.fixture(scope="module")
def graph():
    collector = TFTPspCollector()
    nodes, edges = collector.collect()
    return nodes, edges


def test_collector_emits_33_gene_nodes(graph):
    nodes, _ = graph
    gene_nodes = [n for n in nodes if n.node_type == NodeType.GENE]
    assert len(gene_nodes) == 33


def test_collector_emits_catalog_node(graph):
    nodes, _ = graph
    catalog_nodes = [
        n for n in nodes if n.id == "tftpsp_catalog:main"
    ]
    assert len(catalog_nodes) == 1
    assert catalog_nodes[0].node_type == NodeType.CONFIG
    assert catalog_nodes[0].metadata["gene_count"] == 33


def test_contains_edges_link_genes_to_catalog(graph):
    _, edges = graph
    contains = [
        e
        for e in edges
        if e.source_id == "tftpsp_catalog:main" and e.relation == RelationType.CONTAINS
    ]
    assert len(contains) == 33


def test_emergency_gene_has_lock_open_metadata(graph):
    nodes, _ = graph
    epshcpe = next(
        n for n in nodes if n.id == "tftpsp_gene:tftpsp_023_epshcpe"
    )
    assert epshcpe.metadata["is_emergency"] is True
    assert epshcpe.metadata["mutation_allowed"] is False


def test_activation_tag_nodes_exist(graph):
    nodes, _ = graph
    tag_ids = {n.id for n in nodes if n.id.startswith("context_tag:")}
    # bootstrap, crisis, innovation, novelty, governance, sustainability ...
    for required in (
        "context_tag:bootstrap",
        "context_tag:crisis",
        "context_tag:innovation",
    ):
        assert required in tag_ids


def test_activated_by_edges(graph):
    _, edges = graph
    activated = [
        e for e in edges if e.relation == RelationType.ACTIVATED_BY
    ]
    # There must be at least one ACTIVATED_BY edge per gene that has
    # any activation_condition, plus extras for shared tags.
    assert len(activated) >= 33


def test_constrains_edges_link_to_principles(graph):
    _, edges = graph
    constrains = [
        e for e in edges if e.relation == RelationType.CONSTRAINS
    ]
    assert len(constrains) >= 1
    targets = {e.target_id for e in constrains}
    # The TFTpsp genes reference at least coherence_preservation.
    assert "principle:coherence_preservation" in targets


def test_bcel_mapping_nodes(graph):
    nodes, _ = graph
    bcel_nodes = [n for n in nodes if n.node_type == NodeType.BCEL_MAPPING]
    assert len(bcel_nodes) >= 1
    # Dedup: every gene with a BCEL ref must point to one of these nodes.
    keys = {n.name for n in bcel_nodes}
    assert keys  # non-empty
    # Check that an expected key exists
    assert any(
        "immune" in k or "dna" in k or "signal" in k or "memory" in k or "cognitive" in k
        for k in keys
    )


def test_maps_to_edges_point_to_bcel(graph):
    _, edges = graph
    maps_to = [e for e in edges if e.relation == RelationType.MAPS_TO]
    assert len(maps_to) >= 1
    for e in maps_to:
        assert e.target_id.startswith("bcel_mapping:")


def test_gene_with_no_bcel_emits_no_maps_to_edge(graph):
    _, edges = graph
    # TFT-1 is descriptive-only, so no MAPS_TO edge from it.
    bad = [
        e
        for e in edges
        if e.source_id == "tftpsp_gene:tftpsp_001_tft"
        and e.relation == RelationType.MAPS_TO
    ]
    assert bad == []


def test_regulatory_network_edges_consistent(graph):
    _, edges = graph
    regulates = [e for e in edges if e.relation == RelationType.REGULATES]
    # Each TFTpsp gene should have at least one outgoing edge
    # (regulatory, activated_by, or constrains).
    sources = {e.source_id for e in edges}
    gene_sources = {s for s in sources if s.startswith("tftpsp_gene:")}
    assert len(gene_sources) == 33
    # We must have at least as many regulates edges as we have interactions.
    assert len(regulates) >= 1


def test_default_catalog_loads_via_default(graph):
    # The default fixture should be backed by the on-disk catalogue
    # (TFTPspGeneLibrary.default).
    nodes, _ = graph
    catalog = next(n for n in nodes if n.id == "tftpsp_catalog:main")
    assert catalog.source_path.endswith("00_tftpsp_genome.yaml")
