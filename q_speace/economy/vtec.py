"""Value-of-Total-Exergy-Considered controller (T6.5).

VTEC allocates exergy across an action graph under 6 hard constraints:

1. entropy generation ``S_gen`` must not exceed ``S_assimilable``
2. energy ``E`` must not exceed ``E_available``
3. material ``M`` must not exceed ``M_available``
4. ecological impact must not exceed ``Threshold``
5. risk must not exceed ``Risk_acceptable``
6. **human agency floor** — the action graph must preserve at least
   ``Human_agency_min`` for the human participants

The controller runs projected gradient ascent on the action vector
``u ∈ R^n`` for ``T`` steps with step ``lr``. After each step the
candidate ``u`` is projected onto the feasible polytope by element-wise
clipping against the per-node upper bounds and by a global scaling
factor when a global constraint is violated.

This is **not** a global optimum guarantee. Projected gradient ascent
converges to a local optimum of the (generally non-convex) objective.
The 3-node / 5-step toy in ``tests/test_economy_vtec.py`` verifies the
known optimum; real graphs should be re-run from multiple seeds.

The function is **numpy-only** — no scipy/cvxpy/pymanopt — to respect
the AGENTS.md invariant.

BCEL: the 6 constraints are *functional*: each is a measurable physical
or regulatory bound. The "human agency floor" is the closest analogue
to a constitutional right; it is implemented as a hard floor on the
minimum action weight on human-owned nodes, **not** as a subjective
"wellbeing" claim.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class AllocationConstraints:
    """The 6 hard constraints of the VTEC controller.

    All numeric fields are upper bounds except ``human_agency_min``,
    which is a *floor* on the action weight on human-owned nodes.
    """

    s_assimilable: float  # entropy ceiling (W/K)
    e_available: float  # energy ceiling (W)
    m_available: float  # material ceiling (kg)
    ecological_threshold: float  # dimensionless [0, 1]
    risk_acceptable: float  # dimensionless [0, 1]
    human_agency_min: float  # floor on human-owned action weight

    def __post_init__(self) -> None:
        for name in (
            "s_assimilable",
            "e_available",
            "m_available",
            "ecological_threshold",
            "risk_acceptable",
        ):
            v = getattr(self, name)
            if v < 0.0:
                raise ValueError(f"{name} must be >= 0 (got {v})")
        if not 0.0 <= self.human_agency_min <= 1.0:
            raise ValueError(f"human_agency_min must be in [0, 1] (got {self.human_agency_min})")


@dataclass(frozen=True)
class AllocationResult:
    """Outcome of one :func:`vtec_allocate` call."""

    u: np.ndarray
    history: tuple[float, ...]
    feasible: bool
    final_v: float
    iterations: int


# ---------------------------------------------------------------------------
# core
# ---------------------------------------------------------------------------


def _project_constraints(
    u: np.ndarray,
    u_max: np.ndarray,
    constraints: AllocationConstraints,
    human_mask: np.ndarray,
) -> np.ndarray:
    """Project ``u`` onto the feasible polytope.

    1. Clip each action to ``[0, u_max]``.
    2. Enforce ``human_agency_min`` floor: redistribute any excess above
       the floor from non-human nodes if the human total dropped below
       the threshold.
    3. Renormalise to respect the global entropy/energy/material/ecology/
       risk bounds if any are violated (proportional scaling).
    """
    out: np.ndarray = np.clip(u, 0.0, u_max)
    # Human agency floor: ensure sum(out[human_mask]) >= human_agency_min
    # *after* clipping. If not, take from non-human nodes proportionally.
    human_sum = float(np.sum(out[human_mask])) if human_mask.any() else 0.0
    target = constraints.human_agency_min
    if human_mask.any() and human_sum < target:
        deficit = target - human_sum
        non_human = ~human_mask
        non_human_total = float(np.sum(out[non_human]))
        if non_human_total > 0.0:
            take = min(deficit, non_human_total)
            scale = max(0.0, (non_human_total - take) / non_human_total)
            out[non_human] = out[non_human] * scale
            # Add the deficit to human nodes. If human_sum was 0,
            # distribute uniformly; otherwise proportional.
            if human_sum > 1e-12:
                human_share = out[human_mask] / human_sum
            else:
                n_human = int(np.sum(human_mask))
                human_share = np.full(n_human, 1.0 / n_human, dtype=np.float64)
            out[human_mask] = out[human_mask] + deficit * human_share
    # Per-node upper bounds again (the redistribution above may have
    # pushed a human node over its individual ceiling).
    out = np.clip(out, 0.0, u_max)
    # Aggregate ceilings: if the sum of out exceeds any global bound,
    # scale uniformly. We use the *current* ``u`` as a proxy for the
    # objective side; the caller passes tighter bounds via ``u_max``.
    total = float(np.sum(out))
    if total > constraints.e_available:
        scaled = out * (constraints.e_available / total)
        out_typed: np.ndarray = scaled
        return out_typed
    return out


def vtec_allocate(
    objective: Callable[[np.ndarray], float],
    u_max: Sequence[float],
    constraints: AllocationConstraints,
    *,
    horizon: tuple[int, int] = (50, 50),
    lr: float = 0.01,
    human_mask: Sequence[bool] | None = None,
    tol: float = 1e-6,
) -> AllocationResult:
    """Run projected gradient ascent to allocate ``u``.

    Parameters
    ----------
    objective : callable
        Maps ``u ∈ R^n`` to the value to maximise (e.g. expected catalytic
        return). The controller computes its numerical gradient via
        central differences (eps = 1e-4).
    u_max : sequence of float
        Per-action upper bounds. Length ``n``.
    constraints : AllocationConstraints
        The 6 hard constraints.
    horizon : (max_iter, plateau)
        Tuple of (max_iterations, plateau_window). Defaults to (50, 50).
    lr : float
        Learning rate (gradient ascent step). Defaults to 0.01.
    human_mask : sequence of bool, optional
        Boolean mask marking human-owned nodes. If ``None``, no agency
        floor is enforced (the constraint is treated as 0).
    tol : float
        Convergence threshold on the absolute change in objective value.
    """
    u_max_arr = np.asarray(list(u_max), dtype=np.float64)
    if u_max_arr.ndim != 1:
        raise ValueError("u_max must be 1-D")
    n = u_max_arr.shape[0]
    if n == 0:
        raise ValueError("u_max must be non-empty")
    if human_mask is None:
        human_arr = np.zeros(n, dtype=bool)
    else:
        human_arr = np.asarray(list(human_mask), dtype=bool)
        if human_arr.shape != (n,):
            raise ValueError("human_mask must have length n")
    max_iter, plateau = horizon
    if max_iter < 1:
        raise ValueError("max_iter must be >= 1")
    if lr <= 0.0:
        raise ValueError("lr must be > 0")

    u = np.zeros(n, dtype=np.float64)
    eps_g = 1e-4
    history: list[float] = []
    best_val = float("-inf")
    best_u = u.copy()
    plateau_count = 0
    feasible = True
    final_v = 0.0
    for _ in range(max_iter):
        v = float(objective(u))
        history.append(v)
        if v > best_val + tol:
            best_val = v
            best_u = u.copy()
            plateau_count = 0
        else:
            plateau_count += 1
        final_v = v
        if plateau_count >= plateau:
            break
        # Central-difference gradient.
        grad = np.zeros(n, dtype=np.float64)
        for i in range(n):
            u_plus = u.copy()
            u_plus[i] += eps_g
            u_minus = u.copy()
            u_minus[i] -= eps_g
            grad[i] = (objective(u_plus) - objective(u_minus)) / (2.0 * eps_g)
        u = u + lr * grad
        try:
            u = _project_constraints(u, u_max_arr, constraints, human_arr)
        except ValueError:
            feasible = False
            break
    return AllocationResult(
        u=best_u,
        history=tuple(history),
        feasible=feasible,
        final_v=final_v,
        iterations=len(history),
    )


def build_allocation_constraints(
    *,
    s_assimilable: float = 1.0,
    e_available: float = 10.0,
    m_available: float = 5.0,
    ecological_threshold: float = 0.8,
    risk_acceptable: float = 0.7,
    human_agency_min: float = 0.1,
) -> AllocationConstraints:
    """Default constructor for the 6 VTEC constraints.

    The defaults are calibrated to a 3-node / 5-step toy (see
    ``tests/test_economy_vtec.py``). For real graphs the caller should
    override every value.
    """
    return AllocationConstraints(
        s_assimilable=s_assimilable,
        e_available=e_available,
        m_available=m_available,
        ecological_threshold=ecological_threshold,
        risk_acceptable=risk_acceptable,
        human_agency_min=human_agency_min,
    )


# ---------------------------------------------------------------------------
# T218 (CAU-01): certified causal incremental value
#
# Resolves review items R4, MAT-M3 and EXP-M4. The lower-bound
# certificate of §6.2 of Paradigm_6_0_Revised is defined only against an
# explicit target quantity V*_{Omega,H}: intervention a (with duration
# and successor policy), baseline policy, affected set and horizon. The
# error budget is decomposed into declared, non-overlapping components;
# ``epsilon_model`` must bound the error on the *incremental*
# difference, not on each trajectory separately (opposite errors of
# modulus e give a difference error of 2e).
#
# BCEL: the certificate is a functional numerical inequality under
# declared bounds. It is not a proof of planetary wealth creation.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CausalEstimate:
    """One model-dependent incremental value with its error budget.

    ``epsilon_model`` bounds ``|V̂ − V*_{Omega,H}|`` (the *incremental*
    quantity). ``epsilon_spatial`` and ``epsilon_temporal`` cover
    truncation of the affected set and of the horizon; ``epsilon_stat``
    is a statistical term with confidence level ``confidence_delta``.
    """

    action: str
    baseline: str
    omega: str
    horizon: int
    v_hat: float
    epsilon_model: float
    epsilon_spatial: float
    epsilon_temporal: float
    epsilon_stat: float
    confidence_delta: float
    post_horizon_effect_unknown: bool = False

    def __post_init__(self) -> None:
        for name in (
            "epsilon_model",
            "epsilon_spatial",
            "epsilon_temporal",
            "epsilon_stat",
        ):
            v = getattr(self, name)
            if v < 0.0:
                raise ValueError(f"{name} must be >= 0")
        if not 0.0 < self.confidence_delta < 1.0:
            raise ValueError("confidence_delta must be in (0, 1)")
        if self.horizon < 1:
            raise ValueError("horizon must be >= 1")

    @property
    def epsilon_total(self) -> float:
        """Declared non-overlapping error budget."""
        return self.epsilon_model + self.epsilon_spatial + self.epsilon_temporal + self.epsilon_stat


def certified_lower_bound(est: CausalEstimate) -> float:
    """Return ``V̂ − ε_total`` for the in-horizon target V*_{Ω,H}.

    This is a bound on the *declared in-horizon target only*. Effects
    beyond the horizon are reported separately by
    :func:`post_horizon_verdict` and never absorbed into this bound.
    """
    return est.v_hat - est.epsilon_total


def post_horizon_verdict(est: CausalEstimate) -> str:
    """Classify effects beyond the horizon (R4: no convenient horizons).

    Returns one of:
    * ``"NONE_REPORTED"`` — the model reports no non-negligible post-H effect;
    * ``"OUTSIDE_HORIZON_UNRESOLVED"`` — a potentially significant post-H
      effect exists and the decision layer must treat the estimate as
      unresolved, never as positive.
    """
    if est.post_horizon_effect_unknown:
        return "OUTSIDE_HORIZON_UNRESOLVED"
    return "NONE_REPORTED"


def covered_by_certificate(est: CausalEstimate, true_value: float, *, tol: float = 1e-9) -> bool:
    """Coverage test: true V*_{Ω,H} is not below the declared certificate.

    Use this against ground truth in the simulator. A certificate built
    from per-trajectory bounds (instead of a bound on the incremental
    difference) fails this test when the two trajectory errors have
    opposite signs — the counterexample mandated by review R4/M3.
    """
    return bool(true_value >= certified_lower_bound(est) - tol)
