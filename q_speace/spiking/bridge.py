"""SpikeQuantumBridge — spikes to quantum representations (T202 P2).

The quantum kernel receives only a sparse integer representation; it never
sees the neural model (separation of levels). Two encodings:

  - amplitude encoding: |spikes| padded to a power of 2 -> QuantumState
  - rotation encoding: per-cell spike counts -> RY angles pi * rate
    (same idiom as earth_feed's EarthSignals.rotation_angles)
"""

from __future__ import annotations

import math

import numpy as np

from ..quantum import QuantumState
from .encoder import SpikeEncodingResult, dynamic_spikes


class SpikeQuantumBridge:
    """Encodes spike activity into quantum states and QCA rotation angles."""

    def __init__(self, seed: int | None = None) -> None:
        self._seed = seed

    def encode(
        self,
        activity: np.ndarray,
        k: float = 3.0,
        coherence_phi: float | None = None,
        beta: float = 0.0,
    ) -> SpikeEncodingResult:
        """Dynamic spike encoding of an activity tensor."""
        return dynamic_spikes(activity, k=k, coherence_phi=coherence_phi, beta=beta)

    def to_state(self, spikes: np.ndarray) -> QuantumState:
        """Amplitude-encode |spikes| into a normalized quantum state.

        The vector is padded with zeros to the next power of 2 (cap 16
        qubits, the statevector limit of the numpy kernel).
        """
        raw = np.asarray(spikes, dtype=float).ravel()
        if raw.size == 0:
            raise ValueError("spike vector must be non-empty")
        if not np.all(np.isfinite(raw)):
            raise ValueError("spike vector must contain only finite values")
        s = np.abs(raw)
        if s.size > (1 << 16):
            raise ValueError("spike vector too large for the 16-qubit statevector cap")
        n = max(int(math.ceil(math.log2(max(s.size, 2)))), 1)
        padded = np.zeros(1 << n, dtype=np.complex128)
        padded[: s.size] = s
        return QuantumState.from_amplitudes(padded, seed=self._seed)

    def to_qca_rotations(self, spikes: np.ndarray, num_cells: int | None = None) -> np.ndarray:
        """Per-cell RY angles in [0, pi], proportional to spike activity.

        Counts are summed over the last axis (per-unit activity); the most
        active cell maps to pi, silent cells to 0.0.
        """
        s = np.asarray(spikes, dtype=float)
        if s.size == 0:
            raise ValueError("spike array must be non-empty")
        if not np.all(np.isfinite(s)):
            raise ValueError("spike array must contain only finite values")
        counts = np.abs(s).sum(axis=-1) if s.ndim > 1 else np.abs(s)
        if num_cells is not None:
            if num_cells < 1:
                raise ValueError("num_cells must be >= 1")
            if counts.size >= num_cells:
                counts = counts[:num_cells]
            else:
                padded = np.zeros(num_cells, dtype=float)
                padded[: counts.size] = counts
                counts = padded
        peak = float(np.max(counts))
        if peak <= 0.0:
            return np.zeros(counts.size, dtype=float)
        out: np.ndarray = np.pi * (counts / peak)
        return out
