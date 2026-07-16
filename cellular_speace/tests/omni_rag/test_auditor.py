"""Tests for Omni-RAG auditor."""

import pytest

from speace_core.omni_rag.auditor import OmniAuditor
from speace_core.omni_rag.graph import CognitiveGraph
from speace_core.omni_rag.models import (
    CognitiveNode,
    CognitiveEdge,
    NodeType,
    RelationType,
    AuditType,
)
from speace_core.omni_rag.persistence.graph_store import GraphStore


@pytest.fixture
def auditor() -> OmniAuditor:
    store = GraphStore(data_dir="data/omni_rag_test")
    store.clear()
    g = CognitiveGraph(store=store)
    nodes = [
        CognitiveNode(id="m:module_a", node_type=NodeType.MODULE, name="Module A"),
        CognitiveNode(id="m:module_b", node_type=NodeType.MODULE, name="Module B"),
        CognitiveNode(id="m:module_c", node_type=NodeType.MODULE, name="Module C (orphan)"),
        CognitiveNode(id="c:LargeClass", node_type=NodeType.CLASS, name="LargeClass",
                       description="A class with many methods"),
        CognitiveNode(id="b:test_bcel", node_type=NodeType.BCEL_MAPPING, name="Test BCEL",
                       description="Test BCEL mapping"),
        CognitiveNode(id="g:test_gene", node_type=NodeType.GENE, name="Test Gene",
                       description="Test gene"),
        CognitiveNode(id="p:test_principle", node_type=NodeType.PRINCIPLE, name="Test Principle",
                       description="Test principle"),
        CognitiveNode(id="e:error_event", node_type=NodeType.RUNTIME_EVENT, name="Error Event",
                       description="error occurred in module X"),
    ]
    for n in nodes:
        g.add_node(n)

    # Add some edges to make some nodes "connected"
    edges = [
        CognitiveEdge(source_id="m:module_a", target_id="m:module_b", relation=RelationType.IMPORTS),
        CognitiveEdge(source_id="m:module_b", target_id="m:module_a", relation=RelationType.IMPORTS),
        # Many methods on LargeClass (simulate god object)
    ]
    for e in edges:
        g.add_edge(e)

    # Add 40 "method" edges to LargeClass to trigger god object detection
    for i in range(40):
        method_node = CognitiveNode(
            id=f"f:method_{i}",
            node_type=NodeType.FUNCTION,
            name=f"method_{i}",
        )
        g.add_node(method_node)
        g.add_edge(CognitiveEdge(
            source_id="c:LargeClass",
            target_id=f"f:method_{i}",
            relation=RelationType.CONTAINS,
        ))

    return OmniAuditor(graph=g)


class TestOmniAuditor:
    def test_arch_audit_finds_circular(self, auditor: OmniAuditor):
        result = auditor.audit(audit_type=AuditType.ARCH)
        assert len(result.findings) > 0
        circular = [f for f in result.findings if f.category == "circular_dependency"]
        assert len(circular) > 0

    def test_arch_audit_finds_god_object(self, auditor: OmniAuditor):
        result = auditor.audit(audit_type=AuditType.ARCH)
        god = [f for f in result.findings if f.category == "god_object"]
        assert len(god) > 0

    def test_bcel_audit(self, auditor: OmniAuditor):
        result = auditor.audit(audit_type=AuditType.BCEL)
        # BCEL without implementation should be flagged
        no_impl = [f for f in result.findings if f.category == "bcel_no_implementation"]
        assert len(no_impl) > 0

    def test_dna_audit(self, auditor: OmniAuditor):
        result = auditor.audit(audit_type=AuditType.DNA)
        # Should find orphan/unexpressed genes
        assert len(result.findings) > 0

    def test_runtime_audit(self, auditor: OmniAuditor):
        result = auditor.audit(audit_type=AuditType.RUNTIME)
        assert len(result.findings) > 0

    def test_all_audit(self, auditor: OmniAuditor):
        result = auditor.audit(audit_type=AuditType.ALL)
        assert len(result.findings) >= 4  # at least one from each category

    def test_audit_summary(self, auditor: OmniAuditor):
        result = auditor.audit(audit_type=AuditType.ALL)
        assert "critical" in result.summary
        assert "warning" in result.summary
        assert "info" in result.summary

    def test_duration_measured(self, auditor: OmniAuditor):
        result = auditor.audit(audit_type=AuditType.ARCH)
        assert result.duration_ms > 0


