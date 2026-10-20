"""Elasticity test gate for the q_speace_economy (T6.23).

The :func:`elasticity_test` decides whether a
:class:`DesynchronizationClaim` (in ``desync_guard.py``) tracks an
:class:`ExternalStandard` within tolerance. It returns one of two
literals: ``"ACCEPT"`` or ``"REJECT"``.

The decision rule is mechanical:

- ACCEPT iff :func:`trajectories_track` returns True AND the claim's
  threshold is also within tolerance of the external's threshold.
- REJECT otherwise.

The function is intentionally **not** a learned classifier. It is a
deterministic gate whose only inputs are the two trajectories and the
tolerance. The "elasticity" name refers to the property that small
perturbations in the external standard produce small perturbations in
the ACCEPT/REJECT verdict (no phase transition).

BCEL: the gate is *functional*: it is a measurable criterion, not a
moral judgement. The asymmetry between a self-defined threshold and a
publicly auditable one is the entire point — the agent cannot vote
itself into compliance.
"""

from __future__ import annotations

from typing import Literal

from .desync_guard import DesynchronizationClaim, ExternalStandard, trajectories_track

Decision = Literal["ACCEPT", "REJECT"]


def elasticity_test(
    claim: DesynchronizationClaim,
    external: ExternalStandard,
    tol: float = 0.05,
) -> Decision:
    """Return ``"ACCEPT"`` iff ``claim`` tracks ``external`` within ``tol``.

    Parameters
    ----------
    claim : DesynchronizationClaim
        The self-defined trajectory claim.
    external : ExternalStandard
        The external reference.
    tol : float
        Absolute tolerance on the trajectory and threshold match.
    """
    if tol < 0.0:
        raise ValueError(f"tol must be >= 0 (got {tol})")
    if trajectories_track(claim, external, tol):
        return "ACCEPT"
    return "REJECT"
