"""Directed spike-lag causal discovery & non-destructive do-calculus DAG (T248).

Synthesized via BCEL from ``speace_agi/brain/causal_inference.py`` with two
critical engineering remediations:
1. ``intervene(do_map)`` and ``counterfactual(...)`` evaluate on an immutable
   mutilated edge mask ``E_bar_X`` and NEVER mutate the underlying graph in-place.
2. All observations and weights require explicit ``math.isfinite`` values (never
   salted string hashes).

Strict invariant (AGENTS.md §2): causal edges model classical directed signal
precedence only and are strictly separated from ``EntanglementRegistry``.
"""

from __future__ import annotations

import math
from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class CausalEdge:
    """Directed structural causal link ``source -> target``."""

    source: str
    target: str
    weight: float
    asymmetry: float = 1.0

    def __post_init__(self) -> None:
        if not self.source or not self.target:
            raise ValueError("source and target must be non-empty")
        if self.source == self.target:
            raise ValueError("self-loops are not permitted in a causal DAG")
        if not math.isfinite(self.weight):
            raise ValueError(f"weight must be finite (got {self.weight!r})")
        if not math.isfinite(self.asymmetry) or not (-1.0 <= self.asymmetry <= 1.0):
            raise ValueError(f"asymmetry must be finite and in [-1, 1] (got {self.asymmetry!r})")


def spike_temporal_asymmetry(
    activity: np.ndarray,
    *,
    max_lag: int = 3,
    min_cooccurrences: int = 2,
    threshold: float = 0.25,
    ids: Sequence[str] | None = None,
) -> list[CausalEdge]:
    """Discover directed temporal-precedence edges from 2-D spike trains (neurons x time).

    For pair ``(i, j)``, counts forward Precedence ``N_{i < j}`` where unit ``i``
    spikes within ``1..max_lag`` steps before unit ``j``, and backward ``N_{j < i}``.
    Emits ``i -> j`` when ``A_ij = (N_{i<j} - N_{j<i}) / (N_{i<j} + N_{j<i}) >= threshold``.
    """
    arr = np.asarray(activity, dtype=float)
    if arr.ndim != 2:
        raise ValueError("activity must be 2-D (neurons x time)")
    if not np.all(np.isfinite(arr)):
        raise ValueError("activity must contain only finite values")
    if max_lag < 1:
        raise ValueError("max_lag must be >= 1")
    if min_cooccurrences < 1:
        raise ValueError("min_cooccurrences must be >= 1")
    if not math.isfinite(threshold) or not (0.0 < threshold <= 1.0):
        raise ValueError("threshold must be finite and in (0, 1]")

    n_units, n_steps = arr.shape
    node_ids = [f"n{i}" for i in range(n_units)] if ids is None else list(ids)
    if len(node_ids) != n_units:
        raise ValueError("ids length must match number of activity rows")

    fired = np.abs(arr) > 0.0
    candidates: list[CausalEdge] = []
    for i in range(n_units):
        for j in range(i + 1, n_units):
            forward = 0
            backward = 0
            for lag in range(1, min(max_lag, n_steps - 1) + 1):
                if lag >= n_steps:
                    break
                forward += int(np.sum(fired[i, : n_steps - lag] & fired[j, lag:]))
                backward += int(np.sum(fired[j, : n_steps - lag] & fired[i, lag:]))
            total = forward + backward
            if total < min_cooccurrences:
                continue
            asym = (forward - backward) / total
            if asym >= threshold:
                conf_weight = 0.5 + 0.4 * abs(asym)
                candidates.append(
                    CausalEdge(
                        source=node_ids[i],
                        target=node_ids[j],
                        weight=conf_weight,
                        asymmetry=asym,
                    )
                )
            elif asym <= -threshold:
                conf_weight = 0.5 + 0.4 * abs(asym)
                candidates.append(
                    CausalEdge(
                        source=node_ids[j],
                        target=node_ids[i],
                        weight=conf_weight,
                        asymmetry=-asym,
                    )
                )
    candidates.sort(key=lambda e: (-abs(e.asymmetry), e.source, e.target))
    return candidates


