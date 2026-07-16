"""Cognitive Infant SensorBus — T173/C2 collector.

Five read-only digital sensors, in the spirit of Fase 1 of
`docs/Istruzioni_periodiche_di_aggiornamento.md` (Cognitive Infant Stage):
the organism observes before it acts.

The collector is *batch* and *additive*: it never spawns background
threads, never writes back to organism state, never opens actuators.

Sensors:
  1. `runtime_event_stream`     — EventBus events (best-effort, skip if absent)
  2. `filesystem_watch`         — `data/logs/*.log` mtime-poll
  3. `gateway_log_stream`       — `data/logs/gateway_*.log` mtime-poll
  4. `health_alerts_watch`      — `data/agi_team/health_alerts.jsonl` line tail
  5. `omni_rag_index_delta`     — node/edge line counts of the cognitive graph

All emitted nodes have:
  - `node_type = RUNTIME_EVENT`
  - `metadata.infant_source` = one of the five source tags
  - tag `cognitive_infant` + tag `infant_source:<source>`
  - tag `cognitive_factor:observation` (telescope link, T172)
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import structlog

from speace_core.omni_rag.models import CognitiveEdge, CognitiveNode, NodeType

logger = structlog.get_logger(__name__)


INFANT_SOURCES = (
    "runtime",
    "fslog",
    "gwlog",
    "health",
    "omni_delta",
)


class InfantSensorConfig:
    """Configuration knobs for the Cognitive Infant SensorBus.

    Defaults are conservative. See docs/T173_COGNITIVE_INFANT_SENSORS_SPEC.md §5.
    """

    def __init__(
        self,
        poll_interval_seconds: float = 1.0,
        max_watched_log_size_mb: float = 32.0,
        health_alerts_max_lines: int = 100,
        enable_runtime_event_stream: bool = True,
        enable_filesystem_watch: bool = True,
        enable_gateway_log_stream: bool = True,
        enable_health_alerts_watch: bool = True,
        enable_omni_rag_index_delta: bool = True,
    ) -> None:
        self.poll_interval_seconds = poll_interval_seconds
        self.max_watched_log_size_mb = max_watched_log_size_mb
        self.health_alerts_max_lines = health_alerts_max_lines
        self.enable_runtime_event_stream = enable_runtime_event_stream
        self.enable_filesystem_watch = enable_filesystem_watch
        self.enable_gateway_log_stream = enable_gateway_log_stream
        self.enable_health_alerts_watch = enable_health_alerts_watch
        self.enable_omni_rag_index_delta = enable_omni_rag_index_delta


class InfantSensorCollector:
    """Read-only collector that emits CognitiveNodes for each sensor's observation."""

    def __init__(
        self,
        data_dir: str = "data",
        config: Optional[InfantSensorConfig] = None,
    ) -> None:
        self._data_dir = Path(data_dir)
        self._config = config or InfantSensorConfig()
        self._ts = time.time()
        self._counter = 0

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def collect(self) -> Tuple[List[CognitiveNode], List[CognitiveEdge]]:
        """Run all enabled sensors once and return (nodes, edges).

        `edges` is always empty: the Infant collector is a pure
        observation stream and never claims structural relations.
        """
        nodes: List[CognitiveNode] = []

        if self._config.enable_runtime_event_stream:
            nodes.extend(self._sensor_runtime_event_stream())
        if self._config.enable_filesystem_watch:
            nodes.extend(self._sensor_filesystem_watch())
        if self._config.enable_gateway_log_stream:
            nodes.extend(self._sensor_gateway_log_stream())
        if self._config.enable_health_alerts_watch:
            nodes.extend(self._sensor_health_alerts_watch())
        if self._config.enable_omni_rag_index_delta:
            nodes.extend(self._sensor_omni_rag_index_delta())

        logger.info(
            "infant_sensor_collector.complete",
            nodes=len(nodes),
            sources=[s for s in INFANT_SOURCES if self._is_enabled(s)],
        )
        return nodes, []

    # ------------------------------------------------------------------ #
    # Internal: source tag lookup
    # ------------------------------------------------------------------ #

    def _is_enabled(self, source: str) -> bool:
        return {
            "runtime": self._config.enable_runtime_event_stream,
            "fslog": self._config.enable_filesystem_watch,
            "gwlog": self._config.enable_gateway_log_stream,
            "health": self._config.enable_health_alerts_watch,
            "omni_delta": self._config.enable_omni_rag_index_delta,
        }.get(source, False)

    # ------------------------------------------------------------------ #
    # Sensor 1 — runtime_event_stream
    # ------------------------------------------------------------------ #

    def _sensor_runtime_event_stream(self) -> List[CognitiveNode]:
        """Try to drain any pending EventBus events. If the bus is
        absent or not yet wired, emit a single observation noting this.
        """
        events = []
        try:
            # Best-effort import to avoid hard dependency on organism layer.
            from speace_core.organism.organism_facade import OrganismFacade

            facade = OrganismFacade()
            events = list(getattr(facade.event_bus, "drain", lambda: [])())
        except Exception as exc:  # pragma: no cover
            return [
                self._node(
                    "runtime",
                    note="event_bus_unavailable",
                    error=str(exc),
                )
            ]
        if not events:
            return [
                self._node(
                    "runtime",
                    note="event_bus_idle",
                    event_count=0,
                )
            ]
        out = []
        for ev in events[:50]:  # cap to avoid runaway
            out.append(
                self._node(
                    "runtime",
                    note="event",
                    event_type=getattr(ev, "event_type", None) or ev.__class__.__name__,
                    event_source=getattr(ev, "source", None) or "unknown",
                )
            )
        return out

    # ------------------------------------------------------------------ #
    # Sensor 2 — filesystem_watch (data/logs/*.log)
    # ------------------------------------------------------------------ #

    def _sensor_filesystem_watch(self) -> List[CognitiveNode]:
        logs_dir = self._data_dir / "logs"
        if not logs_dir.exists():
            return []
        nodes: List[CognitiveNode] = []
        for fpath in sorted(logs_dir.glob("*.log")):
            try:
                stat = fpath.stat()
                if stat.st_size > self._config.max_watched_log_size_mb * 1024 * 1024:
                    nodes.append(
                        self._node(
                            "fslog",
                            note="oversized_skipped",
                            path=str(fpath),
                            size_bytes=stat.st_size,
                        )
                    )
                    continue
                # Read tail (last 4 KiB) for hash signature.
                with fpath.open("rb") as fh:
                    fh.seek(max(0, stat.st_size - 4096))
                    tail = fh.read()
                import hashlib

                tail_hash = hashlib.sha256(tail).hexdigest()[:16]
                nodes.append(
                    self._node(
                        "fslog",
                        note="poll",
                        path=str(fpath),
                        size_bytes=stat.st_size,
                        mtime=stat.st_mtime,
                        tail_hash=tail_hash,
                    )
                )
            except OSError as exc:
                nodes.append(
                    self._node(
                        "fslog",
                        note="os_error",
                        path=str(fpath),
                        error=str(exc),
                    )
                )
        return nodes

    # ------------------------------------------------------------------ #
    # Sensor 3 — gateway_log_stream (data/logs/gateway_*.log)
    # ------------------------------------------------------------------ #

    def _sensor_gateway_log_stream(self) -> List[CognitiveNode]:
        logs_dir = self._data_dir / "logs"
        if not logs_dir.exists():
            return []
        gateway_files = sorted(logs_dir.glob("gateway_*.log"))
        if not gateway_files:
            return [
                self._node(
                    "gwlog",
                    note="no_gateway_files",
                    logs_dir=str(logs_dir),
                )
            ]
        nodes: List[CognitiveNode] = []
        for fpath in gateway_files:
            try:
                stat = fpath.stat()
                nodes.append(
                    self._node(
                        "gwlog",
                        note="poll",
                        path=str(fpath),
                        size_bytes=stat.st_size,
                        mtime=stat.st_mtime,
                    )
                )
            except OSError as exc:
                nodes.append(
                    self._node(
                        "gwlog",
                        note="os_error",
                        path=str(fpath),
                        error=str(exc),
                    )
                )
        return nodes

    # ------------------------------------------------------------------ #
    # Sensor 4 — health_alerts_watch (data/agi_team/health_alerts.jsonl)
    # ------------------------------------------------------------------ #

    def _sensor_health_alerts_watch(self) -> List[CognitiveNode]:
        fpath = self._data_dir / "agi_team" / "health_alerts.jsonl"
        if not fpath.exists():
            return [
                self._node(
                    "health",
                    note="file_not_found",
                    path=str(fpath),
                )
            ]
        try:
            # Tail the file: read last N lines without loading whole file.
            tail_lines: List[str] = []
            with fpath.open("r", encoding="utf-8", errors="ignore") as fh:
                # Simple deque-style tail.
                from collections import deque

                tail = deque(maxlen=self._config.health_alerts_max_lines)
                for line in fh:
                    tail.append(line.rstrip("\n"))
                tail_lines = list(tail)
            return [
                self._node(
                    "health",
                    note="poll",
                    path=str(fpath),
                    line_count=len(tail_lines),
                    sample_last=self._safe_parse(tail_lines[-1]) if tail_lines else None,
                )
            ]
        except OSError as exc:
            return [
                self._node(
                    "health",
                    note="os_error",
                    path=str(fpath),
                    error=str(exc),
                )
            ]

    @staticmethod
    def _safe_parse(line: str) -> Optional[Dict[str, Any]]:
        try:
            return json.loads(line)
        except Exception:
            return None

    # ------------------------------------------------------------------ #
    # Sensor 5 — omni_rag_index_delta
    # ------------------------------------------------------------------ #

    def _sensor_omni_rag_index_delta(self) -> List[CognitiveNode]:
        omni_dir = self._data_dir / "omni_rag"
        nodes_path = omni_dir / "nodes.jsonl"
        edges_path = omni_dir / "edges.jsonl"
        node_count = self._count_lines(nodes_path) if nodes_path.exists() else 0
        edge_count = self._count_lines(edges_path) if edges_path.exists() else 0
        return [
            self._node(
                "omni_delta",
                note="count",
                nodes_path=str(nodes_path),
                edges_path=str(edges_path),
                node_count=node_count,
                edge_count=edge_count,
            )
        ]

    @staticmethod
    def _count_lines(p: Path) -> int:
        try:
            with p.open("rb") as fh:
                return sum(1 for _ in fh)
        except OSError:
            return 0

    # ------------------------------------------------------------------ #
    # Node factory
    # ------------------------------------------------------------------ #

    def _node(self, infant_source: str, **metadata: Any) -> CognitiveNode:
        self._counter += 1
        node_id = f"infant.{infant_source}.{int(self._ts)}.{self._counter}"
        return CognitiveNode(
            id=node_id,
            node_type=NodeType.RUNTIME_EVENT,
            name=f"infant:{infant_source}",
            description="read-only digital observation",
            metadata={
                "infant_source": infant_source,
                "ts": self._ts,
                **metadata,
            },
            tags=[
                "cognitive_infant",
                f"infant_source:{infant_source}",
                "cognitive_factor:observation",
            ],
        )