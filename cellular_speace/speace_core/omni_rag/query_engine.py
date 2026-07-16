import time
from typing import Dict, List, Optional, Set, Tuple

import structlog

from speace_core.omni_rag.models import (
    CognitiveNode,
    CognitiveEdge,
    NodeType,
    RelationType,
    OmniQuery,
    OmniResult,
    LayerFilter,
)
from speace_core.omni_rag.graph import CognitiveGraph
from speace_core.omni_rag.collectors.semantic_collector import SemanticCollector

logger = structlog.get_logger(__name__)


class OmniQueryEngine:
    """Multi-layer query engine combining semantic, graph, and runtime contexts.

    Traverses the cognitive graph across all layers and merges results
    into a unified OmniResult with scoring and explanation.
    """

    def __init__(self, graph: CognitiveGraph) -> None:
        self._graph = graph
        self._semantic_collector: Optional[SemanticCollector] = None

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def query(self, query: OmniQuery) -> OmniResult:
        """Execute a multi-layer query and return unified results."""
        start = time.perf_counter()
        result = OmniResult(query=query)
        result.nodes = []
        result.edges = []
        result.runtime_evidence = []

        seen_node_ids: Set[str] = set()
        seen_edge_keys: Set[tuple] = set()

        for layer in query.layers:
            if layer == LayerFilter.SEMANTIC:
                layer_nodes, layer_edges = self._query_semantic(query)
            elif layer == LayerFilter.ARCH:
                layer_nodes, layer_edges = self._query_arch(query)
            elif layer == LayerFilter.DNA:
                layer_nodes, layer_edges = self._query_dna(query)
            elif layer == LayerFilter.BCEL:
                layer_nodes, layer_edges = self._query_bcel(query)
            elif layer == LayerFilter.RUNTIME:
                layer_nodes, layer_edges = self._query_runtime(query)
            else:
                continue

            for n in layer_nodes:
                if n.id not in seen_node_ids:
                    result.nodes.append(n)
                    seen_node_ids.add(n.id)
            for e in layer_edges:
                key = (e.source_id, e.target_id, e.relation.value)
                if key not in seen_edge_keys:
                    result.edges.append(e)
                    seen_edge_keys.add(key)

        # Find paths between high-scoring nodes
        if len(result.nodes) >= 2:
            result.paths = self._find_paths_between_top_nodes(result.nodes, query.max_depth)

        # Rank and limit
        result.nodes = result.nodes[:query.limit]
        result.total_count = len(result.nodes)
        result.latency_ms = round((time.perf_counter() - start) * 1000, 2)

        # Build explanation
        result.explanation = self._build_explanation(result)

        logger.info(
            "omni_query.complete",
            layers=[l.value for l in query.layers],
            results=result.total_count,
            latency_ms=result.latency_ms,
        )
        return result

    def query_text(self, text: str, **kwargs) -> OmniResult:
        """Shorthand: create OmniQuery from text and execute."""
        query = OmniQuery(text=text, **kwargs)
        return self.query(query)

    def get_impact_analysis(self, node_id: str, depth: int = 3) -> OmniResult:
        """Analyze what would be affected if a node changes."""
        start = time.perf_counter()

        node = self._graph.get_node(node_id)
        if not node:
            return OmniResult(
                query=OmniQuery(text=f"Impact analysis: {node_id}"),
                explanation=f"Node not found: {node_id}",
            )

        result = OmniResult(
            query=OmniQuery(
                text=f"Impact analysis for {node.name}",
                node_ids=[node_id],
                max_depth=depth,
            )
        )
        result.nodes = [node]

        # Forward traversal: what this node affects
        forward = self._graph.traverse_bfs(node_id, max_depth=depth)
        for target_id, d, path in forward:
            target_node = self._graph.get_node(target_id)
            if target_node:
                result.nodes.append(target_node)
            result.edges.extend(path)

        # Backward traversal: what depends on this node
        backward = self._graph.traverse_bfs(node_id, max_depth=depth)
        # Already covered by forward edges

        result.total_count = len(result.nodes)
        result.latency_ms = round((time.perf_counter() - start) * 1000, 2)
        result.explanation = (
            f"Impact analysis for '{node.name}' ({node.node_type.value}): "
            f"{len(result.nodes)} affected nodes at depth ≤{depth}"
        )
        return result

    def get_root_cause_analysis(self, node_id: str, depth: int = 5) -> OmniResult:
        """Trace backward from a node to find root causes."""
        start = time.perf_counter()

        node = self._graph.get_node(node_id)
        if not node:
            return OmniResult(
                query=OmniQuery(text=f"Root cause: {node_id}"),
                explanation=f"Node not found: {node_id}",
            )

        result = OmniResult(
            query=OmniQuery(
                text=f"Root cause for {node.name}",
                node_ids=[node_id],
                max_depth=depth,
            )
        )
        result.nodes = [node]

        # Traverse incoming edges backward
        visited: Set[str] = set()
        frontier: List[Tuple[str, int]] = [(node_id, 0)]

        while frontier:
            current, d = frontier.pop(0)
            if current in visited or d >= depth:
                continue
            visited.add(current)

            for edge in self._graph.get_edges_in(current):
                source = self._graph.get_node(edge.source_id)
                if source:
                    result.nodes.append(source)
                    result.edges.append(edge)
                    if edge.source_id not in visited:
                        frontier.append((edge.source_id, d + 1))

        result.total_count = len(result.nodes)
        result.latency_ms = round((time.perf_counter() - start) * 1000, 2)
        result.explanation = (
            f"Root cause analysis for '{node.name}': "
            f"{len(result.nodes)} upstream nodes traced"
        )
        return result

    def get_dependency_analysis(self, node_id: str, depth: int = 2) -> OmniResult:
        """Get full dependency graph (in + out) for a node."""
        start = time.perf_counter()
        node = self._graph.get_node(node_id)
        if not node:
            return OmniResult(
                query=OmniQuery(text=f"Dependency: {node_id}"),
                explanation=f"Node not found: {node_id}",
            )

        subgraph = self._graph.get_subgraph({node_id}, depth=depth)
        result = OmniResult(
            query=OmniQuery(
                text=f"Dependency analysis for {node.name}",
                node_ids=[node_id],
                max_depth=depth,
            ),
            nodes=subgraph.all_nodes(),
            edges=subgraph.all_edges(),
        )
        result.total_count = len(result.nodes)
        result.latency_ms = round((time.perf_counter() - start) * 1000, 2)
        result.explanation = (
            f"Dependency analysis for '{node.name}': "
            f"{len(result.nodes)} nodes at depth ≤{depth}"
        )
        return result

    def get_mutation_traceability(self, mutation_id: str) -> OmniResult:
        """Trace a mutation through its effects: Mutation -> Behavior -> ILF."""
        return self.get_impact_analysis(mutation_id, depth=5)

    # ------------------------------------------------------------------ #
    # Layer-specific query methods
    # ------------------------------------------------------------------ #

    def _query_semantic(self, query: OmniQuery) -> Tuple[List[CognitiveNode], List[CognitiveEdge]]:
        if not query.text:
            return [], []
        if self._semantic_collector is None:
            self._semantic_collector = SemanticCollector()
            self._semantic_collector.collect()

        results = self._semantic_collector.get_keyword_results(query.text, top_k=query.limit)
        nodes = [r["node"] for r in results]
        for r in results:
            nid = r["node"].id
            if nid not in self._semantic_collector.get_keyword_results("", 0):
                pass

        return nodes, []

    def _query_arch(self, query: OmniQuery) -> Tuple[List[CognitiveNode], List[CognitiveEdge]]:
        nodes: List[CognitiveNode] = []
        edges: List[CognitiveEdge] = []

        if query.node_ids:
            for nid in query.node_ids:
                node = self._graph.get_node(nid)
                if node and node.node_type in {
                    NodeType.MODULE, NodeType.CLASS, NodeType.FUNCTION,
                }:
                    nodes.append(node)
                    edges.extend(self._graph.get_edges_out(nid))
                    edges.extend(self._graph.get_edges_in(nid))

        if query.node_types:
            for nt in query.node_types:
                if nt in {NodeType.MODULE, NodeType.CLASS, NodeType.FUNCTION}:
                    nodes.extend(self._graph.get_nodes_by_type(nt))

        if query.text:
            for node in self._graph.search_nodes(query.text):
                if node.node_type in {NodeType.MODULE, NodeType.CLASS, NodeType.FUNCTION}:
                    if node not in nodes:
                        nodes.append(node)

        return nodes, edges

    def _query_dna(self, query: OmniQuery) -> Tuple[List[CognitiveNode], List[CognitiveEdge]]:
        nodes: List[CognitiveNode] = []
        edges: List[CognitiveEdge] = []

        if query.node_ids:
            for nid in query.node_ids:
                node = self._graph.get_node(nid)
                if node and node.node_type in {NodeType.GENE, NodeType.RNA, NodeType.PRINCIPLE}:
                    nodes.append(node)
                    edges.extend(self._graph.get_edges_out(nid))
                    edges.extend(self._graph.get_edges_in(nid))

        if query.node_types:
            for nt in query.node_types:
                if nt in {NodeType.GENE, NodeType.RNA, NodeType.PRINCIPLE, NodeType.PHENOTYPE}:
                    nodes.extend(self._graph.get_nodes_by_type(nt))

        if query.text:
            for node in self._graph.search_nodes(query.text):
                if node.node_type in {NodeType.GENE, NodeType.RNA, NodeType.PRINCIPLE}:
                    if node not in nodes:
                        nodes.append(node)

        return nodes, edges

    def _query_bcel(self, query: OmniQuery) -> Tuple[List[CognitiveNode], List[CognitiveEdge]]:
        nodes: List[CognitiveNode] = []
        edges: List[CognitiveEdge] = []

        if query.node_ids:
            for nid in query.node_ids:
                node = self._graph.get_node(nid)
                if node and node.node_type in {
                    NodeType.BCEL_MAPPING, NodeType.CONSTRAINT, NodeType.BIOLOGICAL_PRINCIPLE,
                }:
                    nodes.append(node)
                    edges.extend(self._graph.get_edges_out(nid))
                    edges.extend(self._graph.get_edges_in(nid))

        if query.node_types:
            for nt in query.node_types:
                if nt in {
                    NodeType.BCEL_MAPPING, NodeType.CONSTRAINT,
                    NodeType.BIOLOGICAL_PRINCIPLE, NodeType.DIGITAL_MECHANISM,
                }:
                    nodes.extend(self._graph.get_nodes_by_type(nt))

        if query.text:
            for node in self._graph.search_nodes(query.text):
                if node.node_type in {
                    NodeType.BCEL_MAPPING, NodeType.CONSTRAINT,
                    NodeType.BIOLOGICAL_PRINCIPLE,
                }:
                    if node not in nodes:
                        nodes.append(node)

        return nodes, edges

    def _query_runtime(self, query: OmniQuery) -> Tuple[List[CognitiveNode], List[CognitiveEdge]]:
        nodes: List[CognitiveNode] = []
        edges: List[CognitiveEdge] = []

        if query.node_ids:
            for nid in query.node_ids:
                node = self._graph.get_node(nid)
                if node and node.node_type == NodeType.RUNTIME_EVENT:
                    nodes.append(node)
                    edges.extend(self._graph.get_edges_out(nid))
                    edges.extend(self._graph.get_edges_in(nid))

        if query.node_types:
            for nt in query.node_types:
                if nt == NodeType.RUNTIME_EVENT:
                    nodes.extend(self._graph.get_nodes_by_type(nt))

        if query.tags:
            for tag in query.tags:
                for node in self._graph.get_nodes_by_tag(tag):
                    if node.node_type == NodeType.RUNTIME_EVENT and node not in nodes:
                        nodes.append(node)

        if query.text:
            for node in self._graph.search_nodes(query.text):
                if node.node_type == NodeType.RUNTIME_EVENT and node not in nodes:
                    nodes.append(node)

        return nodes, edges

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _find_paths_between_top_nodes(
        self,
        nodes: List[CognitiveNode],
        max_depth: int,
    ) -> List[List[CognitiveEdge]]:
        if len(nodes) < 2:
            return []
        top_ids = [n.id for n in nodes[:min(5, len(nodes))]]
        all_paths: List[List[CognitiveEdge]] = []
        for i in range(len(top_ids)):
            for j in range(i + 1, len(top_ids)):
                paths = self._graph.find_paths(top_ids[i], top_ids[j], max_depth=max_depth)
                all_paths.extend(paths[:2])  # limit paths per pair
                if len(all_paths) >= 10:
                    return all_paths
        return all_paths

    def _build_explanation(self, result: OmniResult) -> str:
        parts = []
        node_types = {}
        for n in result.nodes[:30]:
            node_types[n.node_type.value] = node_types.get(n.node_type.value, 0) + 1

        type_summary = ", ".join(
            f"{count} {nt}" for nt, count in sorted(node_types.items(), key=lambda x: -x[1])[:5]
        )

        parts.append(f"Found {result.total_count} nodes across {len(result.edges)} relationships")
        if type_summary:
            parts.append(f"Types: {type_summary}")
        if result.paths:
            total_paths = len(result.paths)
            avg_len = sum(len(p) for p in result.paths) / total_paths if total_paths else 0
            parts.append(f"{total_paths} connection paths (avg {avg_len:.1f} hops)")

        return ". ".join(parts) + "."
