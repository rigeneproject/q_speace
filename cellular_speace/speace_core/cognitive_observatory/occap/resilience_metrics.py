from collections import defaultdict
from typing import Dict, List, Set

from speace_core.cellular_brain.psn.physiological_signal_bus import PhysiologicalSignalBus


class ResilienceMetrics:
    """Computes R(t) — resilience of the organism.

    R = ε₁·completeness + ε₂·(1−recovery_time) + ε₃·damage_resist + ε₄·degeneracy

    Default ε = [0.25, 0.25, 0.20, 0.30]
    """

    def __init__(self, psn: PhysiologicalSignalBus, epsilon: List[float] | None = None):
        self.psn = psn
        self.epsilon = epsilon if epsilon is not None else [0.25, 0.25, 0.20, 0.30]

    def compute(self, tick: int) -> float:
        snap = self.psn.snapshot(tick)
        phys = self.psn.physiome

        # completeness: fraction of constitutional signals actively streaming
        constitutional = set(phys.constitutional_signals.keys())
        active = set(snap.streams.keys())
        completeness = 0.0
        if constitutional:
            completeness = len(active & constitutional) / len(constitutional)

        # recovery_time: from meta-signals or estimate (inverted)
        recovery_ticks = snap.meta_signals.get("avg_recovery_ticks", 10.0)
        recovery_time = 1.0 - min(1.0, recovery_ticks / 50.0)

        # damage_resist: from estimates
        damage = snap.estimates.get("damage_level", 0.0)
        damage_resist = 1.0 - max(0.0, min(1.0, damage))

        # degeneracy: overlap in tissue function (same signal produced/consumed by multiple tissues)
        degeneracy = self._compute_degeneracy(phys)

        R = (
            self.epsilon[0] * completeness
            + self.epsilon[1] * recovery_time
            + self.epsilon[2] * damage_resist
            + self.epsilon[3] * degeneracy
        )
        return round(max(0.0, min(1.0, R)), 4)

    @staticmethod
    def _compute_degeneracy(phys) -> float:
        tissues = phys.tissues_by_id or {}
        if not tissues:
            return 0.5

        signal_tissue: Dict[str, Set[str]] = defaultdict(set)
        for tid, tdef in tissues.items():
            for sig in tdef.get("consumes", []):
                signal_tissue[sig].add(tid)
            for sig in tdef.get("produces", []):
                signal_tissue[sig].add(tid)

        if not signal_tissue:
            return 0.5

        overlaps = [len(tissues) for tissues in signal_tissue.values()]
        avg_overlap = sum(overlaps) / len(overlaps)
        # degeneracy = how many tissues per signal on average (normalized to [0,1])
        max_overlap = max(1, len(tissues))
        degeneracy = min(1.0, avg_overlap / max_overlap * 3)
        return degeneracy
