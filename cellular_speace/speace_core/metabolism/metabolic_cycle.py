from typing import Any, Dict, List, Optional

from speace_core.cellular_brain.metabolism.energy_accounting import EnergyAccountingLedger
from speace_core.cellular_brain.metabolism.metabolic_governor import MetabolicGovernor
from speace_core.cellular_brain.metabolism.metabolic_models import MetabolicMode, MetabolicState
from speace_core.cellular_brain.metabolism.metabolic_policy_engine import MetabolicPolicyEngine
from speace_core.metabolism.waste_clearance import WasteClearanceEngine


class MetabolicCycle:
    def __init__(
        self,
        governor: Optional[MetabolicGovernor] = None,
        ledger: Optional[EnergyAccountingLedger] = None,
        waste_clearance: Optional[WasteClearanceEngine] = None,
    ):
        self._governor = governor or MetabolicGovernor()
        self._ledger = ledger or EnergyAccountingLedger()
        self._waste = waste_clearance or WasteClearanceEngine()
        self._current_energy: float = 1.0
        self._tick: int = 0
        self._stats: Dict[str, float] = {
            "total_acquired": 0.0,
            "total_consumed": 0.0,
            "total_waste": 0.0,
            "total_cleared": 0.0,
        }

    @property
    def current_energy(self) -> float:
        return self._current_energy

    @property
    def stats(self) -> Dict[str, float]:
        return dict(self._stats)

    def tick(self, orchestrator: Any = None) -> MetabolicState:
        self._tick += 1

        acquired = self._acquire_energy(orchestrator)
        self._current_energy = min(1.0, self._current_energy + acquired)

        transformed = self._transform_energy(orchestrator)
        self._current_energy = max(0.0, self._current_energy - transformed)

        waste_generated = self._compute_waste(orchestrator)
        self._stats["total_waste"] += waste_generated

        cleared = self._waste.tick(orchestrator)
        self._stats["total_cleared"] += cleared

        self._stats["total_acquired"] += acquired
        self._stats["total_consumed"] += transformed

        if orchestrator is not None:
            metrics = getattr(orchestrator, "latest_metrics", {})
            if isinstance(metrics, dict):
                metrics["mean_energy"] = self._current_energy

        return self._governor.capture_metabolic_state(safety_score=self._current_energy)

    def _acquire_energy(self, orchestrator: Any) -> float:
        acquired = 0.0
        if orchestrator is None:
            return 0.02

        circuit = getattr(orchestrator, "circuit", None)
        if circuit is not None:
            n_input = len(getattr(circuit, "input_neurons", []))
            n_hidden = len(getattr(circuit, "hidden_neurons", []))
            n_syn = len(getattr(circuit, "synapses", []))
            acquired += (n_input + n_hidden) * 0.001
            acquired += n_syn * 0.0005

            for neuron in circuit.input_neurons + circuit.hidden_neurons:
                if getattr(neuron, "activation", 0) > 0.5:
                    acquired += 0.001

        episodic = getattr(orchestrator, "_episodic_memory", None)
        if episodic is not None:
            episodes = getattr(episodic, "episodes", [])
            if len(episodes) > 10:
                delta = len(episodes) - 10
                acquired += delta * 0.002

        semantic = getattr(orchestrator, "_semantic_store", None)
        if semantic is not None:
            assembled = getattr(semantic, "_assemblies", {})
            acquired += len(assembled) * 0.001

        return min(0.15, acquired)

    def _transform_energy(self, orchestrator: Any) -> float:
        if orchestrator is None:
            return 0.01
        consumed = 0.01

        circuit = getattr(orchestrator, "circuit", None)
        if circuit is not None:
            active = sum(
                1 for n in circuit.hidden_neurons + circuit.output_neurons
                if getattr(n, "activation", 0) > 0.1
            )
            consumed += active * 0.002

        return min(0.2, consumed)

    def _compute_waste(self, orchestrator: Any) -> float:
        waste = 0.0
        if orchestrator is None:
            return 0.0

        memory = getattr(orchestrator, "_memory", None)
        if memory is not None:
            history = getattr(memory, "history", [])
            if len(history) > 100:
                waste += (len(history) - 100) * 0.001

        circuit = getattr(orchestrator, "circuit", None)
        if circuit is not None:
            pruned = sum(
                1 for s in getattr(circuit, "synapses", [])
                if getattr(s, "state", "") == "pruned"
            )
            waste += pruned * 0.0005

        return min(0.05, waste)

    def snapshot(self) -> Dict[str, Any]:
        return {
            "tick": self._tick,
            "current_energy": self._current_energy,
            "stats": dict(self._stats),
            "waste_pending": self._waste.pending_waste,
        }
