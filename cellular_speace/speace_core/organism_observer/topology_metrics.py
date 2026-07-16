"""TopologyMetrics — metriche topologiche sull'Operational Functional Graph.

Calcola, senza dipendenze esterne (no NetworkX), le metriche essenziali:
  - Degree centrality (in/out)
  - Betweenness centrality (approssimata)
  - Clustering coefficient
  - Modularity (basata su label di comunità)
  - Small-world coefficient (sigma)
  - Hub detection
  - Global efficiency

Tutte le metriche operano sul grafo pesato diretto di FunctionalGraph.
"""

from __future__ import annotations

import math
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Set, Tuple

from speace_core.organism_observer.functional_graph import FunctionalGraph


class TopologyMetrics:
    """Calcola metriche topologiche sul FunctionalGraph.

    Usage::

        graph = FunctionalGraph(collector)
        graph.build()
        metrics = TopologyMetrics(graph)
        report = metrics.compute_all()
    """

    def __init__(self, graph: FunctionalGraph) -> None:
        self.graph = graph
        self._nodes: List[str] = []
        self._node_set: Set[str] = set()
        self._out_edges: Dict[str, List[Tuple[str, float]]] = {}
        self._in_edges: Dict[str, List[Tuple[str, float]]] = {}
        self._sync()

    def _sync(self) -> None:
        """Sincronizza le strutture interne con lo stato corrente del grafo."""
        adj = self.graph.adjacency()
        self._nodes = list(adj.keys())
        # Assicura che anche i nodi con solo archi entranti siano presenti
        all_targets: Set[str] = set()
        for s, targets in adj.items():
            for t in targets:
                all_targets.add(t)
        for t in all_targets:
            if t not in adj:
                adj[t] = {}
        self._nodes = list(set(adj.keys()) | all_targets)
        self._node_set = set(self._nodes)

        self._out_edges = {}
        self._in_edges = defaultdict(list)
        for s, targets in adj.items():
            self._out_edges[s] = [(t, w) for t, w in targets.items()]
            for t, w in targets.items():
                self._in_edges[t].append((s, w))

    # ------------------------------------------------------------------ #
    # Degree centrality
    # ------------------------------------------------------------------ #

    def degree_centrality(self, normalized: bool = True) -> Dict[str, Dict[str, float]]:
        """Degree centrality in e out per ogni nodo."""
        result = {}
        n = max(1, len(self._nodes) - 1) if normalized else 1
        for node in self._nodes:
            out_deg = len(self._out_edges.get(node, []))
            in_deg = len(self._in_edges.get(node, []))
            result[node] = {
                "out_degree": out_deg / n,
                "in_degree": in_deg / n,
                "total_degree": (out_deg + in_deg) / n,
            }
        return result

    # ------------------------------------------------------------------ #
    # Betweenness centrality (approssimata — BFS su nodi campionati)
    # ------------------------------------------------------------------ #

    def betweenness_centrality(self, sample_ratio: float = 0.3) -> Dict[str, float]:
        """Betweenness centrality approssimata.

        Usa campionamento casuale per reti grandi. Per reti piccole
        (< 200 nodi) calcola esattamente.
        """
        import random

        nodes = self._nodes
        if not nodes:
            return {}

        # Se la rete è piccola, calcola esattamente
        if len(nodes) < 200:
            sources = nodes
        else:
            k = max(1, int(len(nodes) * sample_ratio))
            sources = random.sample(nodes, k)

        betweenness: Dict[str, float] = {n: 0.0 for n in nodes}
        n_sources = len(sources)

        for s in sources:
            stack: List[str] = []
            pred: Dict[str, List[str]] = {n: [] for n in nodes}
            sigma: Dict[str, int] = {n: 0 for n in nodes}
            sigma[s] = 1
            dist: Dict[str, Optional[int]] = {n: None for n in nodes}
            dist[s] = 0

            queue: deque = deque([s])
            while queue:
                v = queue.popleft()
                stack.append(v)
                for w, _ in self._out_edges.get(v, []):
                    if w not in self._node_set:
                        continue
                    if dist[w] is None:
                        dist[w] = dist[v] + 1
                        queue.append(w)
                    if dist[w] == dist[v] + 1:
                        sigma[w] += sigma[v]
                        pred[w].append(v)

            delta: Dict[str, float] = {n: 0.0 for n in nodes}
            while stack:
                w = stack.pop()
                for v in pred[w]:
                    delta[v] += (sigma[v] / sigma[w]) * (1.0 + delta[w])
                if w != s:
                    betweenness[w] += delta[w]

        # Normalizza
        for n in betweenness:
            betweenness[n] /= max(1, (n_sources - 1) * (len(nodes) - 1)) if n_sources > 1 else 1

        return betweenness

    # ------------------------------------------------------------------ #
    # Clustering coefficient (locale)
    # ------------------------------------------------------------------ #

    def clustering_coefficient(self) -> Dict[str, float]:
        """Clustering coefficient locale per ogni nodo.

        Per grafi diretti: frazione di coppie di vicini connesse
        rispetto al totale delle coppie possibili.
        """
        result = {}
        for node in self._nodes:
            neighbors = set()
            for n, _ in self._out_edges.get(node, []):
                if n in self._node_set:
                    neighbors.add(n)
            for n, _ in self._in_edges.get(node, []):
                if n in self._node_set:
                    neighbors.add(n)

            k = len(neighbors)
            if k < 2:
                result[node] = 0.0
                continue

            # Conta archi tra i vicini
            edges_between = 0
            nlist = list(neighbors)
            for i in range(len(nlist)):
                for j in range(i + 1, len(nlist)):
                    a, b = nlist[i], nlist[j]
                    out_a = {t for t, _ in self._out_edges.get(a, [])}
                    if b in out_a:
                        edges_between += 1
                    out_b = {t for t, _ in self._out_edges.get(b, [])}
                    if a in out_b:
                        edges_between += 1

            max_possible = k * (k - 1)
            result[node] = edges_between / max_possible if max_possible > 0 else 0.0

        return result

    # ------------------------------------------------------------------ #
    # Modularity
    # ------------------------------------------------------------------ #

    def modularity(self, community_map: Dict[str, int]) -> float:
        """Modularità Q per una partizione in comunità.

        Args:
            community_map: {node_id: community_label}

        Reference: Newman & Girvan (2004)
        """
        m = sum(es.weight for (_, _), es in self.graph._edges.items())
        if m == 0:
            return 0.0

        q = 0.0
        for (s, t), es in self.graph._edges.items():
            if s not in community_map or t not in community_map:
                continue
            if community_map[s] == community_map[t]:
                k_out = self.graph.degree(s, "out")
                k_in = self.graph.degree(t, "in")
                expected = (k_out * k_in) / (2 * m)
                q += es.weight - expected

        return q / (2 * m)

    def detect_communities_leiden(self) -> Dict[str, int]:
        """Community detection euristica (senza NetworkX).

        Usa un approccio greedy: combina iterativamente i nodi in
        comunità massimizzando la modularità.
        """
        community: Dict[str, int] = {n: i for i, n in enumerate(self._nodes)}
        m = sum(es.weight for (_, _), es in self.graph._edges.items())
        if m == 0:
            return community

        improved = True
        while improved:
            improved = False
            for node in self._nodes:
                best_q = self._modularity_of(community, m)
                best_c = community[node]

                # Prova a spostare il nodo in ogni altra comunità
                neighbor_communities = set()
                for n, _ in self._out_edges.get(node, []):
                    if n in community:
                        neighbor_communities.add(community[n])
                for n, _ in self._in_edges.get(node, []):
                    if n in community:
                        neighbor_communities.add(community[n])

                for c in neighbor_communities:
                    if c == community[node]:
                        continue
                    old_c = community[node]
                    community[node] = c
                    new_q = self._modularity_of(community, m)
                    if new_q > best_q + 1e-10:
                        best_q = new_q
                        best_c = c
                        improved = True
                    community[node] = old_c

                community[node] = best_c

        # Ricompatta labels
        label_map = {}
        next_label = 0
        for n in self._nodes:
            c = community[n]
            if c not in label_map:
                label_map[c] = next_label
                next_label += 1
            community[n] = label_map[c]

        return community

    def _modularity_of(self, community: Dict[str, int], m: float) -> float:
        """Calcola modularità per una data partizione."""
        if m == 0:
            return 0.0
        q = 0.0
        for (s, t), es in self.graph._edges.items():
            if community.get(s) == community.get(t):
                k_out = self.graph.degree(s, "out")
                k_in = self.graph.degree(t, "in")
                expected = (k_out * k_in) / (2 * m) if m > 0 else 0
                q += es.weight - expected
        return q / (2 * m) if m > 0 else 0.0

    # ------------------------------------------------------------------ #
    # Small-world metrics
    # ------------------------------------------------------------------ #

    def small_world_sigma(
        self,
        n_rand: int = 100,
    ) -> Dict[str, float]:
        """Coefficiente small-world sigma = (C/C_rand) / (L/L_rand).

        Valori >> 1 indicano struttura small-world.
        """
        import random

        n = len(self._nodes)
        if n < 4:
            return {"sigma": 1.0, "C": 0.0, "L": 0.0, "C_rand": 0.0, "L_rand": 0.0}

        # Clustering medio osservato
        clust = self.clustering_coefficient()
        C_obs = sum(clust.values()) / len(clust) if clust else 0.0

        # Path length medio osservato
        L_obs = self._avg_shortest_path_length()

        # Rete casuale equivalente (Erdos-Renyi con stesso n, stesso grado medio)
        avg_k = sum(len(self._out_edges.get(n, [])) for n in self._nodes) / n
        p = avg_k / max(1, n - 1)

        # Clustering atteso per Erdos-Renyi
        C_rand = p

        # Path length atteso per Erdos-Renyi
        L_rand = math.log(n) / max(math.log(avg_k), 0.01) if avg_k > 1 else 1.0

        sigma = (C_obs / max(C_rand, 1e-10)) / (L_obs / max(L_rand, 1e-10))

        return {
            "sigma": sigma,
            "C": C_obs,
            "L": L_obs,
            "C_rand": C_rand,
            "L_rand": L_rand,
        }

    def _avg_shortest_path_length(self) -> float:
        """Distanza media tra tutte le coppie di nodi (BFS)."""
        n = len(self._nodes)
        if n < 2:
            return 0.0

        total = 0.0
        count = 0
        for s in self._nodes:
            dist = {n: None for n in self._nodes}
            dist[s] = 0
            queue = deque([s])
            while queue:
                v = queue.popleft()
                for w, _ in self._out_edges.get(v, []):
                    if w in dist and dist[w] is None:
                        dist[w] = dist[v] + 1
                        queue.append(w)
            for t, d in dist.items():
                if t != s and d is not None:
                    total += d
                    count += 1

        return total / max(count, 1)

    # ------------------------------------------------------------------ #
    # Global efficiency
    # ------------------------------------------------------------------ #

    def global_efficiency(self) -> float:
        """Efficienza globale = media delle inverse delle distanze.

        Valore tra 0 e 1. 1 = rete completamente connessa.
        """
        n = len(self._nodes)
        if n < 2:
            return 0.0

        total = 0.0
        count = 0
        for s in self._nodes:
            dist = {n: None for n in self._nodes}
            dist[s] = 0
            queue = deque([s])
            while queue:
                v = queue.popleft()
                for w, _ in self._out_edges.get(v, []):
                    if w in dist and dist[w] is None:
                        dist[w] = dist[v] + 1
                        queue.append(w)
            for t, d in dist.items():
                if t != s and d is not None and d > 0:
                    total += 1.0 / d
                    count += 1

        return total / max(count, 1)

    # ------------------------------------------------------------------ #
    # Hub detection
    # ------------------------------------------------------------------ #

    def hub_detection(self, top_k: int = 5) -> Dict[str, Any]:
        """Identifica gli hub: nodi con degree centrality più alta.

        Restituisce i top_k nodi per:
          - out-degree (broadcaster)
          - in-degree (collector)
          - betweenness (bridge)
        """
        dc = self.degree_centrality()
        bc = self.betweenness_centrality(sample_ratio=0.3)

        # Ordina per out-degree
        by_out = sorted(dc.items(), key=lambda x: x[1]["out_degree"], reverse=True)
        # Ordina per in-degree
        by_in = sorted(dc.items(), key=lambda x: x[1]["in_degree"], reverse=True)
        # Ordina per betweenness
        by_between = sorted(bc.items(), key=lambda x: x[1], reverse=True)

        return {
            "broadcasters": [{"node": n, "score": v["out_degree"]} for n, v in by_out[:top_k]],
            "collectors": [{"node": n, "score": v["in_degree"]} for n, v in by_in[:top_k]],
            "bridges": [{"node": n, "score": v} for n, v in by_between[:top_k]],
        }

    # ------------------------------------------------------------------ #
    # Composite
    # ------------------------------------------------------------------ #

    def compute_all(self) -> Dict[str, Any]:
        """Calcola tutte le metriche e restituisce un report completo."""
        degree_c = self.degree_centrality()
        communities = self.detect_communities_leiden()
        n_communities = len(set(communities.values()))

        return {
            "node_count": len(self._nodes),
            "edge_count": self.graph.edge_count,
            "density": self.graph.summary()["density"],
            "degree_centrality": degree_c,
            "clustering_coefficient": self.clustering_coefficient(),
            "avg_clustering": self._avg_dict(
                self.clustering_coefficient()
            ),
            "global_efficiency": self.global_efficiency(),
            "small_world": self.small_world_sigma(),
            "modularity": {
                "Q": self.modularity(communities),
                "n_communities": n_communities,
                "community_map": communities,
            },
            "hubs": self.hub_detection(top_k=10),
            "betweenness_centrality": self.betweenness_centrality(),
        }

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _avg_dict(d: Dict[str, float]) -> float:
        return sum(d.values()) / len(d) if d else 0.0
