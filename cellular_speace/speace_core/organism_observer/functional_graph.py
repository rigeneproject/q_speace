"""FunctionalGraph — grafo pesato delle interazioni tra sottosistemi.

Costruisce un grafo diretto in cui:
- i nodi sono i sottosistemi (source/target degli eventi)
- gli archi sono le comunicazioni, pesati per frequenza, latenza, successo

Questo è l'Operational Functional Graph (OFG): descrive ciò che il
sistema fa realmente, non ciò che potrebbe fare.
"""

from __future__ import annotations

import json
import math
import pathlib
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

from speace_core.organism_observer.event_collector import EventCollector, RecordedEvent


@dataclass
class EdgeStats:
    frequency: int = 0
    total_latency_ms: float = 0.0
    successes: int = 0
    failures: int = 0
    message_types: Dict[str, int] = field(default_factory=dict)
    last_seen: float = 0.0

    @property
    def success_rate(self) -> float:
        total = self.successes + self.failures
        return self.successes / total if total > 0 else 1.0

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.frequency if self.frequency > 0 else 0.0

    @property
    def weight(self) -> float:
        """Peso composito: frequenza × success_rate / log(1 + avg_latency_ms)."""
        base = self.frequency * self.success_rate
        latency_penalty = math.log2(1.0 + self.avg_latency_ms)
        return base / max(latency_penalty, 0.01)


@dataclass
class NodeStats:
    total_sent: int = 0
    total_received: int = 0
    broadcasts: int = 0
    first_seen: float = 0.0
    last_seen: float = 0.0


class FunctionalGraph:
    """Grafo funzionale pesato costruito dagli eventi raccolti.

    Usage::

        collector = EventCollector()
        graph = FunctionalGraph(collector)
        graph.build()
        print(graph.adjacency())
    """

    def __init__(
        self,
        collector: EventCollector,
        decay_hours: float = 0.0,
    ) -> None:
        self.collector = collector
        self.decay_hours = decay_hours
        self._edges: Dict[Tuple[str, str], EdgeStats] = {}
        self._nodes: Dict[str, NodeStats] = {}
        self._built_at: float = 0.0

    # ------------------------------------------------------------------ #
    # Build
    # ------------------------------------------------------------------ #

    def build(self, since: Optional[float] = None) -> None:
        """Costruisce (o ricostruisce) il grafo dal buffer degli eventi."""
        self._edges.clear()
        self._nodes.clear()

        events = self.collector.events(since=since)
        now = time.time()
        cutoff = now - (self.decay_hours * 3600) if self.decay_hours > 0 else 0.0

        for ev in events:
            if ev.timestamp < cutoff:
                continue

            src = ev.source
            tgt = ev.target or "*broadcast*"

            # Update source node
            if src not in self._nodes:
                self._nodes[src] = NodeStats(first_seen=ev.timestamp)
            sn = self._nodes[src]
            sn.total_sent += 1
            sn.last_seen = max(sn.last_seen, ev.timestamp)

            # Update target node
            if tgt not in self._nodes:
                self._nodes[tgt] = NodeStats(first_seen=ev.timestamp)
            tn = self._nodes[tgt]
            tn.total_received += 1
            tn.last_seen = max(tn.last_seen, ev.timestamp)
            if tgt == "*broadcast*":
                tn.broadcasts += 1

            # Update edge
            key = (src, tgt)
            if key not in self._edges:
                self._edges[key] = EdgeStats()
            es = self._edges[key]
            es.frequency += 1
            es.total_latency_ms += ev.latency_ms
            if ev.success:
                es.successes += 1
            else:
                es.failures += 1
            es.message_types[ev.message_type] = es.message_types.get(ev.message_type, 0) + 1
            es.last_seen = max(es.last_seen, ev.timestamp)

        self._built_at = time.time()

    # ------------------------------------------------------------------ #
    # Queries
    # ------------------------------------------------------------------ #

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return len(self._edges)

    def nodes(self) -> List[str]:
        return list(self._nodes.keys())

    def edges(self) -> List[Tuple[str, str, EdgeStats]]:
        return [(s, t, es) for (s, t), es in self._edges.items()]

    def adjacency(self) -> Dict[str, Dict[str, float]]:
        """Matrice di adiacenza pesata: {source → {target → weight}}."""
        adj: Dict[str, Dict[str, float]] = defaultdict(dict)
        for (s, t), es in self._edges.items():
            adj[s][t] = es.weight
        return dict(adj)

    def degree(self, node: str, mode: str = "out") -> int:
        """Grado outgoing (mode='out') o incoming (mode='in')."""
        if mode == "out":
            return sum(1 for (s, _) in self._edges if s == node)
        return sum(1 for (_, t) in self._edges if t == node)

    def neighbors(self, node: str, direction: str = "out") -> List[str]:
        if direction == "out":
            return [t for (s, t) in self._edges if s == node]
        return [s for (s, t) in self._edges if t == node]

    def node_stats(self, node: str) -> Optional[NodeStats]:
        return self._nodes.get(node)

    def edge_stats(self, source: str, target: str) -> Optional[EdgeStats]:
        return self._edges.get((source, target))

    # ------------------------------------------------------------------ #
    # Serialization
    # ------------------------------------------------------------------ #

    def to_dict(self) -> Dict[str, Any]:
        return {
            "built_at": self._built_at,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "nodes": {
                n: asdict(nd) for n, nd in self._nodes.items()
            },
            "edges": [
                {
                    "source": s,
                    "target": t,
                    **asdict(es),
                }
                for (s, t), es in self._edges.items()
            ],
        }

    def save(self, path: str) -> str:
        dst = pathlib.Path(path)
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return str(dst)

    @classmethod
    def load(cls, path: str, collector: EventCollector) -> "FunctionalGraph":
        graph = cls(collector=collector)
        data = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        graph._built_at = data.get("built_at", 0.0)
        for n, nd in data.get("nodes", {}).items():
            graph._nodes[n] = NodeStats(**nd)
        for ed in data.get("edges", []):
            s = ed.pop("source")
            t = ed.pop("target")
            graph._edges[(s, t)] = EdgeStats(**ed)
        return graph

    # ------------------------------------------------------------------ #

    def summary(self) -> Dict[str, Any]:
        return {
            "nodes": self.node_count,
            "edges": self.edge_count,
            "density": (2 * self.edge_count) / max(1, self.node_count * (self.node_count - 1)),
            "built_at": self._built_at,
        }
