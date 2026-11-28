"""Multistep-regression (MR) branching-ratio estimator (T264).

The T248 controller estimates sigma as the mean ratio of consecutive spike counts
``E[(S_t + 1) / (S_{t-1} + 1)]``. T263 showed that estimator is ~1 for constant,
decaying, slowly growing and Poisson-noise sequences, so a band test on it carries
little information.

The MR estimator (Wilting & Priesemann, Nat. Commun. 2018) instead regresses
``A_{t+k}`` on ``A_t`` for lags ``k = 1..K``. For a driven branching process the
slopes follow ``r_k = b * m**k``, so ``m = exp(slope of log r_k vs k)``. It is
robust to subsampling and to the external drive and separates

- independent noise (no propagation)            -> m ~ 0
- sub-critical propagation                     -> 0 < m < 1
- near-critical propagation                    -> m ~ 1
- super-critical growth                        -> m > 1

BCEL: avalanche / epilepsy narratives are accidental; only the linear-regression
estimator over an integer activity series is kept.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class MREstimate:
    """Result of one MR estimate."""

    m: float  # branching parameter; nan when undefined
    slopes: tuple[float, ...]  # r_k for k = 1..K
    defined: bool  # False for zero-variance or too-short input
    reason: str


def mr_branching_ratio(activity: np.ndarray | list[int], k_max: int = 5) -> MREstimate:
    """Estimate the branching parameter ``m`` of an activity series."""
    a = np.asarray(activity, dtype=float)
    if a.ndim != 1:
        raise ValueError("activity must be 1-D")
    if k_max < 1:
        raise ValueError("k_max must be >= 1")
    if a.size < k_max + 4:
        return MREstimate(math.nan, (), False, "too_short")
    if float(np.var(a)) <= 1e-12:
        return MREstimate(math.nan, (), False, "zero_variance")

    slopes: list[float] = []
    for k in range(1, k_max + 1):
        x, y = a[:-k], a[k:]
        vx = float(np.var(x))
        if vx <= 1e-12:
            return MREstimate(math.nan, tuple(slopes), False, "zero_variance_lag")
        slopes.append(float(np.cov(x, y, bias=True)[0, 1] / vx))

    r = np.asarray(slopes)
    # Lag-1 slope indistinguishable from sampling noise (~1/sqrt(N)): memoryless.
    if r[0] <= max(0.05, 2.5 / math.sqrt(a.size)):
        return MREstimate(0.0, tuple(slopes), True, "no_propagation")
    # Nonlinear least squares r_k = b * m**k (as in the original MR estimator):
    # b has a closed form for fixed m; m is found on a fine grid.
    ks = np.arange(1, k_max + 1, dtype=float)
    best_m, best_err = float(r[0]), math.inf
    for m in np.linspace(0.01, 1.6, 1591):
        basis = m**ks
        b = float(basis @ r / (basis @ basis))
        err = float(np.sum((r - b * basis) ** 2))
        if err < best_err:
            best_m, best_err = float(m), err
    return MREstimate(best_m, tuple(slopes), True, "ok")


def driven_branching_process(
    m: float, n: int = 2000, drive: float = 2.0, seed: int = 0, cap: int = 10_000
) -> list[int]:
    """Poisson-driven Galton–Watson process ``A_{t+1} ~ Poisson(m * A_t + drive)``."""
    rng = np.random.default_rng(seed)
    a = [int(drive)]
    for _ in range(n - 1):
        a.append(int(min(cap, rng.poisson(m * a[-1] + drive))))
    return a
