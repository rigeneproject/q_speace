"""Quantum Evolution Engine — Grover, QAOA, Quantum Kernel (T42-T45)."""
# ruff: noqa: N806, N803 — standard physics notation (H, X, U for operators)
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from ..quantum import GateType, QuantumGates, QuantumState


@dataclass
class QEEResult:
    candidate_id: str
    score: float
    confidence: float
    method: str
    details: dict = field(default_factory=dict)


class QuantumOracle:
    """Grover Search oracle for finding promising configurations in DNA.

    Uses amplitude amplification to search through mutation strategies.
    On a classical simulator this provides quadratic speedup simulation.
    """

    def __init__(self, num_qubits: int = 8, seed: int | None = None) -> None:
        self.num_qubits = min(num_qubits, 12)
        self._rng = np.random.default_rng(seed)

    def mark_good_states(self, state: QuantumState, items: list[float], threshold: float) -> QuantumState:
        n = self.num_qubits
        dim = 1 << n
        new_amps = state.amplitudes.copy()
        for idx in range(min(len(items), dim)):
            if items[idx] > threshold:
                new_amps[idx] = -new_amps[idx]
        result = QuantumState.__new__(QuantumState)
        result.num_qubits = n
        result.amplitudes = new_amps
        result._rng = self._rng
        return result

    def diffusion(self, state: QuantumState) -> QuantumState:
        n = self.num_qubits
        1 << n
        avg = np.mean(state.amplitudes)
        new_amps = 2.0 * avg - state.amplitudes
        result = QuantumState.__new__(QuantumState)
        result.num_qubits = n
        result.amplitudes = new_amps
        result._rng = self._rng
        return result

    def search(
        self, items: list[float], threshold: float, num_iterations: int | None = None
    ) -> tuple[int, float]:
        n = self.num_qubits
        dim = 1 << n
        target_size = sum(1 for v in items[:dim] if v > threshold)
        if target_size == 0:
            return (-1, 0.0)
        if num_iterations is None:
            num_iterations = max(1, int((math.pi / 4) * math.sqrt(dim / target_size)))
        state = QuantumState.equal_superposition(n, seed=self._rng.integers(0, 2**31))
        for _ in range(num_iterations):
            state = self.mark_good_states(state, items, threshold)
            state = self.diffusion(state)
        probs = state.probabilities()
        best_idx = int(np.argmax(probs))
        best_score = items[best_idx] if best_idx < len(items) else 0.0
        return (best_idx, float(best_score))


@dataclass
class QAOASelector:
    """QAOA-inspired multi-objective mutation selection.

    Selects the best set of mutations balancing cost, risk, benefit, and energy.
    Uses a classical simulation of the quantum variational approach.
    """

    num_qubits: int = 8
    gamma_range: tuple[float, float, int] = (0.0, 2.0, 10)
    beta_range: tuple[float, float, int] = (0.0, math.pi, 10)

    def _cost_hamiltonian(self, proposals: list[dict]) -> np.ndarray:
        dim = 1 << min(len(proposals), self.num_qubits)
        H = np.zeros((dim, dim), dtype=np.float64)
        for i, p in enumerate(proposals[:dim]):
            for j, q in enumerate(proposals[:dim]):
                if i == j:
                    continue
                benefit_i = p.get("expected_impact", 0.0)
                risk_j = q.get("risk", 0.5)
                energy_i = p.get("energy_cost", 0.1)
                H[i, j] = -benefit_i * (1.0 - risk_j) / (energy_i + 0.01)
        return H

    def _mixer_hamiltonian(self, num_nodes: int) -> np.ndarray:
        dim = 1 << min(num_nodes, self.num_qubits)
        X = np.array([[0, 1], [1, 0]], dtype=np.float64)
        H = np.zeros((dim, dim), dtype=np.float64)
        for k in range(min(num_nodes, self.num_qubits)):
            op = np.array([1.0], dtype=np.float64)
            for i in range(min(num_nodes, self.num_qubits)):
                op = np.kron(op, X if i == k else np.eye(2, dtype=np.float64))
            H += op.reshape(dim, dim)
        return H

    def select(self, proposals: list[dict], num_selected: int = 3) -> list[int]:
        if not proposals:
            return []
        num_nodes = min(len(proposals), self.num_qubits)
        Hc = self._cost_hamiltonian(proposals)
        Hm = self._mixer_hamiltonian(num_nodes)
        dim = 1 << num_nodes

        best_energy = float("inf")
        best_state = 0
        gammas = np.linspace(*self.gamma_range)
        betas = np.linspace(*self.beta_range)

        for gamma in gammas:
            for beta in betas:
                Uc = np.eye(dim, dtype=np.float64) - 1j * gamma * Hc
                Um = np.eye(dim, dtype=np.float64) - 1j * beta * Hm
                psi = np.ones(dim, dtype=np.complex128) / math.sqrt(dim)
                psi = Uc @ Um @ psi
                energy = float(np.real(np.vdot(psi, Hc @ psi)))
                if energy < best_energy:
                    best_energy = energy
                    best_state = np.argmax(np.abs(psi))

        selected = []
        for i in range(num_nodes):
            if (best_state >> i) & 1:
                selected.append(i)
        return selected[:num_selected]