# --------------------------------------------------------------------------- #
# T175/E1 — Cognitive Factors audit
# --------------------------------------------------------------------------- #


@pytest.fixture
def cf_auditor() -> OmniAuditor:
    """A graph with the 10 cognitive-factor BCEL_MAPPINGs + their constraints."""
    store = GraphStore(data_dir="data/omni_rag_test_cf")
    store.clear()
    g = CognitiveGraph(store=store)

    # 10 cognitive factors (BCEL_MAPPINGs) + 1 kept constraint each.
    for factor in OmniAuditor.EXPECTED_COGNITIVE_FACTORS:
        eq_id = f"bcel:{factor.lower().replace(' ', '_')}"
        g.add_node(CognitiveNode(
            id=eq_id,
            node_type=NodeType.BCEL_MAPPING,
            name=factor,
            description=f"preserved function for {factor}",
        ))
        c_id = f"constraint:{factor.split(': ')[1].replace(' ', '_')}_cap"
        g.add_node(CognitiveNode(
            id=c_id,
            node_type=NodeType.CONSTRAINT,
            name=f"{factor.split(': ')[1]}_cap",
            description="kept functional constraint",
            metadata={
                "invariant": "coherence_preservation",
                "mathematical_form": "x <= 1.0",
                "stability_test": "x_below_1_is_stable",
            },
        ))
        g.add_edge(CognitiveEdge(
            source_id=eq_id, target_id=c_id, relation=RelationType.VALIDATES,
        ))

    # Add an Infant SensorBus observation node (cognitive_factor:observation tag)
    g.add_node(CognitiveNode(
        id="infant.runtime.test.1",
        node_type=NodeType.RUNTIME_EVENT,
        name="infant:runtime",
        description="read-only digital observation",
        tags=["cognitive_infant", "infant_source:runtime", "cognitive_factor:observation"],
    ))

    return OmniAuditor(graph=g)


