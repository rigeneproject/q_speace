"""TopologyHistory — serie temporale di snapshot della geometria funzionale.

Campiona periodicamente TopologyMetrics.compute_all() e costruisce
una time-series persistente. Permette di osservare l'evoluzione della
forma dell'organismo nel tempo.
"""

from __future__ import annotations

import copy
import json
import math
import pathlib
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from speace_core.organism_observer.functional_graph import FunctionalGraph
from speace_core.organism_observer.topology_metrics import TopologyMetrics


@dataclass
class TopologySnapshot:
    timestamp: float
    tick: int
    node_count: int
    edge_count: int
    density: float
    avg_clustering: float
    global_efficiency: float
    small_world_sigma: float
    modularity_q: float
    n_communities: int
    top_broadcasters: List[Dict[str, Any]]
    top_collectors: List[Dict[str, Any]]
    top_bridges: List[Dict[str, Any]]
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MorphologicalGenomeRecord:
    """Memoria di una topologia con fitness elevata (Livello 4).

    Salva le metriche topologiche di una configurazione di successo
    per poterla riattivare in futuro quando SPEACE incontra un
    pattern simile.
    """
    timestamp: float
    tick: int
    fitness: float
    modularity: float
    global_efficiency: float
    small_world_sigma: float
    density: float
    avg_clustering: float
    n_communities: int
    signature: Dict[str, float] = field(default_factory=dict)

    def similarity_to(self, other: "MorphologicalGenomeRecord") -> float:
        """Coseno simile tra i vettori delle metriche chiave."""
        v1 = [
            self.modularity, self.global_efficiency,
            self.small_world_sigma, self.density, self.avg_clustering
        ]
        v2 = [
            other.modularity, other.global_efficiency,
            other.small_world_sigma, other.density, other.avg_clustering
        ]
        dot = sum(a * b for a, b in zip(v1, v2))
        n1 = math.sqrt(sum(a * a for a in v1))
        n2 = math.sqrt(sum(a * a for a in v2))
        if n1 == 0 or n2 == 0:
            return 0.0
        return dot / (n1 * n2)


