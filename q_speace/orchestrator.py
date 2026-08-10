"""QuantumOrchestrator — top-level Q-SPEACE runtime (task T7/T8).

Mirrors the ``quantum_enabled`` / ``_run_quantum_step`` hook pattern from
cellular speace's CellularBrainOrchestrator, but standalone. It wires the
quantum kernel, neural bridge, energy cost model, ILF, earth feed,
fractal QCA and radio frontend (SDR, metasurface, compliance) into a
single tick loop with an explicit human/energy gate.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import numpy as np

from .earth_feed import EarthFeed, EarthSignals
from .edd_cvt import InformationalLogicalField
from .fractal_qca import FractalQCA
from .genome import QuantumGeneSet
from .metabolism import QuantumCostModel, QuantumOperation
from .quantum import QuantumNeuralBridge
from .radio import (
    ComplianceFilter,
    MetasurfaceController,
    NullSDR,
    RadioEmulator,
    SDRFrontend,
    SpectrumSensor,
    WavefrontModulator,
)
from .spiking import dynamic_spikes, sparsity


@dataclass
class TickReport:
    tick: int
    coherence_phi: float
    mean_energy_w: float
    num_qubits: int
    num_entanglements: int
    earth: EarthSignals
    gate_blocked: bool = False
    sevo: float = 0.0
    tx_report: object | None = None
    spectrum: object | None = None
    num_spikes: int = 0
    sparsity: float = 1.0


class QuantumOrchestrator:
    """Runs the Q-SPEACE quantum layer with an energy/coherence gate."""

    def __init__(
        self,
        genome: QuantumGeneSet | None = None,
        neurons: list[str] | None = None,
        enable_earth: bool = False,
        seed: int | None = None,
        max_energy_w: float = 10.0,
        coherence_phi_threshold: float = 0.05,
        enable_radio: bool = False,
        enable_metasurface: bool = False,
        enable_spikes: bool = False,
        spike_k: float = 3.0,
        spike_beta: float = 0.0,
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
        self._max_energy_w = max_energy_w
        self._coherence_phi_threshold = coherence_phi_threshold
        self._energy_budget_remaining = max_energy_w
        self._radio_enabled = enable_radio
        self._enable_spikes = enable_spikes
        self._spike_k = spike_k
        self._spike_beta = spike_beta
        self._spike_history: deque[int] = deque(maxlen=64)
        sdr: SDRFrontend = NullSDR(_seed=seed)
        self._sdr = sdr
        self._sensor = SpectrumSensor(sdr=sdr, seed=seed)
        self._modulator = WavefrontModulator(seed=seed)
        self._compliance = ComplianceFilter()
        self._emulator = RadioEmulator(compliance=self._compliance)
        self._metasurface: MetasurfaceController | None = (
            MetasurfaceController(seed=seed) if enable_metasurface else None
        )
        self._neuron_ids = list(neurons or [])
        for nid in self._neuron_ids:
            self._bridge.register(nid)
            self._ilf.register_agent(nid, weight=1.0)

    @property
    def quantum_enabled(self) -> bool:
        return self.genome.enabled

    def enable_qca(self, num_cells: int = 8) -> None:
        self._qca = FractalQCA(num_cells=num_cells, seed=self._seed or 0)

    def _refresh_activity(self, tick: int) -> np.ndarray:
        """Provide deterministic classical activity for opt-in spike costing."""
        count = len(self._neuron_ids)
        if count == 0:
            return np.empty(0, dtype=float)
        rng = np.random.default_rng((self._seed or 0) + tick)
        base = rng.uniform(0.0, 1.0, size=count) ** (1.0 / (1.0 + self._ilf.coherence_phi))
        boost = 1.0 + 0.5 * self._bridge.summary()["num_entanglements"] / count
        activity = base * boost
        self._bridge.set_activity(activity)
        return self._bridge.activity

    def _run_quantum_step(self) -> TickReport:
        tick = self._tick_count
        signals = self._earth.fetch(tick)

        # --- Sense: EM environment (Strato 2/3) ---
        spectrum = self._sensor.sense()

        # ILF adaptive clock (EDD-CVT eq.9), modulated by EM quality.
        noise_factor = max(0.0, min(1.0 - spectrum.quality_index, 1.0))
        self._ilf.coherence_phi = max(0.0, (1.0 - signals.kp) - noise_factor * 0.3)
        self._ilf.adaptive_clock_rate()

        num_spikes = 0
        activity_sparsity = 1.0
        if self._enable_spikes and self._neuron_ids:
            activity = self._refresh_activity(tick)
            encoded = dynamic_spikes(
                activity.reshape(1, -1),
                k=self._spike_k,
                coherence_phi=self._ilf.coherence_phi,
                beta=self._spike_beta,
            )
            num_spikes = encoded.num_spikes
            activity_sparsity = sparsity(encoded.spikes)
            self._spike_history.append(num_spikes)

        # Cost the operation before executing (energy gate).
        op = QuantumOperation(
            num_qubits=self._bridge.total_qubits() or 1,
            num_gates=max(self._bridge.summary()["num_neurons"], 1) * 3,
            entanglement_depth=self._bridge.summary()["num_entanglements"],
            decoherence_budget=1.0 - self._ilf.coherence_phi,
            num_spikes=num_spikes,
        )
        power = self._cost.energy_watts(op)

        # Energy gate: block if power exceeds budget or coherence too low.
        gate_blocked = False
        if power > self._energy_budget_remaining:
            gate_blocked = True
        if self._ilf.coherence_phi < self._coherence_phi_threshold:
            gate_blocked = True

        # Compute Sevo for the step.
        delta_s_info = abs(signals.kp - 0.5) + 0.01  # proxy entropy change
        delta_utility = self._ilf.coherence_phi
        sevo = self._cost.sevo(delta_utility, delta_s_info)

        tx_report: dict[str, object] | None = None
        # Execute only if gate is open.
        if not gate_blocked and self._cost.passes_sevo(delta_utility, delta_s_info):
            if self._qca is not None:
                qca_res = self._qca.step(delta_s_info=delta_s_info)
                self._ilf.update(np.full(4, qca_res.mean_weight))
                for i, nid in enumerate(self._neuron_ids):
                    cell_idx = i % self._qca.num_cells
                    weight = float(self._qca.weights[cell_idx])
                    belief = np.array([weight, 1.0 - weight])
                    self._ilf.set_belief(nid, belief)
                    self._ilf.set_weight(nid, weight)
            self._energy_budget_remaining -= power

            # --- Act: transmit Q* via EM (Strato 2/3) ---
            q_star = self._ilf.compute_q_star()
            waveform = self._modulator.encode_q_star(
                q_star, confidence=max(self._ilf.coherence_phi, 0.01)
            )
            if self._metasurface is not None and self._metasurface.is_active:
                waveform = self._metasurface.beamform(
                    waveform, azimuth_deg=float(self._tick_count % 360)
                )
            compliance = self._emulator.validate(waveform)
            if compliance.passed:
                tx_report_ = self._sdr.transmit(waveform)
                tx_report = {
                    "power_dbm": tx_report_.power_dbm,
                    "frequency_hz": tx_report_.frequency_hz,
                    "compliance": True,
                }
            else:
                tx_report = {
                    "power_dbm": 0.0,
                    "frequency_hz": 0.0,
                    "compliance": False,
                    "reason": compliance.message,
                }
        else:
            # Throttle: energy budget recharges fractionally when blocked.
            self._energy_budget_remaining = min(
                self._max_energy_w,
                self._energy_budget_remaining + self._max_energy_w * 0.1,
            )

        report = TickReport(
            tick=tick,
            coherence_phi=self._ilf.coherence_phi,
            mean_energy_w=power,
            num_qubits=self._bridge.total_qubits(),
            num_entanglements=self._bridge.summary()["num_entanglements"],
            earth=signals,
            gate_blocked=gate_blocked,
            sevo=sevo,
            tx_report=tx_report,
            spectrum=spectrum,
            num_spikes=num_spikes,
            sparsity=activity_sparsity,
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

    def report(self) -> dict[str, object]:
        if not self._history:
            return {}
        blocked = sum(1 for r in self._history if r.gate_blocked)
        return {
            "mean_coherence_phi": float(
                sum(r.coherence_phi for r in self._history) / len(self._history)
            ),
            "mean_energy_w": float(
                sum(r.mean_energy_w for r in self._history) / len(self._history)
            ),
            "ticks": len(self._history),
            "gate_blocked_ratio": blocked / len(self._history),
            "mean_num_spikes": float(sum(r.num_spikes for r in self._history) / len(self._history)),
            "mean_sparsity": float(sum(r.sparsity for r in self._history) / len(self._history)),
        }
