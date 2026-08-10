"""Common data types for the SpikingBrain satellite (T205).

``ThinkResult`` is the language-agnostic payload returned by every
SpikingBrain backend. It mirrors the three downstream consumers inside
Q-SPEACE:

- ``belief``     — ILF belief vector, ``shape (n_classes,)``, ``sum == 1``.
- ``spikes``     — ``SpikeEncodingResult`` from ``q_speace.spiking.encoder``
                   so the same dynamic-spike rule is reused end-to-end.
- ``plasticity`` — ``np.ndarray`` of coefficients in ``[0, 1]`` driving
                   the ``SpikePlasticity`` EMA (T202 P-plasticity).
- ``text``       — raw model output (reasoning trace) for logging.
- ``confidence`` — scalar in ``[0, 1]`` (log-prob-based, used for
                   metacognitive gating by ``ILFRegulator``).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..spiking import SpikeEncodingResult


@dataclass
class ThinkResult:
    """Outcome of one SpikingBrain "thinking" call.

    All arrays are float64 and immutable in the sense that downstream
    code must not mutate them (use ``.copy()`` if needed).
    """

    text: str
    confidence: float
    belief: np.ndarray
    spikes: SpikeEncodingResult
    plasticity: np.ndarray
    n_tokens: int = 0
    latency_s: float = 0.0
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Defensive normalisation: downstream ILF/quantum code assumes
        # ``belief`` is a probability vector.
        b = np.asarray(self.belief, dtype=float)
        if b.ndim != 1:
            b = b.ravel()
        s = float(b.sum())
        if s > 0:
            self.belief = b / s
        else:
            self.belief = np.ones_like(b) / max(b.size, 1)
        self.confidence = float(min(max(self.confidence, 0.0), 1.0))
