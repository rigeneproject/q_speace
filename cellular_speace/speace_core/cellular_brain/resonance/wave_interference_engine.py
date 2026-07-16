from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from speace_core.cellular_brain.resonance.frequency_oscillator import (
    FrequencyBand,
    FrequencyOscillator,
)


class InterferenceType(str, Enum):
    CONSTRUCTIVE = "constructive"
    DESTRUCTIVE = "destructive"
    PARTIAL = "partial"
    RESONANT = "resonant"


@dataclass
class InterferencePattern:
    pattern_id: str
    interference_type: InterferenceType
    source_ids: List[str] = field(default_factory=list)
    target_ids: List[str] = field(default_factory=list)
    amplitude: float = 0.0
    phase: float = 0.0
    band: Optional[FrequencyBand] = None
    strength: float = 0.0


class WaveInterferenceEngine(BaseModel):
    engine_id: str
    patterns: Dict[str, InterferencePattern] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def compute_interference(
        self,
        oscillators: List[FrequencyOscillator],
        pattern_id: str = "default",
    ) -> InterferencePattern:
        if not oscillators:
            return InterferencePattern(
                pattern_id=pattern_id,
                interference_type=InterferenceType.DESTRUCTIVE,
            )

        sin_sum = sum(o.amplitude * math.sin(o.phase) for o in oscillators)
        cos_sum = sum(o.amplitude * math.cos(o.phase) for o in oscillators)
        total_amplitude = sum(o.amplitude for o in oscillators)

        result_amplitude = math.sqrt(sin_sum**2 + cos_sum**2)
        result_phase = math.atan2(sin_sum, cos_sum) if (sin_sum != 0 or cos_sum != 0) else 0.0

        ratio = result_amplitude / (total_amplitude + 1e-12)
        if ratio < 0.15:
            if_type = InterferenceType.DESTRUCTIVE
        elif ratio > 0.85:
            if_type = InterferenceType.CONSTRUCTIVE
        elif ratio > 0.5:
            if_type = InterferenceType.RESONANT
        else:
            if_type = InterferenceType.PARTIAL

        pattern = InterferencePattern(
            pattern_id=pattern_id,
            interference_type=if_type,
            source_ids=[o.oscillator_id for o in oscillators],
            amplitude=min(1.0, result_amplitude),
            phase=result_phase,
            band=oscillators[0].band if oscillators else None,
            strength=result_amplitude / (total_amplitude + 1e-12),
        )

        self.patterns[pattern_id] = pattern
        return pattern

    def interfere_fields(
        self,
        field_a_oscillators: List[FrequencyOscillator],
        field_b_oscillators: List[FrequencyOscillator],
        pattern_id: str = "cross_field",
    ) -> InterferencePattern:
        combined = field_a_oscillators + field_b_oscillators
        return self.compute_interference(combined, pattern_id)

    def amplify_region(
        self,
        target_oscillators: List[FrequencyOscillator],
        reference_oscillator: FrequencyOscillator,
        amplification_factor: float = 0.3,
    ) -> None:
        ref_phase = reference_oscillator.phase
        for osc in target_oscillators:
            phase_diff = abs(osc.phase - ref_phase) % (2.0 * math.pi)
            phase_diff = min(phase_diff, 2.0 * math.pi - phase_diff)
            if phase_diff < math.pi / 4.0:
                osc.boost_amplitude(amplification_factor)
                osc.phase = (osc.phase + ref_phase) / 2.0

    def suppress_region(
        self,
        target_oscillators: List[FrequencyOscillator],
        reference_oscillator: FrequencyOscillator,
        suppression_factor: float = 0.3,
    ) -> None:
        ref_phase = reference_oscillator.phase
        for osc in target_oscillators:
            phase_diff = abs(osc.phase - ref_phase) % (2.0 * math.pi)
            phase_diff = min(phase_diff, 2.0 * math.pi - phase_diff)
            if phase_diff < math.pi / 4.0:
                osc.amplitude = max(0.0, osc.amplitude - suppression_factor)

    def get_resonance_condition(
        self, osc_a: FrequencyOscillator, osc_b: FrequencyOscillator
    ) -> float:
        fa, fb = osc_a.frequency, osc_b.frequency
        if fa < 0.01 or fb < 0.01:
            return 0.0
        ratio = fa / fb
        scores = []
        for n in range(1, 6):
            for m in range(1, 6):
                ideal = n / m
                deviation = abs(ratio - ideal)
                score = max(0.0, 1.0 - deviation * 8.0)
                scores.append(score)
        resonance_score = max(scores)
        return resonance_score

    def find_resonant_pairs(
        self, oscillators: List[FrequencyOscillator], threshold: float = 0.8
    ) -> List[Tuple[str, str, float]]:
        pairs: List[Tuple[str, str, float]] = []
        for i in range(len(oscillators)):
            for j in range(i + 1, len(oscillators)):
                score = self.get_resonance_condition(oscillators[i], oscillators[j])
                if score >= threshold:
                    pairs.append((oscillators[i].oscillator_id, oscillators[j].oscillator_id, score))
        return pairs

    def clear_patterns(self) -> None:
        self.patterns.clear()
