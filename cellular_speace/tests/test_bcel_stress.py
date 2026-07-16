"""Operational stress tests for BCEL functional constraints."""

import asyncio

import pytest

from speace_core.bcel import ConstraintStressTester, FunctionalConstraint
from speace_core.bcel.stress_circuit import make_minimal_builder


def _build_minimal_orchestrator(constraint_name: str):
    return make_minimal_builder(constraint_name)()


@pytest.mark.asyncio
async def test_rate_limiter_constraint_is_protective():
    tester = ConstraintStressTester(
        build_orchestrator=lambda: _build_minimal_orchestrator("rate_limiter")
    )
    constraint = FunctionalConstraint(
        name="rate_limiter",
        invariant="coherence_preservation",
        biological_form="neural refractory period limits firing rate",
        mathematical_form="digital neuron enforces minimum inter-spike interval",
        parameters={"min_inter_spike_ticks": 2},
        stability_test="firing_rate_stays_bounded",
    )
    result = await tester.run(constraint, metric="total_spikes", ticks=20)
    assert result.passed, result.interpretation
    assert result.relative_change >= 2.0


@pytest.mark.asyncio
async def test_short_term_depression_constraint_is_protective():
    tester = ConstraintStressTester(
        build_orchestrator=lambda: _build_minimal_orchestrator("short_term_depression")
    )
    constraint = FunctionalConstraint(
        name="short_term_depression",
        invariant="destructive_entropy_reduction",
        biological_form="vesicle depletion reduces repeated gain",
        mathematical_form="activity-dependent synaptic gain decay",
        parameters={"decay_per_spike": 0.05, "recovery_tau": 10.0},
        stability_test="prevents_runaway_excitation",
    )
    result = await tester.run(constraint, metric="max_activation", ticks=20)
    assert result.passed, result.interpretation
    assert result.relative_change >= 2.0


@pytest.mark.asyncio
async def test_delay_as_lowpass_filter_constraint_is_protective():
    tester = ConstraintStressTester(
        build_orchestrator=lambda: _build_minimal_orchestrator("delay_as_lowpass_filter")
    )
    constraint = FunctionalConstraint(
        name="delay_as_lowpass_filter",
        invariant="coherence_preservation",
        biological_form="1-2 ms synaptic delay",
        mathematical_form="leaky integrator + rate limiter",
        parameters={"tau_ms": 5.0, "max_rate_hz": 100.0},
        stability_test="network_does_not_oscillate_when_delay_removed",
    )
    result = await tester.run(constraint, metric="max_activation", ticks=20)
    assert result.passed, result.interpretation
    assert result.relative_change >= 2.0


def test_stress_tester_without_builder_returns_placeholder():
    tester = ConstraintStressTester()
    constraint = FunctionalConstraint(
        name="unknown_constraint",
        invariant="coherence_preservation",
        biological_form="unknown",
        mathematical_form="unknown",
    )
    result = asyncio.run(tester.run(constraint))
    assert not result.passed or "placeholder" in result.test_name
    assert "could not be executed" in result.interpretation
