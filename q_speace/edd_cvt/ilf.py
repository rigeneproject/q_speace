from __future__ import annotations

import math

import numpy as np


class InformationalLogicalField:
    def __init__(self, coherence_phi: float = 1.0) -> None:
        self.coherence_phi = float(coherence_phi)
        self._agent_beliefs: dict[str, np.ndarray] = {}
        self._agent_weights: dict[str, float] = {}
        self._q_star: np.ndarray | None = None

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
        if total > 0:
            self._q_star = q_unorm / total
        else:
            self._q_star = np.ones(dim) / dim
        coherence = 1.0 - (
            -np.sum(self._q_star * np.log(np.maximum(self._q_star, 1e-12))) / math.log(max(dim, 2))
        )
        self.coherence_phi = float(coherence)
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
