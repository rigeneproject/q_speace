import time
from collections import deque
from typing import Dict, List, Optional, Set, Tuple

import structlog

from speace_core.omni_rag.models import (
    CognitiveNode,
    CognitiveEdge,
    NodeType,
    RelationType,
)
from speace_core.omni_rag.persistence.graph_store import GraphStore

logger = structlog.get_logger(__name__)


class CognitiveGraph:
    """In-memory cognitive graph with adjacency lists.

    Wraps GraphStore for persistence and provides graph algorithms
    (traversal, pathfinding, subgraph extraction).
    """

    def __init__(self, store: Optional[GraphStore] = None) -> None:
        self._store = store or GraphStore()
        self._nodes: Dict[str, CognitiveNode] = {}
        self._edges_out: Dict[str, List[CognitiveEdge]] = {}
        self._edges_in: Dict[str, List[CognitiveEdge]] = {}
        self._load_from_store()

    # ------------------------------------------------------------------ #
    # Node operations
    # ------------------------------------------------------------------ #

    def add_node(self, node: CognitiveNode) -> None:
        self._nodes[node.id] = node
        self._store.put_node(node)

    def get_node(self, node_id: str) -> Optional[CognitiveNode]:
        return self._nodes.get(node_id)

    def has_node(self, node_id: str) -> bool:
        return node_id in self._nodes

    def get_nodes_by_type(self, node_type: NodeType) -> List[CognitiveNode]:
        return [n for n in self._nodes.values() if n.node_type == node_type]

    def get_nodes_by_tag(self, tag: str) -> List[CognitiveNode]:
        return [n for n in self._nodes.values() if tag in n.tags]

    def search_nodes(self, query: str) -> List[CognitiveNode]:
        q = query.lower()
        results = []
        for node in self._nodes.values():
            if q in node.name.lower() or q in node.description.lower():
                results.append(node)
        return results

    def all_nodes(self) -> List[CognitiveNode]:
        return list(self._nodes.values())

    def node_count(self) -> int:
        return len(self._nodes)

    # ------------------------------------------------------------------ #
    # Edge operations
    # ------------------------------------------------------------------ #

    def add_edge(self, edge: CognitiveEdge) -> None:
        self._edges_out.setdefault(edge.source_id, []).append(edge)
        self._edges_in.setdefault(edge.target_id, []).append(edge)
        self._store.put_edge(edge)

    def add_edge_simple(
        self,
        source_id: str,
        target_id: str,
        relation: RelationType,
        weight: float = 1.0,
        metadata: Optional[dict] = None,
    ) -> None:
        if not self.has_node(source_id):
            logger.warning("graph.edge_source_missing", source_id=source_id)
            return
        if not self.has_node(target_id):
            logger.warning("graph.edge_target_missing", target_id=target_id)
            return
        edge = CognitiveEdge(
            source_id=source_id,
            target_id=target_id,
            relation=relation,
            weight=weight,
            metadata=metadata or {},
        )
        self.add_edge(edge)

    def get_edges_out(self, node_id: str) -> List[CognitiveEdge]:
        return list(self._edges_out.get(node_id, []))

    def get_edges_in(self, node_id: str) -> List[CognitiveEdge]:
        return list(self._edges_in.get(node_id, []))

    def get_edges_between(self, source_id: str, target_id: str) -> List[CognitiveEdge]:
        edges = self._edges_out.get(source_id, [])
        return [e for e in edges if e.target_id == target_id]

    def all_edges(self) -> List[CognitiveEdge]:
        result = []
        for edges in self._edges_out.values():
            result.extend(edges)
        return result

    def edge_count(self) -> int:
        return sum(len(edges) for edges in self._edges_out.values())

    # ------------------------------------------------------------------ #
    # Graph algorithms
    # ------------------------------------------------------------------ #

    def traverse_bfs(
        self,
        start_id: str,
        max_depth: int = 3,
        relation_filter: Optional[Set[RelationType]] = None,
    ) -> List[Tuple[str, int, List[CognitiveEdge]]]:
        """BFS traversal from start_id, returning (node_id, depth, path_edges)."""
        visited: Set[str] = set()
        queue: deque = deque()
        queue.append((start_id, 0, []))
        result = []

        while queue:
            node_id, depth, path = queue.popleft()
            if node_id in visited or depth > max_depth:
                continue
            visited.add(node_id)
            if depth > 0:
                result.append((node_id, depth, path))
            for edge in self._edges_out.get(node_id, []):
                if relation_filter and edge.relation not in relation_filter:
                    continue
                if edge.target_id not in visited:
                    queue.append((edge.target_id, depth + 1, path + [edge]))

        return result

    def find_paths(
        self,
        from_id: str,
        to_id: str,
        max_depth: int = 5,
    ) -> List[List[CognitiveEdge]]:
        """Find all paths between two nodes up to max_depth."""
        paths: List[List[CognitiveEdge]] = []
        self._dfs_paths(from_id, to_id, [], set(), max_depth, paths)
        return paths

    def _dfs_paths(
        self,
        current: str,
        target: str,
        path: List[CognitiveEdge],
        visited: Set[str],
        max_depth: int,
        results: List[List[CognitiveEdge]],
    ) -> None:
        if len(path) > max_depth:
            return
        if current == target and path:
            results.append(list(path))
            return
        visited.add(current)
        for edge in self._edges_out.get(current, []):
            if edge.target_id not in visited:
                path.append(edge)
                self._dfs_paths(edge.target_id, target, path, visited, max_depth, results)
                path.pop()
        visited.discard(current)

    def get_subgraph(self, node_ids: Set[str], depth: int = 1) -> "CognitiveGraph":
        """Extract a subgraph containing node_ids and their neighbors up to `depth`."""
        sub = CognitiveGraph(store=GraphStore())
        frontier: Set[str] = set(node_ids)
        explored: Set[str] = set()

        for _ in range(depth + 1):
            new_frontier: Set[str] = set()
            for nid in frontier:
                if nid in explored:
                    continue
                explored.add(nid)
                node = self.get_node(nid)
                if node:
                    sub.add_node(node)
                for edge in self._edges_out.get(nid, []):
                    if edge.target_id not in explored:
                        new_frontier.add(edge.target_id)
                        sub.add_node(self.get_node(edge.target_id))
                    if self.has_node(edge.target_id):
                        sub.add_edge(edge)
                for edge in self._edges_in.get(nid, []):
                    if edge.source_id not in explored:
                        new_frontier.add(edge.source_id)
                        sub.add_node(self.get_node(edge.source_id))
                    if self.has_node(edge.source_id):
                        sub.add_edge(edge)
            frontier = new_frontier

        return sub

    def get_relation_chain(
        self,
        from_type: NodeType,
        to_type: NodeType,
        max_depth: int = 5,
    ) -> List[List[CognitiveEdge]]:
        """Find all paths from nodes of from_type to nodes of to_type."""
        paths: List[List[CognitiveEdge]] = []
        for node in self._nodes.values():
            if node.node_type == from_type:
                for edge in self._edges_out.get(node.id, []):
                    self._dfs_paths_to_type(
                        edge.target_id, to_type, [edge], {node.id}, max_depth, paths
                    )
        return paths

    def _dfs_paths_to_type(
        self,
        current: str,
        target_type: NodeType,
        path: List[CognitiveEdge],
        visited: Set[str],
        max_depth: int,
        results: List[List[CognitiveEdge]],
    ) -> None:
        if len(path) > max_depth:
            return
        node = self.get_node(current)
        if node and node.node_type == target_type:
            results.append(list(path))
            return
        visited.add(current)
        for edge in self._edges_out.get(current, []):
            if edge.target_id not in visited:
                path.append(edge)
                self._dfs_paths_to_type(
                    edge.target_id, target_type, path, visited, max_depth, results
                )
                path.pop()
        visited.discard(current)

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #

    def persist(self) -> None:
        self._store.compact()

    def _load_from_store(self) -> None:
        for node in self._store.get_all_nodes():
            self._nodes[node.id] = node
        for edge in self._store.get_all_edges():
            self._edges_out.setdefault(edge.source_id, []).append(edge)
            self._edges_in.setdefault(edge.target_id, []).append(edge)
        if self._nodes:
            logger.info(
                "graph.loaded",
                nodes=len(self._nodes),
                edges=self.edge_count(),
            )

    def clear(self) -> None:
        self._nodes.clear()
        self._edges_out.clear()
        self._edges_in.clear()
        self._store.clear()

    def __repr__(self) -> str:
        return f"CognitiveGraph(nodes={len(self._nodes)}, edges={self.edge_count()})"
