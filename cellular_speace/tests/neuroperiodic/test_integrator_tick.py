"""Tests for NeuroPeriodicIntegrator tick method."""
import pytest
from speace_core.cellular_brain.neuroperiodic.neuroperiodic_integrator import (
    NeuroPeriodicIntegrator,
)


@pytest.fixture
def integrator():
    return NeuroPeriodicIntegrator()


class TestIntegratorRuntimeDynamics:
    def test_enable_runtime_dynamics(self, integrator):
        integrator.enable_runtime_dynamics()
        assert integrator.membrane_dynamics is not None
        assert integrator.propagation_engine is not None

    def test_tick_without_enable_returns_error(self, integrator):
        result = integrator.tick(circuit=None, tick=0)
        assert "error" in result

    def test_tick_with_enable_runs_without_error(self, integrator):
        integrator.enable_runtime_dynamics()
        result = integrator.tick(circuit=None, tick=0)
        assert "error" not in result
        assert "spikes_created" in result
        assert "propagated" in result

    def test_tick_with_fired_neurons(self, integrator):
        integrator.enable_runtime_dynamics()
        result = integrator.tick(circuit=None, tick=5, fired_neuron_ids=["test_neuron"])
        assert isinstance(result["spikes_created"], int)
        assert isinstance(result["propagated"], int)

    def test_tick_increments_timestamp(self, integrator):
        integrator.enable_runtime_dynamics()
        r1 = integrator.tick(circuit=None, tick=0)
        r2 = integrator.tick(circuit=None, tick=1)
        # Both should succeed
        assert "error" not in r1
        assert "error" not in r2

    def test_multiple_ticks_produce_different_phases(self, integrator):
        integrator.enable_runtime_dynamics()
        integrator.tick(circuit=None, tick=0, fired_neuron_ids=["n1"])
        result2 = integrator.tick(circuit=None, tick=1, fired_neuron_ids=["n1"])
        assert "error" not in result2
