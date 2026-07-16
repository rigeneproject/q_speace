"""TFTpsp Omni-RAG collector.

Indexes every TFTpsp gene (the 33 Problem-Solving Parameters from the
Rigene Project's Technological Fields Theory) as a ``CognitiveNode``
and emits typed edges to:

* the informational principle it constrains (``CONSTRAINS``)
* the context tags that activate it (``ACTIVATED_BY``)
* its BCEL equivalent (``MAPS_TO`` against a ``BCEL_MAPPING`` node)
* its regulatory network (``REGULATES`` / ``SUPPORTS`` / ``INHIBITS``)

The collector is read-only and integrates with the existing Omni-RAG
graph via the standard ``(nodes, edges) -> (graph.merge(...))`` pattern
used by the other collectors.
"""

import time
from pathlib import Path
from typing import List, Tuple

import structlog

from speace_core.dna.tftpsp_library import TFTPspGeneLibrary
from speace_core.omni_rag.models import (
    CognitiveEdge,
    CognitiveNode,
    NodeType,
    RelationType,
)

logger = structlog.get_logger(__name__)


# Tag for catalog-level overview node (one per source file)
_CATALOG_PREFIX = "tftpsp_catalog"


class TFTPspCollector:
    """Index the TFTpsp gene catalogue into the Omni-RAG graph."""

    def __init__(self, catalog_path: str | Path | None = None) -> None:
        self._catalog_path = (
            Path(catalog_path) if catalog_path is not None else None
        )

    def collect(self) -> Tuple[List[CognitiveNode], List[CognitiveEdge]]:
        nodes: List[CognitiveNode] = []
        edges: List[CognitiveEdge] = []

        try:
            if self._catalog_path is not None:
                lib = TFTPspGeneLibrary.from_file(self._catalog_path)
            else:
                lib = TFTPspGeneLibrary.default()
        except Exception as exc:
            logger.warning("tftpsp_collector.catalog_load_failed", error=str(exc))
            return nodes, edges

        # 1. Catalog overview node
        catalog_node = CognitiveNode(
            id=f"{_CATALOG_PREFIX}:main",
            node_type=NodeType.CONFIG,
            name="TFTpsp Catalogue",
            description=(
                f"Catalogue of {len(lib)} TFT Problem-Solving Parameters from the "
                "Rigene Project. Source: docs/List of the 33 TFT problem solving.txt"
            ),
            source_path=str(lib.source_path),
            metadata={"gene_count": len(lib), "enabled": lib.enabled},
            tags=["tftpsp", "catalog", "rigene"],
        )
        nodes.append(catalog_node)

        # 2. One node per gene + one per activation tag + one per BCEL mapping
        for gene in lib.all():
            gene_node = self._gene_node(gene)
            nodes.append(gene_node)
            edges.append(CognitiveEdge(
                source_id=catalog_node.id,
                target_id=gene_node.id,
                relation=RelationType.CONTAINS,
            ))

            # Activation tags
            for ac in gene.activation_conditions:
                tag_id = self._tag_node_id(ac.trigger_tag)
                nodes.append(self._tag_node(ac.trigger_tag, tag_id))
                edges.append(CognitiveEdge(
                    source_id=gene_node.id,
                    target_id=tag_id,
                    relation=RelationType.ACTIVATED_BY,
                    metadata={"min_signal": ac.min_signal, "boost": ac.boost},
                ))

            # Epigenetic rules (use the same tag nodes)
            for rule in gene.epigenetic_mechanisms:
                tag_id = self._tag_node_id(rule.tag)
                # Ensure the tag node exists even if not in activation_conditions
                if not any(n.id == tag_id for n in nodes):
                    nodes.append(self._tag_node(rule.tag, tag_id))
                edges.append(CognitiveEdge(
                    source_id=gene_node.id,
                    target_id=tag_id,
                    relation=RelationType.REGULATES,
                    metadata={"effect": rule.effect, "modifier": rule.modifier},
                ))

            # Functional constraints -> informational principles
            for constraint in gene.constraints:
                princ_id = f"principle:{constraint.invariant}"
                # The dna_collector already creates these nodes; we still
                # emit a CONSTRAINS edge even if the principle node is
                # produced elsewhere (idempotent at merge time).
                edges.append(CognitiveEdge(
                    source_id=gene_node.id,
                    target_id=princ_id,
                    relation=RelationType.CONSTRAINS,
                    metadata={
                        "constraint_name": constraint.name,
                        "description": constraint.description,
                    },
                ))

            # Interactions
            for inter in gene.interactions:
                target_id = f"tftpsp_gene:{inter.target_gene_id}"
                # We don't know yet if the target node exists; we still
                # emit the edge so the graph is complete.
                edges.append(CognitiveEdge(
                    source_id=gene_node.id,
                    target_id=target_id,
                    relation=self._map_relation(inter.relation),
                    metadata={"weight": inter.weight},
                ))

            # BCEL mapping
            if gene.bcel_equivalent:
                bcel_id = f"bcel_mapping:{self._bcel_key(gene.bcel_equivalent)}"
                bcel_node = CognitiveNode(
                    id=bcel_id,
                    node_type=NodeType.BCEL_MAPPING,
                    name=self._bcel_key(gene.bcel_equivalent),
                    description=(
                        f"Cybernetic equivalent referenced by TFTpsp gene "
                        f"{gene.gene_id} ({gene.short_label})."
                    ),
                    source_path=str(lib.source_path),
                    metadata={
                        "source_gene": gene.gene_id,
                        "raw_reference": gene.bcel_equivalent,
                    },
                    tags=["bcel", "tftpsp_bcel"],
                )
                # Deduplicate: only add the BCEL node if not already present
                if not any(n.id == bcel_id for n in nodes):
                    nodes.append(bcel_node)
                edges.append(CognitiveEdge(
                    source_id=gene_node.id,
                    target_id=bcel_id,
                    relation=RelationType.MAPS_TO,
                ))

        logger.info(
            "tftpsp_collector.complete",
            genes=len(lib),
            nodes=len(nodes),
            edges=len(edges),
        )
        return nodes, edges

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _tag_node_id(tag: str) -> str:
        return f"context_tag:{tag}"

    @staticmethod
    def _tag_node(tag: str, node_id: str) -> CognitiveNode:
        return CognitiveNode(
            id=node_id,
            node_type=NodeType.PHENOTYPE,
            name=tag,
            description=f"Context tag '{tag}' that activates TFTpsp genes.",
            tags=["context_tag", "tftpsp_activator"],
            metadata={"tag": tag},
        )

    @staticmethod
    def _gene_node(gene) -> CognitiveNode:
        return CognitiveNode(
            id=f"tftpsp_gene:{gene.gene_id}",
            node_type=NodeType.GENE,
            name=gene.short_label,
            description=gene.function.strip(),
            source_path="speace_core/dna/genome/tftpsp/00_tftpsp_genome.yaml",
            metadata={
                "gene_id": gene.gene_id,
                "tft_index": gene.tft_index,
                "full_name": gene.name,
                "priority": gene.priority,
                "domain_tags": list(gene.domain_tags),
                "bcel_equivalent": gene.bcel_equivalent,
                "mutation_allowed": gene.mutation_policy.allowed,
                "is_emergency": any(
                    r.effect == "lock_open" for r in gene.epigenetic_mechanisms
                ),
            },
            tags=["tftpsp_gene", f"tftpsp_index_{gene.tft_index:02d}"],
        )

    @staticmethod
    def _bcel_key(raw: str) -> str:
        """Extract the catalog key from the parenthetical suffix."""
        # Convention: "Human Name (catalog_key)"
        if "(" in raw and raw.endswith(")"):
            return raw[raw.rfind("(") + 1 : -1].strip()
        return raw.strip()

    @staticmethod
    def _map_relation(rel: str) -> RelationType:
        return {
            "depends_on": RelationType.DEPENDS_ON,
            "gates": RelationType.REGULATES,
            "inhibits": RelationType.REGULATES,
            "supports": RelationType.REGULATES,
            "contradicts": RelationType.CORRELATES_WITH,
        }.get(rel, RelationType.REFERENCES)