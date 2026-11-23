"""Dynamic equations of the AACM model (T-AACM-SPEC §2).

All functions are **pure**: they take the current state and return the
next state or a derived scalar. No side effects, no I/O. The functions
are the executable form of the strategic equations in §1 of the spec.

BCEL: the equations are *functional* — they compute a deterministic
result from measurable quantities. They are not a "theory of mind"
or a model of an agent's intent.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from .constants import OMEGA_MIN
from .exceptions import InvariantViolation
from .primitives import LegitimationChannel, ResilienceManifest

# ---------------------------------------------------------------------------
# Fase A — Acquisizione (regole 1, 2, 3)
# ---------------------------------------------------------------------------


def dS_dt(
    S: float,
    C: float,
    sigma_central_hit: float,
    Phi: float,
    leverage_a: float,
    alpha: float = 1.0,
    beta: float = 0.1,
) -> float:
    """Rate of change of target integrity under acquisition.

    dS/dt = -alpha * C * sigma_central_hit - beta * Phi * (1 + a)

    Parameters
    ----------
    S : float
        Current integrity, in [0, 1]. Unused in the formula but kept
        for signature symmetry with downstream integrators.
    C : float
        Attacker's centrality share, in [0, 1].
    sigma_central_hit : float
        1.0 if the action targets a central node, 0.0 otherwise.
    Phi : float
        Total fracture magnitude, in [0, len(axes)].
    leverage_a : float
        Amplification of pre-existing fractures, in [0, 2].
    alpha : float
        Effectiveness of a central hit, default 1.0.
    beta : float
        Cost of generating *new* fractures (kept small: we amplify
        existing ones, we don't create them), default 0.1.
    """
    _check_unit("S", S)
    _check_unit("C", C)
    if sigma_central_hit not in (0.0, 1.0):
        raise ValueError(f"sigma_central_hit must be 0.0 or 1.0 (got {sigma_central_hit})")
    _check_nonneg("Phi", Phi)
    _check_nonneg("leverage_a", leverage_a)
    _check_nonneg("alpha", alpha)
    _check_nonneg("beta", beta)
    return -alpha * C * sigma_central_hit - beta * Phi * (1.0 + leverage_a)


def t_a_within_budget(tau_a: float, tau_r: float) -> bool:
    """Regola 2: tau_a < tau_r / 2.

    Returns True if the action fits within the reaction window.
    """
    _check_nonneg("tau_a", tau_a)
    _check_pos("tau_r", tau_r)
    return tau_a < (tau_r / 2.0)


def leverage_pre_existing_fractures(Phi: float, current_signal_quality: float) -> float:
    """Regola 3: amplifica Phi quando il segnale le espone.

    If the signal quality is below 0.5, the agent amplifies fractures
    (×1.5). Otherwise Phi passes through unchanged.
    """
    _check_nonneg("Phi", Phi)
    _check_unit("current_signal_quality", current_signal_quality)
    if current_signal_quality < 0.5:
        return Phi * 1.5
    return Phi


# ---------------------------------------------------------------------------
# Fase B — Conversione (regole 4, 5, 6)
# ---------------------------------------------------------------------------


def convert_opposition_to_capacity(
    C_self: float,
    C_defeated: Sequence[float],
    rho_loss: float = 0.05,
) -> float:
    """Regola 5: l'opposizione integrata aumenta C_tot a basso costo.

    C_tot = C_self + sum((1 - rho) * c for c in C_defeated)
    """
    _check_unit("C_self", C_self)
    for i, c in enumerate(C_defeated):
        _check_unit(f"C_defeated[{i}]", c)
    _check_unit("rho_loss", rho_loss)
    return C_self + sum((1.0 - rho_loss) * c for c in C_defeated)


def reputation_multiplier(L: float) -> float:
    """Regola 6: L riduce la forza effettiva necessaria.

    multiplier = 1 / (1 + L), in (0, 1] for L >= 0.
    """
    _check_nonneg("L", L)
    return 1.0 / (1.0 + L)


# ---------------------------------------------------------------------------
# Fase C — Stabilizzazione (regole 7, 8)
# ---------------------------------------------------------------------------


def resistance_decay(
    eta_0: float,
    channels: Sequence[LegitimationChannel],
    sigma_per_channel: float = 0.2,
) -> float:
    """Regola 7: resistenza decade come prodotto dei canali verificati.

    eta = eta_0 * prod_{c in channels, c.verified} (1 - sigma)
    """
    _check_nonneg("eta_0", eta_0)
    _check_unit("sigma_per_channel", sigma_per_channel)
    factor = 1.0
    for ch in channels:
        if ch.verified:
            factor *= 1.0 - sigma_per_channel
    return eta_0 * factor


def infrastructure_self_sustaining(
    R_base: float,
    Lambda: float,
    R_current: float,
    lam_decay: float = 0.01,
) -> float:
    """Regola 8: dR/dt = Lambda * R_base - lam * R (forma chiusa).

    Returns the *delta* to apply to ``R_current`` in one step, not
    ``R_current`` itself.
    """
    _check_nonneg("R_base", R_base)
    _check_unit("Lambda", Lambda)
    _check_nonneg("R_current", R_current)
    _check_nonneg("lam_decay", lam_decay)
    return Lambda * R_base - lam_decay * R_current


# ---------------------------------------------------------------------------
# Vincolo D — Resilienza (regole 9 + 10)
# ---------------------------------------------------------------------------


def collapse_probability(Omega: float) -> float:
    """Probabilità di collasso strutturale in funzione di Omega.

    Liscia, monotona decrescente. Con Omega = 0 → 1.0; con Omega
    grande → ~ 0.
    """
    _check_unit("Omega", Omega)
    if Omega < 1e-9:
        return 1.0
    return 1.0 / (1.0 + 10.0 * Omega)


def assert_resilience(manifest: ResilienceManifest, omega_min: float = OMEGA_MIN) -> None:
    """Vincolo D: omega >= omega_min, nodi indipendenti >= 2, checkpoint >= 1."""
    _check_unit("omega_min", omega_min)
    if manifest.omega < omega_min:
        raise InvariantViolation(
            f"ResilienceManifest.omega={manifest.omega} < omega_min={omega_min}"
        )
    if len(manifest.independent_nodes) < 2:
        raise InvariantViolation("need >= 2 independent_nodes")
    if len(manifest.checkpoint_paths) < 1:
        raise InvariantViolation("need >= 1 checkpoint_path")


# ---------------------------------------------------------------------------
# Funzione obiettivo globale
# ---------------------------------------------------------------------------


def value_integral(
    R_series: Sequence[float],
    Lambda_series: Sequence[float],
    lam: float,
    dt: float = 1.0,
) -> float:
    """V_T = int_0^T R(t) * Lambda(t) * exp(-lam t) dt (forma discreta)."""
    if len(R_series) != len(Lambda_series):
        raise ValueError(
            f"R_series and Lambda_series must have equal length "
            f"(got {len(R_series)} vs {len(Lambda_series)})"
        )
    _check_nonneg("lam", lam)
    _check_pos("dt", dt)
    total = 0.0
    for k, (resource, lambda_value) in enumerate(zip(R_series, Lambda_series, strict=True)):
        _check_nonneg(f"R_series[{k}]", resource)
        _check_unit(f"Lambda_series[{k}]", lambda_value)
        total += resource * lambda_value * math.exp(-lam * k * dt) * dt
    return total


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _check_unit(name: str, v: float) -> None:
    """Validate a finite [0, 1] probability-like quantity."""
    if (
        isinstance(v, bool)
        or not isinstance(v, (int, float))
        or not math.isfinite(v)
        or not 0.0 <= v <= 1.0
    ):
        raise ValueError(f"{name} must be in [0, 1] (got {v})")


def _check_nonneg(name: str, v: float) -> None:
    """Validate a finite non-negative scalar."""
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0.0:
        raise ValueError(f"{name} must be >= 0 (got {v})")


def _check_pos(name: str, v: float) -> None:
    """Validate a finite strictly positive scalar."""
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0.0:
        raise ValueError(f"{name} must be > 0 (got {v})")
