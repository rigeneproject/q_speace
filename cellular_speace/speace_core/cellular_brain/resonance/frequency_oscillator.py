from __future__ import annotations

import math
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class FrequencyBand(str, Enum):
    DELTA = "delta"
    THETA = "theta"
    ALPHA = "alpha"
    BETA = "beta"
    GAMMA = "gamma"


FREQUENCY_RANGES: Dict[FrequencyBand, tuple[float, float]] = {
    FrequencyBand.DELTA: (0.5, 4.0),
    FrequencyBand.THETA: (4.0, 8.0),
    FrequencyBand.ALPHA: (8.0, 12.0),
    FrequencyBand.BETA: (12.0, 30.0),
    FrequencyBand.GAMMA: (30.0, 100.0),
}


FREQUENCY_DEFAULTS: Dict[str, List[FrequencyBand]] = {
    "prefrontal": [FrequencyBand.BETA, FrequencyBand.GAMMA],
    "hippocampus": [FrequencyBand.THETA, FrequencyBand.GAMMA],
    "limbic": [FrequencyBand.THETA, FrequencyBand.ALPHA],
    "cerebellar": [FrequencyBand.BETA, FrequencyBand.GAMMA],
    "brainstem_homeostatic": [FrequencyBand.DELTA, FrequencyBand.THETA],
    "default_mode": [FrequencyBand.ALPHA, FrequencyBand.DELTA],
    "sensory": [FrequencyBand.GAMMA, FrequencyBand.BETA],
    "motor": [FrequencyBand.BETA, FrequencyBand.GAMMA],
}


class FrequencyOscillator(BaseModel):
    oscillator_id: str
    band: FrequencyBand
    frequency: float = 10.0
    phase: float = 0.0
    amplitude: float = 0.5
    damping: float = 0.01
    base_frequency: float = 10.0
    target_phase: Optional[float] = None
    phase_locked: bool = False
    coupling_strength: float = 0.0

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def tick(self, dt: float = 1.0) -> float:
        phase_increment = 2.0 * math.pi * self.frequency * dt / 100.0
        self.phase = (self.phase + phase_increment) % (2.0 * math.pi)

        if self.target_phase is not None and self.phase_locked:
            diff = self.target_phase - self.phase
            self.phase += diff * self.coupling_strength * 0.1

        self.amplitude = max(0.0, min(1.0, self.amplitude - self.damping * dt))
        return self.amplitude * math.sin(self.phase)

    def phase_lock_to(self, target_phase: float, strength: float = 0.1) -> None:
        self.target_phase = target_phase % (2.0 * math.pi)
        self.phase_locked = True
        self.coupling_strength = strength

    def release_phase_lock(self) -> None:
        self.target_phase = None
        self.phase_locked = False
        self.coupling_strength = 0.0

    def modulate_frequency(self, modulation: float) -> None:
        self.frequency = max(0.1, self.base_frequency + modulation)

    def boost_amplitude(self, boost: float) -> None:
        self.amplitude = min(1.0, self.amplitude + boost)

    def reset_phase(self) -> None:
        self.phase = 0.0

    def get_normalized_phase(self) -> float:
        return self.phase / (2.0 * math.pi)

    def get_instantaneous_value(self) -> float:
        return self.amplitude * math.sin(self.phase)

    def phase_difference_to(self, other: FrequencyOscillator) -> float:
        diff = abs(self.phase - other.phase) % (2.0 * math.pi)
        return min(diff, 2.0 * math.pi - diff)


def default_oscillators_for_region(
    region_type: str,
    region_id: str,
    base_amplitude: float = 0.5,
) -> List[FrequencyOscillator]:
    bands = FREQUENCY_DEFAULTS.get(region_type, [FrequencyBand.ALPHA])
    oscillators: List[FrequencyOscillator] = []
    for band in bands:
        low, high = FREQUENCY_RANGES[band]
        freq = (low + high) / 2.0
        oscillators.append(
            FrequencyOscillator(
                oscillator_id=f"{region_id}_{band.value}",
                band=band,
                frequency=freq,
                base_frequency=freq,
                amplitude=base_amplitude,
            )
        )
    return oscillators
