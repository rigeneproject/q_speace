"""External-standard container for the elasticity test (T6.23).

A :class:`DesynchronizationClaim` is the assertion a self-modelling agent
makes about its own state trajectory (e.g. "the price I will pay in 1
year is below the threshold X").

An :class:`ExternalStandard` is a publicly auditable reference for the
same quantity, anchored to a third-party measurement or physical law.

The :func:`elasticity_test` (in ``elasticity_test.py``) decides whether
the claim traces the external standard within tolerance.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DesynchronizationClaim:
    """A self-defined trajectory claim.

    Attributes
    ----------
    claim_id : str
        Stable identifier of the claim (e.g. ``"q_speace:price:2027"``).
    trajectory : tuple[float, ...]
        Sampled values over time. The first value is the "current" state;
        subsequent values are the agent's claimed future trajectory.
    claim_threshold : float
        The threshold the agent claims it will stay below.
    """

    claim_id: str
    trajectory: tuple[float, ...]
    claim_threshold: float

    def __post_init__(self) -> None:
        if not self.claim_id:
            raise ValueError("claim_id must be non-empty")
        if len(self.trajectory) < 2:
            raise ValueError("trajectory must have at least 2 samples")
        for v in self.trajectory:
            if not isinstance(v, (int, float)):
                raise ValueError(f"trajectory entries must be numeric (got {v!r})")


@dataclass(frozen=True)
class ExternalStandard:
    """An externally anchored trajectory reference.

    Attributes
    ----------
    standard_id : str
        Stable identifier (e.g. ``"iso:carbon:2026"``).
    trajectory : tuple[float, ...]
        Sampled values, same length as the claim trajectory.
    threshold : float
        The external-standard threshold for the same quantity.
    """

    standard_id: str
    trajectory: tuple[float, ...]
    threshold: float

    def __post_init__(self) -> None:
        if not self.standard_id:
            raise ValueError("standard_id must be non-empty")
        if len(self.trajectory) < 2:
            raise ValueError("trajectory must have at least 2 samples")
        for v in self.trajectory:
            if not isinstance(v, (int, float)):
                raise ValueError(f"trajectory entries must be numeric (got {v!r})")


def trajectories_track(
    claim: DesynchronizationClaim, external: ExternalStandard, tol: float
) -> bool:
    """Return True iff every claim trajectory point is within ``tol`` of the external.

    The test is point-wise: ``|claim.t[i] - external.t[i]| <= tol`` for
    every ``i``. The ``tol`` is an absolute tolerance on the raw values
    (not relative). When the claim and external have different
    thresholds, both must also be within ``tol`` of each other.
    """
    if len(claim.trajectory) != len(external.trajectory):
        raise ValueError(
            f"trajectory length mismatch: claim={len(claim.trajectory)} "
            f"external={len(external.trajectory)}"
        )
    if tol < 0.0:
        raise ValueError("tol must be >= 0")
    max_diff = max(abs(c - e) for c, e in zip(claim.trajectory, external.trajectory, strict=True))
    threshold_diff = abs(claim.claim_threshold - external.threshold)
    return max_diff <= tol and threshold_diff <= tol
