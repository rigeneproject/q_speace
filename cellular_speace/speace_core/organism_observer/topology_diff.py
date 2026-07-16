"""TopologyDiff — delta strutturali tra snapshot consecutivi della topologia.

Confronta due TopologySnapshot e produce un report delle differenze:
  - Variazioni assolute e relative delle metriche scalari
  - Nodi entrati/usciti
  - Hub cambiati
  - Velocita' di cambiamento (derivata temporale prima approssimazione)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from speace_core.organism_observer.topology_history import TopologyHistory, TopologySnapshot


@dataclass
class StructureDelta:
    # Delta metriche scalari
    d_node_count: float = 0.0
    d_edge_count: float = 0.0
    d_density: float = 0.0
    d_avg_clustering: float = 0.0
    d_global_efficiency: float = 0.0
    d_small_world_sigma: float = 0.0
    d_modularity_q: float = 0.0
    d_n_communities: float = 0.0

    # Variazioni relative (per confronto scale diverse)
    rel_d_node_count: float = 0.0
    rel_d_edge_count: float = 0.0
    rel_d_density: float = 0.0
    rel_d_avg_clustering: float = 0.0
    rel_d_global_efficiency: float = 0.0
    rel_d_small_world_sigma: float = 0.0
    rel_d_modularity_q: float = 0.0

    # Delta hub
    broadcasters_changed: List[str] = field(default_factory=list)
    collectors_changed: List[str] = field(default_factory=list)
    bridges_changed: List[str] = field(default_factory=list)

    # Nodi
    nodes_appeared: List[str] = field(default_factory=list)
    nodes_disappeared: List[str] = field(default_factory=list)

    # Velocita' di cambiamento (Δt in secondi)
    delta_t: float = 1.0
    change_velocity: float = 0.0  # norma L2 delle variazione relative / dt
    entropy_change: float = 0.0   # variazione di entropia della distribuzione dei nodi

    # Raw
    raw: Dict[str, Any] = field(default_factory=dict)


class TopologyDiff:
    """Confronta snapshot e calcola delta strutturali.

    Usage::

        history = TopologyHistory(graph)
        past = history.sample(tick=100)
        future = history.sample(tick=200)

        diff = TopologyDiff.compute(past, future)
        print(diff.d_modularity_q)       # +0.05
        print(diff.nodes_appeared)       # ["Cache"]
        print(diff.change_velocity)      # 0.42
    """

    @staticmethod
    def compute(
        older: TopologySnapshot,
        newer: TopologySnapshot,
        prev_raw: Optional[Dict[str, Any]] = None,
        cur_raw: Optional[Dict[str, Any]] = None,
    ) -> StructureDelta:
        """Calcola il delta strutturale tra due snapshot consecutivi."""
        dt = max(newer.timestamp - older.timestamp, 0.001)

        older_raw = prev_raw or older.raw
        newer_raw = cur_raw or newer.raw

        delta = StructureDelta()
        delta.delta_t = dt

        # ------------------------------------------------------------------ #
        # Delta scalari assoluti
        # ------------------------------------------------------------------ #
        delta.d_node_count = float(newer.node_count - older.node_count)
        delta.d_edge_count = float(newer.edge_count - older.edge_count)
        delta.d_density = newer.density - older.density
        delta.d_avg_clustering = newer.avg_clustering - older.avg_clustering
        delta.d_global_efficiency = newer.global_efficiency - older.global_efficiency
        delta.d_small_world_sigma = newer.small_world_sigma - older.small_world_sigma
        delta.d_modularity_q = newer.modularity_q - older.modularity_q
        delta.d_n_communities = float(newer.n_communities - older.n_communities)

        # ------------------------------------------------------------------ #
        # Delta scalari relativi
        # ------------------------------------------------------------------ #
        def _rel(new: float, old: float) -> float:
            if abs(old) < 1e-12:
                return 0.0 if abs(new) < 1e-12 else float("inf")
            return (new - old) / abs(old)

        delta.rel_d_node_count = _rel(
            float(newer.node_count), float(older.node_count)
        )
        delta.rel_d_edge_count = _rel(
            float(newer.edge_count), float(older.edge_count)
        )
        delta.rel_d_density = _rel(newer.density, older.density)
        delta.rel_d_avg_clustering = _rel(newer.avg_clustering, older.avg_clustering)
        delta.rel_d_global_efficiency = _rel(
            newer.global_efficiency, older.global_efficiency
        )
        delta.rel_d_small_world_sigma = _rel(
            newer.small_world_sigma, older.small_world_sigma
        )
        delta.rel_d_modularity_q = _rel(newer.modularity_q, older.modularity_q)

        # ------------------------------------------------------------------ #
        # Delta hub
        # ------------------------------------------------------------------ #
        delta.broadcasters_changed = TopologyDiff._hub_diff(
            older.top_broadcasters, newer.top_broadcasters
        )
        delta.collectors_changed = TopologyDiff._hub_diff(
            older.top_collectors, newer.top_collectors
        )
        delta.bridges_changed = TopologyDiff._hub_diff(
            older.top_bridges, newer.top_bridges
        )

        # ------------------------------------------------------------------ #
        # Nodi apparsi/scomparsi
        # ------------------------------------------------------------------ #
        old_nodes = set(older_raw.get("degree_centrality", {}).keys())
        new_nodes = set(newer_raw.get("degree_centrality", {}).keys())
        delta.nodes_appeared = sorted(new_nodes - old_nodes)
        delta.nodes_disappeared = sorted(old_nodes - new_nodes)

        # ------------------------------------------------------------------ #
        # Velocita' di cambiamento aggregata
        # ------------------------------------------------------------------ #
        rel_deltas = [
            delta.rel_d_node_count,
            delta.rel_d_edge_count,
            delta.rel_d_density,
            delta.rel_d_avg_clustering,
            delta.rel_d_global_efficiency,
            delta.rel_d_small_world_sigma,
            delta.rel_d_modularity_q,
        ]
        # Norma L2 normalizzata su dt
        if dt > 0:
            finite = [v for v in rel_deltas if math.isfinite(v)]
            l2_norm = math.sqrt(sum(v * v for v in finite) / max(len(finite), 1))
            delta.change_velocity = l2_norm / dt
        else:
            delta.change_velocity = 0.0

        # ------------------------------------------------------------------ #
        # Variazione di entropia (distribuzione nodi)
        # ------------------------------------------------------------------ #
        old_deg = older_raw.get("degree_centrality", {})
        new_deg = newer_raw.get("degree_centrality", {})
        delta.entropy_change = TopologyDiff._entropy_change(
            old_deg, new_deg, old_nodes | new_nodes
        )

        # raw
        delta.raw = {
            "degree_centrality_old": {k: v.get("total_degree", 0) for k, v in old_deg.items()},
            "degree_centrality_new": {k: v.get("total_degree", 0) for k, v in new_deg.items()},
        }

        return delta

    # ------------------------------------------------------------------ #
    # Diffs consecutive
    # ------------------------------------------------------------------ #

    @staticmethod
    def compute_series(
        history: TopologyHistory,
    ) -> List[StructureDelta]:
        """Calcola delta consecutivi per l'intera history."""
        snaps = history.snapshots()
        if len(snaps) < 2:
            return []
        deltas: List[StructureDelta] = []
        for i in range(1, len(snaps)):
            prev = snaps[i - 1]
            cur = snaps[i]
            delta = TopologyDiff.compute(prev, cur)
            deltas.append(delta)
        return deltas

    @staticmethod
    def compute_on_sample(
        history: TopologyHistory,
        older_tick: int,
        newer_tick: int,
    ) -> Optional[StructureDelta]:
        """Calcola delta tra due snapshot specifici per tick."""
        snaps = {s.tick: s for s in history.snapshots()}
        older = snaps.get(older_tick)
        newer = snaps.get(newer_tick)
        if older is None or newer is None:
            return None
        return TopologyDiff.compute(older, newer)

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _hub_diff(
        old_hubs: List[Dict[str, Any]],
        new_hubs: List[Dict[str, Any]],
    ) -> List[str]:
        old_names = {h.get("node", "") for h in old_hubs}
        new_names = {h.get("node", "") for h in new_hubs}
        return sorted((old_names - new_names) | (new_names - old_names))

    @staticmethod
    def _entropy_change(
        old_deg: Dict[str, Dict[str, Any]],
        new_deg: Dict[str, Dict[str, Any]],
        all_nodes: Set[str],
    ) -> float:
        def _norm_entropy(
            deg: Dict[str, Dict[str, Any]],
        ) -> float:
            vals = [
                v.get("total_degree", 0)
                for n, v in deg.items()
            ]
            total = sum(vals) or 1.0
            probs = [v / total for v in vals]
            h = -sum(p * math.log2(p) for p in probs if p > 0)
            return h

        h_old = _norm_entropy(old_deg)
        h_new = _norm_entropy(new_deg)
        return h_new - h_old
