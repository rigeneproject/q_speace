import json
import time
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional

import structlog

from speace_core.omni_rag.models import CognitiveNode, CognitiveEdge

logger = structlog.get_logger(__name__)


class GraphStore:
    """JSONL-persisted storage for the cognitive graph.

    Nodes and edges are stored in separate JSONL files.
    The store is append-only with optional compaction.
    """

    def __init__(self, data_dir: str = "data/omni_rag") -> None:
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)

        self._nodes_path = self._data_dir / "nodes.jsonl"
        self._edges_path = self._data_dir / "edges.jsonl"
        self._lock = Lock()

        self._nodes: Dict[str, CognitiveNode] = {}
        self._edges_out: Dict[str, List[CognitiveEdge]] = {}
        self._edges_in: Dict[str, List[CognitiveEdge]] = {}

        self._load()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def put_node(self, node: CognitiveNode) -> None:
        with self._lock:
            self._nodes[node.id] = node
            self._append_jsonl(self._nodes_path, node.model_dump())

    def put_edge(self, edge: CognitiveEdge) -> None:
        with self._lock:
            self._edges_out.setdefault(edge.source_id, []).append(edge)
            self._edges_in.setdefault(edge.target_id, []).append(edge)
            self._append_jsonl(self._edges_path, edge.model_dump())

    def get_node(self, node_id: str) -> Optional[CognitiveNode]:
        with self._lock:
            return self._nodes.get(node_id)

    def get_edges_out(self, node_id: str) -> List[CognitiveEdge]:
        with self._lock:
            return list(self._edges_out.get(node_id, []))

    def get_edges_in(self, node_id: str) -> List[CognitiveEdge]:
        with self._lock:
            return list(self._edges_in.get(node_id, []))

    def get_all_edges(self) -> List[CognitiveEdge]:
        with self._lock:
            result = []
            for edges in self._edges_out.values():
                result.extend(edges)
            return result

    def get_all_nodes(self) -> List[CognitiveNode]:
        with self._lock:
            return list(self._nodes.values())

    def query_nodes(
        self,
        *,
        node_type: Optional[str] = None,
        name_contains: Optional[str] = None,
        tag: Optional[str] = None,
        limit: int = 100,
    ) -> List[CognitiveNode]:
        with self._lock:
            results = []
            for node in self._nodes.values():
                if node_type is not None and node.node_type.value != node_type:
                    continue
                if name_contains is not None and name_contains.lower() not in node.name.lower():
                    continue
                if tag is not None and tag not in node.tags:
                    continue
                results.append(node)
                if len(results) >= limit:
                    break
            return results

    def node_count(self) -> int:
        with self._lock:
            return len(self._nodes)

    def edge_count(self) -> int:
        with self._lock:
            return sum(len(edges) for edges in self._edges_out.values())

    def clear(self) -> None:
        with self._lock:
            self._nodes.clear()
            self._edges_out.clear()
            self._edges_in.clear()
            self._nodes_path.write_text("", encoding="utf-8")
            self._edges_path.write_text("", encoding="utf-8")

    def compact(self) -> int:
        """Rewrite JSONL files from in-memory state (removes stale entries)."""
        with self._lock:
            with open(self._nodes_path, "w", encoding="utf-8") as f:
                for node in self._nodes.values():
                    f.write(json.dumps(node.model_dump(), ensure_ascii=False) + "\n")
            with open(self._edges_path, "w", encoding="utf-8") as f:
                seen: set[tuple[str, str, str]] = set()
                for edges in self._edges_out.values():
                    for edge in edges:
                        key = (edge.source_id, edge.target_id, edge.relation.value)
                        if key not in seen:
                            seen.add(key)
                            f.write(json.dumps(edge.model_dump(), ensure_ascii=False) + "\n")
            written_nodes = len(self._nodes)
            written_edges = len(seen)
            logger.info("graph_store.compacted", nodes=written_nodes, edges=written_edges)
            return written_nodes + written_edges

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    def _append_jsonl(self, path: Path, data: dict) -> None:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")

    def _load(self) -> None:
        self._load_nodes()
        self._load_edges()

    def _load_nodes(self) -> None:
        if not self._nodes_path.exists():
            return
        count = 0
        with open(self._nodes_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    node = CognitiveNode(**data)
                    self._nodes[node.id] = node
                    count += 1
                except Exception as exc:
                    logger.warning("graph_store.load_node_skipped", error=str(exc))
        logger.info("graph_store.nodes_loaded", count=count)

    def _load_edges(self) -> None:
        if not self._edges_path.exists():
            return
        count = 0
        with open(self._edges_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    edge = CognitiveEdge(**data)
                    self._edges_out.setdefault(edge.source_id, []).append(edge)
                    self._edges_in.setdefault(edge.target_id, []).append(edge)
                    count += 1
                except Exception as exc:
                    logger.warning("graph_store.load_edge_skipped", error=str(exc))
        logger.info("graph_store.edges_loaded", count=count)