class StructuralCausalDAG:
    """Linear structural causal model supporting non-destructive Pearl interventions."""

    def __init__(
        self,
        nodes: Sequence[str],
        edges: Sequence[CausalEdge] = (),
    ) -> None:
        unique_nodes = list(dict.fromkeys(nodes))
        if not unique_nodes or any(not n for n in unique_nodes):
            raise ValueError("nodes must be non-empty strings")
        node_set = set(unique_nodes)
        edge_map: dict[tuple[str, str], CausalEdge] = {}
        for edge in edges:
            if edge.source not in node_set or edge.target not in node_set:
                raise ValueError(
                    f"edge ({edge.source!r} -> {edge.target!r}) references unknown node"
                )
            edge_map[(edge.source, edge.target)] = edge

        self._nodes: tuple[str, ...] = tuple(unique_nodes)
        self._edges: tuple[CausalEdge, ...] = tuple(edge_map.values())
        self._topo_order: tuple[str, ...] = self._compute_topological_order(
            self._nodes, self._edges
        )

    @staticmethod
    def _compute_topological_order(
        nodes: Sequence[str], edges: Sequence[CausalEdge]
    ) -> tuple[str, ...]:
        in_degree: dict[str, int] = dict.fromkeys(nodes, 0)
        children: dict[str, list[str]] = {n: [] for n in nodes}
        for e in edges:
            in_degree[e.target] += 1
            children[e.source].append(e.target)
        queue: deque[str] = deque(n for n in nodes if in_degree[n] == 0)
        order: list[str] = []
        while queue:
            u = queue.popleft()
            order.append(u)
            for v in children[u]:
                in_degree[v] -= 1
                if in_degree[v] == 0:
                    queue.append(v)
        if len(order) != len(nodes):
            raise ValueError("causal graph contains a directed cycle")
        return tuple(order)

    @property
    def nodes(self) -> tuple[str, ...]:
        return self._nodes

    @property
    def edges(self) -> tuple[CausalEdge, ...]:
        return self._edges

    @classmethod
    def from_temporal_edges(
        cls, nodes: Sequence[str], candidate_edges: Sequence[CausalEdge]
    ) -> StructuralCausalDAG:
        """Greedily accept strongest temporal edges that preserve DAG acyclicity."""
        accepted: list[CausalEdge] = []
        ordered_candidates = sorted(
            candidate_edges, key=lambda e: (-abs(e.asymmetry), -abs(e.weight), e.source, e.target)
        )
        for edge in ordered_candidates:
            trial = [*accepted, edge]
            try:
                cls._compute_topological_order(nodes, trial)
                accepted.append(edge)
            except ValueError:
                continue
        return cls(nodes=nodes, edges=accepted)

    def parents_of(self, node: str) -> tuple[CausalEdge, ...]:
        if node not in self._nodes:
            raise KeyError(f"unknown node: {node!r}")
        return tuple(e for e in self._edges if e.target == node)

    def predict(self, exogenous: Mapping[str, float] | None = None) -> dict[str, float]:
        """Evaluate structural equations X_v = sum_{u->v} w_{uv} X_u + U_v."""
        return self.intervene(do_map={}, exogenous=exogenous)

    def intervene(
        self,
        do_map: Mapping[str, float],
        exogenous: Mapping[str, float] | None = None,
    ) -> dict[str, float]:
        """Evaluate P(V | do(X = x)) on the mutilated DAG G_{\\overline{X}} without mutating self."""
        exo = dict(exogenous) if exogenous is not None else {}
        for k, v in exo.items():
            if k not in self._nodes:
                raise KeyError(f"unknown exogenous node: {k!r}")
            if not math.isfinite(v):
                raise ValueError(f"exogenous[{k!r}] must be finite")
        clamped: dict[str, float] = {}
        for k, v in do_map.items():
            if k not in self._nodes:
                raise KeyError(f"unknown intervention node: {k!r}")
            fval = float(v)
            if not math.isfinite(fval):
                raise ValueError(f"do_map[{k!r}] must be finite")
            clamped[k] = fval

        # Mutilated incoming parent map: incoming edges to clamped nodes are ignored, never deleted.
        incoming: dict[str, list[CausalEdge]] = {n: [] for n in self._nodes}
        for e in self._edges:
            if e.target not in clamped:
                incoming[e.target].append(e)

        values: dict[str, float] = {}
        for node in self._topo_order:
            if node in clamped:
                values[node] = clamped[node]
            else:
                u_val = float(exo.get(node, 0.0))
                parent_sum = sum(e.weight * values[e.source] for e in incoming[node])
                values[node] = u_val + parent_sum
        return values

    def counterfactual(
        self,
        observed: Mapping[str, float],
        do_map: Mapping[str, float],
    ) -> dict[str, float]:
        """Pearl 3-step counterfactual: (1) Abduction of U, (2) Action do(X=x), (3) Prediction."""
        obs: dict[str, float] = {}
        for node in self._nodes:
            if node not in observed:
                raise KeyError(f"observed missing node {node!r}")
            fval = float(observed[node])
            if not math.isfinite(fval):
                raise ValueError(f"observed[{node!r}] must be finite")
            obs[node] = fval

        # Step 1 (Abduction): infer structural residuals U_v = X_v - sum_{u->v} w_{uv} X_u
        inferred_exo: dict[str, float] = {}
        for node in self._topo_order:
            parent_sum = sum(e.weight * obs[e.source] for e in self.parents_of(node))
            inferred_exo[node] = obs[node] - parent_sum

        # Steps 2 & 3 (Action on mutilated DAG + Prediction with abducted U)
        return self.intervene(do_map=do_map, exogenous=inferred_exo)
