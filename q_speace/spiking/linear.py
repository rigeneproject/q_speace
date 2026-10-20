"""Pseudo-spiking linear layer (W8ASpike-style) in numpy.

Numpy analog of ``QuantLinear`` from ``W8ASpike/quant_linear.py``
(SpikingBrain-7B): weights are quantized int8-like per group (symmetric
scaling) and activations pass through ``dynamic_spikes`` before the matmul:

    out = (round(x / vth) * vth) @ W_q + b

This is the classical sparsifying layer placed *before* the quantum kernel
(T202 P2). The quantum layer never sees the neural model — only the sparse
integer representation.
"""

from __future__ import annotations

import numpy as np

from .encoder import dynamic_spikes


class SpikeEncodedLinear:
    """Feed-forward layer with dynamic spike activations and quantized weights."""

    def __init__(
        self,
        in_features: int,
        out_features: int,
        k: float = 3.0,
        group_size: int | None = None,
        seed: int | None = None,
    ) -> None:
        if in_features < 1 or out_features < 1:
            raise ValueError("in_features and out_features must be >= 1")
        if group_size is not None and (group_size < 1 or in_features % group_size != 0):
            raise ValueError("group_size must divide in_features")
        self.in_features = in_features
        self.out_features = out_features
        self.k = k
        self.group_size = group_size
        rng = np.random.default_rng(seed)
        limit = np.sqrt(6.0 / (in_features + out_features))
        self.weight = rng.uniform(-limit, limit, size=(out_features, in_features))
        self.bias = rng.uniform(-0.1, 0.1, size=(out_features,))
        self._weight_q, self._scales = self._quantize_weights()

    def _quantize_weights(self) -> tuple[np.ndarray, np.ndarray]:
        w = self.weight
        if self.group_size is None:
            scales = np.max(np.abs(w), axis=1, keepdims=True) / 127.0
            scales = np.maximum(scales, 1e-8)
            wq = np.round(w / scales) * scales
            return wq, scales
        w3 = w.reshape(self.out_features, -1, self.group_size)
        scales = np.max(np.abs(w3), axis=-1, keepdims=True) / 127.0
        scales = np.maximum(scales, 1e-8)
        wq = np.round(w3 / scales) * scales
        return wq.reshape(self.out_features, self.in_features), scales

    @property
    def quantized_weight(self) -> np.ndarray:
        """Group-wise int8-style quantized weight matrix."""
        return self._weight_q

    def quantization_error(self) -> float:
        """Max abs deviation of the quantized weights from the raw ones."""
        return float(np.max(np.abs(self.weight - self._weight_q)))

    def forward(
        self,
        x: np.ndarray,
        coherence_phi: float | None = None,
        beta: float = 0.0,
    ) -> np.ndarray:
        """Apply spike encoding then a linear map with quantized weights."""
        arr = np.asarray(x, dtype=float)
        if arr.shape[-1] != self.in_features:
            raise ValueError(f"expected last dim {self.in_features}, got {arr.shape[-1]}")
        enc = dynamic_spikes(arr, k=self.k, coherence_phi=coherence_phi, beta=beta)
        x_hat = enc.spikes * enc.vth
        out: np.ndarray = x_hat @ self._weight_q.T + self.bias
        return out
