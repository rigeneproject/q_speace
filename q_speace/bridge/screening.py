"""Bridge-v0 two-stage parameter screening (T218-T02, BR-02).

Resolves review items L1, MAT-M1 and SYS-C6: the projection in
§2.2 of Paradigm_6_0_Revised is now performed on the *intersection*

    F_i^k = P_i ∩ { p : ||p − p_i^k||_{S_i} ≤ Δ_i }

so a candidate outside the update budget can never emerge from
projection. Declared outcomes cover: empty admissible set, policy
migration when the last approved parameter leaves a new policy set,
and a deterministic lexicographic tie-break for future non-convex
permitted sets.

In v0 the permitted set ``P_i`` is an axis-aligned box, hence convex
and the projection is unique. The deterministic fallback for a
non-unique projection (lexicographically smallest candidate) is
provided as :func:`lexicographic_select`.

All operations are numpy-only and deterministic.

BCEL: set intersection, Euclidean projection and a lexicographic
tie-break are *functional* mathematical rules. Nothing here is
"homeostatic" in a biological sense — it is convex geometry.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

import numpy as np


class ScreeningOutcome(StrEnum):
    ACCEPTED = "ACCEPTED"
    REJECTED_EMPTY_SET = "REJECTED_EMPTY_SET"
    REJECTED_MIGRATION = "REJECTED_MIGRATION"


@dataclass(frozen=True, eq=False)
class ScreeningResult:
    """Outcome of the two-stage screening (BR-02: reason always recorded)."""

    outcome: ScreeningOutcome
    candidate: np.ndarray | None
    reason: str


def _validate_bounds(p_set: np.ndarray, lower: np.ndarray, upper: np.ndarray) -> None:
    if p_set.ndim != 1:
        raise ValueError("p_set must be 1-D")
    if lower.shape != p_set.shape or upper.shape != p_set.shape:
        raise ValueError("lower/upper bounds must match p_set shape")
    if np.any(lower > upper):
        raise ValueError("lower bound exceeds upper bound")


def weighted_norm(v: np.ndarray, scale: np.ndarray) -> float:
    """Return ``||v||_S`` with diagonal scaling ``S = diag(scale)``."""
    if np.any(scale <= 0.0):
        raise ValueError("scale entries must be positive")
    return float(np.sqrt(np.sum((v / scale) ** 2)))


def lexicographic_select(candidates: list[np.ndarray]) -> np.ndarray:
    """Deterministic tie-break: lexicographically smallest candidate.

    Declared rule for permitted sets whose projection is non-unique
    (non-convex ``P_i``). Vectors are compared coordinate by coordinate
    in declaration order; the first decisive coordinate wins.
    """
    if not candidates:
        raise ValueError("candidates must be non-empty")
    best = candidates[0]
    best_key = tuple(float(x) for x in best)
    for c in candidates[1:]:
        key = tuple(float(x) for x in c)
        if key < best_key:
            best = c
            best_key = key
    return np.asarray(best, dtype=np.float64)  # type: ignore[no-any-return]


def select_projection_tie_break(
    candidates: list[np.ndarray],
    proposal: np.ndarray,
    scale: np.ndarray,
    *,
    epsilon_tie: float = 1e-12,
) -> np.ndarray:
    """Deterministic projection for non-convex permitted sets.

    When ``F_i^k`` is non-convex and has several global minima at (nearly)
    equal weighted distance ``||p − p̃||_S``, solver noise (~1e-15) can
    make one minimum appear strictly closer than another, silently
    overriding the declared lexicographic rule. This projector therefore:

    1. computes the weighted distance of every candidate;
    2. collects all candidates within the tolerance band
       ``ε_tie = 1e-12`` of the optimal distance;
    3. applies :func:`lexicographic_select` on that subset.

    Candidates strictly outside the band can never win, however
    lexicographically small they are.
    """
    if not candidates:
        raise ValueError("candidates must be non-empty")
    if epsilon_tie < 0.0:
        raise ValueError("epsilon_tie must be non-negative")
    if np.any(scale <= 0.0):
        raise ValueError("scale entries must be positive")
    distances = [weighted_norm(np.asarray(c) - proposal, scale) for c in candidates]
    d_min = min(distances)
    band = [c for c, d in zip(candidates, distances, strict=True) if d <= d_min + epsilon_tie]
    return lexicographic_select(band)


def project_onto_intersection(
    proposal: np.ndarray,
    p_last: np.ndarray,
    *,
    lower: np.ndarray,
    upper: np.ndarray,
    scale: np.ndarray,
    budget: float,
) -> np.ndarray:
    """Project ``proposal`` onto ``P ∩ B_Delta(p_last)``.

    Algorithm (declared, deterministic):

    1. clip the proposal into the box ``P`` and into the coordinate
       reach ``|p_j − p^k_j| ≤ Δ·s_j``;
    2. if the clipped point still exceeds the budget norm (possible in
       multiple dimensions: the reach box contains the ellipsoid),
       rescale the step along the segment ``[p^k, clipped]`` so that
       the weighted norm equals ``Δ`` exactly. The segment lies inside
       the box (both endpoints are in the box, convexity), so the
       result satisfies both constraints.

    Raises ``ValueError`` if the intersection is empty (use
    :func:`screen_candidate` to obtain a declared rejection instead).
    """
    _validate_bounds(proposal, lower, upper)
    if budget < 0.0:
        raise ValueError("budget must be non-negative")
    if np.any(scale <= 0.0):
        raise ValueError("scale entries must be positive")
    reach = budget * scale
    lo = np.maximum(lower, p_last - reach)
    hi = np.minimum(upper, p_last + reach)
    if np.any(lo > hi):
        raise ValueError("P ∩ B_Delta(p^k) is empty")
    clipped = np.clip(proposal, lo, hi)
    step = clipped - p_last
    norm = weighted_norm(step, scale)
    if norm > budget:
        t = budget / norm
        clipped = p_last + t * step
    return np.asarray(clipped, dtype=np.float64)


def screen_candidate(
    proposal: np.ndarray,
    p_last: np.ndarray,
    *,
    lower: np.ndarray,
    upper: np.ndarray,
    scale: np.ndarray,
    budget: float,
    new_lower: np.ndarray | None = None,
    new_upper: np.ndarray | None = None,
    tol: float = 1e-12,
) -> ScreeningResult:
    """Two-stage screening of a supervisory proposal (BR-02).

    Stage 1: check the admissible set ``F = P ∩ B_Delta(p_last)`` is
    non-empty. If a *new policy* is supplied (``new_lower/new_upper``)
    and the last approved parameter has left it, the result is
    ``REJECTED_MIGRATION`` — the caller must fall back to the last
    certified configuration (spec §4.1, migration rule).

    Stage 2: project the proposal onto ``F`` and accept, recording the
    projection in the candidate. The projection is unique for the v0
    box representation of ``P_i``; for non-convex future sets use
    :func:`lexicographic_select` on the candidate list.
    """
    _validate_bounds(proposal, lower, upper)
    if budget < 0.0:
        raise ValueError("budget must be non-negative")
    if np.any(scale <= 0.0):
        raise ValueError("scale entries must be positive")
    if new_lower is not None and new_upper is not None:
        _validate_bounds(proposal, new_lower, new_upper)
        if np.any(p_last < new_lower - tol) or np.any(p_last > new_upper + tol):
            return ScreeningResult(
                outcome=ScreeningOutcome.REJECTED_MIGRATION,
                candidate=None,
                reason=(
                    "last approved parameter p^k left the new policy set; "
                    "fallback to last certified configuration required"
                ),
            )
    reach = budget * scale
    lo = np.maximum(lower, p_last - reach)
    hi = np.minimum(upper, p_last + reach)
    if np.any(lo > hi):
        return ScreeningResult(
            outcome=ScreeningOutcome.REJECTED_EMPTY_SET,
            candidate=None,
            reason="P ∩ B_Delta(p^k) is empty: no admissible candidate",
        )
    candidate = project_onto_intersection(
        proposal,
        p_last,
        lower=lower,
        upper=upper,
        scale=scale,
        budget=budget,
    )
    return ScreeningResult(
        outcome=ScreeningOutcome.ACCEPTED,
        candidate=candidate,
        reason="projected onto P ∩ B_Delta(p^k)",
    )
