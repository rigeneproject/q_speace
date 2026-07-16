"""Tests for the NativeBackend (always-available backend)."""
import math
import pytest

from speace_core.cellular_brain.simulator_backends import (
    ConnectionSpec,
    NativeBackend,
    NeuronSpec,
    Population,
    Projection,
)


def make_population(n: int, label: str = "p", threshold: float = 0.5,
                    tau_ms: float = 10.0) -> Population:
    specs = [
        NeuronSpec(neuron_id=f"{label}_{i}", threshold=threshold, tau_ms=tau_ms)
        for i in range(n)
    ]
    return Population(label=label, neurons=specs)


class TestNativeBackend:
    def test_capabilities(self):
        b = NativeBackend()
        caps = b.capabilities()
        assert caps.max_neurons > 0
        assert caps.supports_continuous_state is True

    def test_is_available(self):
        assert NativeBackend().is_available() is True

    def test_setup_and_run_with_no_inputs(self):
        b = NativeBackend()
        pop = make_population(3)
        b.setup([pop], [])
        result = b.run(duration_ms=2.0, dt_ms=0.1)
        # no spikes without input
        assert all(len(v) == 0 for v in result.spikes.values())
        # state samples equal to number of steps
        n_steps = int(2.0 / 0.1)
        for samples in result.state.values():
            assert len(samples) == n_steps

    def test_spike_under_strong_input(self):
        b = NativeBackend()
        spec = NeuronSpec(neuron_id="n1", threshold=0.5, tau_ms=20.0, refractory_ms=1.0)
        pop = Population(label="p", neurons=[spec])
        b.setup([pop], [])
        b.set_neurons_input({"n1": 100.0})
        result = b.run(duration_ms=20.0, dt_ms=0.1)
        assert len(result.spikes["n1"]) >= 1

    def test_synapse_delivers_input(self):
        b = NativeBackend()
        src = make_population(2, label="src", threshold=0.1, tau_ms=20.0)
        tgt = Population(
            label="tgt",
            neurons=[
                NeuronSpec(neuron_id="tgt_0", threshold=0.5, tau_ms=20.0,
                           refractory_ms=1.0)
            ],
        )
        proj = Projection(source=src, target=tgt)
        proj.connect_all(weight=2.0, delay_ms=1.0)
        b.setup([src, tgt], [proj])
        # strong current on source to make it fire
        b.set_neurons_input({"src_0": 100.0, "src_1": 100.0})
        result = b.run(duration_ms=20.0, dt_ms=0.1)
        # target should have received input and eventually spiked
        assert len(result.spikes["tgt_0"]) >= 1

    def test_reset(self):
        b = NativeBackend()
        spec = NeuronSpec(neuron_id="n1", threshold=0.5, tau_ms=20.0,
                          refractory_ms=1.0, initial_voltage=0.7)
        pop = Population(label="p", neurons=[spec])
        b.setup([pop], [])
        state_before = b.get_neurons_state(["n1"])
        b.reset()
        state_after = b.get_neurons_state(["n1"])
        # after reset, voltage = resting (0.0)
        assert state_after["n1"] == 0.0

    def test_get_neurons_state(self):
        b = NativeBackend()
        pop = make_population(3)
        b.setup([pop], [])
        states = b.get_neurons_state([f"p_{i}" for i in range(3)])
        assert set(states.keys()) == {"p_0", "p_1", "p_2"}

    def test_set_neurons_input(self):
        b = NativeBackend()
        pop = make_population(2)
        b.setup([pop], [])
        b.set_neurons_input({"p_0": 1.0, "p_1": 2.0})
        # No assertion on internal state; just that the call works.

    def test_invalid_run_args(self):
        b = NativeBackend()
        pop = make_population(2)
        b.setup([pop], [])
        with pytest.raises(ValueError):
            b.run(duration_ms=0)
        with pytest.raises(ValueError):
            b.run(duration_ms=10.0, dt_ms=0.0)

    def test_runtime_tracked(self):
        b = NativeBackend()
        pop = make_population(2)
        b.setup([pop], [])
        result = b.run(duration_ms=1.0, dt_ms=0.1)
        assert result.runtime_ms >= 0.0
