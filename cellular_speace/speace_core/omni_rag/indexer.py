import time
from typing import Any, Dict, List, Optional

import structlog

from speace_core.omni_rag.models import CognitiveNode, CognitiveEdge
from speace_core.omni_rag.graph import CognitiveGraph
from speace_core.omni_rag.collectors.semantic_collector import SemanticCollector
from speace_core.omni_rag.collectors.arch_collector import ArchCollector
from speace_core.omni_rag.collectors.dna_collector import DNACollector
from speace_core.omni_rag.collectors.bcel_collector import BCELCollector
from speace_core.omni_rag.collectors.runtime_collector import RuntimeCollector
from speace_core.omni_rag.collectors.cognitive_state_collector import CognitiveStateCollector
from speace_core.omni_rag.collectors.narrative_collector import NarrativeCollector
from speace_core.omni_rag.collectors.self_model_collector import SelfModelCollector
from speace_core.omni_rag.collectors.metacognitive_collector import MetacognitiveCollector
from speace_core.omni_rag.collectors.infant_sensor_collector import (
    InfantSensorCollector,
    InfantSensorConfig,
)

logger = structlog.get_logger(__name__)


class OmniIndexer:
    """Orchestrates all collectors to build the unified cognitive graph.

    Runs each collector in sequence and merges their outputs into a
    single CognitiveGraph. Deduplicates nodes by ID and edges by
    (source, target, relation).
    """

    def __init__(self, graph: Optional[CognitiveGraph] = None) -> None:
        self._graph = graph or CognitiveGraph()
        self._index_timestamp: float = 0.0
        self._stats: dict = {}

    @property
    def graph(self) -> CognitiveGraph:
        return self._graph

    def index_all(
        self,
        semantic: bool = True,
        arch: bool = True,
        dna: bool = True,
        bcel: bool = True,
        runtime: bool = True,
        cognitive_state: bool = False,
        narrative: bool = False,
        self_model: bool = False,
        metacognitive: bool = False,
        infant: bool = True,
        force: bool = False,
        observatory_state: Optional[Dict[str, Any]] = None,
    ) -> dict:
        """Run all enabled collectors and build the unified graph.

        Args:
            observatory_state: dict with keys 'state_graph', 'narrative_memory',
                'self_model_engine', 'metacognitive_engine' to enable collection
                from the Cognitive Self Observatory.

        Returns a dictionary with indexing statistics.
        """
        if force:
            self._graph.clear()

        start = time.perf_counter()
        total_nodes = 0
        total_edges = 0

        if semantic:
            n, e = self._run_collector("semantic", SemanticCollector())
            total_nodes += n
            total_edges += e

        if arch:
            n, e = self._run_collector("arch", ArchCollector())
            total_nodes += n
            total_edges += e

        if dna:
            n, e = self._run_collector("dna", DNACollector())
            total_nodes += n
            total_edges += e

        if bcel:
            n, e = self._run_collector("bcel", BCELCollector())
            total_nodes += n
            total_edges += e

        if runtime:
            n, e = self._run_collector("runtime", RuntimeCollector())
            total_nodes += n
            total_edges += e

        if infant:
            n, e = self._run_collector(
                "infant", InfantSensorCollector(config=InfantSensorConfig())
            )
            total_nodes += n
            total_edges += e

        if cognitive_state and observatory_state and "state_graph" in observatory_state:
            n, e = self._run_collector(
                "cognitive_state",
                CognitiveStateCollector(observatory_state["state_graph"]),
            )
            total_nodes += n
            total_edges += e

        if narrative and observatory_state and "narrative_memory" in observatory_state:
            n, e = self._run_collector(
                "narrative",
                NarrativeCollector(observatory_state["narrative_memory"]),
            )
            total_nodes += n
            total_edges += e

        if self_model and observatory_state and "self_model_engine" in observatory_state:
            n, e = self._run_collector(
                "self_model",
                SelfModelCollector(observatory_state["self_model_engine"]),
            )
            total_nodes += n
            total_edges += e

        if metacognitive and observatory_state and "metacognitive_engine" in observatory_state:
            n, e = self._run_collector(
                "metacognitive",
                MetacognitiveCollector(observatory_state["metacognitive_engine"]),
            )
            total_nodes += n
            total_edges += e

        elapsed = time.perf_counter() - start
        self._index_timestamp = time.time()

        self._graph.persist()

        stats = {
            "total_nodes": self._graph.node_count(),
            "total_edges": self._graph.edge_count(),
            "new_nodes": total_nodes,
            "new_edges": total_edges,
            "elapsed_seconds": round(elapsed, 3),
            "timestamp": self._index_timestamp,
            "layers": {
                "semantic": semantic,
                "arch": arch,
                "dna": dna,
                "bcel": bcel,
                "runtime": runtime,
                "cognitive_state": cognitive_state,
                "narrative": narrative,
                "self_model": self_model,
                "metacognitive": metacognitive,
                "infant": infant,
            },
        }
        self._stats = stats

        logger.info(
            "omni_indexer.complete",
            **stats,
        )
        return stats

    def index_incremental(self) -> dict:
        """Incremental update — run runtime collector only (fastest path)."""
        start = time.perf_counter()
        collector = RuntimeCollector()
        nodes, edges = collector.collect_historical()

        added_nodes = 0
        added_edges = 0
        for node in nodes:
            if not self._graph.has_node(node.id):
                self._graph.add_node(node)
                added_nodes += 1
        for edge in edges:
            self._graph.add_edge(edge)
            added_edges += 1

        self._graph.persist()
        elapsed = time.perf_counter() - start

        stats = {
            "total_nodes": self._graph.node_count(),
            "total_edges": self._graph.edge_count(),
            "new_nodes": added_nodes,
            "new_edges": added_edges,
            "elapsed_seconds": round(elapsed, 3),
            "mode": "incremental",
        }
        self._stats = stats
        return stats

    def get_stats(self) -> dict:
        return dict(self._stats)

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    def _run_collector(self, name: str, collector) -> tuple:
        """Run a single collector and merge its output into the graph."""
        start = time.perf_counter()

        if hasattr(collector, "collect_historical"):
            nodes, edges = collector.collect_historical()
        elif hasattr(collector, "collect"):
            result = collector.collect()
            if isinstance(result, tuple):
                nodes, edges = result
            elif isinstance(result, list):
                nodes = result
                edges = []
            else:
                nodes, edges = [], []
        else:
            logger.warning("omni_indexer.unknown_collector", name=name)
            return 0, 0

        added_nodes = 0
        added_edges = 0

        for node in nodes:
            if not self._graph.has_node(node.id):
                self._graph.add_node(node)
                added_nodes += 1

        dedup_key: set = set()
        for edge in edges:
            key = (edge.source_id, edge.target_id, edge.relation.value)
            if key not in dedup_key:
                dedup_key.add(key)
                self._graph.add_edge(edge)
                added_edges += 1

        elapsed = time.perf_counter() - start
        logger.info(
            "omni_indexer.collector_done",
            collector=name,
            nodes=added_nodes,
            edges=added_edges,
            elapsed_seconds=round(elapsed, 3),
        )
        return added_nodes, added_edges
