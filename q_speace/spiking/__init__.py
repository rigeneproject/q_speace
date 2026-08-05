"""Pseudo-spiking layer for Q-SPEACE (task T202).

Selective adaptation of SpikingBrain-7B (arXiv:2509.05276) dynamic spike
encoding to the quantum layer: sparse integer spike representation,
event-driven energy, plasticity coefficients, classical spike-correlation
binding and spike-entropy gradients. Pseudo-spiking at tensor level only;
numpy-only, no torch, no neuromorphic hardware.
"""
from __future__ import annotations

from .bridge import SpikeQuantumBridge
from .correlation import (
    entangle_by_correlation,
    spike_correlation,
    spike_entropy_gradient,
)
from .encoder import SpikeEncodingResult, dynamic_spikes, spike_count, spike_rate, sparsity
from .linear import SpikeEncodedLinear
from .plasticity import SpikePlasticity

__all__ = [
    "SpikeEncodingResult",
    "dynamic_spikes",
    "spike_count",
    "spike_rate",
    "sparsity",
    "SpikeEncodedLinear",
    "SpikePlasticity",
    "spike_correlation",
    "entangle_by_correlation",
    "spike_entropy_gradient",
    "SpikeQuantumBridge",
]
