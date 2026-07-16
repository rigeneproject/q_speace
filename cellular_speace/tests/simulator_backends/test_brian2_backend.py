"""Conditional tests for the Brian2 simulator backend.

These tests are skipped if `brian2` is not installed. They validate:
  - availability detection
  - setup with Population/Projection
  - run returning spikes and state
  - input injection
  - reset
  - transparent fallback to NativeBackend when unavailable
"""
from __future__ import annotations

import pytest

brian2 = pytest.importorskip("brian2", reason="brian2 not installed; install with `pip install brian2`")

from speace_core.cellular_brain.simulator_backends.backend_selector import BackendChoice, BackendSelector
from speace_core.cellular_brain.simulator_backends.brian2_backend import Brian2Backend
from speace_core.cellular_brain.simulator_backends.population import NeuronSpec, Population, Projection


def _make_single_neuron_backend():
    backend = Brian2Backend()
    pop = Population(
        label="test_pop",
        neurons=[NeuronSpec(neuron_id="n0", threshold=0.2, tau_ms=10.0)],
    )
    proj = Projection(source=pop, target=pop, label="test_proj")
    proj.connect("n0", "n0", weight=0.0)  # dummy self-loop so Brian2 has a synapse
    backend.setup([pop], [proj])
    return backend


def test_brian2_backend_available():
    backend = Brian2Backend()
    assert backend.is_available() is True


def test_brian2_backend_capabilities():
    backend = Brian2Backend()
    caps = backend.capabilities()
    assert caps.max_neurons > 0
    assert caps.supports_continuous_state is True
    assert caps.metadata["engine"] == "brian2"


def test_brian2_backend_setup_and_run():
    backend = Brian2Backend()
    pop = Population(
        label="test_pop",
        neurons=[
            NeuronSpec(neuron_id="n0", threshold=0.5, tau_ms=10.0),
            NeuronSpec(neuron_id="n1", threshold=0.5, tau_ms=10.0),
        ],
    )
    proj = Projection(source=pop, target=pop, label="test_proj")
    proj.connect("n0", "n1", weight=0.5)

    backend.setup([pop], [proj])
    result = backend.run(duration_ms=50.0, dt_ms=0.1)

    assert result is not None
    assert "n0" in result.spikes
    assert "n1" in result.spikes
    assert result.runtime_ms == pytest.approx(50.0)


def test_brian2_backend_input_injection():
    backend = _make_single_neuron_backend()
    backend.set_neurons_input({"n0": 1.0})
    result = backend.run(duration_ms=30.0)
    assert result.spikes["n0"]


def test_brian2_backend_reset():
    backend = _make_single_neuron_backend()
    backend.set_neurons_input({"n0": 1.0})
    backend.run(duration_ms=30.0)
    backend.reset()
    # After reset, membrane voltage and input current should be zeroed.
    assert float(backend._ng.v[0]) == pytest.approx(0.0, abs=1e-6)
    assert float(backend._ng.I[0]) == pytest.approx(0.0, abs=1e-6)


def test_backend_selector_builds_brian2_when_available():
    selector = BackendSelector()
    backend = selector.build(BackendChoice.BRIAN2)
    assert backend.is_available() is True
    assert backend.kind == BackendChoice.BRIAN2


def test_backend_selector_recommends_native_for_python_only_workload():
    selector = BackendSelector()
    choice = selector.recommend(
        neuron_count=100,
        needs_morphology=False,
        needs_stdp=False,
        prefers_python=True,
        allow_external_deps=True,
    )
    assert choice == BackendChoice.NATIVE


def test_backend_selector_fallback_to_native_when_brian2_unavailable(monkeypatch):
    """If Brian2 reports itself unavailable, build must fall back to native."""
    from speace_core.cellular_brain.simulator_backends import backend_selector as selector_mod
    from speace_core.cellular_brain.simulator_backends.native_backend import NativeBackend

    selector = BackendSelector()
    # Ensure the cached Brian2 (if any) is considered unavailable.
    monkeypatch.setattr(Brian2Backend, "is_available", lambda self: False)
    backend = selector.build(BackendChoice.BRIAN2)
    assert isinstance(backend, NativeBackend)
    assert backend.kind == BackendChoice.NATIVE
