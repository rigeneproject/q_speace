"""Topology helpers for the AACM model (T-AACM-SPEC §1.2 + §2).

Implements:
- :func:`betweenness_centrality` — Brandes' algorithm, adapted for
  directed weighted graphs, in pure Python over numpy adjacency.
- :func:`edge_weights_from_observations` — build edge weights from
  observed (success/failure) counts.
- :func:`node_failure_streak` — count consecutive failures per node,
  used by the fail-fast (regola 2) logic in the controller.

BCEL: "centrality" is a graph-theoretic quantity, not a metaphor. The
helpers operate on the *control graph* of the agent's tool/agent
network, not on the agent's beliefs.
"""

from __future__ import annotations

from collections import deque

import numpy as np

from .primitives import CentralityGraph


def edge_weights_from_observations(
    success_counts: dict[tuple[str, str], int],
    failure_counts: dict[tuple[str, str], int],
) -> list[tuple[str, str, float]]:
    """Compute edge weights from observed (success, failure) counts.

    weight = (success + 1) / (success + failure + 2)  in (0, 1)
    """
    keys = set(success_counts) | set(failure_counts)
    out: list[tuple[str, str, float]] = []
    for k in keys:
        s = success_counts.get(k, 0)
        f = failure_counts.get(k, 0)
        w = (s + 1) / (s + f + 2)
        out.append((k[0], k[1], float(w)))
    return out


def betweenness_centrality(graph: CentralityGraph) -> dict[str, float]:
    """Compute betweenness centrality on a directed weighted graph.

    Brandes' algorithm, O(V*E) per source, total O(V^2*E) in the worst
    case. Edge weights are interpreted as *inverse distance*: a higher
    weight means a *shorter* path (closer to 1.0 ⇒ more central
    connection). For unweighted-like behaviour, pass all weights = 1.0.

    Returns a dict mapping each node to its betweenness score, in
    [0, 1] (normalized by the number of pairs of *other* nodes).
    """
    nodes = list(graph.nodes)
    n = len(nodes)
    if n < 3:
        return dict.fromkeys(nodes, 0.0)

    idx = {nd: i for i, nd in enumerate(nodes)}
    # Build adjacency with distances = 1 - w (clipped to [0, 1]).
    dist_adj: list[list[tuple[int, float]]] = [[] for _ in range(n)]
    for src, dst, w in graph.edges:
        i, j = idx[src], idx[dst]
        d = max(0.0, min(1.0, 1.0 - float(w)))
        # Skip self-loops with weight 1.0 (distance 0): they create
        # zero-length paths and confuse the accumulation.
        if i == j and d == 0.0:
            continue
        dist_adj[i].append((j, d))

    bc = np.zeros(n, dtype=np.float64)

    for s in range(n):
        # Brandes: BFS-like accumulation over Dijkstra.
        sigma = np.zeros(n, dtype=np.float64)
        sigma[s] = 1.0
        dist = np.full(n, np.inf)
        dist[s] = 0.0
        order: list[int] = []
        # predecessors[v] = list of nodes u such that u -> v on a shortest path
        preds: list[list[int]] = [[] for _ in range(n)]
        # Use a deque for BFS-like exploration over a weighted graph
        # (this is approximate; for unweighted graphs it is exact).
        queue: deque[int] = deque([s])
        while queue:
            v = queue.popleft()
            order.append(v)
            for w_v, d_vw in dist_adj[v]:
                # First visit of w_v?
                if dist[w_v] == np.inf:
                    queue.append(w_v)
                    dist[w_v] = dist[v] + d_vw
                # If this is a shortest path, accumulate.
                if dist[w_v] >= dist[v] + d_vw - 1e-12:
                    sigma[w_v] += sigma[v]
                    preds[w_v].append(v)

        delta = np.zeros(n, dtype=np.float64)
        # Accumulate in reverse order.
        for w_v in reversed(order):
            for v in preds[w_v]:
                if sigma[w_v] > 0.0:
                    delta[v] += (sigma[v] / sigma[w_v]) * (1.0 + delta[w_v])
            if w_v != s:
                bc[w_v] += delta[w_v]

    # Normalize: divide by (n-1)(n-2)/2 for undirected, but for directed
    # we divide by (n-1)(n-2). The output is therefore in [0, 1].
    denom = max(1, (n - 1) * (n - 2))
    bc = bc / denom
    return {nodes[i]: float(bc[i]) for i in range(n)}


def node_failure_streak(node: str, history: list[tuple[str, bool]]) -> int:
    """Count consecutive trailing failures for ``node`` in ``history``.

    ``history`` is a list of ``(node, success)`` pairs in chronological
    order. The returned count is reset by the first trailing success.
    """
    streak = 0
    for n, ok in reversed(history):
        if n != node:
            continue
        if ok:
            break
        streak += 1
    return streak
