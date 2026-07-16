import time
from collections import deque
from typing import Any, Dict, List, Optional, Set, Tuple

import structlog

from speace_core.cognitive_observatory.models import (
    CognitiveNodeObs,
    CognitiveEdgeObs,
    NodeTypeObs,
    RelationTypeObs,
    CausalPath,
)
from speace_core.cognitive_observatory.persistence.observatory_store import ObservatoryStore

logger = structlog.get_logger(__name__)


class CognitiveStateGraph:
    """L1 — Cognitive State Graph.

    A persistent graph of cognitive states: thoughts, decisions, goals,
    beliefs, hypotheses, mutations, actions, errors, learning events.
    Supports causal tracing and temporal queries.
    """

    def __init__(self, store: Optional[ObservatoryStore] = None) -> None:
        self._store = store or ObservatoryStore()
        self._nodes: Dict[str, CognitiveNodeObs] = {}
        self._edges_out: Dict[str, List[CognitiveEdgeObs]] = {}
        self._edges_in: Dict[str, List[CognitiveEdgeObs]] = {}
        self._load()

    # ------------------------------------------------------------------ #
    # Node operations
    # ------------------------------------------------------------------ #

    def record_thought(
        self, name: str, description: str = "",
        node_type: NodeTypeObs = NodeTypeObs.THOUGHT,
        metadata: Optional[dict] = None, subsystem: str = "",
    ) -> CognitiveNodeObs:
        node = CognitiveNodeObs(
            id=f"thought:{int(time.time() * 1000)}:{hash(name) % 100000}",
            node_type=node_type,
            name=name,
            description=description,
            metadata=metadata or {},
            source_subsystem=subsystem,
        )
        self._add_node(node)
        return node

    def record_decision(
        self, name: str, description: str = "",
        metadata: Optional[dict] = None, subsystem: str = "",
    ) -> CognitiveNodeObs:
        node = CognitiveNodeObs(
            id=f"decision:{int(time.time() * 1000)}:{hash(name) % 100000}",
            node_type=NodeTypeObs.DECISION,
            name=name,
            description=description,
            metadata=metadata or {},
            source_subsystem=subsystem,
        )
        self._add_node(node)
        return node

    def record_goal(
        self, name: str, description: str = "",
        metadata: Optional[dict] = None,
    ) -> CognitiveNodeObs:
        node = CognitiveNodeObs(
            id=f"goal:{int(time.time() * 1000)}:{hash(name) % 100000}",
            node_type=NodeTypeObs.GOAL,
            name=name,
            description=description,
            metadata=metadata or {},
        )
        self._add_node(node)
        return node

    def record_belief(
        self, name: str, description: str = "",
        confidence: float = 0.5, metadata: Optional[dict] = None,
    ) -> CognitiveNodeObs:
        node = CognitiveNodeObs(
            id=f"belief:{int(time.time() * 1000)}:{hash(name) % 100000}",
            node_type=NodeTypeObs.BELIEF,
            name=name,
            description=description,
            metadata={"confidence": confidence, **(metadata or {})},
        )
        self._add_node(node)
        return node

    def record_hypothesis(
        self, name: str, description: str = "",
        metadata: Optional[dict] = None,
    ) -> CognitiveNodeObs:
        node = CognitiveNodeObs(
            id=f"hypothesis:{int(time.time() * 1000)}:{hash(name) % 100000}",
            node_type=NodeTypeObs.HYPOTHESIS,
            name=name,
            description=description,
            metadata=metadata or {},
        )
        self._add_node(node)
        return node

    def record_error(
        self, name: str, description: str = "",
        severity: str = "warning", metadata: Optional[dict] = None,
        subsystem: str = "",
    ) -> CognitiveNodeObs:
        node = CognitiveNodeObs(
            id=f"error:{int(time.time() * 1000)}:{hash(name) % 100000}",
            node_type=NodeTypeObs.ERROR,
            name=name,
            description=description,
            metadata={"severity": severity, **(metadata or {})},
            source_subsystem=subsystem,
        )
        self._add_node(node)
        return node

    def record_learning(
        self, name: str, description: str = "",
        metadata: Optional[dict] = None, subsystem: str = "",
    ) -> CognitiveNodeObs:
        node = CognitiveNodeObs(
            id=f"learning:{int(time.time() * 1000)}:{hash(name) % 100000}",
            node_type=NodeTypeObs.LEARNING_EVENT,
            name=name,
            description=description,
            metadata=metadata or {},
            source_subsystem=subsystem,
        )
        self._add_node(node)
        return node

    def record_action(
        self, name: str, description: str = "",
        metadata: Optional[dict] = None, subsystem: str = "",
    ) -> CognitiveNodeObs:
        node = CognitiveNodeObs(
            id=f"action:{int(time.time() * 1000)}:{hash(name) % 100000}",
            node_type=NodeTypeObs.ACTION,
            name=name,
            description=description,
            metadata=metadata or {},
            source_subsystem=subsystem,
        )
        self._add_node(node)
        return node

    # ------------------------------------------------------------------ #
    # Edge operations
    # ------------------------------------------------------------------ #

    def relate(
        self, source_id: str, target_id: str,
        relation: RelationTypeObs, weight: float = 1.0,
        metadata: Optional[dict] = None,
    ) -> None:
        if source_id not in self._nodes or target_id not in self._nodes:
            logger.warning("cognitive_graph.relate_missing_node",
                           source=source_id in self._nodes,
                           target=target_id in self._nodes)
            return
        edge = CognitiveEdgeObs(
            source_id=source_id,
            target_id=target_id,
            relation=relation,
            weight=weight,
            metadata=metadata or {},
        )
        self._add_edge(edge)

    def link_causal(self, source_id: str, target_id: str, weight: float = 1.0) -> None:
        self.relate(source_id, target_id, RelationTypeObs.CAUSED, weight=weight)

    def link_generated(self, source_id: str, target_id: str) -> None:
        self.relate(source_id, target_id, RelationTypeObs.GENERATED)

    def link_influenced(self, source_id: str, target_id: str, weight: float = 0.5) -> None:
        self.relate(source_id, target_id, RelationTypeObs.INFLUENCED, weight=weight)

    def link_contradicted(self, source_id: str, target_id: str) -> None:
        self.relate(source_id, target_id, RelationTypeObs.CONTRADICTED)

    def link_learned_from(self, source_id: str, target_id: str) -> None:
        self.relate(source_id, target_id, RelationTypeObs.LEARNED_FROM)

    # ------------------------------------------------------------------ #
    # Query
    # ------------------------------------------------------------------ #

    def get_node(self, node_id: str) -> Optional[CognitiveNodeObs]:
        return self._nodes.get(node_id)

    def get_edges_out(self, node_id: str) -> List[CognitiveEdgeObs]:
        return list(self._edges_out.get(node_id, []))

    def get_edges_in(self, node_id: str) -> List[CognitiveEdgeObs]:
        return list(self._edges_in.get(node_id, []))

    def get_nodes_by_type(self, node_type: NodeTypeObs) -> List[CognitiveNodeObs]:
        return [n for n in self._nodes.values() if n.node_type == node_type]

    def get_nodes_by_subsystem(self, subsystem: str) -> List[CognitiveNodeObs]:
        return [n for n in self._nodes.values() if n.source_subsystem == subsystem]

    def search_nodes(self, query: str) -> List[CognitiveNodeObs]:
        q = query.lower()
        return [
            n for n in self._nodes.values()
            if q in n.name.lower() or q in n.description.lower()
        ]

    def get_recent_nodes(self, limit: int = 50) -> List[CognitiveNodeObs]:
        sorted_nodes = sorted(
            self._nodes.values(), key=lambda n: n.timestamp, reverse=True
        )
        return sorted_nodes[:limit]

    def get_error_rate(self, window: int = 100) -> float:
        recent = self.get_recent_nodes(window)
        if not recent:
            return 0.0
        errors = sum(1 for n in recent if n.node_type == NodeTypeObs.ERROR)
        return errors / len(recent)

    # ------------------------------------------------------------------ #
    # Causal tracing
    # ------------------------------------------------------------------ #

    def trace_causal_path(
        self, from_id: str, to_id: str, max_depth: int = 5
    ) -> Optional[CausalPath]:
        """Find a causal path between two nodes."""
        if from_id not in self._nodes or to_id not in self._nodes:
            return None

        all_paths: List[List[CognitiveEdgeObs]] = []
        self._dfs_paths(from_id, to_id, [], set(), max_depth, all_paths)

        if not all_paths:
            return None

        best = min(all_paths, key=len)
        node_ids = {from_id, to_id}
        for e in best:
            node_ids.add(e.source_id)
            node_ids.add(e.target_id)

        return CausalPath(
            nodes=[self._nodes[nid] for nid in node_ids if nid in self._nodes],
            edges=best,
            start_id=from_id,
            end_id=to_id,
            depth=len(best),
            description=(
                f"Causal path: {self._nodes[from_id].name} → "
                f"{self._nodes[to_id].name} ({len(best)} hops)"
            ),
        )

    def trace_upstream(self, node_id: str, max_depth: int = 5) -> CausalPath:
        """Trace backward from a node to find its causal parents."""
        nodes: List[CognitiveNodeObs] = []
        edges: List[CognitiveEdgeObs] = []
        visited: Set[str] = set()
        frontier: deque = deque()
        frontier.append((node_id, 0))

        while frontier:
            current, depth = frontier.popleft()
            if current in visited or depth > max_depth:
                continue
            visited.add(current)
            node = self._nodes.get(current)
            if node and current != node_id:
                nodes.append(node)
            for edge in self._edges_in.get(current, []):
                edges.append(edge)
                if edge.source_id not in visited:
                    frontier.append((edge.source_id, depth + 1))

        start_node = self._nodes.get(node_id)
        return CausalPath(
            nodes=([start_node] if start_node else []) + nodes,
            edges=edges,
            start_id=node_id,
            depth=max_depth,
            description=f"Upstream trace from {start_node.name if start_node else node_id} ({len(nodes)} ancestors)",
        )

    def trace_downstream(self, node_id: str, max_depth: int = 5) -> CausalPath:
        """Trace forward from a node to find its causal descendants."""
        nodes: List[CognitiveNodeObs] = []
        edges: List[CognitiveEdgeObs] = []
        visited: Set[str] = set()
        frontier: deque = deque()
        frontier.append((node_id, 0))

        while frontier:
            current, depth = frontier.popleft()
            if current in visited or depth > max_depth:
                continue
            visited.add(current)
            node = self._nodes.get(current)
            if node and current != node_id:
                nodes.append(node)
            for edge in self._edges_out.get(current, []):
                edges.append(edge)
                if edge.target_id not in visited:
                    frontier.append((edge.target_id, depth + 1))

        start_node = self._nodes.get(node_id)
        return CausalPath(
            nodes=([start_node] if start_node else []) + nodes,
            edges=edges,
            start_id=node_id,
            depth=max_depth,
            description=f"Downstream trace from {start_node.name if start_node else node_id} ({len(nodes)} descendants)",
        )

    # ------------------------------------------------------------------ #
    # Stats
    # ------------------------------------------------------------------ #

    def node_count(self) -> int:
        return len(self._nodes)

    def edge_count(self) -> int:
        return sum(len(edges) for edges in self._edges_out.values())

    def clear(self) -> None:
        self._nodes.clear()
        self._edges_out.clear()
        self._edges_in.clear()
        self._store.clear()

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    def _add_node(self, node: CognitiveNodeObs) -> None:
        self._nodes[node.id] = node
        self._store.put_node(node)

    def _add_edge(self, edge: CognitiveEdgeObs) -> None:
        self._edges_out.setdefault(edge.source_id, []).append(edge)
        self._edges_in.setdefault(edge.target_id, []).append(edge)
        self._store.put_edge(edge)

    def _dfs_paths(
        self, current: str, target: str, path: List[CognitiveEdgeObs],
        visited: Set[str], max_depth: int, results: List[List[CognitiveEdgeObs]],
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

    def _load(self) -> None:
        for node in self._store.get_all_nodes():
            self._nodes[node.id] = node
        for edge in self._store.get_all_edges():
            self._edges_out.setdefault(edge.source_id, []).append(edge)
            self._edges_in.setdefault(edge.target_id, []).append(edge)
        if self._nodes:
            logger.info(
                "cognitive_state_graph.loaded",
                nodes=len(self._nodes), edges=self.edge_count(),
            )
