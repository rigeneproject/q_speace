"""Brian2Backend — optional, lazy-imported Brian2 backend.

If brian2 is not installed, importing this module still succeeds, but
`is_available()` returns False and `setup()` raises RuntimeError.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from speace_core.cellular_brain.simulator_backends.optional_imports import (
    optional_import,
)
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


class Brian2Backend(SimulatorBackend):
    """Brian2-backed simulator. Requires the `brian2` package."""

    kind = BackendKind.BRIAN2

    def __init__(self) -> None:
        self._brian2 = optional_import("brian2")
        self._neurons: Dict[str, int] = {}  # neuron_id -> index in NeuronGroup
        self._ng: Any = None
        self._synapses: Any = None
        self._spike_monitor: Any = None
        self._state_monitor: Any = None
        self._projections: List[Projection] = []

    def is_available(self) -> bool:
        return self._brian2 is not None

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            max_neurons=1_000_000,
            supports_continuous_state=True,
            supports_synapse_plasticity=True,
            supports_single_neuron_morphology=False,
            requires_gil=False,
            metadata={"engine": "brian2"},
        )

    def setup(
        self,
        populations: List[Population],
        projections: List[Projection],
    ) -> None:
        if not self.is_available():
            raise RuntimeError(
                "brian2 is not installed; install with `pip install brian2` "
                "or use NativeBackend instead"
            )
        b2 = self._brian2
        # Aggregate neurons into a single NeuronGroup for simplicity
        all_neurons: List[NeuronSpec] = []
        for pop in populations:
            all_neurons.extend(pop.neurons)
        if not all_neurons:
            raise ValueError("no neurons to simulate")
        eqs = """
        dv/dt = (v_rest - v + I) / tau : 1
        v_rest : 1
        threshold : 1
        reset_v : 1
        tau : second
        I : 1
        """
        ng = b2.NeuronGroup(
            N=len(all_neurons),
            model=eqs,
            threshold="v > threshold",
            reset="v = reset_v",
            method="euler",
            dt=0.1 * b2.ms,
        )
        ng.v = 0.0
        ng.v_rest = b2.array([n.resting for n in all_neurons])
        ng.threshold = b2.array([n.threshold for n in all_neurons])
        ng.reset_v = b2.array([n.reset for n in all_neurons])
        ng.tau = b2.array([max(0.1, n.tau_ms) for n in all_neurons]) * b2.ms
        ng.I = 0.0
        self._ng = ng
        self._neurons = {n.neuron_id: i for i, n in enumerate(all_neurons)}
        # Build Synapses with per-connection weights.
        syn = b2.Synapses(ng, ng, model="weight : 1", on_pre="v_post += weight")
        conns: List[ConnectionSpec] = []
        sources: List[int] = []
        targets: List[int] = []
        weights: List[float] = []
        for proj in projections:
            for c in proj.connections:
                if c.source_id in self._neurons and c.target_id in self._neurons:
                    sources.append(self._neurons[c.source_id])
                    targets.append(self._neurons[c.target_id])
                    weights.append(float(c.weight))
                    conns.append(c)
        if sources:
            syn.connect(i=b2.array(sources), j=b2.array(targets))
            syn.weight = b2.array(weights)
        self._synapses = syn
        self._projections = projections
        self._spike_monitor = b2.SpikeMonitor(ng)
        self._state_monitor = b2.StateMonitor(ng, "v", record=True)
        # Keep references to avoid garbage collection
        self._net = b2.Network(ng, syn, self._spike_monitor, self._state_monitor)

    def run(self, duration_ms: float, dt_ms: float = 0.1) -> SimulationResult:
        if not self.is_available():
            raise RuntimeError("brian2 not installed")
        if self._ng is None:
            raise RuntimeError("call setup() before run()")
        b2 = self._brian2
        # Reset accumulators (brian2 accumulates spikes over runs)
        t_start = self._spike_monitor.t[-1] if len(self._spike_monitor.t) > 0 else 0 * b2.ms
        self._net.run(duration_ms * b2.ms)
        spikes: Dict[str, List[float]] = {nid: [] for nid in self._neurons}
        for t, i in zip(self._spike_monitor.t, self._spike_monitor.i):
            if t < t_start:
                continue
            # invert index
            for nid, idx in self._neurons.items():
                if idx == int(i):
                    spikes[nid].append(float(t / b2.ms))
                    break
        state: Dict[str, List[float]] = {}
        for nid, idx in self._neurons.items():
            try:
                samples = [float(v) for v in self._state_monitor.v[idx].tolist()]
            except Exception:
                samples = []
            state[nid] = samples
        runtime = float(duration_ms)
        return SimulationResult(spikes=spikes, state=state, runtime_ms=runtime)

    def reset(self) -> None:
        if self._ng is not None and self._brian2 is not None:
            self._ng.v = 0.0
            self._ng.I = 0.0

    def set_neurons_input(
        self,
        neuron_id_to_current: Dict[str, float],
    ) -> None:
        if self._ng is None:
            return
        for nid, c in neuron_id_to_current.items():
            if nid in self._neurons:
                self._ng.I[self._neurons[nid]] = float(c)
