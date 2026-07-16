"""NESTBackend — optional, lazy-imported NEST backend."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

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


class NESTBackend(SimulatorBackend):
    """NEST simulator backend. Requires the `nest` package."""

    kind = BackendKind.NEST

    def __init__(self) -> None:
        self._nest = optional_import("nest")
        self._neurons: Dict[str, int] = {}
        self._projections: List[Projection] = []
        self._nest_pop: Any = None
        self._spike_detector: Any = None

    def is_available(self) -> bool:
        return self._nest is not None

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            max_neurons=10_000_000,
            supports_continuous_state=False,
            supports_synapse_plasticity=True,
            supports_single_neuron_morphology=False,
            requires_gil=False,
            metadata={"engine": "nest"},
        )

    def setup(
        self,
        populations: List[Population],
        projections: List[Projection],
    ) -> None:
        if not self.is_available():
            raise RuntimeError(
                "nest is not installed; install with `pip install nest-simulator` "
                "or use NativeBackend instead"
            )
        nest = self._nest
        all_neurons: List[NeuronSpec] = []
        for pop in populations:
            all_neurons.extend(pop.neurons)
        if not all_neurons:
            raise ValueError("no neurons to simulate")
        # Use a single iaf_psc_alpha population
        self._nest_pop = nest.Create(
            "iaf_psc_alpha",
            n=len(all_neurons),
            params={
                "V_th": -50.0,
                "V_reset": -70.0,
                "V_m": -70.0,
                "tau_m": 10.0,
            },
        )
        self._neurons = {n.neuron_id: i for i, n in enumerate(all_neurons)}
        self._spike_detector = nest.Create("spike_detector")
        nest.Connect(self._nest_pop, self._spike_detector)
        # Synaptic connections
        for proj in projections:
            for c in proj.connections:
                if c.source_id in self._neurons and c.target_id in self._neurons:
                    src_id = int(self._neurons[c.source_id]) + 1
                    tgt_id = int(self._neurons[c.target_id]) + 1
                    nest.Connect(
                        self._nest_pop[src_id - 1],
                        self._nest_pop[tgt_id - 1],
                        syn_spec={"weight": float(c.weight), "delay": float(c.delay_ms)},
                    )
        self._projections = projections

    def run(self, duration_ms: float, dt_ms: float = 0.1) -> SimulationResult:
        if not self.is_available():
            raise RuntimeError("nest not installed")
        if self._nest_pop is None:
            raise RuntimeError("call setup() before run()")
        nest = self._nest
        nest.Simulate(duration_ms)
        events = nest.GetStatus(self._spike_detector, "events")[0]
        senders = events.get("senders", [])
        times = events.get("times", [])
        spikes: Dict[str, List[float]] = {nid: [] for nid in self._neurons}
        for s, t in zip(senders, times):
            for nid, idx in self._neurons.items():
                if idx == int(s) - 1:
                    spikes[nid].append(float(t))
                    break
        return SimulationResult(spikes=spikes, runtime_ms=float(duration_ms))

    def reset(self) -> None:
        if self._nest is not None:
            self._nest.ResetKernel()
            self._neurons.clear()
            self._nest_pop = None
            self._spike_detector = None
