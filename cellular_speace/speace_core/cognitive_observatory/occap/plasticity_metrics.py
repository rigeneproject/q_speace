import math
from typing import List

from speace_core.cellular_brain.psn.physiological_signal_bus import PhysiologicalSignalBus


class PlasticityMetrics:
    """Computes P(t) — plasticity of the organism.

    P = β₁·neuro + β₂·epigenetic + β₃·structural + β₄·functional + β₅·learning

    Default β = [0.25, 0.20, 0.15, 0.15, 0.25]
    """

    BDNF_LIKE_MOLECULES = ["bdnf", "ngf", "neurotrophin"]

    def __init__(self, psn: PhysiologicalSignalBus, beta: List[float] | None = None):
        self.psn = psn
        self.beta = beta if beta is not None else [0.25, 0.20, 0.15, 0.15, 0.25]

    def compute(self, tick: int) -> float:
        snap = self.psn.snapshot(tick)

        # neuro: BDNF-like molecule concentration in endocrine pool
        neuro = 0.3
        bdnf_pool = None
        for mol in self.BDNF_LIKE_MOLECULES:
            if mol in snap.endocrine_pools:
                bdnf_pool = snap.endocrine_pools[mol]
                break
        if bdnf_pool is not None:
            neuro = min(1.0, bdnf_pool)

        # epigenetic: active epigenetic modification count (normalized)
        epi_signals = self.psn.physiome.epigenetic_signals or {}
        n_epi = len(epi_signals)
        epi_active = sum(
            1 for sid in epi_signals if sid in snap.streams or sid in (
                e.get("signal_id", "") for evts in snap.events.values() for e in evts
            )
        )
        epigenetic = min(1.0, epi_active / max(n_epi, 1)) if n_epi else 0.3

        # structural: from growth rules
        growth = self.psn.physiome.growth_rules or {}
        growth_rate = growth.get("default_growth_rate", 0.01) if isinstance(growth, dict) else 0.01
        structural = min(1.0, max(0.0, growth_rate * 20))

        # functional: coeff of variation of stream signals (more variation = more plastic)
        stream_vals = list(snap.streams.values())
        if len(stream_vals) > 1:
            mean = sum(stream_vals) / len(stream_vals)
            if abs(mean) > 1e-6:
                var = sum((v - mean) ** 2 for v in stream_vals) / len(stream_vals)
                functional = min(1.0, math.sqrt(var) / abs(mean))
            else:
                functional = 0.3
        else:
            functional = 0.3

        # learning: from PBM learning_rate estimate
        learning = snap.estimates.get("learning_rate", 0.5)
        learning = max(0.0, min(1.0, learning))

        P = (
            self.beta[0] * neuro
            + self.beta[1] * epigenetic
            + self.beta[2] * structural
            + self.beta[3] * functional
            + self.beta[4] * learning
        )
        return round(max(0.0, min(1.0, P)), 4)
