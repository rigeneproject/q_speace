"""Spike correlation -> functional entanglement layer (T202 P3).

Spike-timing synchrony is kept as a *functional* rule: statistical
correlation between spike trains feeds the EntanglementRegistry as a
classical **fidelity-proxy**. The stored fidelity is a software binding
metric, NOT quantum state fidelity — no physical entanglement is created
and the no-communication theorem is untouched (BCEL catalog, T202).
"""

from __future__ import annotations

import numpy as np

from ..quantum import EntangledPair, QuantumNeuralBridge
from .plasticity import SpikePlasticity


def spike_correlation(activity: np.ndarray) -> np.ndarray:
    """Pairwise Pearson correlation between spike trains (rows = neurons).

    Constant/zero-variance rows are treated as uncorrelated (0.0), never
    NaN. Diagonal is 1.0 by definition.
    """
    a = np.asarray(activity, dtype=float)
    if a.ndim != 2:
        raise ValueError("activity must be 2-D (neurons x time)")
    centered = a - a.mean(axis=1, keepdims=True)
    std = centered.std(axis=1, keepdims=True)
    std = np.where(std < 1e-12, 1.0, std)
    normalized = centered / std
    corr = (normalized @ normalized.T) / max(a.shape[1] - 1, 1)
    corr = np.nan_to_num(corr, nan=0.0, posinf=0.0, neginf=0.0)
    np.fill_diagonal(corr, 1.0)
    out: np.ndarray = np.clip(corr, -1.0, 1.0)
    return out


def entangle_by_correlation(
    bridge: QuantumNeuralBridge,
    activity: np.ndarray,
    threshold: float = 0.5,
    label: str = "spike-correlation",
    ids: list[str] | None = None,
    plasticity: SpikePlasticity | None = None,
) -> list[EntangledPair]:
    """Register entangled pairs from spike correlation.

    Only pairs with ``corr >= threshold`` are bound. The fidelity stored is
    the classical correlation (optionally scaled by the mean plasticity of
    the pair). This is the *functional entanglement layer*: a software
    binding in the registry, never a physical entangled state.
    """
    if not -1.0 <= threshold <= 1.0:
        raise ValueError("threshold must be in [-1, 1]")
    corr = spike_correlation(activity)
    n = corr.shape[0]
    if ids is None:
        ids = [f"n{i}" for i in range(n)]
    if len(ids) != n:
        raise ValueError("ids must match the number of activity rows")
    pairs: list[EntangledPair] = []
    coeffs = plasticity.coefficients() if plasticity is not None else None
    for i in range(n):
        bridge.register(ids[i])
    for i in range(n):
        for j in range(i + 1, n):
            if corr[i, j] < threshold:
                continue
            fidelity = float(corr[i, j])
            if coeffs is not None:
                fidelity *= float(np.mean(coeffs[[i, j]]))
            bridge.entangle_neurons(ids[i], ids[j], fidelity=fidelity, label=label)
            for pair in bridge.registry.pairs_of(ids[i]):
                if pair.involves(ids[j]) and pair.label == label:
                    pairs.append(pair)
    return pairs


def spike_entropy_gradient(spikes: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    """Gradient of spike Shannon entropy w.r.t. spike counts (T202 P5).

    With p = |s| / Z and H = -sum p ln p:

        dH/ds_k = sign(s_k) * -(ln p_k + H) / Z

    It is zero for a uniform spike distribution (entropy maximum) and for
    silent units. Drives the CosmicVirusOptimizer (EDD-CVT loop) toward
    sparser, lower-entropy spike distributions.
    """
    s = np.asarray(spikes, dtype=float)
    z = float(np.sum(np.abs(s)))
    grad: np.ndarray = np.zeros_like(s)
    if z <= eps:
        return grad
    p = np.abs(s) / z
    h = float(-np.sum(p * np.log(p + eps)))
    term = -(np.log(p + eps) + h) / z
    grad = np.sign(s) * term
    grad[s == 0.0] = 0.0
    return grad
