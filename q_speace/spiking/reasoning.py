"""Symbolic graph abduction, 2-hop Jaccard analogy & TDM maintenance scheduler (T249-05).

Synthesized via BCEL from ``speace_agi``
(``brain/reasoning.py``, ``cognitive/cognitive_rhythms.py``):
- Associative intuition and theta/gamma brainwave narratives are *accidental*.
- Typed confidence-product forward chaining, O(b^(d/2)) bidirectional BFS
  shortest-path abduction, 2-hop relational-neighborhood Jaccard structural
  analogy, and deterministic active/maintenance time-division scheduling survive.
"""

from __future__ import annotations

import math
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

TDMOperatingMode = Literal["active", "maintenance"]
TDMPhase = Literal["sense", "route", "evaluate", "verify", "consolidate"]

_DEFAULT_PHASES: tuple[TDMPhase, ...] = ("sense", "route", "evaluate", "verify", "consolidate")


@dataclass(frozen=True)
class RelationEdge:
    """Typed directed edge ``source -[relation]-> target`` with confidence in (0, 1]."""

    source: str
    relation: str
    target: str
    confidence: float = 1.0

    def __post_init__(self) -> None:
        if not self.source or not self.relation or not self.target:
            raise ValueError("source, relation, and target must be non-empty")
        if not math.isfinite(self.confidence) or not (0.0 < self.confidence <= 1.0):
            raise ValueError("confidence must be finite and in (0, 1]")


class SymbolicGraphReasoner:
    """Deterministic forward chaining, bidirectional BFS abduction & Jaccard analogy."""

    def __init__(self, edges: Sequence[RelationEdge] = ()) -> None:
        self._out: dict[str, list[RelationEdge]] = {}
        self._in: dict[str, list[RelationEdge]] = {}
        self._nodes: set[str] = set()
        for e in edges:
            self.add_edge(e)

    def add_edge(self, edge: RelationEdge) -> None:
        self._nodes.add(edge.source)
        self._nodes.add(edge.target)
        self._out.setdefault(edge.source, []).append(edge)
        self._in.setdefault(edge.target, []).append(edge)

    @property
    def nodes(self) -> tuple[str, ...]:
        return tuple(sorted(self._nodes))

    def forward_chain(
        self,
        start: str,
        *,
        max_hops: int = 3,
        min_confidence: float = 0.1,
    ) -> dict[str, float]:
        """Compute maximum multiplicative path confidence reachable from ``start``."""
        if max_hops < 1:
            raise ValueError("max_hops must be >= 1")
        if not math.isfinite(min_confidence) or not (0.0 < min_confidence <= 1.0):
            raise ValueError("min_confidence must be finite and in (0, 1]")
        if start not in self._nodes:
            return {}

        best: dict[str, float] = {}
        queue: deque[tuple[str, float, int]] = deque([(start, 1.0, 0)])
        while queue:
            cur, conf, hops = queue.popleft()
            if hops >= max_hops:
                continue
            for edge in self._out.get(cur, []):
                nxt_conf = conf * edge.confidence
                if nxt_conf < min_confidence:
                    continue
                if nxt_conf > best.get(edge.target, 0.0):
                    best[edge.target] = float(nxt_conf)
                    queue.append((edge.target, nxt_conf, hops + 1))
        return best

    def abduce(
        self,
        source: str,
        target: str,
        *,
        max_depth: int = 6,
    ) -> list[RelationEdge] | None:
        """Find shortest directed explanatory chain ``source ->* target`` via bidirectional BFS."""
        if max_depth < 1:
            raise ValueError("max_depth must be >= 1")
        if source not in self._nodes or target not in self._nodes:
            return None
        if source == target:
            return []

        fwd_parent: dict[str, tuple[str, RelationEdge] | None] = {source: None}
        bwd_child: dict[str, tuple[str, RelationEdge] | None] = {target: None}
        fwd_frontier: list[str] = [source]
        bwd_frontier: list[str] = [target]

        depth = 0
        meet: str | None = None
        while fwd_frontier and bwd_frontier and depth < max_depth:
            # Expand smaller frontier by one level
            if len(fwd_frontier) <= len(bwd_frontier):
                next_fwd: list[str] = []
                for u in fwd_frontier:
                    for edge in self._out.get(u, []):
                        v = edge.target
                        if v not in fwd_parent:
                            fwd_parent[v] = (u, edge)
                            if v in bwd_child:
                                meet = v
                                break
                            next_fwd.append(v)
                    if meet is not None:
                        break
                fwd_frontier = next_fwd
            else:
                next_bwd: list[str] = []
                for v in bwd_frontier:
                    for edge in self._in.get(v, []):
                        u = edge.source
                        if u not in bwd_child:
                            bwd_child[u] = (v, edge)
                            if u in fwd_parent:
                                meet = u
                                break
                            next_bwd.append(u)
                    if meet is not None:
                        break
                bwd_frontier = next_bwd
            depth += 1
            if meet is not None:
                break

        if meet is None:
            return None

        # Reconstruct path source -> meet -> target
        left_edges: list[RelationEdge] = []
        cur = meet
        while fwd_parent[cur] is not None:
            prev_pair = fwd_parent[cur]
            assert prev_pair is not None
            prev_node, edge = prev_pair
            left_edges.append(edge)
            cur = prev_node
        left_edges.reverse()

        right_edges: list[RelationEdge] = []
        cur = meet
        while bwd_child[cur] is not None:
            nxt_pair = bwd_child[cur]
            assert nxt_pair is not None
            nxt_node, edge = nxt_pair
            right_edges.append(edge)
            cur = nxt_node

        full_path = [*left_edges, *right_edges]
        return full_path if len(full_path) <= max_depth else None

    def _relational_signature(self, node: str) -> set[str]:
        """Extract 1-hop and 2-hop typed relational role signatures around ``node``."""
        sig: set[str] = set()
        for e1 in self._out.get(node, []):
            sig.add(f"out1:{e1.relation}")
            for e2 in self._out.get(e1.target, []):
                sig.add(f"out2:{e1.relation}->{e2.relation}")
        for e1 in self._in.get(node, []):
            sig.add(f"in1:{e1.relation}")
            for e2 in self._in.get(e1.source, []):
                sig.add(f"in2:{e2.relation}->{e1.relation}")
        return sig

    def find_analogies(self, node: str, *, top_k: int = 3) -> list[tuple[str, float]]:
        """Rank structurally analogous nodes by 2-hop relational-signature Jaccard similarity."""
        if top_k < 1 or node not in self._nodes:
            return []
        target_sig = self._relational_signature(node)
        if not target_sig:
            return []

        scored: list[tuple[str, float]] = []
        for cand in sorted(self._nodes):
            if cand == node:
                continue
            cand_sig = self._relational_signature(cand)
            union = target_sig | cand_sig
            if not union:
                continue
            jacc = len(target_sig & cand_sig) / len(union)
            if jacc > 0.0:
                scored.append((cand, float(jacc)))

        scored.sort(key=lambda item: (-item[1], item[0]))
        return scored[:top_k]


