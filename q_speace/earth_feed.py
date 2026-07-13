"""Earth feed — real planetary signals as quantum circuit parameters.

Maps external geophysical time series (geomagnetic Kp index, sunspot
number, tides) to normalized rotation angles for RX/RY/RZ gates. This is
a *deterministic modulation* of computation parameters, not "planetary
perception" (see guidelines §4). Network access is best-effort; a
deterministic synthetic fallback keeps the system reproducible offline.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass
class EarthSignals:
    """Normalized planetary signals in [0, 1]."""

    kp: float  # geomagnetic activity (0 calm .. 1 storm)
    sunspot: float  # solar activity
    tide: float  # tidal phase [0, 1]

    def rotation_angles(self) -> dict[str, float]:
        """Map signals to parametric rotation angles (radians)."""
        return {
            "rx": self.kp * math.pi,
            "ry": self.sunspot * math.pi,
            "rz": self.tide * 2.0 * math.pi,
        }


class EarthFeed:
    """Provides Earth signals, real when possible, synthetic otherwise."""

    def __init__(self, use_network: bool = False, seed: int | None = None) -> None:
        self.use_network = use_network
        self._rng = np.random.default_rng(seed)

    def fetch(self, tick: int = 0) -> EarthSignals:
        if self.use_network:
            try:
                return self._fetch_real()
            except Exception:
                pass
        return self._synthetic(tick)

    def _fetch_real(self) -> EarthSignals:
        # Best-effort: NOAA SWPC planetary K-index (last value).
        import httpx

        resp = httpx.get(
            "https://services.swpc.noaa.gov/json/planetary_k_index_1m.json",
            timeout=5.0,
        )
        rows = resp.json()
        latest = float(rows[-1]["Kp"])
        kp = min(max(latest / 9.0, 0.0), 1.0)
        # Sunspot / tide are not critical; fall back to neutral.
        return EarthSignals(kp=kp, sunspot=0.5, tide=0.5)

    def _synthetic(self, tick: int) -> EarthSignals:
        # Deterministic, reproducible modulation if offline.
        kp = 0.5 + 0.4 * math.sin(tick / 7.0)
        sunspot = 0.5 + 0.3 * math.sin(tick / 13.0 + 1.0)
        tide = (tick % 24) / 24.0
        return EarthSignals(
            kp=float(min(max(kp, 0.0), 1.0)),
            sunspot=float(min(max(sunspot, 0.0), 1.0)),
            tide=float(tide),
        )
