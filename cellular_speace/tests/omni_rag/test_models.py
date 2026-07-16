"""Tests for Omni-RAG data models."""

import pytest

from speace_core.omni_rag.models import (
    CognitiveNode,
    CognitiveEdge,
    NodeType,
    RelationType,
    OmniQuery,
    OmniResult,
    AuditResult,
    AuditFinding,
    AuditType,
    LayerFilter,
)


class TestCognitiveNode:
    def test_create_minimal(self):
        node = CognitiveNode(id="test:1", name="Test Node")
        assert node.id == "test:1"
        assert node.name == "Test Node"
        assert node.node_type == NodeType.UNKNOWN

    def test_create_with_type(self):
        node = CognitiveNode(
            id="module:test",
            node_type=NodeType.MODULE,
            name="Test Module",
        )
        assert node.node_type == NodeType.MODULE

    def test_add_tag(self):
        node = CognitiveNode(id="test:1", name="Test")
        node.add_tag("important")
        assert "important" in node.tags
        node.add_tag("important")  # no duplicate
        assert node.tags.count("important") == 1


class TestCognitiveEdge:
    def test_create_minimal(self):
        edge = CognitiveEdge(
            source_id="src:1",
            target_id="tgt:1",
            relation=RelationType.IMPLEMENTS,
        )
        assert edge.source_id == "src:1"
        assert edge.target_id == "tgt:1"
        assert edge.relation == RelationType.IMPLEMENTS
        assert edge.weight == 1.0

    def test_default_weight(self):
        edge = CognitiveEdge(
            source_id="a", target_id="b", relation=RelationType.DEPENDS_ON
        )
        assert edge.weight == 1.0

    def test_custom_weight(self):
        edge = CognitiveEdge(
            source_id="a", target_id="b", relation=RelationType.DEPENDS_ON,
            weight=0.5,
        )
        assert edge.weight == 0.5


class TestOmniQuery:
    def test_default_layers(self):
        q = OmniQuery(text="test")
        assert len(q.layers) == 5  # all layers by default

    def test_custom_layers(self):
        q = OmniQuery(text="test", layers=[LayerFilter.ARCH, LayerFilter.DNA])
        assert len(q.layers) == 2
        assert LayerFilter.ARCH in q.layers
        assert LayerFilter.DNA in q.layers
        assert LayerFilter.SEMANTIC not in q.layers


class TestOmniResult:
    def test_empty_result(self):
        r = OmniResult(
            query=OmniQuery(text="test"),
        )
        assert r.total_count == 0
        assert r.nodes == []
        assert r.edges == []

    def test_with_nodes(self):
        node = CognitiveNode(id="n:1", name="Node 1")
        r = OmniResult(
            query=OmniQuery(text="test"),
            nodes=[node],
            total_count=1,
        )
        assert r.total_count == 1
        assert r.nodes[0].name == "Node 1"


class TestAuditResult:
    def test_empty(self):
        r = AuditResult(audit_type=AuditType.ALL)
        assert r.passed is True
        assert len(r.findings) == 0

    def test_with_findings(self):
        r = AuditResult(audit_type=AuditType.ARCH)
        r.findings.append(AuditFinding(
            severity="warning",
            category="test_category",
            message="Test finding",
        ))
        assert len(r.findings) == 1
        assert r.summary["warning"] == 0  # summary is static, not auto-updated
