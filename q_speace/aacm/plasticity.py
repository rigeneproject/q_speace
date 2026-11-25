"""Entropy-bounded UCB1 stream gating & conservative proposal-only graph plasticity (T249-02).

Synthesized via BCEL from ``speaceorganismocibernetico`` M5
(``AttentionGating``, ``EdgePruner``, ``EdgeGrower``):
- Thalamic spotlight and Hebbian synaptogenesis narratives are *accidental*.
- Multi-stream UCB1 allocation with an explicit Shannon entropy floor
  ``H(w) >= H_min``, conservative edge weight decay/pruning, and immutable
  ``EdgeGrowthProposal`` records (zero unapproved topology insertion) survive.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

GatingPolicy = Literal["uniform", "salience", "ucb1"]


def shannon_entropy_bits(weights: Sequence[float]) -> float:
    """Compute Shannon entropy -sum w_i log2(w_i) in bits for a probability vector."""
    h = 0.0
    for w in weights:
        if w > 1e-12:
            h -= float(w) * math.log2(float(w))
    return max(0.0, h)


class EntropyBoundedUCB1Gating:
    """Multi-stream attention allocator with UCB1 bandit & Shannon diversity floor."""

    def __init__(
        self,
        streams: Sequence[str],
        *,
        policy: GatingPolicy = "ucb1",
        exploration_c: float = 1.0,
        min_weight: float = 0.05,
        min_entropy_ratio: float = 0.65,
    ) -> None:
        unique_streams = list(dict.fromkeys(streams))
        if not unique_streams or any(not s for s in unique_streams):
            raise ValueError("streams must be non-empty strings")
        if policy not in ("uniform", "salience", "ucb1"):
            raise ValueError(f"unknown gating policy: {policy!r}")
        if not math.isfinite(exploration_c) or exploration_c < 0.0:
            raise ValueError("exploration_c must be finite and >= 0")
        max_possible_floor = 1.0 / len(unique_streams)
        if not math.isfinite(min_weight) or not (0.0 <= min_weight <= max_possible_floor + 1e-12):
            raise ValueError(f"min_weight must be in [0, {max_possible_floor:.4f}]")
        if not math.isfinite(min_entropy_ratio) or not (0.0 <= min_entropy_ratio <= 1.0):
            raise ValueError("min_entropy_ratio must be finite and in [0, 1]")

        self._streams: tuple[str, ...] = tuple(unique_streams)
        self.policy: GatingPolicy = policy
        self.exploration_c = float(exploration_c)
        self.min_weight = min(float(min_weight), max_possible_floor)
        self.min_entropy_ratio = float(min_entropy_ratio)
        self._counts: dict[str, int] = dict.fromkeys(self._streams, 0)
        self._mean_reward: dict[str, float] = dict.fromkeys(self._streams, 0.5)
        self._total_pulls: int = 0

    @property
    def min_entropy_bits(self) -> float:
        if len(self._streams) <= 1:
            return 0.0
        return self.min_entropy_ratio * math.log2(len(self._streams))

    def record_reward(self, stream: str, reward: float) -> None:
        """Update empirical reward statistics for ``stream`` in [0, 1]."""
        if stream not in self._counts:
            raise KeyError(f"unknown stream: {stream!r}")
        if not math.isfinite(reward) or not (0.0 <= reward <= 1.0):
            raise ValueError(f"reward must be finite and in [0, 1] (got {reward!r})")
        n = self._counts[stream] + 1
        self._counts[stream] = n
        self._total_pulls += 1
        prev = self._mean_reward[stream]
        self._mean_reward[stream] = prev + (float(reward) - prev) / n

    def allocate(self, saliences: Mapping[str, float] | None = None) -> dict[str, float]:
        """Return normalized stream weights satisfying ``w_i >= min_weight`` and ``H(w) >= H_min``."""
        n = len(self._streams)
        if n == 1:
            return {self._streams[0]: 1.0}

        uniform_w = 1.0 / n
        if self.policy == "uniform":
            return dict.fromkeys(self._streams, uniform_w)

        sal_map = dict(saliences) if saliences is not None else {}
        for k, v in sal_map.items():
            if k not in self._counts:
                raise KeyError(f"unknown stream in saliences: {k!r}")
            if not math.isfinite(v) or v < 0.0:
                raise ValueError(f"salience[{k!r}] must be finite and >= 0")

        scores: list[float] = []
        total = max(self._total_pulls, n)
        for s in self._streams:
            sal = float(sal_map.get(s, 0.5))
            if self.policy == "salience":
                scores.append(max(1e-6, sal))
            else:
                pulls = self._counts[s]
                bonus = self.exploration_c * math.sqrt(math.log(total + 1.0) / (pulls + 1.0))
                scores.append(max(1e-6, 0.5 * self._mean_reward[s] + 0.5 * sal + bonus))

        # Softmax-like normalization via temperature-1 positive scores, then floor projection
        score_sum = sum(scores)
        raw = [sc / score_sum for sc in scores]
        floored = self._apply_floor(raw)

        # Enforce Shannon entropy floor by convex blending toward uniform via bisection
        target_h = self.min_entropy_bits
        if shannon_entropy_bits(floored) < target_h - 1e-9:
            lo, hi = 0.0, 1.0
            for _ in range(24):
                mid = 0.5 * (lo + hi)
                cand = [(1.0 - mid) * w + mid * uniform_w for w in floored]
                if shannon_entropy_bits(cand) >= target_h:
                    hi = mid
                else:
                    lo = mid
            floored = [(1.0 - hi) * w + hi * uniform_w for w in floored]

        norm = sum(floored)
        return {s: float(floored[i] / norm) for i, s in enumerate(self._streams)}

    def _apply_floor(self, weights: list[float]) -> list[float]:
        n = len(weights)
        if self.min_weight <= 0.0:
            return weights
        free_mass = max(0.0, 1.0 - n * self.min_weight)
        excess = [max(0.0, w - self.min_weight) for w in weights]
        ex_sum = sum(excess)
        if ex_sum <= 1e-12:
            return [1.0 / n] * n
        return [self.min_weight + free_mass * (e / ex_sum) for e in excess]


@dataclass(frozen=True)
class EdgeGrowthProposal:
    """Immutable proposal for adding a new directed edge; never self-executed (T249-02)."""

    source: str
    target: str
    coactivation_score: float
    proposed_weight: float
    risk: str = "HIGH"
    requires_external_approval: bool = True


class GraphEdgePruner:
    """Conservative edge weight decay & bounded pruning preserving incident connectivity."""

    def __init__(
        self,
        *,
        decay_rate: float = 0.05,
        prune_threshold: float = 0.10,
        min_age_ticks: int = 3,
        max_prune_per_cycle: int = 1,
    ) -> None:
        if not math.isfinite(decay_rate) or not (0.0 <= decay_rate < 1.0):
            raise ValueError("decay_rate must be finite and in [0, 1)")
        if not math.isfinite(prune_threshold) or not (0.0 <= prune_threshold < 1.0):
            raise ValueError("prune_threshold must be finite and in [0, 1)")
        if min_age_ticks < 0 or max_prune_per_cycle < 0:
            raise ValueError("min_age_ticks and max_prune_per_cycle must be >= 0")
        self.decay_rate = float(decay_rate)
        self.prune_threshold = float(prune_threshold)
        self.min_age_ticks = min_age_ticks
        self.max_prune_per_cycle = max_prune_per_cycle

    def step(
        self,
        edges: Sequence[tuple[str, str, float]],
        edge_ages: Mapping[tuple[str, str], int],
        active_pairs: set[tuple[str, str]] | None = None,
    ) -> tuple[list[tuple[str, str, float]], list[tuple[str, str]]]:
        """Decay inactive edges and prune at most ``max_prune_per_cycle`` weak mature edges."""
        active = active_pairs or set()
        updated: list[tuple[str, str, float]] = []
        degree: dict[str, int] = {}

        for u, v, w in edges:
            if not math.isfinite(w) or w < 0.0:
                raise ValueError(f"edge weight ({u}->{v}) must be finite and >= 0")
            new_w = min(1.0, w * 1.05) if (u, v) in active else w * (1.0 - self.decay_rate)
            updated.append((u, v, float(new_w)))
            degree[u] = degree.get(u, 0) + 1
            degree[v] = degree.get(v, 0) + 1

        # Identify weak mature candidates sorted weakest-first
        candidates = sorted(
            [
                (w, idx)
                for idx, (u, v, w) in enumerate(updated)
                if w < self.prune_threshold and edge_ages.get((u, v), 0) >= self.min_age_ticks
            ],
            key=lambda item: item[0],
        )

        pruned_indices: set[int] = set()
        pruned_pairs: list[tuple[str, str]] = []
        for _w, idx in candidates:
            if len(pruned_indices) >= self.max_prune_per_cycle:
                break
            u, v, _ = updated[idx]
            # Never isolate either endpoint if it would drop degree below 1
            if degree[u] <= 1 or degree[v] <= 1:
                continue
            pruned_indices.add(idx)
            pruned_pairs.append((u, v))
            degree[u] -= 1
            degree[v] -= 1

        kept = [edge for idx, edge in enumerate(updated) if idx not in pruned_indices]
        return kept, pruned_pairs


class ProposalOnlyEdgeGrower:
    """Tracks node co-activations and emits proposal-only ``EdgeGrowthProposal`` records."""

    def __init__(
        self,
        *,
        ema_alpha: float = 0.25,
        proposal_threshold: float = 0.70,
        min_observations: int = 3,
    ) -> None:
        if not math.isfinite(ema_alpha) or not (0.0 < ema_alpha <= 1.0):
            raise ValueError("ema_alpha must be finite and in (0, 1]")
        if not math.isfinite(proposal_threshold) or not (0.0 < proposal_threshold <= 1.0):
            raise ValueError("proposal_threshold must be finite and in (0, 1]")
        if min_observations < 1:
            raise ValueError("min_observations must be >= 1")
        self.ema_alpha = float(ema_alpha)
        self.proposal_threshold = float(proposal_threshold)
        self.min_observations = min_observations
        self._coact: dict[tuple[str, str], float] = {}
        self._obs_count: dict[tuple[str, str], int] = {}

    def observe_and_propose(
        self,
        activations: Mapping[str, float],
        existing_edges: set[tuple[str, str]],
    ) -> list[EdgeGrowthProposal]:
        """Update pairwise co-activation EMAs and emit proposals without mutating ``existing_edges``."""
        nodes = sorted(activations.keys())
        for n in nodes:
            val = activations[n]
            if not math.isfinite(val) or not (0.0 <= val <= 1.0):
                raise ValueError(f"activation[{n!r}] must be finite and in [0, 1]")

        proposals: list[EdgeGrowthProposal] = []
        for i, src in enumerate(nodes):
            for dst in nodes[i + 1 :]:
                pair = (src, dst)
                if pair in existing_edges or (dst, src) in existing_edges:
                    continue
                prod = float(activations[src]) * float(activations[dst])
                prev = self._coact.get(pair, prod)
                score = (1.0 - self.ema_alpha) * prev + self.ema_alpha * prod
                self._coact[pair] = score
                count = self._obs_count.get(pair, 0) + 1
                self._obs_count[pair] = count
                if count >= self.min_observations and score >= self.proposal_threshold:
                    proposals.append(
                        EdgeGrowthProposal(
                            source=src,
                            target=dst,
                            coactivation_score=float(score),
                            proposed_weight=round(min(0.5, 0.5 * score), 4),
                        )
                    )
        proposals.sort(key=lambda p: (-p.coactivation_score, p.source, p.target))
        return proposals
