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


class BCELCollector:
    """Parses the BCEL catalog and related files to create the BCEL knowledge graph.

    Produces nodes for BCEL_MAPPING, BIOLOGICAL_PRINCIPLE, CONSTRAINT,
    DIGITAL_MECHANISM and edges for TRANSLATED_TO, IMPLEMENTS, VALIDATES.
    """

    def __init__(self) -> None:
        pass

    def collect(self) -> Tuple[List[CognitiveNode], List[CognitiveEdge]]:
        """Read BCEL catalog and related source files."""
        nodes: List[CognitiveNode] = []
        edges: List[CognitiveEdge] = []

        try:
            from speace_core.bcel.catalog import BCELCatalog, default_catalog

            catalog = default_catalog()
            for name in catalog.list_components():
                eq = catalog.get(name)
                if eq is None:
                    continue

                eq_node = CognitiveNode(
                    id=f"bcel:{name.lower().replace(' ', '_').replace('-', '_')}",
                    node_type=NodeType.BCEL_MAPPING,
                    name=name,
                    description=eq.preserved_function,
                    source_path="speace_core/bcel/catalog.py",
                    metadata={
                        "preserved_function": eq.preserved_function,
                        "digital_implementation": eq.digital_implementation,
                        "config": eq.configuration,
                    },
                    tags=["bcel_mapping"],
                )
                nodes.append(eq_node)

                # Biological principle nodes
                for fc in eq.kept_constraints:
                    constraint_id = f"constraint:{fc.name}"
                    constraint_node = CognitiveNode(
                        id=constraint_id,
                        node_type=NodeType.CONSTRAINT,
                        name=fc.name,
                        description=fc.biological_form,
                        source_path="speace_core/bcel/catalog.py",
                        metadata={
                            "invariant": fc.invariant,
                            "mathematical_form": fc.mathematical_form,
                            "parameters": fc.parameters,
                            "stability_test": fc.stability_test,
                        },
                        tags=["functional_constraint", fc.invariant],
                    )
                    nodes.append(constraint_node)

                    edges.append(CognitiveEdge(
                        source_id=eq_node.id,
                        target_id=constraint_id,
                        relation=RelationType.VALIDATES,
                        metadata={"constraint_type": "functional"},
                    ))

                for rc in eq.removed_constraints:
                    constraint_id = f"constraint:accidental:{rc.lower().replace(' ', '_')}"
                    constraint_node = CognitiveNode(
                        id=constraint_id,
                        node_type=NodeType.CONSTRAINT,
                        name=f"Accidental: {rc}",
                        description=f"Accidental constraint removed: {rc}",
                        source_path="speace_core/bcel/catalog.py",
                        tags=["accidental_constraint"],
                    )
                    nodes.append(constraint_node)

                    edges.append(CognitiveEdge(
                        source_id=eq_node.id,
                        target_id=constraint_id,
                        relation=RelationType.VALIDATES,
                        metadata={"constraint_type": "accidental"},
                    ))

        except ImportError as exc:
            logger.warning("bcel_collector.import_failed", error=str(exc))
            return nodes, edges

        # Link BCEL to digital implementations via IMPLEMENTS
        self._link_digital_implementations(nodes, edges)

        logger.info(
            "bcel_collector.complete",
            nodes=len(nodes),
            edges=len(edges),
        )
        return nodes, edges

    def _link_digital_implementations(
        self,
        nodes: List[CognitiveNode],
        edges: List[CognitiveEdge],
    ) -> None:
        mapping = {
            "dna-rna_expression": "module:speace_core.digital_rna.engine",
            "chemical_synapse": "module:speace_core.cellular_brain.neuroperiodic.synaptic_bond",
            "biological_homeostasis": "module:speace_core.cellular_brain.runtime.coordinators.metabolism_coordinator",
            "immune_response": "module:speace_core.cellular_brain.immune.immune_response_engine",
            "cellular_metabolism": "module:speace_core.cellular_brain.runtime.coordinators.metabolism_coordinator",
            "apoptosis": "module:speace_core.cellular_brain.immune.immune_response_engine",
            "neural_refractory_period": "module:speace_core.cellular_brain.neuroperiodic.neural_element",
            "slow_long-term_memory_consolidation": "module:speace_core.cellular_brain.sleep.memory_consolidation_engine",
        }

        for node in nodes:
            if node.node_type != NodeType.BCEL_MAPPING:
                continue
            target_id = mapping.get(node.id.replace("bcel:", ""))
            if target_id:
                edges.append(CognitiveEdge(
                    source_id=node.id,
                    target_id=target_id,
                    relation=RelationType.IMPLEMENTS,
                ))
