from __future__ import annotations
from typing import Dict, Optional

from speace_core.cellular_brain.psn.models import TissueMetabolicBudget, TissueStatus


class DigitalMetabolism:
    """Tracks energy budgets, global energy pool, heat generation.

    Every operation has a metabolic cost. Tissues have per-tick budgets.
    When budgets are exceeded, tissues enter low-power or crisis mode.
    """

    def __init__(
        self,
        global_energy: float = 5.0,
        max_energy: float = 10.0,
        base_production_rate: float = 0.05,
        heat_coefficient: float = 0.3,
        cooling_rate: float = 0.02,
        crisis_threshold: float = 0.5,
    ):
        self.global_energy = global_energy
        self.max_energy = max_energy
        self.base_production_rate = base_production_rate
        self.heat_coefficient = heat_coefficient
        self.cooling_rate = cooling_rate
        self.crisis_threshold = crisis_threshold

        self.heat: float = 0.0
        self._tissue_budgets: Dict[str, TissueMetabolicBudget] = {}
        self._tissue_usage: Dict[str, float] = {}
        self._total_demand: float = 0.0
        self._current_tick: int = 0

    def register_tissue(
        self, tissue_id: str, budget: TissueMetabolicBudget
    ) -> None:
        self._tissue_budgets[tissue_id] = budget
        self._tissue_usage[tissue_id] = 0.0

    @property
    def in_crisis(self) -> bool:
        return self.global_energy < self.crisis_threshold

    def deduct(self, tissue_id: str, cost: float, operation: str = "") -> bool:
        """Deduct cost from tissue budget and global energy.

        Returns False if the tissue has exceeded its budget (triggers
        low-power / crisis response).
        """
        budget = self._tissue_budgets.get(tissue_id)
        if budget is None:
            self.global_energy = max(0.0, self.global_energy - cost)
            self.heat += cost * self.heat_coefficient
            return True

        budget.current_usage += cost
        self._tissue_usage[tissue_id] = (
            self._tissue_usage.get(tissue_id, 0.0) + cost
        )
        self._total_demand += cost

        self.global_energy = max(0.0, self.global_energy - cost)
        self.heat += cost * self.heat_coefficient

        return not budget.in_critical

    def get_tissue_status(self, tissue_id: str) -> TissueStatus:
        budget = self._tissue_budgets.get(tissue_id)
        if budget is None:
            return TissueStatus.ACTIVE
        if budget.in_critical:
            return TissueStatus.CRISIS
        if budget.in_low_power:
            return TissueStatus.LOW_POWER
        return TissueStatus.ACTIVE

    def tick_begin(self, tick: int) -> None:
        """Reset per-tick usage counters and apply production/decay."""
        self._current_tick = tick
        self._total_demand = 0.0
        for tid in self._tissue_usage:
            self._tissue_usage[tid] = 0.0
        for budget in self._tissue_budgets.values():
            budget.current_usage = 0.0

        self.global_energy = min(
            self.max_energy,
            self.global_energy + self.base_production_rate,
        )
        self.heat = max(0.0, self.heat - self.cooling_rate)

    def tick_end(self, tick: int) -> None:
        pass

    def reallocate(self, allocations: Dict[str, float]) -> None:
        """Reallocate tissue budgets based on policy (sum of parts = 1.0)."""
        total_budget = sum(
            b.base_budget for b in self._tissue_budgets.values()
        )
        for tissue_id, fraction in allocations.items():
            if tissue_id in self._tissue_budgets:
                self._tissue_budgets[tissue_id].base_budget = (
                    total_budget * fraction
                )

    @property
    def metabolic_demand(self) -> float:
        return self._total_demand

    @property
    def tissue_count(self) -> int:
        return len(self._tissue_budgets)

    def snapshot(self) -> Dict[str, float]:
        return {
            "global_energy": self.global_energy,
            "heat": self.heat,
            "metabolic_demand": self._total_demand,
            "in_crisis": float(self.in_crisis),
        }
