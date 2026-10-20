from __future__ import annotations

import math

import numpy as np


class InformationalLogicalField:
    """ILF with optional temporal smoothing (T-SPB-3-A).

    Two opt-in parameters control whether ``compute_q_star`` and the
    derived ``coherence_phi`` blend with their previous values:

    - ``q_star_ema``: blend coefficient α ∈ [0, 1) for ``q_star``.
      With α=0 (default) the field is bit-identical to the legacy
      implementation. With α>0 the freshly-computed q_star is mixed
      as ``_q_star ← α·prev + (1-α)·fresh`` before normalising.
    - ``coherence_phi_ema``: separate blend for the scalar φ. With
      α=0 the φ is the entropy of the raw q_star (legacy); with α>0
      it is smoothed across consecutive ``compute_q_star`` calls.

    Defaults preserve every existing call site; ``SpikingBrainCortex``
    opts in with α=0.5 to stabilise multi-turn apply.
    """

    def __init__(
        self,
        coherence_phi: float = 1.0,
        q_star_ema: float = 0.0,
        coherence_phi_ema: float = 0.0,
    ) -> None:
        if not (0.0 <= q_star_ema < 1.0):
            raise ValueError("q_star_ema must be in [0, 1)")
        if not (0.0 <= coherence_phi_ema < 1.0):
            raise ValueError("coherence_phi_ema must be in [0, 1)")
        self.coherence_phi = float(coherence_phi)
        self.q_star_ema = float(q_star_ema)
        self.coherence_phi_ema = float(coherence_phi_ema)
        self._agent_beliefs: dict[str, np.ndarray] = {}
        self._agent_weights: dict[str, float] = {}
        self._q_star: np.ndarray | None = None
        # Previous values for EMA blending. None on first compute.
        self._q_star_prev: np.ndarray | None = None
        self._phi_prev: float | None = None

    def register_agent(self, agent_id: str, weight: float = 1.0) -> None:
        self._agent_weights[agent_id] = weight

    def set_belief(self, agent_id: str, distribution: np.ndarray) -> None:
        p = np.asarray(distribution, dtype=float).flatten()
        p = np.abs(p)
        norm = np.sum(p)
        if norm > 0:
            p = p / norm
        self._agent_beliefs[agent_id] = p

    def set_weight(self, agent_id: str, weight: float) -> None:
        if agent_id in self._agent_weights:
            self._agent_weights[agent_id] = weight

    @property
    def q_star(self) -> np.ndarray:
        if self._q_star is None:
            self.compute_q_star()
        assert self._q_star is not None
        return self._q_star

    def compute_q_star(self) -> np.ndarray:
        if not self._agent_beliefs:
            self._q_star = np.array([1.0])
            return self._q_star
        beliefs = list(self._agent_beliefs.values())
        dim = beliefs[0].shape[0]
        for p in beliefs:
            if p.shape[0] != dim:
                raise ValueError(f"belief dimension mismatch: {p.shape[0]} != {dim}")
        log_q = np.zeros(dim, dtype=np.float64)
        for agent_id, p in self._agent_beliefs.items():
            w = self._agent_weights.get(agent_id, 1.0)
            eps = 1e-12
            log_q += w * np.log(np.maximum(p, eps))
        log_q_max = np.max(log_q)
        log_q_shifted = log_q - log_q_max
        q_unorm = np.exp(log_q_shifted)
        total = np.sum(q_unorm)
        q_fresh = q_unorm / total if total > 0 else np.ones(dim) / dim

        # T-SPB-3-A: optional EMA blend with previous q_star.
        if (
            self.q_star_ema > 0.0
            and self._q_star_prev is not None
            and self._q_star_prev.shape == q_fresh.shape
        ):
            blended = self.q_star_ema * self._q_star_prev + (1.0 - self.q_star_ema) * q_fresh
            s = float(np.sum(blended))
            if s > 0:
                self._q_star = blended / s
            else:
                self._q_star = q_fresh
        else:
            self._q_star = q_fresh

        coherence = 1.0 - (
            -np.sum(self._q_star * np.log(np.maximum(self._q_star, 1e-12))) / math.log(max(dim, 2))
        )

        # T-SPB-3-A: optional EMA blend on the scalar coherence_phi.
        if self.coherence_phi_ema > 0.0 and self._phi_prev is not None:
            blended_phi = (
                self.coherence_phi_ema * self._phi_prev + (1.0 - self.coherence_phi_ema) * coherence
            )
            self.coherence_phi = float(np.clip(blended_phi, 0.0, 1.0))
        else:
            self.coherence_phi = float(coherence)

        self._q_star_prev = self._q_star.copy()
        self._phi_prev = self.coherence_phi
        return self._q_star

    def update(self, state_vector: np.ndarray) -> None:
        v = np.asarray(state_vector, dtype=float)
        norm = np.sqrt(np.sum(v**2))
        if norm > 0:
            v = v / norm
        probs = v**2
        entropy = -np.sum(probs * np.log(probs + 1e-12))
        max_entropy = math.log(max(len(probs), 2))
        self.coherence_phi = float(1.0 - entropy / max_entropy)

    @property
    def s_info(self) -> float:
        return float(1.0 - self.coherence_phi)

    def adaptive_clock_rate(self) -> float:
        s = max(self.s_info, 1e-6)
        return 10.0 / math.sqrt(s)

    def clear_beliefs(self) -> None:
        self._agent_beliefs.clear()
        self._q_star = None
        self._q_star_prev = None
        self._phi_prev = None
