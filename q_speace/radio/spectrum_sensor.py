from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .models import SpectrumReading
from .sdr_frontend import NullSDR, SDRFrontend


@dataclass
class EnvironmentMAP:
    frequency_hz: float
    mean_rssi_dbm: float
    mean_snr_db: float
    occupancy_pct: float


class SpectrumSensor:
    def __init__(
        self,
        sdr: SDRFrontend | None = None,
        band: tuple[float, float] = (2.4e9, 2.4835e9),
        scan_steps: int = 50,
        seed: int | None = None,
    ) -> None:
        self._sdr = sdr or NullSDR(_seed=seed)
        self._band = band
        self._scan_steps = scan_steps
        self._rng = np.random.default_rng(seed)
        self._map: list[EnvironmentMAP] = []
        self._last_reading: SpectrumReading | None = None

    def sense(self) -> SpectrumReading:
        readings = self._sdr.scan_spectrum(self._band[0], self._band[1], self._scan_steps)
        if not readings:
            return SpectrumReading(
                center_freq_hz=(self._band[0] + self._band[1]) / 2.0,
                bandwidth_hz=self._band[1] - self._band[0],
            )
        center = readings[len(readings) // 2]
        avg_rssi = float(np.mean([r.rssi_dbm for r in readings]))
        avg_snr = float(np.mean([r.snr_db for r in readings]))
        occupied = sum(1 for r in readings if r.rssi_dbm > -90.0) / len(readings)
        reading = SpectrumReading(
            center_freq_hz=center.center_freq_hz,
            bandwidth_hz=self._band[1] - self._band[0],
            rssi_dbm=avg_rssi,
            snr_db=avg_snr,
            channel_occupancy=occupied,
            interference_level=1.0 - center.quality_index,
        )
        self._last_reading = reading
        return reading

    def update_environment_map(self) -> None:
        readings = self._sdr.scan_spectrum(self._band[0], self._band[1], self._scan_steps)
        self._map = [
            EnvironmentMAP(
                frequency_hz=r.center_freq_hz,
                mean_rssi_dbm=r.rssi_dbm,
                mean_snr_db=r.snr_db,
                occupancy_pct=1.0 if r.rssi_dbm > -90.0 else 0.0,
            )
            for r in readings
        ]

    @property
    def environment_map(self) -> list[EnvironmentMAP]:
        if not self._map:
            self.update_environment_map()
        return self._map

    @property
    def last_reading(self) -> SpectrumReading | None:
        return self._last_reading

    def close(self) -> None:
        self._sdr.close()
