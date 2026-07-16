from typing import Any, Dict, List


class WasteClearanceEngine:
    def __init__(
        self,
        scan_interval_ticks: int = 50,
        clearance_cost: float = 0.01,
        max_waste_before_forced: float = 0.3,
    ):
        self._scan_interval = scan_interval_ticks
        self._clearance_cost = clearance_cost
        self._max_waste_before_forced = max_waste_before_forced
        self._pending_waste: float = 0.0
        self._total_cleared: float = 0.0
        self._tick: int = 0
        self._waste_log: List[Dict[str, float]] = []

    @property
    def pending_waste(self) -> float:
        return self._pending_waste

    def add_waste(self, amount: float) -> None:
        self._pending_waste = min(1.0, self._pending_waste + amount)

    def tick(self, orchestrator: Any = None) -> float:
        self._tick += 1
        cleared = 0.0

        if self._tick % self._scan_interval != 0 and self._pending_waste < self._max_waste_before_forced:
            return 0.0

        if orchestrator is not None:
            cleared = self._run_clearance(orchestrator)
        else:
            cleared = self._basic_clearance()

        self._total_cleared += cleared
        self._pending_waste = max(0.0, self._pending_waste - cleared)

        self._waste_log.append({
            "tick": self._tick,
            "pending_before": self._pending_waste + cleared,
            "cleared": cleared,
            "pending_after": self._pending_waste,
        })
        if len(self._waste_log) > 1000:
            self._waste_log = self._waste_log[-1000:]

        return cleared

    def _run_clearance(self, orchestrator: Any) -> float:
        cleared = 0.0
        energy = getattr(orchestrator, "_metabolic_cycle", None)
        available = energy.current_energy if energy else 1.0

        if available < self._clearance_cost:
            return 0.0

        memory = getattr(orchestrator, "_memory", None)
        if memory is not None:
            history = getattr(memory, "history", [])
            if len(history) > 50:
                removed = 0
                while len(history) > 50 and removed < 10:
                    try:
                        history.pop(0)
                        removed += 1
                    except IndexError:
                        break
                cleared += removed * 0.002

        circuit = getattr(orchestrator, "circuit", None)
        if circuit is not None:
            synapses = getattr(circuit, "synapses", [])
            pruned = [s for s in synapses if getattr(s, "state", "") == "pruned"]
            removed_pruned = 0
            for s in pruned[:20]:
                try:
                    synapses.remove(s)
                    removed_pruned += 1
                except ValueError:
                    pass
            cleared += removed_pruned * 0.001

        return min(self._pending_waste, cleared, self._clearance_cost * 10)

    def _basic_clearance(self) -> float:
        if self._pending_waste <= 0.01:
            return self._pending_waste
        return min(self._pending_waste, self._clearance_cost)

    def snapshot(self) -> Dict[str, float]:
        return {
            "pending_waste": self._pending_waste,
            "total_cleared": self._total_cleared,
            "last_clearance": self._waste_log[-1]["cleared"] if self._waste_log else 0.0,
            "scan_interval": self._scan_interval,
        }
