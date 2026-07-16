from typing import List

from speace_core.cellular_brain.psn.physiological_signal_bus import PhysiologicalSignalBus


class IntegrationMetrics:
    """Computes I(t) — integration quality of the PSN dual-bus.

    I = α₁·bus_util + α₂·cross_corr + α₃·(1−delay) + α₄·occupancy + α₅·coverage

    Default α = [0.30, 0.20, 0.15, 0.15, 0.20]
    """

    def __init__(self, psn: PhysiologicalSignalBus, alpha: List[float] | None = None):
        self.psn = psn
        self.alpha = alpha if alpha is not None else [0.30, 0.20, 0.15, 0.15, 0.20]

    def compute(self, tick: int) -> float:
        snap = self.psn.snapshot(tick)
        phys = self.psn.physiome

        # bus_util: fraction of registered constitutional signals currently streaming
        constitutional = set(phys.constitutional_signals.keys())
        active = set(snap.streams.keys())
        bus_util = 0.0
        if constitutional:
            bus_util = len(active & constitutional) / len(constitutional)

        # cross_corr: active-signal diversity / total possible
        total_sigs = max(len(constitutional), 1)
        cross_corr = len(active) / total_sigs if total_sigs else 0.5

        # delay: synaptic latency proxy — lower is better
        n_synapses = len(snap.neural_synapses)
        delay = min(1.0, n_synapses / (total_sigs * 5 + 1)) if total_sigs else 0.1

        # occupancy: receptor occupancy from meta-signals
        occupancy = snap.meta_signals.get("receptor_occupancy", 0.5)

        # coverage: fraction of organs that have at least one active signal
        coverage = 0.5
        organ_signals = snap.meta_signals.get("organ_coverage")
        if organ_signals is not None:
            coverage = min(1.0, max(0.0, organ_signals))
        else:
            n_organs = max(len(phys.organs or {}), 1)
            covered = min(len(active), n_organs)
            coverage = covered / n_organs if n_organs else 0.5

        I = (
            self.alpha[0] * bus_util
            + self.alpha[1] * cross_corr
            + self.alpha[2] * (1.0 - delay)
            + self.alpha[3] * occupancy
            + self.alpha[4] * coverage
        )
        return round(max(0.0, min(1.0, I)), 4)
