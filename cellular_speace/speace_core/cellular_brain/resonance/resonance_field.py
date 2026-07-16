from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from speace_core.cellular_brain.resonance.frequency_oscillator import (
    FrequencyBand,
    FrequencyOscillator,
)


@dataclass
class WaveState:
    field_id: str
    band: FrequencyBand
    phase: float = 0.0
    amplitude: float = 0.0
    coherence: float = 0.0
    source_ids: List[str] = field(default_factory=list)
    timestamp: float = 0.0


class ResonanceField(BaseModel):
    field_id: str
    oscillators: Dict[str, FrequencyOscillator] = Field(default_factory=dict)
    source_map: Dict[str, List[str]] = Field(default_factory=dict)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def add_oscillator(self, oscillator: FrequencyOscillator, source_id: str) -> None:
        self.oscillators[oscillator.oscillator_id] = oscillator
        if source_id not in self.source_map:
            self.source_map[source_id] = []
        self.source_map[source_id].append(oscillator.oscillator_id)

    def remove_oscillator(self, oscillator_id: str) -> None:
        self.oscillators.pop(oscillator_id, None)
        for source_id in list(self.source_map.keys()):
            if oscillator_id in self.source_map[source_id]:
                self.source_map[source_id].remove(oscillator_id)
            if not self.source_map[source_id]:
                del self.source_map[source_id]

    def remove_source(self, source_id: str) -> None:
        osc_ids = self.source_map.pop(source_id, [])
        for oid in osc_ids:
            self.oscillators.pop(oid, None)

    def tick_all(self, dt: float = 1.0) -> Dict[str, float]:
        outputs: Dict[str, float] = {}
        for oid, osc in self.oscillators.items():
            outputs[oid] = osc.tick(dt)
        return outputs

    def get_field_state(self, band: Optional[FrequencyBand] = None) -> Dict[str, WaveState]:
        by_band: Dict[FrequencyBand, WaveState] = {}
        for oid, osc in self.oscillators.items():
            if band is not None and osc.band != band:
                continue
            if osc.band not in by_band:
                by_band[osc.band] = WaveState(
                    field_id=self.field_id,
                    band=osc.band,
                )
            ws = by_band[osc.band]
            ws.phase = (ws.phase + osc.phase) / 2.0
            ws.amplitude += osc.amplitude
            ws.coherence += osc.amplitude * math.cos(osc.phase)
            ws.source_ids.append(oid)

        result: Dict[str, WaveState] = {}
        for b, ws in by_band.items():
            n = len(ws.source_ids) if ws.source_ids else 1
            ws.amplitude = min(1.0, ws.amplitude / n * 2.0)
            ws.coherence = ws.coherence / n if n > 0 else 0.0
            result[b.value] = ws
        return result

    def get_global_coherence(self) -> float:
        if not self.oscillators:
            return 0.0
        phases = [osc.phase for osc in self.oscillators.values()]
        amplitudes = [osc.amplitude for osc in self.oscillators.values()]
        sin_sum = sum(a * math.sin(p) for a, p in zip(amplitudes, phases))
        cos_sum = sum(a * math.cos(p) for a, p in zip(amplitudes, phases))
        n = len(self.oscillators)
        order_param = math.sqrt(sin_sum**2 + cos_sum**2) / (sum(amplitudes) + 1e-12)
        return max(0.0, min(1.0, order_param))

    def get_source_coherence(self, source_id: str) -> float:
        osc_ids = self.source_map.get(source_id, [])
        if not osc_ids:
            return 0.0
        oscillators = [self.oscillators[oid] for oid in osc_ids if oid in self.oscillators]
        if not oscillators:
            return 0.0
        sin_sum = sum(math.sin(o.phase) for o in oscillators)
        cos_sum = sum(math.cos(o.phase) for o in oscillators)
        n = len(oscillators)
        return math.sqrt(sin_sum**2 + cos_sum**2) / (n + 1e-12)

    def get_dominant_frequency(self) -> Tuple[float, float]:
        if not self.oscillators:
            return (10.0, 0.0)
        best_freq = 10.0
        best_mag = 0.0
        for osc in self.oscillators.values():
            if osc.amplitude > best_mag:
                best_mag = osc.amplitude
                best_freq = osc.frequency
        return (best_freq, best_mag)

    def reset(self) -> None:
        for osc in self.oscillators.values():
            osc.reset_phase()
            osc.release_phase_lock()
