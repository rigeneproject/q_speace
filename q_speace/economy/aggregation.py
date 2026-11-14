"""KL-barycentre aggregation for the q_speace_economy (T6.3).

Implements :func:`aggregate`, the iterative Bregman projection
algorithm of Ben-Tal, Margalit & Nemirovski (2001) for finding the
barycentre of ``N`` probability distributions under the KL-divergence
Bregman distance.

The barycentre ``p*`` minimises

    Σ_i w_i KL(p || p_i)

subject to ``p`` being a valid probability vector. The iteration is:

    p^{(k+1)} ∝ exp(Σ_i w_i log p_i^{(k)})

with projection onto the simplex after each step.

This is the multi-domain aggregation primitive referenced in
``docs/q_speace_economy.md`` §4.7. The function is intentionally
**numpy-only** — no scipy — to respect the AGENTS.md invariant and to
keep the package importable on the Windows control process.

BCEL: the aggregation is *functional*: it produces a deterministic
weighted mean of distributions. The output is not a "consensus belief"
of any conscious mind — it is the unique Bregman projection of a set of
probability vectors onto the simplex.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

_EPS = 1e-15


def _validate_distribution(p: np.ndarray, name: str) -> np.ndarray:
    """Validate ``p`` is a 1-D probability vector and return a float copy."""
    if p.ndim != 1:
        raise ValueError(f"{name} must be 1-D (got shape {p.shape})")
    if np.any(p < 0.0):
        raise ValueError(f"{name} has negative entries")
    s = float(np.sum(p))
    if s <= 0.0:
        raise ValueError(f"{name} sums to zero or negative ({s})")
    out: np.ndarray = p.astype(np.float64) / s
    return out


def kl(p: np.ndarray, q: np.ndarray) -> float:
    """KL divergence D(p || q) in nats, both 1-D probability vectors."""
    p = _validate_distribution(p, "p")
    q = _validate_distribution(q, "q")
    mask = p > _EPS
    return float(np.sum(p[mask] * np.log(p[mask] / np.maximum(q[mask], _EPS))))


def aggregate(
    distributions: Sequence[np.ndarray],
    weights: Sequence[float] | None = None,
    *,
    max_iter: int = 100,
    tol: float = 1e-8,
) -> np.ndarray:
    """Iterative Bregman projection for the KL-barycentre.

    Parameters
    ----------
    distributions : sequence of 1-D ``np.ndarray``
        Probability vectors. All must share the same length ``d``.
    weights : sequence of float, optional
        Non-negative weights, one per distribution. If ``None``, uniform
        weights are used. Weights are normalised to sum to 1.
    max_iter : int
        Maximum number of iterations (default 100).
    tol : float
        Convergence threshold on the L1 change in ``p`` between iterations
        (default 1e-8).

    Returns
    -------
    np.ndarray
        The barycentre probability vector of shape ``(d,)``.

    Raises
    ------
    ValueError
        If fewer than 2 distributions are given, if their dimensions
        disagree, or if weights are negative.
    """
    dists = list(distributions)
    if len(dists) < 2:
        raise ValueError(f"need at least 2 distributions, got {len(dists)}")
    cleaned = [_validate_distribution(d, f"distributions[{i}]") for i, d in enumerate(dists)]
    d = cleaned[0].shape[0]
    for i, p in enumerate(cleaned):
        if p.shape[0] != d:
            raise ValueError(f"distributions[{i}] has shape {p.shape[0]}, expected {d}")
    if weights is None:
        w = np.full(len(cleaned), 1.0 / len(cleaned), dtype=np.float64)
    else:
        w = np.asarray(list(weights), dtype=np.float64)
        if w.shape != (len(cleaned),):
            raise ValueError(f"weights must have {len(cleaned)} entries")
        if np.any(w < 0.0):
            raise ValueError("weights must be non-negative")
        s = float(np.sum(w))
        if s <= 0.0:
            raise ValueError("weights must not all be zero")
        w = w / s
    if max_iter < 1:
        raise ValueError("max_iter must be >= 1")
    if tol <= 0.0:
        raise ValueError("tol must be > 0")

    p = np.full(d, 1.0 / d, dtype=np.float64)  # start at uniform barycentre
    logs = [np.log(np.maximum(p_i, _EPS)) for p_i in cleaned]
    for _ in range(max_iter):
        p_next = np.exp(np.einsum("i,ij->j", w, np.stack(logs, axis=0)))
        s = float(np.sum(p_next))
        # Numerical underflow restarts from a uniform distribution.
        p_next = np.full(d, 1.0 / d, dtype=np.float64) if s <= 0.0 else p_next / s
        diff = float(np.sum(np.abs(p_next - p)))
        p = p_next
        if diff < tol:
            break
    return p


def lossless_check(
    barycentre: np.ndarray,
    distributions: Sequence[np.ndarray],
    weights: Sequence[float] | None = None,
    tol: float = 1e-6,
) -> bool:
    """Return True iff the barycentre is the Bregman projection minimum.

    A Bregman projection always satisfies
    ``Σ_i w_i KL(p_i || p*) ≤ Σ_i w_i KL(p_i || q)`` for any other valid
    probability vector ``q`` (in particular ``q = uniform``). The check
    returns True iff the barycentre is not worse than uniform by more than
    ``tol`` — a numerical tolerance for Bregman projection noise.
    """
    dists = [_validate_distribution(d, "d") for d in distributions]
    if weights is None:
        w = np.full(len(dists), 1.0 / len(dists), dtype=np.float64)
    else:
        w = np.asarray(list(weights), dtype=np.float64)
        if float(np.sum(w)) <= 0.0:
            return False
        w = w / float(np.sum(w))
    uniform = np.full_like(barycentre, 1.0 / barycentre.shape[0])
    bary_kl = float(np.sum(w * np.array([kl(p, barycentre) for p in dists])))
    uni_kl = float(np.sum(w * np.array([kl(p, uniform) for p in dists])))
    return bary_kl <= uni_kl + tol


# ---------------------------------------------------------------------- #
# T218 (SCO-01/02/03): admissible reporting score, additive aggregation
# and cumulative-harm limits.
#
# Resolves review items L4, MAT-M2/M6 and GOV-G4. The score
#
#     U = sum_l alpha_l * b_l  -  sum_m beta_m * h_m
#
# has *monotonicity at fixed coordinates* and *no multiplicative
# cancellation* — it does not forbid trade-offs: an action may raise a
# harm and the total score simultaneously. Non-compensable harms remain
# constraints outside the scalar.
#
# BCEL: the score is a functional linear form with published, frozen
# coefficients. It is a reporting index, not a measure of value, wealth
# or ethics.
# ---------------------------------------------------------------------- #


@dataclass(frozen=True)
class ScorePolicy:
    """Frozen, versioned score coefficients (L4: policy version is part
    of every comparison — two different versions are never subtracted)."""

    alpha: tuple[float, ...]
    beta: tuple[float, ...]
    version: str

    def __post_init__(self) -> None:
        if any(a < 0.0 for a in self.alpha):
            raise ValueError("alpha coefficients must be non-negative")
        if any(b < 0.0 for b in self.beta):
            raise ValueError("beta coefficients must be non-negative")
        if not self.version:
            raise ValueError("policy version must be recorded")


def reporting_score(
    policy: ScorePolicy,
    benefits: np.ndarray,
    harms: np.ndarray,
) -> float:
    """Return ``U = Σ α_l b_l − Σ β_m h_m`` (additive, non-cancelling)."""
    b = np.asarray(benefits, dtype=np.float64)
    h = np.asarray(harms, dtype=np.float64)
    if b.shape != (len(policy.alpha),) or h.shape != (len(policy.beta),):
        raise ValueError("benefits/harms length must match the policy vectors")
    if np.any(b < 0.0) or np.any(b > 1.0):
        raise ValueError("benefits must be normalized in [0, 1]")
    if np.any(h < 0.0):
        raise ValueError("harms must be non-negative")
    return float(np.sum(policy.alpha * b) - np.sum(policy.beta * h))


def monotonicity_at_fixed_coordinates(
    policy: ScorePolicy,
    benefits: np.ndarray,
    harms: np.ndarray,
) -> bool:
    """SCO-01: at fixed coordinates, raising one harm never raises U.

    This tests the *algebraic* property only. A joint change (raising a
    harm AND a benefit) may legitimately raise the total — that is a
    trade-off, not a bug (M6).
    """
    base = reporting_score(policy, benefits, harms)
    for m in range(len(policy.beta)):
        h2 = np.array(harms, dtype=np.float64, copy=True)
        h2[m] += 0.01
        if reporting_score(policy, benefits, h2) > base + 1e-15:
            return False
    return True


def additive_score(
    densities: np.ndarray,
    measure: np.ndarray,
    policy: ScorePolicy,
) -> float:
    """SCO-02: integral of the density over an additive measure μ.

    ``densities`` holds benefit-minus-harm densities ``u(z)`` on the
    reference granularity; ``measure`` holds the μ-measure of each
    element. The cell score is ``Σ u(z) μ(z)`` — invariant under
    merging/splitting *by construction* because it is an integral, not
    a nonlinear normalisation of a local mean.
    """
    d = np.asarray(densities, dtype=np.float64)
    m = np.asarray(measure, dtype=np.float64)
    if d.shape != m.shape:
        raise ValueError("densities and measure must share shape")
    if np.any(m < 0.0):
        raise ValueError("measure entries must be non-negative")
    return float(np.sum(d * m))


def cumulative_harm_check(
    cumulative_harm: np.ndarray,
    cumulative_limits: np.ndarray,
) -> tuple[bool, str]:
    """SCO-03: per-group cumulative limits (GOV-G4).

    A sequence of individually-admissible actions that pushes a group's
    cumulative harm past its declared limit is blocked (or escalated)
    *independently of the scalar score*.

    Returns ``(ok, reason)`` with ``ok=False`` naming the first violated
    group index.
    """
    c = np.asarray(cumulative_harm, dtype=np.float64)
    lim = np.asarray(cumulative_limits, dtype=np.float64)
    if c.shape != lim.shape:
        raise ValueError("cumulative harm and limits must share shape")
    if np.any(lim < 0.0):
        raise ValueError("limits must be non-negative")
    violated = np.flatnonzero(c > lim)
    if violated.size > 0:
        return False, f"cumulative harm limit exceeded for group {int(violated[0])}"
    return True, "all group cumulative limits respected"
