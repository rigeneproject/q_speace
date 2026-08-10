from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np

from .models import SpectrumReading, TransmissionReport, Waveform


class SDRFrontend(ABC):
    name: str = "abstract"

    @abstractmethod
    def transmit(self, waveform: Waveform) -> TransmissionReport:
        raise NotImplementedError

    @abstractmethod
    def receive(self, frequency_hz: float, bandwidth_hz: float, duration_s: float) -> Waveform:
        raise NotImplementedError

    @abstractmethod
    def scan_spectrum(
        self, start_hz: float, end_hz: float, steps: int = 100
    ) -> list[SpectrumReading]:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError


@dataclass
class NullSDR(SDRFrontend):
    name: str = "null"

    _noise_floor_dbm: float = -100.0
    _seed: int | None = None

    def __post_init__(self) -> None:
        self._rng = np.random.default_rng(self._seed)

    def transmit(self, waveform: Waveform) -> TransmissionReport:
        return TransmissionReport(
            success=True,
            frequency_hz=waveform.center_freq_hz,
            power_dbm=waveform.power_dbm,
            duration_s=waveform.duration_s,
        )

    def receive(self, frequency_hz: float, bandwidth_hz: float, duration_s: float) -> Waveform:
        num_samples = max(int(duration_s * 1e6), 1)
        noise = self._rng.normal(
            0.0, 10.0 ** (self._noise_floor_dbm / 20.0), (num_samples,)
        ).astype(np.complex128)
        return Waveform(
            iq_samples=noise,
            sample_rate=1e6,
            center_freq_hz=frequency_hz,
            power_dbm=self._noise_floor_dbm,
        )

    def scan_spectrum(
        self, start_hz: float, end_hz: float, steps: int = 100
    ) -> list[SpectrumReading]:
        readings: list[SpectrumReading] = []
        for i in range(steps):
            f = start_hz + (end_hz - start_hz) * i / steps
            rssi = self._noise_floor_dbm + self._rng.uniform(-3.0, 3.0)
            readings.append(
                SpectrumReading(
                    center_freq_hz=f,
                    bandwidth_hz=(end_hz - start_hz) / steps,
                    rssi_dbm=rssi,
                    snr_db=0.0,
                )
            )
        return readings

    def close(self) -> None:
        pass
