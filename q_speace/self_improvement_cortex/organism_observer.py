"""OrganismObserver — collects the full physiological profile (T34)."""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class PhysiologicalProfile:
    timestamp: float = 0.0
    coherence_phi: float = 0.0
    mean_energy_w: float = 0.0
    sci: float = 0.0
    plasticity_index: float = 0.0
    metabolic_cost: float = 0.0
    energy_consumption: float = 0.0
    world_model_accuracy: float = 0.0
    memory_compression: float = 0.0
    prediction_error: float = 0.0
    goal_completion: float = 0.0
    resilience: float = 0.0
    adaptation_speed: float = 0.0
    novelty: float = 0.0
    entropy: float = 0.0
    dna_stability: float = 0.0
    mutation_success_rate: float = 0.0
    ilf_coherence: float = 0.0
    extra: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, float]:
        base = {
            k: float(v) for k, v in self.__dict__.items()
            if isinstance(v, (int, float)) and k != "extra"
        }
        base.update(self.extra)
        return base

    def delta(self, baseline: PhysiologicalProfile) -> dict[str, float]:
        d: dict[str, float] = {}
        for k in self.to_dict():
            if k in baseline.to_dict():
                d[k] = self.to_dict()[k] - baseline.to_dict()[k]
        return d


class OrganismObserver:
    """Collects real-time physiological metrics from the SPEACE organism."""

    def __init__(self, history_size: int = 1000) -> None:
        self._history: list[PhysiologicalProfile] = []
        self._history_size = history_size

    def snapshot(
        self,
        coherence_phi: float = 0.0,
        mean_energy_w: float = 0.0,
        **extra: float,
    ) -> PhysiologicalProfile:
        profile = PhysiologicalProfile(
            timestamp=time.time(),
            coherence_phi=coherence_phi,
            mean_energy_w=mean_energy_w,
            **extra,
        )
        self._history.append(profile)
        if len(self._history) > self._history_size:
            self._history.pop(0)
        return profile

    def latest(self) -> PhysiologicalProfile | None:
        return self._history[-1] if self._history else None

    def trend(self, metric: str, window: int = 10) -> list[float]:
        values = [getattr(p, metric, None) for p in self._history[-window:]]
        return [v for v in values if v is not None]

    def mean(self, metric: str, window: int = 10) -> float:
        vals = self.trend(metric, window)
        return sum(vals) / len(vals) if vals else 0.0

    def clear(self) -> None:
        self._history.clear()
