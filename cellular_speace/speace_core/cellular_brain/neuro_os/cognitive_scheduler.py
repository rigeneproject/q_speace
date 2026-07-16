"""CognitiveScheduler — adaptive Neuro-OS scheduling layer for SPEACE.

Unifies SubsystemScheduler, UtilityArbitrationEngine, and CircadianScheduler
into a single adaptive scheduler that uses:
  - prediction error (salience)
  - coherence delta (system tension)
  - metabolic urgency
  - circadian phase
  - ILF field state

as scheduling inputs instead of fixed phase order.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from speace_core.cellular_brain.regulation.utility_drive_system import UtilityDriveSystem
from speace_core.cellular_brain.regulation.utility_arbitration_engine import (
    UtilityArbitrationEngine,
)
from speace_core.runtime.circadian_scheduler import CircadianScheduler


@dataclass
class ModulePriority:
    """Priority assignment for a single module at a given tick."""
    module_id: str
    base_weight: float = 0.0
    salience_boost: float = 0.0
    metabolic_boost: float = 0.0
    coherence_boost: float = 0.0
    circadian_boost: float = 0.0

    @property
    def effective_weight(self) -> float:
        return max(0.0, min(1.0,
            self.base_weight
            + self.salience_boost
            + self.metabolic_boost
            + self.coherence_boost
            + self.circadian_boost
        ))


@dataclass
class SchedulingDecision:
    """Output of the CognitiveScheduler for one tick cycle."""
    module_order: List[str]
    module_priorities: Dict[str, ModulePriority]
    dominant_drive: str
    circadian_phase: str
    system_tension: float
    prediction_error: float
    skipped_modules: List[str] = field(default_factory=list)

    def should_run(self, module_id: str) -> bool:
        return module_id not in self.skipped_modules

    def priority_of(self, module_id: str) -> float:
        mp = self.module_priorities.get(module_id)
        return mp.effective_weight if mp else 0.0


class CognitiveScheduler:
    """Adaptive cognitive scheduler for SPEACE Neuro-OS.

    Replaces the fixed-phase SubsystemScheduler with a dynamic scheduler
    where module execution order is determined by:
      1. Base drive weights (UtilityArbitrationEngine)
      2. Salience (prediction error from predictive coding)
      3. System tension (delta coherence)
      4. Metabolic urgency (energy level)
      5. Circadian phase (awake/sleep/consolidation)
      6. ILF field coherence (if available)
    """

    # Modules that must always run regardless of priority
    CRITICAL_MODULES: set = {
        "homeostasis_engine",
        "emergency_halt_gate",
        "brainstem_controller",
    }

    # Module categories for scheduling
    MODULE_CATEGORIES: Dict[str, str] = {
        "neural_core": "core",
        "homeostasis": "regulation",
        "regional": "core",
        "defense": "protection",
        "memory": "cognition",
        "evolution": "growth",
        "metabolism": "regulation",
        "persistence": "maintenance",
        "self_improvement": "growth",
        "organism": "integration",
        "cyber_physical": "embodiment",
        "world_model": "cognition",
        "action_governance": "protection",
        "snapshot": "maintenance",
    }

    # Default salience thresholds per category (overridden by genome)
    CATEGORY_SALIENCE_THRESHOLDS: Dict[str, float] = {
        "core": 0.0,
        "regulation": 0.0,
        "protection": 0.1,
        "cognition": 0.15,
        "growth": 0.2,
        "maintenance": 0.3,
        "integration": 0.1,
        "embodiment": 0.2,
    }

    def __init__(
        self,
        drive_system: Optional[UtilityDriveSystem] = None,
        arbitration_engine: Optional[UtilityArbitrationEngine] = None,
        circadian_scheduler: Optional[CircadianScheduler] = None,
        tick_interval: float = 1.0,
    ) -> None:
        self.drive_system = drive_system or UtilityDriveSystem()
        self.arbitration = arbitration_engine or UtilityArbitrationEngine(
            drive_system=self.drive_system
        )
        self.circadian = circadian_scheduler or CircadianScheduler()

        self._tick_interval = tick_interval
        self._tick_count: int = 0

        # Module registry: module_id -> callable
        self._modules: Dict[str, Callable[[Any], Any]] = {}

        # Previous coherence for delta computation
        self._prev_coherence: float = 0.5

        # Scheduling history for trend analysis (last 100)
        self._history: List[Dict[str, Any]] = []
        self._max_history: int = 100

        # Salience memory: decaying trace of prediction errors
        self._salience_trace: float = 0.0
        self._salience_decay: float = 0.9

        # Module skip counter for load shedding
        self._module_skip_counters: Dict[str, int] = {}

    # ------------------------------------------------------------------ #
    # Registration
    # ------------------------------------------------------------------ #

    def register_module(
        self,
        module_id: str,
        callable_fn: Callable[[Any], Any],
        category: Optional[str] = None,
    ) -> None:
        category = category or self.MODULE_CATEGORIES.get(module_id, "cognition")
        self._modules[module_id] = callable_fn

    def unregister_module(self, module_id: str) -> None:
        self._modules.pop(module_id, None)

    # ------------------------------------------------------------------ #
    # Tick
    # ------------------------------------------------------------------ #

    def tick(
        self,
        *,
        prediction_error: float = 0.0,
        coherence: float = 0.5,
        energy: float = 1.0,
        noise_level: float = 0.0,
        novelty_score: float = 0.0,
        curiosity_score: float = 0.0,
        metabolism_cost: float = 0.0,
        causal_model_uncertainty: float = 0.0,
        dialogue_recency: float = 0.0,
        distributed_node_count: int = 0,
        endogenous_bonus: float = 0.0,
        ilf_coherence: Optional[float] = None,
        context: Any = None,
    ) -> SchedulingDecision:
        """Run one scheduling cycle.

        Args:
            prediction_error: Current prediction error (from predictive coding).
            coherence: Current system coherence (from homeostasis).
            energy: Current energy level.
            noise_level: Current noise level.
            novelty_score: Novelty detection score.
            curiosity_score: Curiosity drive input.
            metabolism_cost: Current metabolic cost.
            causal_model_uncertainty: Causal model uncertainty.
            dialogue_recency: Recent dialogue activity.
            distributed_node_count: Number of distributed nodes.
            endogenous_bonus: Endogenous curiosity bonus.
            ilf_coherence: ILF field coherence (if available).
            context: Opaque context passed to module callables.

        Returns a SchedulingDecision for this tick.
        """
        self._tick_count += 1

        # --- Circadian phase ---
        circadian_phase = self.circadian.tick()

        # --- Update drives ---
        drives = self.drive_system.tick(
            curiosity_score=curiosity_score,
            novelty_score=novelty_score,
            prediction_error=prediction_error,
            coherence=coherence,
            noise_level=noise_level,
            energy=energy,
            circadian_phase=circadian_phase,
            dialogue_recency=dialogue_recency,
            distributed_node_count=distributed_node_count,
            metabolism_cost=metabolism_cost,
            causal_model_uncertainty=causal_model_uncertainty,
            endogenous_bonus=endogenous_bonus,
        )
        dominant_drive = self.drive_system.get_dominant_drive()

        # --- System tension (delta coherence) ---
        system_tension = abs(coherence - self._prev_coherence)
        self._prev_coherence = coherence

        # --- Salience trace (decaying prediction error) ---
        self._salience_trace = (
            self._salience_decay * self._salience_trace
            + (1.0 - self._salience_decay) * prediction_error
        )

        # --- Compute module priorities ---
        module_priorities: Dict[str, ModulePriority] = {}
        for module_id in self._modules:
            mp = ModulePriority(module_id=module_id)

            # Base weight from arbitration engine
            mp.base_weight = self.arbitration.get_weight(module_id)

            # Salience boost: prediction error drives attention
            mp.salience_boost = prediction_error * 0.3

            # Metabolic boost: low energy prioritises regulation
            if energy < 0.3:
                cat = self.MODULE_CATEGORIES.get(module_id, "cognition")
                if cat in ("regulation", "protection"):
                    mp.metabolic_boost = (1.0 - energy) * 0.4

            # Coherence boost: high system tension prioritises stability
            if system_tension > 0.1:
                cat = self.MODULE_CATEGORIES.get(module_id, "cognition")
                if cat in ("regulation", "protection", "core"):
                    mp.coherence_boost = system_tension * 0.5

            # Circadian boost
            if circadian_phase in ("sleep", "consolidation"):
                cat = self.MODULE_CATEGORIES.get(module_id, "cognition")
                if cat in ("maintenance", "growth"):
                    mp.circadian_boost = 0.2
                elif cat in ("embodiment", "integration"):
                    mp.circadian_boost = -0.1
            elif circadian_phase == "awake":
                cat = self.MODULE_CATEGORIES.get(module_id, "cognition")
                if cat in ("embodiment", "integration", "cognition"):
                    mp.circadian_boost = 0.1

            # ILF field coherence modulates all weights
            if ilf_coherence is not None:
                if ilf_coherence < 0.3:
                    cat = self.MODULE_CATEGORIES.get(module_id, "cognition")
                    if cat in ("regulation", "protection", "core"):
                        mp.base_weight = mp.base_weight * (1.0 + (0.5 - ilf_coherence))

            module_priorities[module_id] = mp

        # --- Determine execution order ---
        sorted_modules = sorted(
            module_priorities.items(),
            key=lambda kv: kv[1].effective_weight,
            reverse=True,
        )

        # --- Determine skipped modules (load shedding) ---
        skipped: List[str] = []
        threshold = self._compute_salience_threshold(drives, energy)
        for module_id, prio in sorted_modules:
            if module_id in self.CRITICAL_MODULES:
                continue
            if prio.effective_weight < threshold and energy < 0.4:
                skipped.append(module_id)

        module_order = [m for m, _ in sorted_modules if m not in skipped]

        # --- Record history ---
        self._history.append({
            "tick": self._tick_count,
            "circadian_phase": circadian_phase,
            "dominant_drive": dominant_drive,
            "system_tension": system_tension,
            "prediction_error": prediction_error,
            "coherence": coherence,
            "energy": energy,
            "salience_trace": self._salience_trace,
            "module_count": len(module_order),
            "skipped_count": len(skipped),
            "module_order": module_order,
        })
        if len(self._history) > self._max_history:
            self._history.pop(0)

        return SchedulingDecision(
            module_order=module_order,
            module_priorities=module_priorities,
            dominant_drive=dominant_drive,
            circadian_phase=circadian_phase,
            system_tension=system_tension,
            prediction_error=prediction_error,
            skipped_modules=skipped,
        )

    # ------------------------------------------------------------------ #
    # Salience threshold
    # ------------------------------------------------------------------ #

    def _compute_salience_threshold(
        self,
        drives: Dict[str, float],
        energy: float,
    ) -> float:
        """Compute dynamic threshold for module skipping.

        When energy is low or stability drive is high, raise threshold
        to skip low-priority modules.
        """
        base = self.CATEGORY_SALIENCE_THRESHOLDS.get("cognition", 0.15)
        energy_penalty = max(0.0, (0.5 - energy)) * 0.3
        stability_boost = drives.get("stability", 0.0) * 0.1
        return base + energy_penalty + stability_boost

    # ------------------------------------------------------------------ #
    # Module execution
    # ------------------------------------------------------------------ #

    def run_scheduled_modules(
        self,
        decision: SchedulingDecision,
        context: Any = None,
    ) -> Dict[str, Any]:
        """Execute modules in scheduled order."""
        results: Dict[str, Any] = {}
        for module_id in decision.module_order:
            fn = self._modules.get(module_id)
            if fn is not None:
                try:
                    results[module_id] = fn(context)
                except Exception as exc:
                    results[module_id] = {"error": str(exc)}
        return results

    # ------------------------------------------------------------------ #
    # Queries
    # ------------------------------------------------------------------ #

    @property
    def tick_count(self) -> int:
        return self._tick_count

    def get_drive(self, name: str) -> float:
        return self.drive_system.get_drive(name)

    def get_dominant_drive(self) -> str:
        return self.drive_system.get_dominant_drive()

    def snapshot(self) -> Dict[str, Any]:
        return {
            "tick": self._tick_count,
            "circadian_phase": self.circadian.phase,
            "dominant_drive": self.drive_system.get_dominant_drive(),
            "drives": {
                name: self.drive_system.get_drive(name)
                for name in UtilityDriveSystem.DRIVE_NAMES
            },
            "salience_trace": self._salience_trace,
            "prev_coherence": self._prev_coherence,
            "module_count": len(self._modules),
            "modules": list(self._modules.keys()),
            "history_sample": self._history[-20:] if self._history else [],
        }

    def get_scheduling_stats(self) -> Dict[str, Any]:
        """Return summary statistics about recent scheduling."""
        if not self._history:
            return {}
        recent = self._history[-50:]
        avg_tension = sum(h["system_tension"] for h in recent) / len(recent)
        avg_skipped = sum(h["skipped_count"] for h in recent) / len(recent)
        return {
            "average_system_tension": avg_tension,
            "average_skipped_modules": avg_skipped,
            "current_circadian_phase": self.circadian.phase,
            "salience_trace": self._salience_trace,
        }

    def shutdown(self) -> None:
        """Graceful shutdown of all scheduled subsystems."""
        self._history.clear()
