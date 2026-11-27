"""Small-System Minimum Information Partition Coupling Index & CV Strategy Selector (T256-04).

Synthesized via BCEL from ``SPEACE PROTOTIPO CLAUDE`` (``phi_calculator.py``, ``metacognitive.py``):
- All ``consciousness_index`` labels and subjective experience claims are *accidental*
  and strictly prohibited under ``AGENTS.md`` §2.
- Pure-numpy Gaussian mutual-information evaluation across all ``2^(n-1) - 1`` bipartitions
  for ``2 <= n <= 10`` (closing ``T25`` strictly as an information-theoretic network
  coupling diagnostic, fixing the prototype's ``np.trace`` zero-diagonal bug, and
  requiring zero ``scikit-learn`` dependency) plus ``exp(-CV)`` variance-adaptive
  strategy switching survive as deterministic mathematical tools.
"""

from __future__ import annotations

import itertools
import math
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class MIPResult:
    """Outcome of Minimum Information Partition network-coupling analysis (non-consciousness)."""

    mip_coupling_index: float
    best_partition_a: tuple[int, ...]
    best_partition_b: tuple[int, ...]
    evaluated_partitions: int
    mode: str  # "exact_mip" | "bisection_proxy"


def _gaussian_mutual_information(
    cov: np.ndarray,
    idx_a: Sequence[int],
    idx_b: Sequence[int],
    reg: float = 1e-6,
) -> float:
    """Compute regularized Gaussian mutual information I(X_A; X_B) >= 0 in nats."""
    n = cov.shape[0]
    cov_reg = cov + reg * np.eye(n, dtype=np.float64)
    sub_a = cov_reg[np.ix_(idx_a, idx_a)]
    sub_b = cov_reg[np.ix_(idx_b, idx_b)]

    sign_ab, logdet_ab = np.linalg.slogdet(cov_reg)
    sign_a, logdet_a = np.linalg.slogdet(sub_a)
    sign_b, logdet_b = np.linalg.slogdet(sub_b)
    if sign_ab <= 0 or sign_a <= 0 or sign_b <= 0:
        return 0.0
    mi = 0.5 * float(logdet_a + logdet_b - logdet_ab)
    return max(0.0, mi)


def _cross_cut_weight(
    connectivity: np.ndarray | None,
    idx_a: Sequence[int],
    idx_b: Sequence[int],
) -> float:
    """Mean non-negative coupling strength across the cut (A, B)."""
    if connectivity is None:
        return 1.0
    cross_ab = np.abs(connectivity[np.ix_(idx_a, idx_b)])
    cross_ba = np.abs(connectivity[np.ix_(idx_b, idx_a)])
    mean_cut = 0.5 * float(np.mean(cross_ab) + np.mean(cross_ba))
    return mean_cut