class QuantumKernelClassifier:
    """Quantum Kernel for classifying evolutionary patterns.

    Projects mutation features into a quantum Hilbert space via a
    feature map and computes similarity via the quantum kernel trick.
    """

    def __init__(self, num_qubits: int = 6, seed: int | None = None) -> None:
        self.num_qubits = min(num_qubits, 10)
        self._rng = np.random.default_rng(seed)
        self._support_vectors: list[np.ndarray] = []
        self._support_labels: list[float] = []
        self._trained = False

    def _feature_map(self, x: np.ndarray, n: int) -> QuantumState:
        state = QuantumState(num_qubits=n, seed=self._rng.integers(0, 2**31))
        for i in range(min(len(x), n)):
            angle = float(x[i]) * math.pi
            u = QuantumGates.single_qubit(GateType.RY, n, i, angle)
            state.apply_unitary(u)
        for i in range(min(len(x) - 1, n - 1)):
            if i + 1 < n:
                u = QuantumGates.two_qubit(GateType.CNOT, n, i, i + 1)
                state.apply_unitary(u)
        return state

    def _kernel(self, x1: np.ndarray, x2: np.ndarray) -> float:
        n = self.num_qubits
        psi1 = self._feature_map(x1, n)
        psi2 = self._feature_map(x2, n)
        overlap = abs(np.vdot(psi1.amplitudes, psi2.amplitudes)) ** 2
        return float(overlap)

    def fit(self, X: list[np.ndarray], y: list[float]) -> None:
        self._support_vectors = list(X)
        self._support_labels = list(y)
        self._trained = True

    def predict(self, x: np.ndarray) -> float:
        if not self._trained:
            return 0.0
        weights = []
        for sv, label in zip(self._support_vectors, self._support_labels, strict=False):
            k = self._kernel(x, sv)
            weights.append(k * label)
        return float(np.mean(weights)) if weights else 0.0

    def predict_proba(self, x: np.ndarray) -> float:
        raw = self.predict(x)
        return 1.0 / (1.0 + math.exp(-raw))


@dataclass
class QuantumEvolutionEngine:
    """Integrated QEE — combines Grover, QAOA, and Quantum Kernel.

    Operates as a consultative engine within the Evolution Council cycle.
    All candidates are validated by classical sandbox execution.
    """

    oracle: QuantumOracle = field(default_factory=lambda: QuantumOracle(num_qubits=8))
    qaoa: QAOASelector = field(default_factory=lambda: QAOASelector(num_qubits=8))
    kernel: QuantumKernelClassifier = field(default_factory=lambda: QuantumKernelClassifier(num_qubits=6))
    enabled: bool = True

    def propose_candidates(
        self,
        strategies: list[dict],
        context: dict,
        top_k: int = 3,
    ) -> list[QEEResult]:
        if not self.enabled or not strategies:
            return []

        results: list[QEEResult] = []

        scores = [s.get("score", 0.5) for s in strategies]
        threshold = float(np.mean(scores) if scores else 0.5)
        idx, grover_score = self.oracle.search(scores, threshold)
        if idx >= 0:
            results.append(QEEResult(
                candidate_id=strategy_id(strategies, idx),
                score=grover_score,
                confidence=min(1.0, grover_score),
                method="grover",
            ))

        qaoa_selected = self.qaoa.select(strategies, num_selected=top_k)
        for i in qaoa_selected:
            if i < len(strategies):
                s = strategies[i]
                results.append(QEEResult(
                    candidate_id=s.get("id", str(i)),
                    score=s.get("expected_impact", 0.5),
                    confidence=1.0 - s.get("risk", 0.5),
                    method="qaoa",
                    details={"energy_cost": s.get("energy_cost", 0.1)},
                ))

        if self.kernel._trained and strategies:
            for i, s in enumerate(strategies[:top_k]):
                features = _strategy_to_features(s)
                prob = self.kernel.predict_proba(features)
                if prob > 0.6:
                    results.append(QEEResult(
                        candidate_id=s.get("id", str(i)),
                        score=float(prob),
                        confidence=float(prob),
                        method="quantum_kernel",
                    ))

        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def train_kernel(self, X: list[np.ndarray], y: list[float]) -> None:
        self.kernel.fit(X, y)


def strategy_id(strategies: list[dict], idx: int) -> str:
    if 0 <= idx < len(strategies):
        return strategies[idx].get("id", str(idx))
    return str(idx)


def _strategy_to_features(s: dict) -> np.ndarray:
    return np.array([
        s.get("expected_impact", 0.5),
        1.0 - s.get("risk", 0.5),
        s.get("confidence", 0.5),
        s.get("energy_cost", 0.1),
        s.get("novelty", 0.0),
    ], dtype=np.float64)
