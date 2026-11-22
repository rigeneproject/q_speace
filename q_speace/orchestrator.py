"""QuantumOrchestrator — top-level Q-SPEACE runtime (task T7/T8).

Mirrors the ``quantum_enabled`` / ``_run_quantum_step`` hook pattern from
cellular speace's CellularBrainOrchestrator, but standalone. It wires the
quantum kernel, neural bridge, energy cost model, ILF, earth feed,
fractal QCA and radio frontend (SDR, metasurface, compliance) into a
single tick loop with an explicit human/energy gate.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

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

if TYPE_CHECKING:
    from .aacm import CentralityGraph, FractureMap, StepDecision


class _AACMControllerProtocol(Protocol):
    def step(self, graph: CentralityGraph, fracture_map: FractureMap) -> object: ...


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
    # AACM extension (T-AACM-SPEC §4.1): strategy tag emitted by an
    # optional :class:`q_speace.aacm.AACMController`. ``"default"`` when
    # no controller is attached. ``aacm_omega`` mirrors the controller's
    # resilience distribution; ``aacm_central_node`` is the top
    # betweenness node when strategy is ``central_hit``.
    aacm_strategy: str = "default"
    aacm_omega: float = 1.0
    aacm_central_node: str | None = None


class QuantumOrchestrator:
    """Runs the Q-SPEACE quantum layer with an energy/coherence gate."""

    def __init__(
        self,
        genome: QuantumGeneSet | None = None,
        neurons: list[str] | None = None,
        enable_earth: bool = False,
        seed: int | None = None,
        max_energy_w: float = 250.0,
        coherence_phi_threshold: float = 0.05,
        enable_radio: bool = False,
        enable_metasurface: bool = False,
        enable_spikes: bool = False,
        spike_k: float = 3.0,
        spike_beta: float = 0.0,
    ) -> None:
        if not math.isfinite(max_energy_w) or max_energy_w < 0.0:
            raise ValueError(f"max_energy_w must be finite and >= 0 (got {max_energy_w})")
        if not math.isfinite(coherence_phi_threshold) or not (
            0.0 <= coherence_phi_threshold <= 1.0
        ):
            raise ValueError(
                f"coherence_phi_threshold must be finite and in [0, 1] (got {coherence_phi_threshold})"
            )
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
        # AACM extension (T-AACM-SPEC §4.1): an optional controller
        # that emits a strategy tag for each tick. ``None`` means
        # the orchestrator runs without AACM, and the TickReport
        # falls back to ``aacm_strategy="default"``.
        self._aacm_controller: _AACMControllerProtocol | None = None
        # T-AACM-LOOP §C2: optional AACMLoop reference. The loop is
        # NOT auto-invoked; the orchestrator only EXPOSES the
        # ``attached_loop`` property so external code (CLI, tests)
        # can ask "is there a loop on this orchestrator?" and
        # optionally drive it. This is opt-in and side-effect-free
        # at construction time.
        self._attached_loop: object | None = None

    def attach_loop(self, loop: object) -> None:
        """Attach an :class:`q_speace.aacm.AACMLoop` for observation.

        The orchestrator does NOT invoke the loop. The loop must be
        driven externally (e.g. ``python -m q_speace.aacm.loop`` or
        ``loop.run()``). The orchestrator just holds the reference
        so other components can ask whether a loop is attached.
        """
        self._attached_loop = loop

    def detach_loop(self) -> object | None:
        """Detach the loop, returning the previous reference (or None)."""
        prev = self._attached_loop
        self._attached_loop = None
        return prev

    @property
    def attached_loop(self) -> object | None:
        """The loop attached via :meth:`attach_loop`, or None."""
        return self._attached_loop

    @property
    def quantum_enabled(self) -> bool:
        return self.genome.enabled

    def enable_qca(self, num_cells: int = 8) -> None:
        self._qca = FractalQCA(num_cells=num_cells, seed=self._seed or 0)

    def attach_aacm(self, controller: _AACMControllerProtocol | None) -> None:
        """Attach an :class:`q_speace.aacm.AACMController`.

        The controller is queried at every tick to produce a strategy
        tag. Attaching ``None`` is a no-op (and the default state).
        """
        self._aacm_controller = controller

    def detach_aacm(self) -> None:
        """Remove any attached AACM controller."""
        self._aacm_controller = None

    def _aacm_tick(self, report: TickReport) -> StepDecision:
        """Run one AACM decision for the current tick.

        Builds a :class:`q_speace.aacm.CentralityGraph` over the
        orchestrator's instrument nodes and a :class:`FractureMap`
        from the current EM / coherence state, then asks the
        controller for a decision. Returns a
        :class:`q_speace.aacm.StepDecision`.
        """
        # Local import to keep the orchestrator importable without
        # the AACM package (numpy-only invariant).
        from .aacm import (
            AACMStrategy,
            CentralityGraph,
            FractureMap,
            StepDecision,
        )

        nodes = ("sensor", "modulator", "sdr", "metasurface", "qca", "bridge")
        # Edges encode the call graph of _run_quantum_step.
        edges = (
            ("sensor", "modulator", 0.8),
            ("modulator", "sdr", 0.7),
            ("modulator", "metasurface", 0.5),
            ("bridge", "qca", 0.6),
            ("qca", "modulator", 0.4),
            ("bridge", "sensor", 0.3),
        )
        graph = CentralityGraph(
            nodes=nodes,
            edges=edges,
            controlled_share=report.coherence_phi,
            timestamp=float(report.tick),
        )
        # FractureMap proxy: low spectrum quality = high fracture
        # magnitude on the EM axis.
        spectrum_quality = float(getattr(report.spectrum, "quality_index", 1.0))
        em_fracture = max(0.0, 1.0 - spectrum_quality)
        fracture_map = FractureMap(
            magnitudes={
                "EM_quality": em_fracture,
                "coherence_phi": max(0.0, 1.0 - report.coherence_phi),
            },
            leverage_multiplier=1.5 if em_fracture > 0.5 else 1.0,
        )
        controller = self._aacm_controller
        if controller is None:
            raise RuntimeError("AACM tick invoked without an attached controller")
        decision = controller.step(graph, fracture_map)
        # Defensive: if a foreign controller returns a plain dict, wrap it.
        if not isinstance(decision, StepDecision):
            resilience = getattr(controller, "resilience", None)
            return StepDecision(
                strategy=AACMStrategy.DEFAULT,
                central_node=None,
                aacm_omega=float(getattr(resilience, "omega", 1.0)),
                recommended_redirect=None,
                notes={"foreign_decision": str(decision)},
            )
        return decision

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
        if not self._cost.passes_sevo(delta_utility, delta_s_info):
            gate_blocked = True

        tx_report: dict[str, object] | None = None
        # Execute only if gate is open (energy, coherence, and Sevo all passed).
        if not gate_blocked:
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

            # --- Act: transmit Q* via EM (Strato 2/3) only when radio is enabled ---
            if self._radio_enabled:
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
        # AACM: if a controller is attached, query it for a strategy
        # tag. The controller does not perform any action; it only
        # describes the strategic posture of this tick.
        if self._aacm_controller is not None:
            aacm_decision = self._aacm_tick(report)
            report.aacm_strategy = aacm_decision.strategy.value
            report.aacm_omega = aacm_decision.aacm_omega
            report.aacm_central_node = aacm_decision.central_node
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
