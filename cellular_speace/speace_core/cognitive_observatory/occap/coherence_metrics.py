import math
from typing import List

from speace_core.cellular_brain.psn.physiological_signal_bus import PhysiologicalSignalBus


class CoherenceMetrics:
    """Computes Φₒ(t) — organismic coherence under perturbation.

    Φₒ = γ₁·prediction + γ₂·recovery + γ₃·stability + γ₄·synchrony + γ₅·reallocation

    Default γ = [0.30, 0.20, 0.20, 0.15, 0.15]
    """

    def __init__(self, psn: PhysiologicalSignalBus, gamma: List[float] | None = None):
        self.psn = psn
        self.gamma = gamma if gamma is not None else [0.30, 0.20, 0.20, 0.15, 0.15]
        self._prev_streams: dict = {}
        self._stability_buffer: list = []

    def compute(self, tick: int) -> float:
        snap = self.psn.snapshot(tick)

        # prediction: inverted prediction error from PBM estimates
        pred_error = snap.estimates.get("prediction_error", 0.5)
        prediction = 1.0 - max(0.0, min(1.0, pred_error))

        # recovery: recent recovery rate (how fast signals return to baseline)
        recovery = self._compute_recovery(snap)

        # stability: inverse of homeostasis variance over recent ticks
        self._stability_buffer.append(dict(snap.streams))
        if len(self._stability_buffer) > 50:
            self._stability_buffer.pop(0)
        stability = self._compute_stability()

        # synchrony: cross-stream correlation (higher = more coherent)
        synchrony = self._compute_synchrony(snap)

        # reallocation: metabolic reallocation capability
        reallocation = snap.meta_signals.get("reallocation_capacity", 0.5)
        reallocation = max(0.0, min(1.0, reallocation))

        Phi = (
            self.gamma[0] * prediction
            + self.gamma[1] * recovery
            + self.gamma[2] * stability
            + self.gamma[3] * synchrony
            + self.gamma[4] * reallocation
        )
        return round(max(0.0, min(1.0, Phi)), 4)

    def _compute_recovery(self, snap) -> float:
        if not self._prev_streams:
            self._prev_streams = dict(snap.streams)
            return 0.5

        deltas = []
        for sid, val in snap.streams.items():
            prev = self._prev_streams.get(sid, val)
            deltas.append(abs(val - prev))
        self._prev_streams = dict(snap.streams)

        if not deltas:
            return 0.5
        mean_delta = sum(deltas) / len(deltas)
        recovery = 1.0 - min(1.0, mean_delta * 5)
        return max(0.0, recovery)

    def _compute_stability(self) -> float:
        if len(self._stability_buffer) < 5:
            return 0.5

        variances = []
        for sid in self._stability_buffer[0]:
            vals = [frame.get(sid, 0.5) for frame in self._stability_buffer if sid in frame]
            if len(vals) > 1:
                mean = sum(vals) / len(vals)
                var = sum((v - mean) ** 2 for v in vals) / len(vals)
                variances.append(var)

        if not variances:
            return 0.5
        avg_var = sum(variances) / len(variances)
        stability = 1.0 - min(1.0, math.sqrt(avg_var) * 5)
        return max(0.0, stability)

    def _compute_synchrony(self, snap) -> float:
        streams = list(snap.streams.values())
        if len(streams) < 2:
            return 0.5

        mean = sum(streams) / len(streams)
        if abs(mean) < 1e-6:
            return 0.5
        diffs = sum(abs(v - mean) for v in streams) / len(streams)
        synchrony = 1.0 - min(1.0, diffs / (mean + 1e-6))
        return max(0.0, synchrony)