def compute_mip_integration(
    trajectories: np.ndarray,
    connectivity: np.ndarray | None = None,
    *,
    max_exact_nodes: int = 10,
    reg: float = 1e-6,
) -> MIPResult:
    """Compute the Minimum Information Partition coupling index over ``T x n`` state samples.

    Strictly an information-theoretic network integration diagnostic (``AGENTS.md`` §2:
    zero claim of consciousness). For ``2 <= n <= max_exact_nodes``, searches all
    ``2^(n-1) - 1`` non-trivial bipartitions normalized by ``min(|A|, |B|)``. For
    ``n > max_exact_nodes``, evaluates balanced bisection cuts in ``O(n^3)``.
    """
    x = np.asarray(trajectories, dtype=np.float64)
    if x.ndim != 2:
        raise ValueError("trajectories must be a 2D array of shape (n_samples, n_nodes)")
    n_samples, n_nodes = x.shape
    if n_nodes < 2:
        raise ValueError("n_nodes must be >= 2")
    if n_samples < 3:
        raise ValueError("n_samples must be >= 3")
    if not np.all(np.isfinite(x)):
        raise ValueError("trajectories must contain only finite values")
    if not math.isfinite(reg) or reg <= 0.0:
        raise ValueError("reg must be finite and > 0")

    conn_arr: np.ndarray | None = None
    if connectivity is not None:
        conn_arr = np.asarray(connectivity, dtype=np.float64)
        if conn_arr.shape != (n_nodes, n_nodes) or not np.all(np.isfinite(conn_arr)):
            raise ValueError("connectivity must be a finite (n_nodes, n_nodes) matrix")

    # Center variables and compute sample covariance (n_nodes x n_nodes)
    centered = x - np.mean(x, axis=0, keepdims=True)
    cov = (centered.T @ centered) / max(1, n_samples - 1)

    all_indices = tuple(range(n_nodes))
    bipartitions: list[tuple[tuple[int, ...], tuple[int, ...]]] = []

    if n_nodes <= max_exact_nodes:
        mode = "exact_mip"
        for r in range(1, n_nodes // 2 + 1):
            for comb in itertools.combinations(all_indices, r):
                # Avoid symmetric duplicates when n_nodes is even and r == n_nodes // 2
                if n_nodes % 2 == 0 and r == n_nodes // 2 and 0 not in comb:
                    continue
                comp = tuple(i for i in all_indices if i not in comb)
                bipartitions.append((comb, comp))
    else:
        mode = "bisection_proxy"
        mid = n_nodes // 2
        bipartitions.append((all_indices[:mid], all_indices[mid:]))
        evens = tuple(i for i in all_indices if i % 2 == 0)
        odds = tuple(i for i in all_indices if i % 2 == 1)
        bipartitions.append((evens, odds))

    best_score = float("inf")
    best_a: tuple[int, ...] = bipartitions[0][0]
    best_b: tuple[int, ...] = bipartitions[0][1]

    for part_a, part_b in bipartitions:
        mi = _gaussian_mutual_information(cov, part_a, part_b, reg=reg)
        norm_factor = float(min(len(part_a), len(part_b)))
        cut_w = _cross_cut_weight(conn_arr, part_a, part_b)
        score = (mi / norm_factor) * cut_w
        if score < best_score:
            best_score = score
            best_a = part_a
            best_b = part_b

    return MIPResult(
        mip_coupling_index=float(max(0.0, best_score)),
        best_partition_a=best_a,
        best_partition_b=best_b,
        evaluated_partitions=len(bipartitions),
        mode=mode,
    )


class CVStrategySelector:
    """Coefficient-of-variation ``exp(-CV)`` confidence monitor & strategy selector (T256-04)."""

    DEFAULT_STRATEGIES: tuple[str, ...] = (
        "exploration",
        "exploitation",
        "recovery",
        "generalization",
    )

    def __init__(
        self,
        *,
        strategies: Sequence[str] = DEFAULT_STRATEGIES,
        window_size: int = 20,
        confidence_threshold: float = 0.65,
    ) -> None:
        if not strategies:
            raise ValueError("strategies must be non-empty")
        if window_size < 3:
            raise ValueError("window_size must be >= 3")
        if not math.isfinite(confidence_threshold) or not (0.0 < confidence_threshold <= 1.0):
            raise ValueError("confidence_threshold must be in (0, 1]")

        self.strategies: tuple[str, ...] = tuple(strategies)
        self.window_size = int(window_size)
        self.confidence_threshold = float(confidence_threshold)
        self.current_strategy: str = self.strategies[0]
        self._perf_history: deque[float] = deque(maxlen=window_size)
        self._strategy_scores: dict[str, deque[float]] = {
            s: deque(maxlen=window_size) for s in self.strategies
        }
        self.confidence: float = 1.0

    def observe(self, reward: float, *, strategy: str | None = None) -> str:
        """Record ``reward`` for ``strategy`` (defaults to ``current_strategy``) and select next."""
        if not math.isfinite(reward):
            raise ValueError("reward must be finite")
        used = strategy or self.current_strategy
        if used not in self._strategy_scores:
            raise KeyError(f"Unknown strategy: {used!r}")

        self._perf_history.append(float(reward))
        self._strategy_scores[used].append(float(reward))

        if len(self._perf_history) >= 3:
            arr = np.asarray(self._perf_history, dtype=np.float64)
            mean_val = float(np.mean(arr))
            std_val = float(np.std(arr))
            if abs(mean_val) > 1e-8:
                cv = std_val / abs(mean_val)
                self.confidence = float(np.clip(math.exp(-cv), 0.0, 1.0))
            else:
                self.confidence = 0.50

        recent = list(self._perf_history)[-5:]
        declining = len(recent) >= 4 and all(
            recent[i] > recent[i + 1] for i in range(len(recent) - 1)
        )

        if declining or self.confidence < self.confidence_threshold:
            untried = [s for s, hist in self._strategy_scores.items() if len(hist) == 0]
            if untried:
                self.current_strategy = untried[0]
            else:
                self.current_strategy = max(
                    self.strategies,
                    key=lambda s: float(np.mean(self._strategy_scores[s])),
                )

        return self.current_strategy
