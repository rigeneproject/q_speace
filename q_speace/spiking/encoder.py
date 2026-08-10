"""Dynamic spike encoding (pseudo-spiking), adapted from SpikingBrain-7B.

Implements the dynamic-threshold quantization of ``W8ASpike/quant_linear.py``
(BICLab/SpikingBrain-7B, arXiv:2509.05276) in pure numpy:

    vth = mean(|x|, axis=-1) / k            (k = 3.0 in SpikingBrain)
    spikes = round(x / vth)

Optional ILF modulation of the threshold (T202 spec section 5):

    vth = mean(|x|) / (k * (1 + beta * coherence_phi))

The firing of biological neurons is *accidental* (BCEL gate); only the
integer quantization rule survives in silicon.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SpikeEncodingResult:
    """Outcome of one dynamic spike encoding pass."""

    spikes: np.ndarray  # integer-valued array (float dtype), same shape as input
    vth: np.ndarray  # per-slice thresholds used for the encoding
    num_spikes: int  # total non-zero spikes
    sparsity: float  # fraction of zero elements in [0, 1]
    rate: float  # mean absolute spike count per element


def dynamic_spikes(
    x: np.ndarray,
    k: float = 3.0,
    coherence_phi: float | None = None,
    beta: float = 0.0,
) -> SpikeEncodingResult:
    """Encode an activity tensor as sparse integer spike counts.

    Args:
        x: activity array, at least 1-D (threshold is per last axis).
        k: threshold divisor (SpikingBrain default 3.0).
        coherence_phi: if given, ILF-modulates the threshold via
            ``1 + beta * coherence_phi``.
        beta: sensitivity of the threshold to the ILF field.

    A silent (all-zero) input yields zero spikes and sparsity 1.0.
    """
    arr = np.asarray(x, dtype=float)
    if arr.ndim < 1:
        raise ValueError("x must be at least 1-D")
    if k <= 0.0:
        raise ValueError("k must be > 0")
    if beta < 0.0:
        raise ValueError("beta must be >= 0")
    denom = k * (1.0 + beta * coherence_phi) if coherence_phi is not None else k
    vth = np.mean(np.abs(arr), axis=-1, keepdims=True) / denom
    vth = np.clip(vth, 1e-5, 1e4)
    spikes = np.round(arr / vth)
    return SpikeEncodingResult(
        spikes=spikes,
        vth=vth,
        num_spikes=int(np.count_nonzero(spikes)),
        sparsity=float(1.0 - np.count_nonzero(spikes) / spikes.size),
        rate=float(np.mean(np.abs(spikes))),
    )


def spike_count(spikes: np.ndarray) -> int:
    """Total number of non-zero spikes (event-driven cost driver, T202 P1)."""
    return int(np.count_nonzero(np.asarray(spikes)))


def sparsity(spikes: np.ndarray) -> float:
    """Fraction of zero elements in [0, 1]."""
    s = np.asarray(spikes)
    if s.size == 0:
        return 1.0
    return float(1.0 - np.count_nonzero(s) / s.size)


def spike_rate(spikes: np.ndarray) -> float:
    """Mean absolute spike count per element."""
    return float(np.mean(np.abs(np.asarray(spikes, dtype=float))))
