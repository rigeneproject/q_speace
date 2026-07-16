"""SpikeEvent — first-class spike datatype bridging periodic table and runtime.

Represents a single firing event with temporal coding (ISI, phase, strength)
and periodic-element provenance (source_z, target_z). Connects the static
element ontology to the dynamic burst/propagation pipeline.
"""
from __future__ import annotations

import math
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class SpikeEvent(BaseModel):
    """A single spike traversing (or originating from) a periodic element pair.

    Fields
    ------
    spike_id : str
        Unique identifier (auto-generated).
    source_z : int
        Atomic number of the presynaptic element.
    target_z : int | None
        Atomic number of the postsynaptic element (None for spontaneous firing).
    timestamp : int
        Tick number at which this spike occurred.
    phase : float
        Oscillation phase at firing time, in [0, 2π).
    inter_spike_interval : int
        Ticks since the last spike from the same source.
    strength : float
        Normalized amplitude in [0, 1].
    bond_id : str | None
        Which bond this spike traverses (None for spontaneous).
    payload : dict
        Optional typed data for non-neural signals (transducer output).
    """
    spike_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    source_z: int
    target_z: Optional[int] = None
    timestamp: int = 0
    phase: float = 0.0
    inter_spike_interval: int = 1
    strength: float = 1.0
    bond_id: Optional[str] = None
    payload: dict = Field(default_factory=dict)

    def temporal_code(self) -> list[float]:
        """Return (ISI, phase_norm, strength) as a 3D temporal code vector.

        phase_norm = phase / 2π maps [0, 2π) → [0, 1).
        """
        return [
            float(self.inter_spike_interval),
            self.phase / (2.0 * math.pi),
            self.strength,
        ]

    def with_propagation(self, bond: Any) -> "SpikeEvent":
        """Return a copy adjusted for bond-specific attenuation and delay.

        The returned spike has its strength scaled by the bond's amplification
        factor and is assigned to the bond's target element.
        """
        amp = bond.molecule.amplification_factor() if hasattr(bond, "molecule") else 1.0
        delay = bond.signal_delay() if hasattr(bond, "signal_delay") else 0.0
        return SpikeEvent(
            source_z=self.target_z or self.source_z,
            target_z=bond.target_z if hasattr(bond, "target_z") else None,
            timestamp=self.timestamp + int(delay * 10),
            phase=(self.phase + 0.1) % (2.0 * math.pi),
            inter_spike_interval=self.inter_spike_interval,
            strength=self.strength * amp,
            bond_id=bond.bond_id if hasattr(bond, "bond_id") else self.bond_id,
            payload=self.payload,
        )

    def is_strong(self, threshold: float = 0.7) -> bool:
        return self.strength >= threshold

    def is_weak(self, threshold: float = 0.3) -> bool:
        return self.strength < threshold
