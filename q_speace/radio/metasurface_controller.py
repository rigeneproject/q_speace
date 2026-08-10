from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .models import BeamformingConfig, Waveform


@dataclass
class MetasurfaceConfig:
    num_elements: int = 64
    element_spacing_wavelengths: float = 0.5
    frequency_hz: float = 2.4e9
    phase_resolution_bits: int = 4
    amplitude_resolution_bits: int = 4


class MetasurfaceController:
    def __init__(
        self,
        config: MetasurfaceConfig | None = None,
        seed: int | None = None,
    ) -> None:
        self.config = config or MetasurfaceConfig()
        self._rng = np.random.default_rng(seed)
        self._phase_profile: np.ndarray = np.zeros(self.config.num_elements)
        self._amplitude_profile: np.ndarray = np.ones(self.config.num_elements)
        self._active = False

    @property
    def is_active(self) -> bool:
        return self._active

    def activate(self) -> None:
        self._active = True

    def deactivate(self) -> None:
        self._active = False

    def configure(self, bf: BeamformingConfig) -> None:
        wavelength = 3e8 / self.config.frequency_hz
        d = self.config.element_spacing_wavelengths * wavelength
        k = 2.0 * math.pi / wavelength
        theta = math.radians(bf.azimuth_deg)
        phi = math.radians(bf.elevation_deg)

        if bf.phase_profile is not None:
            self._phase_profile = bf.phase_profile.copy()
        else:
            phases = np.zeros(self.config.num_elements)
            for n in range(self.config.num_elements):
                phases[n] = -k * n * d * (math.sin(theta) * math.cos(phi))
            self._phase_profile = phases

        if bf.amplitude_taper is not None:
            self._amplitude_profile = bf.amplitude_taper.copy()
        else:
            self._amplitude_profile = np.ones(self.config.num_elements)

    def beamform(self, waveform: Waveform, azimuth_deg: float = 0.0) -> Waveform:
        if not self._active:
            return waveform
        self.configure(BeamformingConfig(azimuth_deg=azimuth_deg))
        steering = np.exp(1j * self._phase_profile)
        taper = self._amplitude_profile
        weights = steering * taper
        composite_gain = float(np.abs(np.sum(weights))) / self.config.num_elements
        shaped = waveform.iq_samples * composite_gain
        return Waveform(
            iq_samples=shaped,
            sample_rate=waveform.sample_rate,
            center_freq_hz=waveform.center_freq_hz,
            power_dbm=waveform.power_dbm + 20.0 * math.log10(composite_gain + 1e-12),
            modulation=waveform.modulation,
        )

    def interference_pattern(self, focal_point_m: tuple[float, float, float]) -> BeamformingConfig:
        x, y, z = focal_point_m
        r = math.sqrt(x**2 + y**2 + z**2) or 1.0
        azimuth = math.degrees(math.atan2(y, x))
        elevation = math.degrees(math.asin(z / r))
        return BeamformingConfig(azimuth_deg=azimuth, elevation_deg=elevation)

    def randomize(self) -> None:
        self._phase_profile = self._rng.uniform(0, 2 * math.pi, size=self.config.num_elements)
