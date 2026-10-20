from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class FrequencyRange:
    start_hz: float
    end_hz: float

    @property
    def center_hz(self) -> float:
        return (self.start_hz + self.end_hz) / 2.0

    @property
    def bandwidth_hz(self) -> float:
        return self.end_hz - self.start_hz


@dataclass
class ModulationParams:
    modulation: str = "bpsk"
    symbol_rate: float = 1e6
    spreading_factor: int = 1


@dataclass
class Waveform:
    iq_samples: np.ndarray
    sample_rate: float = 1e6
    center_freq_hz: float = 2.4e9
    power_dbm: float = 0.0
    modulation: str = "bpsk"

    @property
    def duration_s(self) -> float:
        return len(self.iq_samples) / self.sample_rate if self.sample_rate > 0 else 0.0

    @property
    def power_watts(self) -> float:
        return float(10.0 ** ((self.power_dbm - 30.0) / 10.0))

    def normalized(self) -> Waveform:
        max_amp = float(np.max(np.abs(self.iq_samples))) or 1.0
        return Waveform(
            iq_samples=self.iq_samples / max_amp,
            sample_rate=self.sample_rate,
            center_freq_hz=self.center_freq_hz,
            power_dbm=self.power_dbm,
            modulation=self.modulation,
        )


@dataclass
class SpectrumReading:
    center_freq_hz: float
    bandwidth_hz: float
    rssi_dbm: float = -100.0
    snr_db: float = 0.0
    channel_occupancy: float = 0.0
    interference_level: float = 0.0
    psd: np.ndarray | None = None

    @property
    def is_clear(self) -> bool:
        return self.rssi_dbm < -90.0

    @property
    def quality_index(self) -> float:
        snr_norm = max(0.0, min(self.snr_db / 30.0, 1.0))
        occ_norm = 1.0 - min(self.channel_occupancy, 1.0)
        int_norm = 1.0 - min(self.interference_level, 1.0)
        return (snr_norm + occ_norm + int_norm) / 3.0


@dataclass
class BeamformingConfig:
    azimuth_deg: float = 0.0
    elevation_deg: float = 0.0
    phase_profile: np.ndarray | None = None
    amplitude_taper: np.ndarray | None = None


@dataclass
class TransmissionReport:
    success: bool
    frequency_hz: float
    power_dbm: float
    duration_s: float
    compliance_check: bool = True
    error_message: str = ""
