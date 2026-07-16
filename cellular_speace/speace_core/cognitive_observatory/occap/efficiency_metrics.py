from __future__ import annotations

from typing import TYPE_CHECKING

from speace_core.cellular_brain.psn.physiological_signal_bus import PhysiologicalSignalBus

if TYPE_CHECKING:
    from speace_core.cognitive_observatory.occap.occap_calculator import OCCapState


class EfficiencyMetrics:
    """Computes OCEff(t) — Organismic Cognitive Efficiency.

    OCEff = OCCap / (total_energy + 0.01·ticks + damage_penalty)

    where damage_penalty = 1 + 10·damage.
    """

    def __init__(self, psn: PhysiologicalSignalBus):
        self.psn = psn

    def compute(self, state: OCCapState, tick: int) -> float:
        snap = self.psn.snapshot(tick)

        total_energy = max(0.0, snap.global_energy)
        # Use a small epsilon to avoid division by zero
        energy_term = 1.0 if total_energy < 0.01 else total_energy

        time_cost = 0.01 * tick

        damage = snap.estimates.get("damage_level", 0.0)
        damage_penalty = 1.0 + 10.0 * max(0.0, min(1.0, damage))

        denominator = energy_term + time_cost + damage_penalty
        if denominator <= 0:
            return 0.0

        oceff = state.occap / denominator
        return round(max(0.0, min(10.0, oceff)), 4)
