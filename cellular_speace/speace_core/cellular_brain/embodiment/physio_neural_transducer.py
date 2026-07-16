"""PhysioNeuralTransducer — principled signal transduction avoiding ADC artifacts.

Maps continuous physical signals to structured neural spike trains by
preserving the signal's frequency decomposition, phase structure, and
temporal envelope — analogous to how the cochlea transduces sound.

Signal flow:
  signal_array → filter_bank → envelope_extraction → phase_preserving_encoding → spike_train
"""
from __future__ import annotations

import math
from enum import Enum
from typing import Callable, List, Optional

import numpy as np


class SignalType(str, Enum):
    AUDIO = "audio"
    VISUAL = "visual"
    TEMPERATURE = "temperature"
    PRESSURE = "pressure"
    PROPRIOCEPTIVE = "proprioceptive"


class TransductionConfig:
    """Tunable parameters per signal type."""

    def __init__(
        self,
        filter_count: int = 8,
        min_freq: float = 20.0,
        max_freq: float = 20000.0,
        spike_rate_max: float = 100.0,
        phase_bins: int = 10,
    ):
        self.filter_count = filter_count
        self.min_freq = min_freq
        self.max_freq = max_freq
        self.spike_rate_max = spike_rate_max
        self.phase_bins = phase_bins

    @classmethod
    def default_for(cls, signal_type: SignalType) -> "TransductionConfig":
        configs = {
            SignalType.AUDIO: cls(filter_count=12, min_freq=20, max_freq=20000),
            SignalType.VISUAL: cls(filter_count=6, min_freq=0.5, max_freq=60),
            SignalType.TEMPERATURE: cls(filter_count=3, min_freq=0.0, max_freq=1.0, spike_rate_max=20),
            SignalType.PRESSURE: cls(filter_count=4, min_freq=0.0, max_freq=10.0, spike_rate_max=50),
            SignalType.PROPRIOCEPTIVE: cls(filter_count=6, min_freq=0.0, max_freq=20.0, spike_rate_max=80),
        }
        return configs.get(signal_type, cls())


class PhysioNeuralTransducer:
    """Converts physical signals to neural spike trains with structure preservation.

    Uses a gammatone-like filter bank (simplified) for frequency decomposition,
    followed by envelope extraction and phase-preserving spike generation.

    The output is a list of SpikeEvent-compatible dicts with:
      - source_z (mapped to periodic element by frequency band)
      - timestamp
      - phase (preserved from signal)
      - inter_spike_interval (from envelope slope)
      - strength (normalized amplitude)
      - payload (original signal metadata)
    """

    # Mapping from frequency-band index to periodic element atomic number
    # Low frequencies → earlier periods, higher frequencies → later periods
    FREQ_BAND_TO_Z: List[int] = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

    def __init__(self):
        self._last_spike_time: dict[str, float] = {}

    def transduce(
        self,
        signal_array: "np.ndarray",
        sample_rate: float = 44100.0,
        signal_type: SignalType = SignalType.AUDIO,
    ) -> List[dict]:
        """Convert a physical signal to a list of spike-event dicts.

        Parameters
        ----------
        signal_array : np.ndarray
            1D array of signal samples.
        sample_rate : float
            Samples per second.
        signal_type : SignalType
            Type of signal being transduced.

        Returns
        -------
        list[dict]
            Each dict has keys: source_z, timestamp, phase,
            inter_spike_interval, strength, payload.
        """
        config = TransductionConfig.default_for(signal_type)

        if len(signal_array) == 0:
            return []

        signal = np.asarray(signal_array, dtype=np.float64)
        if np.max(np.abs(signal)) > 0:
            signal = signal / np.max(np.abs(signal))

        # 1. Filter bank: decompose into frequency bands
        bands = self._filter_bank(signal, sample_rate, config)

        # 2. Per-band envelope extraction and spike generation
        spikes: List[dict] = []
        tick_ratio = sample_rate / 100.0

        for band_idx, band_signal in enumerate(bands):
            envelope = np.abs(band_signal)
            phase = np.angle(band_signal)
            source_z = self._band_to_z(band_idx, config.filter_count)

            for i in range(1, len(envelope)):
                # Detect rising edge of envelope → generate spike
                slope = envelope[i] - envelope[i - 1]
                if slope > 0.01 and envelope[i] > 0.05:
                    isi = self._compute_isi(source_z, i / sample_rate)
                    spikes.append({
                        "source_z": source_z,
                        "timestamp": int(i / tick_ratio),
                        "phase": (phase[i] + math.pi) / (2.0 * math.pi),
                        "inter_spike_interval": isi,
                        "strength": float(min(1.0, envelope[i])),
                        "payload": {
                            "signal_type": signal_type,
                            "band_index": band_idx,
                            "sample_index": int(i),
                            "sample_rate": sample_rate,
                        },
                    })

        return sorted(spikes, key=lambda s: s["timestamp"])

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _filter_bank(
        self,
        signal: "np.ndarray",
        sample_rate: float,
        config: TransductionConfig,
    ) -> List["np.ndarray"]:
        """Simplified gammatone-like filter bank.

        Each band is a bandpass IIR filter (approximated as FFT mask
        for simplicity and numerical stability).
        """
        n = len(signal)
        spectrum = np.fft.rfft(signal)
        freqs = np.fft.rfftfreq(n, d=1.0 / sample_rate)

        bands: List[np.ndarray] = []
        for band_idx in range(config.filter_count):
            center = self._band_center_freq(band_idx, config.filter_count,
                                             config.min_freq, config.max_freq)
            bw = self._bandwidth(band_idx, config.filter_count, config.max_freq)

            mask = np.exp(-0.5 * ((freqs - center) / max(bw, 1.0)) ** 2)
            filtered = np.fft.irfft(spectrum * mask, n=n)
            bands.append(filtered)

        return bands

    def _band_center_freq(
        self, band_idx: int, num_bands: int, min_freq: float, max_freq: float
    ) -> float:
        """Logarithmic spacing of center frequencies (cochlea-like)."""
        if num_bands <= 1:
            return (min_freq + max_freq) / 2.0
        ratio = (max_freq / max(min_freq, 1.0)) ** (1.0 / (num_bands - 1))
        return max(min_freq, 1.0) * (ratio ** band_idx)

    def _bandwidth(self, band_idx: int, num_bands: int, max_freq: float) -> float:
        """Bandwidth increases with frequency (ERB-like scaling)."""
        return max_freq / (num_bands * 2.0) * (1.0 + 0.3 * band_idx)

    def _band_to_z(self, band_idx: int, num_bands: int) -> int:
        """Map frequency band to periodic table atomic number.

        Lower bands → lower atomic numbers (sensory transduction elements).
        """
        idx = min(band_idx, len(self.FREQ_BAND_TO_Z) - 1)
        return self.FREQ_BAND_TO_Z[idx]

    def _compute_isi(self, source_z: int, current_time: float) -> int:
        """Compute inter-spike-interval (in ticks) from firing history."""
        key = f"z{source_z}"
        last = self._last_spike_time.get(key, current_time)
        diff = current_time - last
        self._last_spike_time[key] = current_time
        return max(1, int(diff * 100))
