"""T220 §10: Seed contact layer sandbox enforcement, simulation-first, and value rollback."""

from __future__ import annotations

import pytest

from q_speace.seed import (
    ConstitutionalFault,
    ContactPlan,
    ContactSpec,
    IgnitionObservation,
    SeedContactLayer,
    SeedLifecycle,
    SeedState,
)


def _ignited_seed() -> SeedLifecycle:
    seed = SeedLifecycle()
    v = seed.attempt_ignition(
        IgnitionObservation(
            accepted_mutations=3,
            min_metric_delta=0.01,
            consolidations=1,
            metabolic_balance_j=10.0,
            constitutional_faults=0,
            rollbacks_exercised=1,
            window_ticks=10,
        )
    )
    assert v.passed is True
    return seed


def test_contact_spec_enforces_sandbox_only_and_no_entanglement_channel() -> None:
    with pytest.raises(ConstitutionalFault, match="non-sandboxed"):
        ContactSpec(
            contact_id="phys-actuator",
            protocol="modbus",
            capabilities=("write",),
            read_scope=("bus",),
            sandboxed=False,
        )
    with pytest.raises(ConstitutionalFault, match="forbidden contact protocol"):
        ContactSpec(
            contact_id="bad-channel",
            protocol="entanglement",
            capabilities=("read",),
            read_scope=("state",),
            sandboxed=True,
        )
    with pytest.raises(ConstitutionalFault, match="rollback_plan"):
        ContactPlan(
            contact_id="sim-1",
            scope=("telemetry",),
            expected_value_j=10.0,
            estimated_cost_j=2.0,
            rollback_plan="   ",
        )


def test_contact_requires_simulation_before_execution() -> None:
    layer = SeedContactLayer()
    layer.register(
        ContactSpec(
            contact_id="sim-1",
            protocol="local-sim",
            capabilities=("read",),
            read_scope=("metrics",),
        )
    )
    with pytest.raises(ConstitutionalFault, match="simulate_plan"):
        layer.execute_plan("sim-1", measured_value_j=10.0)


def test_assimilation_rolls_back_on_negative_measured_surplus_and_consolidates_with_council() -> (
    None
):
    seed = _ignited_seed()
    seed.register_contact(
        ContactSpec(
            contact_id="sim-logistics",
            protocol="local-sim",
            capabilities=("schedule",),
            read_scope=("bins",),
            estimated_cost_j=5.0,
        )
    )
    plan = ContactPlan(
        contact_id="sim-logistics",
        scope=("bins",),
        expected_value_j=12.0,
        estimated_cost_j=5.0,
        rollback_plan="detach sim-logistics adapter and restore snapshot",
    )

    # Failed value verification triggers rollback and removes active contact
    rb = seed.assimilate_contact(plan, measured_value_j=2.0, council_approved=True)
    assert rb.status == "rolled_back"
    assert "sim-logistics" not in seed.contacts.active_ids()
    assert seed.state == SeedState.IMPROVING

    # Verified value with council approval consolidates cleanly
    ok = seed.assimilate_contact(plan, measured_value_j=15.0, council_approved=True)
    assert ok.status == "consolidated"
    assert "sim-logistics" in seed.contacts.consolidated_ids()
    assert seed.registry.count() >= 2