@dataclass(frozen=True)
class TDMScheduleTick:
    """Outcome of one time-division multiplexed scheduler tick."""

    tick: int
    mode: TDMOperatingMode
    dominant_phase: TDMPhase
    phase_multipliers: dict[TDMPhase, float]
    idle_streak: int


class TDMMaintenanceScheduler:
    """Deterministic time-division phase rotator & idle-triggered maintenance switcher."""

    def __init__(
        self,
        *,
        idle_ticks_threshold: int = 3,
        phases: Sequence[TDMPhase] = _DEFAULT_PHASES,
    ) -> None:
        if idle_ticks_threshold < 1:
            raise ValueError("idle_ticks_threshold must be >= 1")
        if not phases:
            raise ValueError("phases must be non-empty")
        self.idle_ticks_threshold = idle_ticks_threshold
        self.phases: tuple[TDMPhase, ...] = tuple(phases)
        self._tick = 0
        self._idle_streak = 0

    def step(self, *, has_stimulus: bool) -> TDMScheduleTick:
        if has_stimulus:
            self._idle_streak = 0
        else:
            self._idle_streak += 1

        mode: TDMOperatingMode = (
            "maintenance" if self._idle_streak >= self.idle_ticks_threshold else "active"
        )
        dominant: TDMPhase = (
            "consolidate" if mode == "maintenance" else self.phases[self._tick % len(self.phases)]
        )
        multipliers: dict[TDMPhase, float] = {
            p: (1.5 if p == dominant else (0.4 if mode == "maintenance" else 0.8))
            for p in self.phases
        }
        cur_tick = self._tick
        self._tick += 1
        return TDMScheduleTick(
            tick=cur_tick,
            mode=mode,
            dominant_phase=dominant,
            phase_multipliers=multipliers,
            idle_streak=self._idle_streak,
        )
