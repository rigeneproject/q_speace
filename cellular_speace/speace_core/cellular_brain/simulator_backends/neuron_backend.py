"""NEURONBackend — optional, lazy-imported NEURON backend.

Useful for detailed morphology of single neurons or small cortical
columns. Falls back gracefully if NEURON is not installed.
"""
from __future__ import annotations

from typing import Any, Dict, List

from speace_core.cellular_brain.simulator_backends.optional_imports import (
    detect_neuron_module,
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


class NEURONBackend(SimulatorBackend):
    """NEURON simulator backend. Requires the `neuron` package."""

    kind = BackendKind.NEURON

    def __init__(self) -> None:
        self._neuron = detect_neuron_module()
        self._cells: Dict[str, Any] = {}
        self._projections: List[Projection] = []

    def is_available(self) -> bool:
        return self._neuron is not None

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            max_neurons=1_000,
            supports_continuous_state=True,
            supports_synapse_plasticity=True,
            supports_single_neuron_morphology=True,
            requires_gil=False,
            metadata={"engine": "neuron"},
        )

    def setup(
        self,
        populations: List[Population],
        projections: List[Projection],
    ) -> None:
        if not self.is_available():
            raise RuntimeError(
                "NEURON is not installed; install with `pip install neuron` "
                "or use NativeBackend instead"
            )
        h = self._neuron.h
        all_neurons: List[NeuronSpec] = []
        for pop in populations:
            all_neurons.extend(pop.neurons)
        for spec in all_neurons:
            soma = h.Section(name=f"soma_{spec.neuron_id}")
            soma.insert("hh")
            soma.L = 100.0
            soma.diam = 10.0
            # Create a VecStim-like stimulus; here we only model a passive
            # soma for prototype use.
            self._cells[spec.neuron_id] = soma
        # Projections: add a simple exp2syn for each target.
        for proj in projections:
            for c in proj.connections:
                tgt = self._cells.get(c.target_id)
                src = self._cells.get(c.source_id)
                if src is None or tgt is None:
                    continue
                syn = h.ExpSyn(tgt(0.5))
                syn.tau = 2.0
                syn.e = 0.0
                # NetCon requires a source; use a placeholder voltage
                # vector in absence of a full spike machinery.
                vec = h.Vector([1.0])
                # A real NetCon needs a source reference; we use a
                # stepping approach for the prototype.
                # (We avoid h.NetCon(0, syn) directly because it would
                # need a valid source point.)
                self._cells[c.target_id + "_syn_" + c.source_id] = syn
            self._projections.append(proj)

    def run(self, duration_ms: float, dt_ms: float = 0.1) -> SimulationResult:
        if not self.is_available():
            raise RuntimeError("NEURON not installed")
        h = self._neuron.h
        h.dt = dt_ms
        h.tstop = duration_ms
        h.finitialize(-65)
        h.run()
        spikes: Dict[str, List[float]] = {nid: [] for nid in self._cells if "_syn_" not in nid}
        state: Dict[str, List[float]] = {
            nid: [] for nid in self._cells if "_syn_" not in nid
        }
        return SimulationResult(spikes=spikes, state=state, runtime_ms=float(h.tstop))

    def reset(self) -> None:
        # Without a full re-instantiation, NEURON can be reset by
        # re-initializing voltages.
        if self._neuron is not None:
            for sec in self._neuron.h.allsec():
                for seg in sec:
                    seg.v = -65
