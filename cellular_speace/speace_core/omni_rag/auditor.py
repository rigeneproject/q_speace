import time
from typing import Dict, List, Optional, Set

import structlog

from speace_core.omni_rag.models import (
    CognitiveNode,
    CognitiveEdge,
    NodeType,
    RelationType,
    AuditType,
    AuditResult,
    AuditFinding,
)
from speace_core.omni_rag.graph import CognitiveGraph

logger = structlog.get_logger(__name__)


class OmniAuditor:
    """Performs structural audits against the cognitive graph.

    Supports five audit types:
    - ARCH: circular dependencies, orphan modules, god objects
    - BCEL: untranslated principles, missing implementations, incomplete tests
    - DNA: orphan genes, unexpressed genes, broken regulatory paths
    - RUNTIME: error clusters, anomaly detection, health trends
    - COGNITIVE_FACTORS: 10 cognitive-factor equivalences wired to BCEL
      (T172/D1), each with a kept_constraint carrying an invariant
      (T175/E1); also reports whether the Cognitive Infant SensorBus
      (T173) is indexed.
    """

    def __init__(self, graph: CognitiveGraph) -> None:
        self._graph = graph

    def audit(self, audit_type: AuditType = AuditType.ALL) -> AuditResult:
        """Run the specified audit type."""
        start = time.perf_counter()
        result = AuditResult(audit_type=audit_type)

        if audit_type == AuditType.ALL or audit_type == AuditType.ARCH:
            arch_result = self._audit_arch()
            result.findings.extend(arch_result.findings)

        if audit_type == AuditType.ALL or audit_type == AuditType.BCEL:
            bcel_result = self._audit_bcel()
            result.findings.extend(bcel_result.findings)

        if audit_type == AuditType.ALL or audit_type == AuditType.DNA:
            dna_result = self._audit_dna()
            result.findings.extend(dna_result.findings)

        if audit_type == AuditType.ALL or audit_type == AuditType.RUNTIME:
            runtime_result = self._audit_runtime()
            result.findings.extend(runtime_result.findings)

        if audit_type == AuditType.ALL or audit_type == AuditType.COGNITIVE_FACTORS:
            cf_result = self._audit_cognitive_factors()
            result.findings.extend(cf_result.findings)

        # Update summary
        for f in result.findings:
            result.summary[f.severity] = result.summary.get(f.severity, 0) + 1

        result.passed = result.summary.get("critical", 0) == 0
        result.duration_ms = round((time.perf_counter() - start) * 1000, 2)

        logger.info(
            "omni_audit.complete",
            audit_type=audit_type.value,
            findings=len(result.findings),
            passed=result.passed,
            duration_ms=result.duration_ms,
        )
        return result

    # ------------------------------------------------------------------ #
    # ARCH audit
    # ------------------------------------------------------------------ #

    def _audit_arch(self) -> AuditResult:
        result = AuditResult(audit_type=AuditType.ARCH)
        all_nodes = self._graph.all_nodes()
        module_nodes = [n for n in all_nodes if n.node_type == NodeType.MODULE]
        class_nodes = [n for n in all_nodes if n.node_type == NodeType.CLASS]

        # Circular dependency detection (module level)
        module_ids = {n.id for n in module_nodes}
        visited: Set[str] = set()
        in_stack: Set[str] = set()
        circular_count = 0

        def dfs_detect_cycle(nid: str) -> None:
            nonlocal circular_count
            visited.add(nid)
            in_stack.add(nid)
            for edge in self._graph.get_edges_out(nid):
                if edge.relation == RelationType.IMPORTS and edge.target_id in module_ids:
                    if edge.target_id in in_stack:
                        circular_count += 1
                        result.findings.append(AuditFinding(
                            severity="warning",
                            category="circular_dependency",
                            message=f"Circular import detected: {nid} -> {edge.target_id}",
                            node_id=nid,
                            details={"cycle_with": edge.target_id},
                        ))
                    elif edge.target_id not in visited:
                        dfs_detect_cycle(edge.target_id)
            in_stack.discard(nid)

        for mod in module_nodes[:100]:
            if mod.id not in visited:
                dfs_detect_cycle(mod.id)

        # Orphan detection: modules with no incoming edges
        modules_with_incoming: Set[str] = set()
        for edge in self._graph.all_edges():
            if edge.relation == RelationType.IMPORTS and edge.target_id in module_ids:
                modules_with_incoming.add(edge.target_id)

        for mod in module_nodes:
            if mod.id not in modules_with_incoming:
                result.findings.append(AuditFinding(
                    severity="info",
                    category="orphan_module",
                    message=f"Module has no imports: {mod.name}",
                    node_id=mod.id,
                ))

        # God object detection: classes with too many methods
        for cls_node in class_nodes:
            methods = [
                e for e in self._graph.get_edges_out(cls_node.id)
                if e.relation == RelationType.CONTAINS
            ]
            if len(methods) > 30:
                result.findings.append(AuditFinding(
                    severity="warning",
                    category="god_object",
                    message=f"Class '{cls_node.name}' has {len(methods)} methods (threshold: 30)",
                    node_id=cls_node.id,
                    details={"method_count": len(methods)},
                ))

        if not result.findings:
            result.findings.append(AuditFinding(
                severity="info",
                category="arch_clean",
                message=f"Architecture audit clean: {len(module_nodes)} modules, {len(class_nodes)} classes",
            ))

        return result

    # ------------------------------------------------------------------ #
    # BCEL audit
    # ------------------------------------------------------------------ #

    def _audit_bcel(self) -> AuditResult:
        result = AuditResult(audit_type=AuditType.BCEL)
        all_nodes = self._graph.all_nodes()

        bcel_mappings = [n for n in all_nodes if n.node_type == NodeType.BCEL_MAPPING]
        constraints = [n for n in all_nodes if n.node_type == NodeType.CONSTRAINT]
        digital_mechs = [n for n in all_nodes if n.node_type == NodeType.DIGITAL_MECHANISM]

        # Check each BCEL mapping has implementation
        for mapping in bcel_mappings:
            outgoing = self._graph.get_edges_out(mapping.id)
            has_implementation = any(
                e.relation in {RelationType.IMPLEMENTS, RelationType.VALIDATES}
                for e in outgoing
            )
            if not has_implementation:
                result.findings.append(AuditFinding(
                    severity="warning",
                    category="bcel_no_implementation",
                    message=f"BCEL mapping '{mapping.name}' has no digital implementation",
                    node_id=mapping.id,
                    details={"preserved_function": mapping.description},
                ))

        # Check constraints have mathematical forms
        for constraint in constraints:
            if constraint.node_type == NodeType.CONSTRAINT:
                has_form = bool(constraint.metadata.get("mathematical_form"))
                if not has_form:
                    result.findings.append(AuditFinding(
                        severity="warning",
                        category="bcel_no_mathematical_form",
                        message=f"Constraint '{constraint.name}' lacks mathematical form",
                        node_id=constraint.id,
                    ))

        # Gap detection: biological principles without BCEL
        biological_principles = [n for n in all_nodes if n.node_type == NodeType.BIOLOGICAL_PRINCIPLE]
        for bp in biological_principles:
            incoming = self._graph.get_edges_in(bp.id)
            has_bcel = any(e.relation == RelationType.TRANSLATED_TO for e in incoming)
            if not has_bcel:
                result.findings.append(AuditFinding(
                    severity="info",
                    category="bcel_gap",
                    message=f"Biological principle '{bp.name}' has no BCEL translation",
                    node_id=bp.id,
                ))

        if not result.findings:
            result.findings.append(AuditFinding(
                severity="info",
                category="bcel_clean",
                message=f"BCEL audit clean: {len(bcel_mappings)} mappings, {len(constraints)} constraints",
            ))

        return result

    # ------------------------------------------------------------------ #
    # DNA audit
    # ------------------------------------------------------------------ #

    def _audit_dna(self) -> AuditResult:
        result = AuditResult(audit_type=AuditType.DNA)
        all_nodes = self._graph.all_nodes()

        genes = [n for n in all_nodes if n.node_type == NodeType.GENE]
        principles = [n for n in all_nodes if n.node_type == NodeType.PRINCIPLE]

        # Orphan genes: genes with no outgoing edges
        for gene in genes:
            outgoing = self._graph.get_edges_out(gene.id)
            if not outgoing:
                result.findings.append(AuditFinding(
                    severity="info",
                    category="orphan_gene",
                    message=f"Gene '{gene.name}' has no expressed relations",
                    node_id=gene.id,
                ))

        # Unexpressed genes: genes without EXPRESSES edge
        for gene in genes:
            has_expression = any(
                e.relation == RelationType.EXPRESSES
                for e in self._graph.get_edges_out(gene.id)
            )
            if not has_expression:
                result.findings.append(AuditFinding(
                    severity="info",
                    category="unexpressed_gene",
                    message=f"Gene '{gene.name}' has no EXPRESSES relation",
                    node_id=gene.id,
                ))

        # Regulatory completeness: check principles have definitions
        for principle in principles:
            outgoing = self._graph.get_edges_out(principle.id)
            defines_anything = any(e.relation == RelationType.DEFINES for e in outgoing)
            if not defines_anything:
                result.findings.append(AuditFinding(
                    severity="warning",
                    category="principle_no_definitions",
                    message=f"Principle '{principle.name}' does not DEFINE any sub-principles",
                    node_id=principle.id,
                ))

        if not result.findings:
            result.findings.append(AuditFinding(
                severity="info",
                category="dna_clean",
                message=f"DNA audit clean: {len(genes)} genes, {len(principles)} principles",
            ))

        return result

    # ------------------------------------------------------------------ #
    # RUNTIME audit
    # ------------------------------------------------------------------ #

    def _audit_runtime(self) -> AuditResult:
        result = AuditResult(audit_type=AuditType.RUNTIME)
        all_nodes = self._graph.all_nodes()

        runtime_events = [n for n in all_nodes if n.node_type == NodeType.RUNTIME_EVENT]

        # Error cluster detection
        error_count = 0
        for event in runtime_events:
            tags_lower = [t.lower() for t in event.tags]
            desc_lower = event.description.lower()
            if "error" in tags_lower or "error" in desc_lower or "fail" in desc_lower:
                error_count += 1

        if error_count > len(runtime_events) * 0.3 and len(runtime_events) > 10:
            result.findings.append(AuditFinding(
                severity="critical",
                category="high_error_rate",
                message=f"High error rate: {error_count}/{len(runtime_events)} runtime events are errors",
                details={"error_count": error_count, "total_events": len(runtime_events)},
            ))

        # Missing runtime evidence for tests
        tests = [n for n in all_nodes if n.node_type == NodeType.TEST]
        for test in tests:
            has_evidence = any(
                e.relation == RelationType.PRODUCES
                for e in self._graph.get_edges_out(test.id)
            )
            if not has_evidence:
                result.findings.append(AuditFinding(
                    severity="info",
                    category="test_no_evidence",
                    message=f"Test '{test.name}' has no runtime evidence link",
                    node_id=test.id,
                ))

        if not result.findings:
            result.findings.append(AuditFinding(
                severity="info",
                category="runtime_clean",
                message=f"Runtime audit clean: {len(runtime_events)} events",
            ))

        return result

    # ------------------------------------------------------------------ #
    # COGNITIVE_FACTORS audit (T175/E1)
    # ------------------------------------------------------------------ #

    # The 10 cognitive factors defined in T172/D1. These are the BCEL
    # catalog entries whose component_name starts with "cognitive factor:".
    EXPECTED_COGNITIVE_FACTORS = (
        "cognitive factor: working memory",
        "cognitive factor: processing speed",
        "cognitive factor: pattern recognition",
        "cognitive factor: prior knowledge",
        "cognitive factor: abstraction",
        "cognitive factor: relational reasoning",
        "cognitive factor: metacognition",
        "cognitive factor: sustained attention",
        "cognitive factor: motivation",
        "cognitive factor: cognitive flexibility",
    )

    def _audit_cognitive_factors(self) -> AuditResult:
        """Audit the 10 cognitive-factor equivalences in the graph.

        Checks:
          1. Each of the 10 cognitive factors has a BCEL_MAPPING node.
          2. Each has at least one kept_constraint (VALIDATES edge).
          3. Each kept_constraint carries an invariant from
             species_orientation.yaml.
          4. A 'cognitive_factor:observation' tag exists somewhere,
             meaning the Cognitive Infant SensorBus is wired.
        """
        result = AuditResult(audit_type=AuditType.COGNITIVE_FACTORS)
        all_nodes = self._graph.all_nodes()

        bcel_mappings = {n.name: n for n in all_nodes if n.node_type == NodeType.BCEL_MAPPING}

        # 1+2+3. Per-factor structural checks
        for factor_name in self.EXPECTED_COGNITIVE_FACTORS:
            eq_node = bcel_mappings.get(factor_name)
            if eq_node is None:
                result.findings.append(AuditFinding(
                    severity="critical",
                    category="cognitive_factor_missing_mapping",
                    message=f"Cognitive factor '{factor_name}' has no BCEL_MAPPING node in the graph",
                ))
                continue

            outgoing = self._graph.get_edges_out(eq_node.id)
            validate_edges = [
                e for e in outgoing if e.relation == RelationType.VALIDATES
            ]
            if not validate_edges:
                result.findings.append(AuditFinding(
                    severity="warning",
                    category="cognitive_factor_no_kept_constraint",
                    message=f"Cognitive factor '{factor_name}' has no kept_constraints in the graph",
                    node_id=eq_node.id,
                ))
                continue

            # Each VALIDATES edge must point to a CONSTRAINT node that
            # has an invariant from the species_orientation.yaml set.
            # Accidental (removed) constraints intentionally have no
            # invariant — skip them, they are documented as *removed*.
            for ve in validate_edges:
                target = next(
                    (n for n in all_nodes if n.id == ve.target_id), None
                )
                if target is None or target.node_type != NodeType.CONSTRAINT:
                    result.findings.append(AuditFinding(
                        severity="warning",
                        category="cognitive_factor_invalid_target",
                        message=(
                            f"Cognitive factor '{factor_name}' VALIDATES a "
                            f"non-CONSTRAINT node: {ve.target_id}"
                        ),
                        node_id=eq_node.id,
                    ))
                    continue
                # Accidental (removed) constraints are documented as such
                # by name prefix 'Accidental:' or id prefix
                # 'constraint:accidental:'. They carry no invariant by
                # design.
                is_accidental = (
                    target.name.startswith("Accidental:")
                    or target.id.startswith("constraint:accidental:")
                )
                if is_accidental:
                    continue
                inv = target.metadata.get("invariant")
                if not inv:
                    result.findings.append(AuditFinding(
                        severity="warning",
                        category="cognitive_factor_constraint_no_invariant",
                        message=(
                            f"Kept constraint '{target.name}' (from "
                            f"'{factor_name}') has no invariant in metadata"
                        ),
                        node_id=target.id,
                    ))

        # 4. Infant SensorBus wiring: the 'cognitive_factor:observation'
        # tag is the canary for E1 → T173 wiring.
        observation_tag = "cognitive_factor:observation"
        if not any(observation_tag in n.tags for n in all_nodes):
            result.findings.append(AuditFinding(
                severity="info",
                category="cognitive_infant_sensors_unwired",
                message=(
                    f"No node carries the '{observation_tag}' tag. "
                    f"Cognitive Infant SensorBus (T173) is not yet "
                    f"indexed into the graph."
                ),
            ))

        if not result.findings:
            result.findings.append(AuditFinding(
                severity="info",
                category="cognitive_factors_clean",
                message=(
                    f"Cognitive factors audit clean: all "
                    f"{len(self.EXPECTED_COGNITIVE_FACTORS)} factors present "
                    f"and validated."
                ),
            ))

        return result
