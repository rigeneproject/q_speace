from speace_core.cellular_brain.psn.physiological_signal_bus import PhysiologicalSignalBus


class MetabolicMetrics:
    """Computes M(t) — metabolic capacity.

    M = (global_energy / max_energy) × (1 − 0.5 × damage_level)

    Metabolic capacity decreases under damage to reflect the cost
    of repair and stress response. max_energy defaults to 1.0.
    """

    def __init__(self, psn: PhysiologicalSignalBus, max_energy: float = 1.0):
        self.psn = psn
        self.max_energy = max_energy

    def compute(self, tick: int) -> float:
        snap = self.psn.snapshot(tick)
        energy = max(0.0, snap.global_energy)
        M = energy / self.max_energy if self.max_energy > 0 else 0.5

        damage = snap.estimates.get("damage_level", 0.0)
        damage = max(0.0, min(1.0, damage))
        M = M * (1.0 - 0.5 * damage)

        return round(max(0.0, min(1.0, M)), 4)
