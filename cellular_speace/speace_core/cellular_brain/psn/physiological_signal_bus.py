from __future__ import annotations
from collections import deque
from typing import Dict, List, Optional, Tuple, Any

from speace_core.cellular_brain.psn.models import (
    SystemSnapshot,
    SynapseKey,
    TissueMetabolicBudget,
    TissueStatus,
)
from speace_core.cellular_brain.psn.neural_bus import NeuralBus
from speace_core.cellular_brain.psn.endocrine_bus import EndocrineBus
from speace_core.cellular_brain.psn.digital_metabolism import DigitalMetabolism
from speace_core.cellular_brain.psn.physiome import Physiome, ConstitutionalViolationError
from speace_core.cellular_brain.psn.physiological_policy import PolicyEngine

try:
    from speace_core.cellular_brain.psn.homeostatic_controller import HomeostaticController
    _HAS_HOMEOSTATIC = True
except ImportError:
    _HAS_HOMEOSTATIC = False


class PhysiologicalSignalBus:
    """Top-level Physiological Signal Network bus.

    Combines the Neural Bus, Endocrine Bus, Digital Metabolism,
    Physiome validation, and Policy Engine into a single interface
    for all digital organs and tissues.
    """

    def __init__(
        self,
        physiome: Physiome,
        auto_register_hormones: bool = True,
        enable_homeostatic_control: bool = True,
        homeostatic_Kp: float = 0.25,
        homeostatic_Kd: float = 0.08,
    ):
        self.physiome = physiome
        self.neural = NeuralBus(receptors=physiome.receptors)
        self.endocrine = EndocrineBus()
        self.metabolism = DigitalMetabolism()
        self.policies = PolicyEngine(physiome.policies)

        self._history: deque = deque(maxlen=1000)
        self._current_tick: int = 0
        self._streams: Dict[str, float] = {}
        self._events: Dict[str, List[Any]] = {}
        self._meta_signals: Dict[str, float] = {}
        self._estimates: Dict[str, float] = {}

        if auto_register_hormones:
            self._register_hormones_from_physiome()

        self._register_tissue_budgets_from_physiome()

        # T177 — optional homeostatic PD controller for coherence stabilisation
        self._homeostatic: HomeostaticController | None = None
        if _HAS_HOMEOSTATIC and enable_homeostatic_control:
            try:
                self._homeostatic = HomeostaticController(
                    physiome=physiome, Kp=homeostatic_Kp, Kd=homeostatic_Kd,
                )
            except Exception:
                self._homeostatic = None

    def _register_hormones_from_physiome(self) -> None:
        routing = self.physiome.routing or {}
        endocrine_routes = routing.get("endocrine", {})
        for mol_id, params in endocrine_routes.items():
            self.endocrine.register_pool(
                molecule=mol_id,
                clearance_rate=params.get("clearance_rate", 0.92),
                delay_ticks=params.get("delay_ticks", 2),
                max_concentration=params.get("max_accumulation", 1.0),
                stream=params.get("stream", True),
                event_mode=params.get("event", False),
                event_duration=params.get("event_duration", 0),
                event_decay=params.get("event_decay", 0.80),
            )

    def _register_tissue_budgets_from_physiome(self) -> None:
        tissues = self.physiome.tissues_by_id
        for tid in tissues:
            budget = self.physiome.get_metabolic_budget(tid)
            self.metabolism.register_tissue(tid, budget)

    # ── Tick lifecycle ───────────────────────────────────────────

    def tick_begin(self, tick: int) -> None:
        """Called at the start of each tick: reuptake, clearance, decay."""
        self._current_tick = tick
        self.neural.set_tick(tick)
        self.endocrine.set_tick(tick)
        self.policies.set_tick(tick)

        self.neural.clear_all()
        self.endocrine.decay_all()
        self.metabolism.tick_begin(tick)

        # Apply homeostatic PD corrections to stabilise coherence
        if self._homeostatic is not None:
            corrections = self._homeostatic.compute_corrections(self._streams)
            for sid, delta in corrections.items():
                current = self._streams.get(sid, 0.5)
                self._streams[sid] = max(0.0, min(1.0, current + delta))

    def tick_end(self, tick: int) -> None:
        """Called at end of each tick: log snapshot."""
        self.metabolism.tick_end(tick)
        self._history.append(self.snapshot(tick))

    # ── Stream operations ────────────────────────────────────────

    def publish_stream(
        self,
        signal_id: str,
        value: float,
        confidence: float = 0.9,
        source: str = "",
    ) -> None:
        """Publish a continuous stream signal.

        Streams are stored as last-value and also published to the
        appropriate bus (neural or endocrine based on routing).
        """
        if not self.physiome.is_signal_registered(signal_id):
            raise ConstitutionalViolationError(
                f"Signal '{signal_id}' is not registered in the Physiome"
            )

        self._streams[signal_id] = max(0.0, min(1.0, value))

        entry = self.physiome.get_ontology_entry(signal_id)
        if entry is None:
            return

        if entry.bus in ("neural", "both") and entry.molecule:
            for mol in entry.molecule:
                if self.physiome.is_molecule_registered(mol):
                    mol_def = self.physiome.get_molecule(mol)
                    if mol_def and mol_def.get("bus") == "neural":
                        self.neural.synapse(
                            molecule=mol,
                            value=value,
                            source=source or "stream",
                            target=source or "broadcast",
                            receptor=mol_def.get("default_receptor", "generic"),
                            confidence=confidence,
                        )

        if entry.bus in ("endocrine", "both") and entry.molecule:
            for mol in entry.molecule:
                if self.physiome.is_molecule_registered(mol):
                    self.endocrine.secrete(
                        hormone=mol,
                        concentration=value,
                        source=source or "stream",
                    )

    def read_stream(self, signal_id: str) -> Optional[float]:
        """Read the current value of a stream signal."""
        return self._streams.get(signal_id)

    # ── Event operations ────────────────────────────────────────

    def publish_event(
        self,
        signal_id: str,
        intensity: float,
        source: str = "",
        category: str = "custom",
        duration: int = 0,
        metadata: Optional[Dict] = None,
    ) -> None:
        """Publish a discrete event signal.

        Events are time-stamped and propagated to the appropriate bus.
        """
        if not self.physiome.is_signal_registered(signal_id):
            raise ConstitutionalViolationError(
                f"Signal '{signal_id}' is not registered in the Physiome"
            )

        if signal_id not in self._events:
            self._events[signal_id] = []

        evt = {
            "signal_id": signal_id,
            "intensity": max(0.0, min(1.0, intensity)),
            "source": source,
            "category": category,
            "duration": duration,
            "onset": self._current_tick,
            "metadata": metadata or {},
        }
        self._events[signal_id].append(evt)

        entry = self.physiome.get_ontology_entry(signal_id)
        if entry is None:
            return

        if entry.bus in ("neural", "both") and entry.molecule:
            for mol in entry.molecule:
                mol_def = self.physiome.get_molecule(mol)
                if mol_def and mol_def.get("bus") == "neural":
                    self.neural.synapse(
                        molecule=mol,
                        value=intensity,
                        source=source or "event",
                        target=source or "broadcast",
                        receptor=mol_def.get("default_receptor", "generic"),
                        confidence=0.9,
                        metadata={"event": signal_id, "category": category},
                    )

        if entry.bus in ("endocrine", "both") and entry.molecule:
            for mol in entry.molecule:
                self.endocrine.secrete_event(
                    hormone=mol,
                    intensity=intensity,
                    source=source or "event",
                    duration=entry.event_duration or duration,
                    decay=entry.decay,
                )

    def read_events(self, signal_id: str) -> Optional[List[Dict]]:
        """Read recent events for a signal."""
        return self._events.get(signal_id)

    # ── Molecule-level operations ────────────────────────────────

    def synapse(
        self,
        molecule: str,
        value: float,
        source: str,
        target: str,
        receptor: str,
        confidence: float = 0.9,
    ) -> None:
        """Direct neural synapse (bypasses signal ontology)."""
        if not self.physiome.is_molecule_registered(molecule):
            raise ConstitutionalViolationError(
                f"Molecule '{molecule}' is not registered in the Physiome"
            )
        self.neural.synapse(molecule, value, source, target, receptor, confidence)

    def secrete(
        self,
        hormone: str,
        concentration: float,
        source: str = "",
        clearance_rate: Optional[float] = None,
        delay_ticks: Optional[int] = None,
    ) -> None:
        """Direct endocrine secretion (bypasses signal ontology)."""
        if not self.physiome.is_molecule_registered(hormone):
            raise ConstitutionalViolationError(
                f"Hormone '{hormone}' is not registered in the Physiome"
            )
        self.endocrine.secrete(hormone, concentration, source, clearance_rate, delay_ticks)

    # ── Metabolism helpers ───────────────────────────────────────

    def deduct_metabolic_cost(self, tissue_id: str, cost: float, operation: str = "") -> bool:
        """Deduct metabolic cost for a tissue operation.

        Returns True if the operation is allowed, False if budget exceeded.
        """
        return self.metabolism.deduct(tissue_id, cost, operation)

    def get_tissue_status(self, tissue_id: str) -> TissueStatus:
        return self.metabolism.get_tissue_status(tissue_id)

    # ── Policy helpers ───────────────────────────────────────────

    def evaluate_policy(self, policy_id: str, context: Dict[str, float]) -> Any:
        """Evaluate a physiological policy with current context."""
        return self.policies.get_policy(policy_id, context)

    # ── Meta-signals and estimates ───────────────────────────────

    def set_meta_signal(self, name: str, value: float) -> None:
        self._meta_signals[name] = value

    def get_meta_signal(self, name: str) -> Optional[float]:
        return self._meta_signals.get(name)

    def set_estimate(self, name: str, value: float) -> None:
        self._estimates[name] = value

    def get_estimate(self, name: str) -> Optional[float]:
        return self._estimates.get(name)

    # ── Snapshot ─────────────────────────────────────────────────

    def snapshot(self, tick: Optional[int] = None) -> SystemSnapshot:
        """Capture the full system state at a given tick."""
        return SystemSnapshot(
            tick=tick if tick is not None else self._current_tick,
            neural_synapses=self.neural.snapshot(),
            endocrine_pools=self.endocrine.snapshot(),
            streams=dict(self._streams),
            events=dict(self._events),
            meta_signals=dict(self._meta_signals),
            estimates=dict(self._estimates),
            global_energy=self.metabolism.global_energy,
            temperature=self.metabolism.heat,
            metabolic_demand=self.metabolism.metabolic_demand,
        )

    def stream_snapshot(self) -> Dict[str, float]:
        return dict(self._streams)

    def meta_snapshot(self) -> Dict[str, float]:
        return dict(self._meta_signals)

    def estimate_snapshot(self) -> Dict[str, float]:
        return dict(self._estimates)

    # ── History ──────────────────────────────────────────────────

    @property
    def history(self) -> List[SystemSnapshot]:
        return list(self._history)

    def clear_history(self) -> None:
        self._history.clear()

    @property
    def current_tick(self) -> int:
        return self._current_tick

    @property
    def stream_count(self) -> int:
        return len(self._streams)

    @property
    def event_count(self) -> int:
        return sum(len(v) for v in self._events.values())
