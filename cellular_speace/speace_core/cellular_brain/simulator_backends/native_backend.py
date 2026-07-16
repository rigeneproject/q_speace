"""NativeBackend — always-available in-process backend.

This is the default backend. It implements a simple LIF (leaky
integrate-and-fire) simulation using only the standard library, so it
has zero external dependencies.

The fidelity is intentionally modest: it's the same shape as the
existing SPEACE tick() loop, exposed through the PyNN-like
Population/Projection surface.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from speace_core.cellular_brain.simulator_backends.population import (
    ConnectionSpec,
    NeuronSpec,
    Population,
    Projection,
)
from speace_core.cellular_brain.simulator_backends.simulator_backend import (
    BackendCapabilities,
    BackendKind,
    SimulationResult,
    SimulatorBackend,
)


@dataclass
class _NeuronRuntime:
    """Mutable runtime state of a neuron."""
    spec: NeuronSpec
    voltage: float
    last_spike_ms: float = -math.inf
    refractory_until_ms: float = 0.0
    input_current: float = 0.0
    state_samples: List[Tuple[float, float]] = field(default_factory=list)


class NativeBackend(SimulatorBackend):
    """In-process LIF simulator. Always available."""

    kind = BackendKind.NATIVE

    def __init__(self) -> None:
        self._neurons: Dict[str, _NeuronRuntime] = {}
        self._projections: List[Projection] = []
        self._current_time_ms: float = 0.0

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            max_neurons=10_000,
            supports_continuous_state=True,
            supports_synapse_plasticity=False,
            supports_single_neuron_morphology=False,
            requires_gil=True,
            metadata={"engine": "native_lif", "language": "python"},
        )

    def setup(
        self,
        populations: List[Population],
        projections: List[Projection],
    ) -> None:
        self._neurons.clear()
        for pop in populations:
            for spec in pop.neurons:
                v0 = spec.initial_voltage if spec.initial_voltage is not None else spec.resting
                self._neurons[spec.neuron_id] = _NeuronRuntime(
                    spec=spec,
                    voltage=float(v0),
                )
        self._projections = list(projections)
        self._current_time_ms = 0.0

    def run(self, duration_ms: float, dt_ms: float = 0.1) -> SimulationResult:
        if dt_ms <= 0:
            raise ValueError("dt_ms must be > 0")
        if duration_ms <= 0:
            raise ValueError("duration_ms must be > 0")
        t0 = time.perf_counter()
        spikes: Dict[str, List[float]] = {nid: [] for nid in self._neurons}
        state: Dict[str, List[float]] = {nid: [] for nid in self._neurons}
        n_steps = max(1, int(round(duration_ms / dt_ms)))
        for step in range(n_steps):
            t = self._current_time_ms + (step + 1) * dt_ms
            # 1) integrate inputs from previous spike deliveries
            for proj in self._projections:
                for conn in proj.connections:
                    src = self._neurons.get(conn.source_id)
                    tgt = self._neurons.get(conn.target_id)
                    if src is None or tgt is None:
                        continue
                    # delayed delivery
                    if src.last_spike_ms >= 0 and t - src.last_spike_ms >= conn.delay_ms:
                        tgt.input_current += conn.weight
            # 2) update each neuron's voltage (LIF)
            for nid, rt in self._neurons.items():
                if t < rt.refractory_until_ms:
                    state[nid].append(rt.voltage)
                    continue
                # tau_ms ~ membrane time constant
                decay = math.exp(-dt_ms / max(0.1, rt.spec.tau_ms))
                rt.voltage = (
                    rt.spec.resting
                    + (rt.voltage - rt.spec.resting) * decay
                    + rt.input_current * dt_ms * 0.05
                )
                rt.input_current = 0.0
                if rt.voltage >= rt.spec.threshold:
                    spikes[nid].append(t)
                    rt.last_spike_ms = t
                    rt.refractory_until_ms = t + rt.spec.refractory_ms
                    rt.voltage = rt.spec.reset
                state[nid].append(rt.voltage)
        self._current_time_ms += duration_ms
        result = SimulationResult(
            spikes=spikes,
            state=state,
            runtime_ms=(time.perf_counter() - t0) * 1000.0,
        )
        return result

    def reset(self) -> None:
        # `initial_voltage` is the *startup* state used at setup() time.
        # reset() returns every neuron to its stationary `resting` level.
        for nid, rt in self._neurons.items():
            rt.voltage = float(rt.spec.resting)
            rt.last_spike_ms = -math.inf
            rt.refractory_until_ms = 0.0
            rt.input_current = 0.0
            rt.state_samples.clear()
        self._current_time_ms = 0.0

    def get_neurons_state(self, neuron_ids: List[str]) -> Dict[str, float]:
        return {nid: self._neurons[nid].voltage for nid in neuron_ids if nid in self._neurons}

    def set_neurons_input(
        self,
        neuron_id_to_current: Dict[str, float],
    ) -> None:
        for nid, c in neuron_id_to_current.items():
            if nid in self._neurons:
                self._neurons[nid].input_current = float(c)
