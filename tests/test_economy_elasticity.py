"""Tests for the q_speace_economy elasticity_test (T6.23)."""

from __future__ import annotations

import pytest

from q_speace.economy.desync_guard import (
    DesynchronizationClaim,
    ExternalStandard,
    trajectories_track,
)
from q_speace.economy.elasticity_test import elasticity_test


def _claim(traj: tuple[float, ...], threshold: float = 1.0) -> DesynchronizationClaim:
    return DesynchronizationClaim(claim_id="test:claim", trajectory=traj, claim_threshold=threshold)


def _external(traj: tuple[float, ...], threshold: float = 1.0) -> ExternalStandard:
    return ExternalStandard(standard_id="test:external", trajectory=traj, threshold=threshold)


def test_trajectories_track_identical() -> None:
    assert trajectories_track(_claim((1.0, 2.0, 3.0)), _external((1.0, 2.0, 3.0)), 0.0)


def test_trajectories_track_within_tol() -> None:
    assert trajectories_track(_claim((1.0, 2.0, 3.0)), _external((1.01, 2.0, 2.99)), 0.05)


def test_trajectories_track_outside_tol() -> None:
    assert not trajectories_track(_claim((1.0, 2.0, 3.0)), _external((1.5, 2.0, 3.0)), 0.05)


def test_trajectories_track_threshold_mismatch() -> None:
    assert not trajectories_track(
        _claim((1.0, 2.0, 3.0), threshold=1.0),
        _external((1.0, 2.0, 3.0), threshold=1.5),
        0.05,
    )


def test_trajectories_track_length_mismatch_raises() -> None:
    with pytest.raises(ValueError):
        trajectories_track(_claim((1.0, 2.0)), _external((1.0, 2.0, 3.0)), 0.05)


def test_trajectories_track_rejects_negative_tol() -> None:
    with pytest.raises(ValueError):
        trajectories_track(_claim((1.0, 2.0)), _external((1.0, 2.0)), -0.1)


def test_elasticity_test_accept_when_tracking() -> None:
    decision = elasticity_test(
        _claim((1.0, 2.0, 3.0)),
        _external((1.01, 2.0, 2.99)),
        tol=0.05,
    )
    assert decision == "ACCEPT"


def test_elasticity_test_reject_when_diverging() -> None:
    decision = elasticity_test(
        _claim((1.0, 2.0, 3.0)),
        _external((2.0, 2.0, 3.0)),
        tol=0.05,
    )
    assert decision == "REJECT"


def test_elasticity_test_rejects_negative_tol() -> None:
    with pytest.raises(ValueError):
        elasticity_test(_claim((1.0, 2.0)), _external((1.0, 2.0)), tol=-0.1)


def test_elasticity_test_rejects_empty_trajectory() -> None:
    with pytest.raises(ValueError):
        _claim((1.0,), threshold=1.0)


def test_desync_guard_validates_claim() -> None:
    with pytest.raises(ValueError):
        DesynchronizationClaim(claim_id="", trajectory=(1.0, 2.0), claim_threshold=1.0)


def test_desync_guard_validates_external() -> None:
    with pytest.raises(ValueError):
        ExternalStandard(standard_id="", trajectory=(1.0, 2.0), threshold=1.0)


def test_elasticity_continuity_small_perturbation() -> None:
    """Small perturbation in external trajectory should not flip the verdict.

    Verifies the 'elasticity' property: the ACCEPT/REJECT gate is
    Lipschitz w.r.t. small input changes within tolerance.
    """
    claim = _claim((1.0, 2.0, 3.0))
    base = elasticity_test(claim, _external((1.01, 2.0, 2.99)), tol=0.05)
    perturbed = elasticity_test(claim, _external((1.02, 2.01, 2.98)), tol=0.05)
    assert base == perturbed == "ACCEPT"
