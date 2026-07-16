import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import structlog

from speace_core.omni_rag.models import (
    CognitiveNode,
    CognitiveEdge,
    NodeType,
    RelationType,
)

logger = structlog.get_logger(__name__)


class DNACollector:
    """Parses the digital DNA genome and related files to create the DNA knowledge graph.

    Produces nodes for GENES, PRINCIPLES, PHENOTYPES and edges for
    EXPRESSES, REGULATES, DEFINES.
    """

    def __init__(self, genome_dir: str = "speace_core/dna/genome") -> None:
        self._genome_dir = Path(genome_dir)

    def collect(self) -> Tuple[List[CognitiveNode], List[CognitiveEdge]]:
        """Walk genome directory and extract DNA graph."""
        nodes: List[CognitiveNode] = []
        edges: List[CognitiveEdge] = []

        if not self._genome_dir.exists():
            logger.warning("dna_collector.genome_dir_not_found", path=str(self._genome_dir))
            return nodes, edges

        yaml_files = list(self._genome_dir.rglob("*.yaml")) + list(self._genome_dir.rglob("*.yml"))
        for fpath in yaml_files:
            file_nodes, file_edges = self._parse_genome_file(fpath)
            nodes.extend(file_nodes)
            edges.extend(file_edges)

        # Add principle nodes from species_orientation
        species_path = self._genome_dir / "core" / "species_orientation.yaml"
        if species_path.exists():
            princ_nodes, princ_edges = self._parse_species_orientation(species_path)
            nodes.extend(princ_nodes)
            edges.extend(princ_edges)

        logger.info(
            "dna_collector.complete",
            files=len(yaml_files),
            nodes=len(nodes),
            edges=len(edges),
        )
        return nodes, edges

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    def _parse_genome_file(self, fpath: Path) -> Tuple[List[CognitiveNode], List[CognitiveEdge]]:
        import yaml

        try:
            data = yaml.safe_load(fpath.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("dna_collector.yaml_parse_error", path=str(fpath), error=str(exc))
            return [], []

        if not isinstance(data, dict):
            return [], []

        nodes: List[CognitiveNode] = []
        edges: List[CognitiveEdge] = []

        rel_path = str(fpath).replace("\\", "/")
        doc_id = f"genome:{rel_path}"

        doc_node = CognitiveNode(
            id=doc_id,
            node_type=NodeType.CONFIG,
            name=fpath.stem,
            description=f"Genome YAML: {fpath.name}",
            source_path=rel_path,
            tags=["genome", "yaml"],
        )
        nodes.append(doc_node)

        self._extract_genes(data, doc_id, nodes, edges, rel_path)

        return nodes, edges

    def _extract_genes(
        self,
        data: dict,
        parent_id: str,
        nodes: List[CognitiveNode],
        edges: List[CognitiveEdge],
        source_path: str,
    ) -> None:
        for key, value in data.items():
            if isinstance(value, dict):
                gene_id = f"gene:{parent_id}.{key}"
                gene_node = CognitiveNode(
                    id=gene_id,
                    node_type=NodeType.GENE,
                    name=key,
                    description=str(value.get("name", value.get("description", "")))[:200],
                    source_path=source_path,
                    metadata={"gene_key": key},
                    tags=["dna_gene"],
                )
                nodes.append(gene_node)
                edges.append(CognitiveEdge(
                    source_id=parent_id,
                    target_id=gene_id,
                    relation=RelationType.CONTAINS,
                ))
                self._extract_genes(value, gene_id, nodes, edges, source_path)

            elif isinstance(value, list) and key in {"invariants", "principles", "genes"}:
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        item_id = f"gene:{parent_id}.{key}[{i}]"
                        item_name = item.get("name", item.get("symbol", f"{key}_{i}"))
                        item_node = CognitiveNode(
                            id=item_id,
                            node_type=NodeType.GENE,
                            name=str(item_name),
                            description=str(item.get("description", item.get("rationale", "")))[:200],
                            source_path=source_path,
                            metadata=item,
                            tags=[f"dna_{key}"],
                        )
                        nodes.append(item_node)
                        edges.append(CognitiveEdge(
                            source_id=parent_id,
                            target_id=item_id,
                            relation=RelationType.CONTAINS,
                        ))

    def _parse_species_orientation(
        self, fpath: Path
    ) -> Tuple[List[CognitiveNode], List[CognitiveEdge]]:
        import yaml

        try:
            data = yaml.safe_load(fpath.read_text(encoding="utf-8"))
        except Exception:
            return [], []

        if not isinstance(data, dict):
            return [], []

        nodes: List[CognitiveNode] = []
        edges: List[CognitiveEdge] = []
        rel_path = str(fpath).replace("\\", "/")

        orientation = data.get("species_orientation", data)
        orientation_id = "principle:species_orientation"

        orientation_node = CognitiveNode(
            id=orientation_id,
            node_type=NodeType.PRINCIPLE,
            name="Species Orientation",
            description=str(orientation.get("core_principle", ""))[:200],
            source_path=rel_path,
            tags=["species_orientation", "dna_principle"],
        )
        nodes.append(orientation_node)

        for principle in orientation.get("informational_principles", []):
            if isinstance(principle, dict):
                princ_id = f"principle:{principle.get('name', 'unknown')}"
                princ_node = CognitiveNode(
                    id=princ_id,
                    node_type=NodeType.PRINCIPLE,
                    name=principle.get("name", "unknown"),
                    description=principle.get("rationale", principle.get("description", "")),
                    source_path=rel_path,
                    metadata={
                        "symbol": principle.get("symbol", ""),
                        "metric": principle.get("metric", ""),
                        "target": principle.get("target_direction", ""),
                    },
                    tags=["informational_principle"],
                )
                nodes.append(princ_node)
                edges.append(CognitiveEdge(
                    source_id=orientation_id,
                    target_id=princ_id,
                    relation=RelationType.DEFINES,
                ))

        return nodes, edges
