"""QuantumOrchestrator — top-level Q-SPEACE runtime (task T7/T8).

Mirrors the ``quantum_enabled`` / ``_run_quantum_step`` hook pattern from
cellular speace's CellularBrainOrchestrator, but standalone. It wires the
quantum kernel, neural bridge, energy cost model, ILF, earth feed and
fractal QCA into a single tick loop with an explicit human/energy gate.
"""
from __future__ import annotations

from dataclasses import dataclass

from .earth_feed import EarthFeed, EarthSignals
from .edd_cvt import InformationalLogicalField
from .fractal_qca import FractalQCA
from .genome import QuantumGeneSet
from .metabolism import QuantumCostModel, QuantumOperation
from .quantum import QuantumNeuralBridge


@dataclass
class TickReport:
    tick: int
    coherence_phi: float
    mean_energy_w: float
    num_qubits: int
    num_entanglements: int
    earth: EarthSignals


class QuantumOrchestrator:
    """Runs the Q-SPEACE quantum layer with an energy/coherence gate."""

    def __init__(
        self,
        genome: QuantumGeneSet | None = None,
        neurons: list[str] | None = None,
        enable_earth: bool = False,
        seed: int | None = None,
    ) -> None:
        self.genome = genome or QuantumGeneSet(enabled=True)
        self.genome.validate()
        self._seed = seed
        self._cost = QuantumCostModel()
        self._ilf = InformationalLogicalField()
        self._earth = EarthFeed(use_network=enable_earth, seed=seed)
        self._bridge = QuantumNeuralBridge(
            num_qubits_per_neuron=self.genome.qubits_per_neuron, seed=seed
        )
        self._qca: FractalQCA | None = None
        self._tick_count = 0
        self._history: list[TickReport] = []
        for nid in neurons or []:
            self._bridge.register(nid)

    @property
    def quantum_enabled(self) -> bool:
        return self.genome.enabled

    def enable_qca(self, num_cells: int = 8) -> None:
        self._qca = FractalQCA(num_cells=num_cells, seed=self._seed)

    def _run_quantum_step(self) -> TickReport:
        tick = self._tick_count
        signals = self._earth.fetch(tick)

        # Cost the operation before executing (energy gate).
        op = QuantumOperation(
            num_qubits=self._bridge.total_qubits() or 1,
            num_gates=max(self._bridge.summary()["num_neurons"], 1) * 3,
            entanglement_depth=self._bridge.summary()["num_entanglements"],
        )
        power = self._cost.energy_watts(op)

        # ILF adaptive clock (EDD-CVT eq.9).
        self._ilf.coherence_phi = 1.0 - signals.kp  # storm -> lower coherence
        _ = self._ilf.adaptive_clock_rate()

        # Fractal QCA step if enabled.
        if self._qca is not None:
            qca_res = self._qca.step()
            self._ilf.update([qca_res.mean_weight] * 4)

        report = TickReport(
            tick=tick,
            coherence_phi=self._ilf.coherence_phi,
            mean_energy_w=power,
            num_qubits=self._bridge.total_qubits(),
            num_entanglements=self._bridge.summary()["num_entanglements"],
            earth=signals,
        )
        self._history.append(report)
        self._tick_count += 1
        return report

    def tick(self) -> TickReport | None:
        if not self.quantum_enabled:
            return None
        return self._run_quantum_step()

    def run(self, ticks: int = 10) -> list[TickReport]:
        return [r for r in (self.tick() for _ in range(ticks)) if r is not None]

    def report(self) -> dict[str, float]:
        if not self._history:
            return {}
        return {
            "mean_coherence_phi": float(
                sum(r.coherence_phi for r in self._history) / len(self._history)
            ),
            "mean_energy_w": float(
                sum(r.mean_energy_w for r in self._history) / len(self._history)
            ),
            "ticks": len(self._history),
        }
