"""Tests for the q_speace_economy VTEC controller (T6.5)."""

from __future__ import annotations

import numpy as np
import pytest

from q_speace.economy.vtec import (
    AllocationConstraints,
    build_allocation_constraints,
    vtec_allocate,
)


def test_constraints_constructor_validates() -> None:
    with pytest.raises(ValueError):
        AllocationConstraints(
            s_assimilable=-1.0,
            e_available=1.0,
            m_available=1.0,
            ecological_threshold=0.5,
            risk_acceptable=0.5,
            human_agency_min=0.1,
        )
    with pytest.raises(ValueError):
        AllocationConstraints(
            s_assimilable=1.0,
            e_available=1.0,
            m_available=1.0,
            ecological_threshold=0.5,
            risk_acceptable=0.5,
            human_agency_min=1.5,
        )


def test_build_allocation_constraints_defaults() -> None:
    c = build_allocation_constraints()
    assert c.s_assimilable == 1.0
    assert c.e_available == 10.0
    assert c.human_agency_min == 0.1


def test_vtec_rejects_empty_u_max() -> None:
    c = build_allocation_constraints()
    with pytest.raises(ValueError):
        vtec_allocate(
            objective=lambda u: float(np.sum(u)),
            u_max=[],
            constraints=c,
        )


def test_vtec_rejects_negative_lr() -> None:
    c = build_allocation_constraints()
    with pytest.raises(ValueError):
        vtec_allocate(
            objective=lambda u: float(np.sum(u)),
            u_max=[1.0, 1.0],
            constraints=c,
            lr=0.0,
        )


def test_vtec_simple_quadratic_maximises_at_corner() -> None:
    """Maximise -sum((u - 1)^2) on a 3-node graph with u_max=1.

    Objective is concave, peak at u = [1, 1, 1] (corner of the box).
    """
    c = build_allocation_constraints(human_agency_min=0.0)

    def objective(u: np.ndarray) -> float:
        return float(-np.sum((u - 1.0) ** 2))

    res = vtec_allocate(
        objective=objective,
        u_max=[1.0, 1.0, 1.0],
        constraints=c,
        horizon=(200, 50),
        lr=0.1,
    )
    np.testing.assert_allclose(res.u, [1.0, 1.0, 1.0], atol=1e-2)
    assert res.feasible


def test_vtec_respects_per_node_upper_bounds() -> None:
    c = build_allocation_constraints(human_agency_min=0.0)

    def objective(u: np.ndarray) -> float:
        return float(np.sum(u))

    res = vtec_allocate(
        objective=objective,
        u_max=[0.5, 0.7, 0.3],
        constraints=c,
        horizon=(100, 30),
        lr=0.05,
    )
    assert np.all(res.u <= np.array([0.5, 0.7, 0.3]) + 1e-9)


def test_vtec_enforces_human_agency_floor() -> None:
    """The floor on human-owned nodes must never be violated."""
    c = build_allocation_constraints(human_agency_min=0.5)

    # Adversarial objective: pushes everything to node 0 (non-human).
    def objective(u: np.ndarray) -> float:
        return float(u[0])

    res = vtec_allocate(
        objective=objective,
        u_max=[1.0, 1.0, 1.0],
        constraints=c,
        horizon=(50, 20),
        lr=0.1,
        human_mask=[False, True, True],
    )
    # At least 0.5 must sit on the human-owned nodes (1 and 2).
    assert float(np.sum(res.u[[1, 2]])) >= 0.5 - 1e-9


def test_vtec_respects_energy_ceiling() -> None:
    """Total mass on ``u`` must not exceed ``e_available``."""
    c = build_allocation_constraints(human_agency_min=0.0, e_available=2.0)

    def objective(u: np.ndarray) -> float:
        return float(np.sum(u))

    res = vtec_allocate(
        objective=objective,
        u_max=[1.0, 1.0, 1.0, 1.0, 1.0],
        constraints=c,
        horizon=(100, 30),
        lr=0.1,
    )
    assert float(np.sum(res.u)) <= 2.0 + 1e-9


def test_vtec_returns_history() -> None:
    c = build_allocation_constraints(human_agency_min=0.0)
    res = vtec_allocate(
        objective=lambda u: float(np.sum(u)),
        u_max=[1.0, 1.0],
        constraints=c,
        horizon=(20, 10),
        lr=0.05,
    )
    assert len(res.history) > 0
    assert res.iterations == len(res.history)


def test_vtec_convergence_with_plateau() -> None:
    c = build_allocation_constraints(human_agency_min=0.0)
    res = vtec_allocate(
        objective=lambda u: float(-np.sum((u - 0.5) ** 2)),
        u_max=[1.0, 1.0],
        constraints=c,
        horizon=(1000, 50),
        lr=0.1,
    )
    # Should converge before 1000 iterations.
    assert res.iterations < 200
