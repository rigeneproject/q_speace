from __future__ import annotations

import math

import numpy as np

from .models import Waveform


class WavefrontModulator:
    def __init__(
        self,
        sample_rate: float = 10e6,
        center_freq_hz: float = 2.4e9,
        power_dbm: float = 0.0,
        spread_factor: int = 32,
        seed: int | None = None,
    ) -> None:
        self.sample_rate = sample_rate
        self.center_freq_hz = center_freq_hz
        self.power_dbm = power_dbm
        self.spread_factor = spread_factor
        self._rng = np.random.default_rng(seed)
        self._spreading_code: np.ndarray | None = None

    def _generate_spreading_code(self) -> np.ndarray:
        if self._spreading_code is not None:
            return self._spreading_code
        code = self._rng.choice([-1, 1], size=self.spread_factor).astype(np.float64)
        self._spreading_code = code
        return code

    def encode(self, state_vector: np.ndarray, modulation: str = "bpsk") -> Waveform:
        data = np.asarray(state_vector, dtype=np.float64).flatten()
        data = data / (np.linalg.norm(data) + 1e-12)
        code = self._generate_spreading_code()
        spread = np.kron(data, code)
        num_samples = max(len(spread), 2)
        t = np.arange(num_samples, dtype=np.float64) / self.sample_rate
        carrier = np.exp(2j * math.pi * self.center_freq_hz * t)
        modulated = spread.astype(np.complex128) * carrier
        return Waveform(
            iq_samples=modulated,
            sample_rate=self.sample_rate,
            center_freq_hz=self.center_freq_hz,
            power_dbm=self.power_dbm,
            modulation=modulation,
        )

    def decode(self, waveform: Waveform, num_symbols: int | None = None) -> np.ndarray:
        code = self._generate_spreading_code()
        carrier = np.exp(
            -2j
            * math.pi
            * self.center_freq_hz
            * (np.arange(len(waveform.iq_samples), dtype=np.float64) / waveform.sample_rate)
        )
        baseband = waveform.iq_samples * carrier
        real_signal = np.real(baseband)
        num_symbols = num_symbols or (len(real_signal) // self.spread_factor)
        recovered = np.zeros(num_symbols, dtype=np.float64)
        for i in range(num_symbols):
            start = i * self.spread_factor
            end = start + self.spread_factor
            if end > len(real_signal):
                break
            chip_seq = real_signal[start:end]
            correlation = float(np.dot(chip_seq, code)) / self.spread_factor
            recovered[i] = correlation
        norm = np.linalg.norm(recovered) or 1.0
        return recovered / norm

    def encode_q_star(self, q_star: np.ndarray, confidence: float = 1.0) -> Waveform:
        noisy = q_star + self._rng.normal(0.0, (1.0 - confidence) * 0.1, size=q_star.shape)
        return self.encode(noisy)

    def decode_to_q_star(self, waveform: Waveform, expected_dim: int = 4) -> np.ndarray:
        return self.decode(waveform, num_symbols=expected_dim)