class TestCognitiveFactorsAudit:
    def test_audit_runs_on_synthetic_graph(self, cf_auditor: OmniAuditor):
        result = cf_auditor.audit(audit_type=AuditType.COGNITIVE_FACTORS)
        assert result.passed, [f.message for f in result.findings if f.severity == "critical"]
        # No critical findings on a well-formed synthetic graph.
        assert result.summary.get("critical", 0) == 0

    def test_audit_reports_clean_when_all_ten_factors_wired(self, cf_auditor: OmniAuditor):
        result = cf_auditor.audit(audit_type=AuditType.COGNITIVE_FACTORS)
        clean = [f for f in result.findings if f.category == "cognitive_factors_clean"]
        assert clean, [f.message for f in result.findings]

    def test_audit_detects_missing_factor(self):
        """A graph with only 5 of the 10 factors must report missing mappings."""
        store = GraphStore(data_dir="data/omni_rag_test_cf_missing")
        store.clear()
        g = CognitiveGraph(store=store)

        for factor in OmniAuditor.EXPECTED_COGNITIVE_FACTORS[:5]:
            eq_id = f"bcel:{factor.lower().replace(' ', '_')}"
            g.add_node(CognitiveNode(
                id=eq_id, node_type=NodeType.BCEL_MAPPING, name=factor,
            ))

        auditor = OmniAuditor(graph=g)
        result = auditor.audit(audit_type=AuditType.COGNITIVE_FACTORS)
        missing = [f for f in result.findings if f.category == "cognitive_factor_missing_mapping"]
        assert len(missing) == 5, f"expected 5 missing, got {len(missing)}"

    def test_audit_detects_kept_constraint_without_invariant(self):
        store = GraphStore(data_dir="data/omni_rag_test_cf_noinv")
        store.clear()
        g = CognitiveGraph(store=store)

        factor = OmniAuditor.EXPECTED_COGNITIVE_FACTORS[0]
        eq_id = f"bcel:{factor.lower().replace(' ', '_')}"
        g.add_node(CognitiveNode(
            id=eq_id, node_type=NodeType.BCEL_MAPPING, name=factor,
        ))
        # Constraint with no invariant in metadata.
        c_id = "constraint:no_invariant"
        g.add_node(CognitiveNode(
            id=c_id, node_type=NodeType.CONSTRAINT, name="no_invariant",
            metadata={},
        ))
        g.add_edge(CognitiveEdge(
            source_id=eq_id, target_id=c_id, relation=RelationType.VALIDATES,
        ))

        auditor = OmniAuditor(graph=g)
        result = auditor.audit(audit_type=AuditType.COGNITIVE_FACTORS)
        no_inv = [f for f in result.findings
                  if f.category == "cognitive_factor_constraint_no_invariant"]
        assert no_inv, "expected a finding for missing invariant"

    def test_audit_skips_accidental_constraints(self, cf_auditor: OmniAuditor):
        """Accidental (removed) constraints must not be flagged for missing invariant."""
        # Add an accidental constraint to one of the factors.
        cf_auditor._graph.add_node(CognitiveNode(
            id="constraint:accidental:limited_neuron_firing_rate",
            node_type=NodeType.CONSTRAINT,
            name="Accidental: limited neuron firing rate",
            metadata={},  # no invariant — that's the point
        ))
        eq_id = f"bcel:{OmniAuditor.EXPECTED_COGNITIVE_FACTORS[0].lower().replace(' ', '_')}"
        cf_auditor._graph.add_edge(CognitiveEdge(
            source_id=eq_id,
            target_id="constraint:accidental:limited_neuron_firing_rate",
            relation=RelationType.VALIDATES,
        ))
        result = cf_auditor.audit(audit_type=AuditType.COGNITIVE_FACTORS)
        no_inv = [f for f in result.findings
                  if f.category == "cognitive_factor_constraint_no_invariant"
                  and "limited_neuron_firing_rate" in (f.node_id or "")]
        assert not no_inv, (
            "accidental (removed) constraints must not be flagged; "
            f"got: {no_inv}"
        )

    def test_audit_reports_infant_unwired_when_no_observation_tag(self):
        store = GraphStore(data_dir="data/omni_rag_test_cf_infant")
        store.clear()
        g = CognitiveGraph(store=store)
        # Add one factor so the structural checks pass
        factor = OmniAuditor.EXPECTED_COGNITIVE_FACTORS[0]
        eq_id = f"bcel:{factor.lower().replace(' ', '_')}"
        g.add_node(CognitiveNode(
            id=eq_id, node_type=NodeType.BCEL_MAPPING, name=factor,
        ))
        c_id = "constraint:x"
        g.add_node(CognitiveNode(
            id=c_id, node_type=NodeType.CONSTRAINT, name="x",
            metadata={"invariant": "coherence_preservation"},
        ))
        g.add_edge(CognitiveEdge(
            source_id=eq_id, target_id=c_id, relation=RelationType.VALIDATES,
        ))
        auditor = OmniAuditor(graph=g)
        result = auditor.audit(audit_type=AuditType.COGNITIVE_FACTORS)
        unwired = [f for f in result.findings
                   if f.category == "cognitive_infant_sensors_unwired"]
        assert unwired, "expected infant_sensors_unwired finding when no observation tag"

    def test_audit_included_in_all_run(self, cf_auditor: OmniAuditor):
        result = cf_auditor.audit(audit_type=AuditType.ALL)
        # The CF audit must run as part of ALL.
        cf_findings = [f for f in result.findings
                       if f.category.startswith("cognitive_")]
        assert cf_findings, "ALL audit should include cognitive_factors findings"

    def test_audit_type_includes_cognitive_factors(self):
        """The AuditType enum must include COGNITIVE_FACTORS (T175/E1)."""
        assert hasattr(AuditType, "COGNITIVE_FACTORS")
        assert AuditType.COGNITIVE_FACTORS.value == "cognitive_factors"
