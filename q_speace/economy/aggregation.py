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