class TopologyHistory:
    """Colleziona snapshot periodici della topologia.

    Usage::

        collector = EventCollector()
        graph = FunctionalGraph(collector)
        history = TopologyHistory(graph)

        # Campiona ogni 60 secondi
        history.sample(tick=current_tick)
        history.sample(tick=current_tick + 60)

        print(history.summary())
        history.save("data/organism_observer/topology_history.jsonl")
    """

    def __init__(
        self,
        graph: FunctionalGraph,
        max_snapshots: int = 10_000,
        persist_path: str = "data/organism_observer/topology_history.jsonl",
    ) -> None:
        self.graph = graph
        self.max_snapshots = max_snapshots
        self.persist_path = pathlib.Path(persist_path)
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        self._snapshots: List[TopologySnapshot] = []
        self._sample_count: int = 0
        self._morphological_genomes: List[MorphologicalGenomeRecord] = []
        self._fitness_threshold: float = 0.7

    # ------------------------------------------------------------------ #
    # Sampling
    # ------------------------------------------------------------------ #

    def sample(self, tick: int = 0) -> TopologySnapshot:
        """Costruisce un nuovo snapshot dal grafo corrente."""
        self.graph.build()
        metrics = TopologyMetrics(self.graph)
        report = metrics.compute_all()

        snapshot = TopologySnapshot(
            timestamp=time.time(),
            tick=tick,
            node_count=report.get("node_count", 0),
            edge_count=report.get("edge_count", 0),
            density=report.get("density", 0.0),
            avg_clustering=report.get("avg_clustering", 0.0),
            global_efficiency=report.get("global_efficiency", 0.0),
            small_world_sigma=report.get("small_world", {}).get("sigma", 0.0),
            modularity_q=report.get("modularity", {}).get("Q", 0.0),
            n_communities=report.get("modularity", {}).get("n_communities", 0),
            top_broadcasters=report.get("hubs", {}).get("broadcasters", [])[:5],
            top_collectors=report.get("hubs", {}).get("collectors", [])[:5],
            top_bridges=report.get("hubs", {}).get("bridges", [])[:5],
            raw={
                "degree_centrality": report.get("degree_centrality", {}),
                "betweenness_centrality": report.get("betweenness_centrality", {}),
                "clustering_coefficient": report.get("clustering_coefficient", {}),
                "community_map": report.get("modularity", {}).get("community_map", {}),
            },
        )

        self._snapshots.append(snapshot)
        self._sample_count += 1

        if len(self._snapshots) > self.max_snapshots:
            self._snapshots = self._snapshots[-self.max_snapshots:]

        return snapshot

    # ------------------------------------------------------------------ #
    # Morphological Genome (Livello 4)
    # ------------------------------------------------------------------ #

    def save_morphological_genome(
        self, snapshot: TopologySnapshot, fitness: float
    ) -> Optional[MorphologicalGenomeRecord]:
        """Salva una topologia come MorphologicalGenome se ha fitness sufficiente."""
        if fitness < self._fitness_threshold:
            return None

        record = MorphologicalGenomeRecord(
            timestamp=snapshot.timestamp,
            tick=snapshot.tick,
            fitness=fitness,
            modularity=snapshot.modularity_q,
            global_efficiency=snapshot.global_efficiency,
            small_world_sigma=snapshot.small_world_sigma,
            density=snapshot.density,
            avg_clustering=snapshot.avg_clustering,
            n_communities=snapshot.n_communities,
            signature=snapshot.raw.get("degree_centrality", {}),
        )

        # Evita duplicati troppo simili
        for existing in self._morphological_genomes:
            if record.similarity_to(existing) > 0.95:
                return existing

        self._morphological_genomes.append(record)
        return record

    def recall_morphological_genome(
        self, current_snapshot: TopologySnapshot, min_similarity: float = 0.8
    ) -> Optional[MorphologicalGenomeRecord]:
        """Cerca un MorphologicalGenome simile alla topologia corrente.

        Quando SPEACE incontra un pattern gia' visto, riattiva
        l'espressione genica associata a quella morfologia di successo.
        """
        current_record = MorphologicalGenomeRecord(
            timestamp=current_snapshot.timestamp,
            tick=current_snapshot.tick,
            fitness=0.0,
            modularity=current_snapshot.modularity_q,
            global_efficiency=current_snapshot.global_efficiency,
            small_world_sigma=current_snapshot.small_world_sigma,
            density=current_snapshot.density,
            avg_clustering=current_snapshot.avg_clustering,
            n_communities=current_snapshot.n_communities,
        )

        best_match = None
        best_similarity = 0.0

        for record in self._morphological_genomes:
            sim = record.similarity_to(current_record)
            if sim > best_similarity and sim >= min_similarity:
                best_similarity = sim
                best_match = record

        return best_match

    def get_morphological_genomes(
        self, top_k: int = 5
    ) -> List[MorphologicalGenomeRecord]:
        """Restituisce i MorphologicalGenome con fitness piu' alta."""
        sorted_genomes = sorted(
            self._morphological_genomes,
            key=lambda r: r.fitness,
            reverse=True,
        )
        return sorted_genomes[:top_k]

    def get_morphological_genome_count(self) -> int:
        return len(self._morphological_genomes)

    # ------------------------------------------------------------------ #
    # Queries
    # ------------------------------------------------------------------ #

    @property
    def count(self) -> int:
        return len(self._snapshots)

    def last(self) -> Optional[TopologySnapshot]:
        return self._snapshots[-1] if self._snapshots else None

    def snapshots(self, since: Optional[float] = None) -> List[TopologySnapshot]:
        if since is None:
            return list(self._snapshots)
        return [s for s in self._snapshots if s.timestamp >= since]

    def time_series(self, metric: str) -> List[Dict[str, Any]]:
        """Estrae una serie temporale per una metrica specifica.

        metric puo' essere: node_count, edge_count, density, avg_clustering,
        global_efficiency, small_world_sigma, modularity_q, n_communities.
        """
        return [
            {"timestamp": s.timestamp, "tick": s.tick, "value": getattr(s, metric, None)}
            for s in self._snapshots
        ]

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #

    def save(self, path: Optional[str] = None) -> int:
        """Appende gli snapshot non ancora persistiti al file JSONL."""
        dst = pathlib.Path(path) if path else self.persist_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not self._snapshots:
            return 0
        try:
            with dst.open("a", encoding="utf-8") as f:
                for s in self._snapshots:
                    line = {
                        "timestamp": s.timestamp,
                        "tick": s.tick,
                        "node_count": s.node_count,
                        "edge_count": s.edge_count,
                        "density": s.density,
                        "avg_clustering": s.avg_clustering,
                        "global_efficiency": s.global_efficiency,
                        "small_world_sigma": s.small_world_sigma,
                        "modularity_q": s.modularity_q,
                        "n_communities": s.n_communities,
                        "top_broadcasters": s.top_broadcasters,
                        "top_collectors": s.top_collectors,
                        "top_bridges": s.top_bridges,
                    }
                    f.write(json.dumps(line) + "\n")
            count = len(self._snapshots)
            self._snapshots.clear()
            return count
        except OSError:
            return 0

    def load(self, path: Optional[str] = None) -> int:
        """Carica snapshot da un file JSONL esistente."""
        src = pathlib.Path(path) if path else self.persist_path
        if not src.exists():
            return 0
        count = 0
        try:
            with src.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    self._snapshots.append(TopologySnapshot(
                        timestamp=data.get("timestamp", 0.0),
                        tick=data.get("tick", 0),
                        node_count=data.get("node_count", 0),
                        edge_count=data.get("edge_count", 0),
                        density=data.get("density", 0.0),
                        avg_clustering=data.get("avg_clustering", 0.0),
                        global_efficiency=data.get("global_efficiency", 0.0),
                        small_world_sigma=data.get("small_world_sigma", 0.0),
                        modularity_q=data.get("modularity_q", 0.0),
                        n_communities=data.get("n_communities", 0),
                        top_broadcasters=data.get("top_broadcasters", []),
                        top_collectors=data.get("top_collectors", []),
                        top_bridges=data.get("top_bridges", []),
                    ))
                    count += 1
        except OSError:
            pass
        return count

    # ------------------------------------------------------------------ #
    # Summary
    # ------------------------------------------------------------------ #

    def summary(self) -> Dict[str, Any]:
        if not self._snapshots:
            latest = None
        else:
            latest = self._snapshots[-1]
        return {
            "total_snapshots": len(self._snapshots),
            "sample_count": self._sample_count,
            "latest": {
                "timestamp": latest.timestamp if latest else None,
                "tick": latest.tick if latest else None,
                "node_count": latest.node_count if latest else None,
                "edge_count": latest.edge_count if latest else None,
                "density": latest.density if latest else None,
                "avg_clustering": latest.avg_clustering if latest else None,
                "global_efficiency": latest.global_efficiency if latest else None,
                "small_world_sigma": latest.small_world_sigma if latest else None,
                "modularity_q": latest.modularity_q if latest else None,
                "n_communities": latest.n_communities if latest else None,
            } if latest else None,
            "persist_path": str(self.persist_path),
        }
