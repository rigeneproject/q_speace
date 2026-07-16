import json
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import structlog

from speace_core.omni_rag.models import (
    CognitiveNode,
    CognitiveEdge,
    NodeType,
    RelationType,
)

logger = structlog.get_logger(__name__)


class RuntimeCollector:
    """Collects runtime events and state snapshots.

    Can operate in two modes:
    1. Historical: reads persisted event/audit logs from data/
    2. Live: subscribes to EventBus (called externally)
    """

    def __init__(self, data_dir: str = "data") -> None:
        self._data_dir = Path(data_dir)
        self._events: List[CognitiveNode] = []
        self._edges: List[CognitiveEdge] = []
        self._event_counter = 0
        self._handler: Optional[Callable] = None

    def collect_historical(self) -> Tuple[List[CognitiveNode], List[CognitiveEdge]]:
        """Scan data/ directories for persisted runtime evidence."""
        nodes: List[CognitiveNode] = []
        edges: List[CognitiveEdge] = []

        # Scan persistence logs
        persistence_dir = self._data_dir / "persistence"
        if persistence_dir.exists():
            for fpath in persistence_dir.glob("*.jsonl"):
                file_nodes, file_edges = self._parse_persistence_log(fpath)
                nodes.extend(file_nodes)
                edges.extend(file_edges)

        # Scan general logs
        logs_dir = self._data_dir / "logs"
        if logs_dir.exists():
            for fpath in logs_dir.glob("*.jsonl"):
                file_nodes, file_edges = self._parse_event_log(fpath)
                nodes.extend(file_nodes)
                edges.extend(file_edges)

        logger.info(
            "runtime_collector.historical_complete",
            nodes=len(nodes),
            edges=len(edges),
        )
        return nodes, edges

    def get_live_handler(self) -> Callable:
        """Return an EventBus-compatible handler function for live collection."""

        def handler(signal: Any) -> None:
            try:
                event_id = f"runtime:event_{self._event_counter}_{int(time.time())}"
                signal_data = {}
                if hasattr(signal, "model_dump"):
                    signal_data = signal.model_dump()
                elif hasattr(signal, "__dict__"):
                    signal_data = signal.__dict__

                event_node = CognitiveNode(
                    id=event_id,
                    node_type=NodeType.RUNTIME_EVENT,
                    name=f"Event {self._event_counter}",
                    description=str(signal_data)[:200],
                    metadata={
                        "signal_type": type(signal).__name__,
                        "data": signal_data,
                    },
                    tags=["runtime_event"],
                )
                self._events.append(event_node)
                self._event_counter += 1
            except Exception as exc:
                logger.warning("runtime_collector.handler_error", error=str(exc))

        self._handler = handler
        return handler

    def get_live_nodes_and_edges(self) -> Tuple[List[CognitiveNode], List[CognitiveEdge]]:
        nodes = list(self._events)
        edges = list(self._edges)
        self._events.clear()
        self._edges.clear()
        return nodes, edges

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    def _parse_persistence_log(
        self, fpath: Path
    ) -> Tuple[List[CognitiveNode], List[CognitiveEdge]]:
        nodes: List[CognitiveNode] = []
        edges: List[CognitiveEdge] = []

        try:
            with open(fpath, "r", encoding="utf-8") as f:
                for i, line in enumerate(f):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        event_id = f"persist:{fpath.stem}:{i}"
                        event_node = CognitiveNode(
                            id=event_id,
                            node_type=NodeType.RUNTIME_EVENT,
                            name=f"Persistence event {i}",
                            description=str(data.get("object_type", data.get("type", ""))),
                            source_path=str(fpath),
                            metadata={"raw": data},
                            tags=["persistence_event"],
                        )
                        nodes.append(event_node)
                    except json.JSONDecodeError:
                        continue

        except Exception as exc:
            logger.warning("runtime_collector.parse_error", path=str(fpath), error=str(exc))

        return nodes, edges

    def _parse_event_log(
        self, fpath: Path
    ) -> Tuple[List[CognitiveNode], List[CognitiveEdge]]:
        nodes: List[CognitiveNode] = []
        edges: List[CognitiveEdge] = []

        try:
            with open(fpath, "r", encoding="utf-8") as f:
                for i, line in enumerate(f):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        event_id = f"event:{fpath.stem}:{i}"
                        event_node = CognitiveNode(
                            id=event_id,
                            node_type=NodeType.RUNTIME_EVENT,
                            name=f"Log event {i}",
                            description=str(data.get("event", data.get("message", "")))[:200],
                            source_path=str(fpath),
                            metadata={"raw": data},
                            tags=["log_event"],
                        )
                        nodes.append(event_node)
                    except json.JSONDecodeError:
                        continue

        except Exception as exc:
            logger.warning("runtime_collector.parse_error", path=str(fpath), error=str(exc))

        return nodes, edges
