"""QuantumState — n-qubit complex state vector (numpy backend).

Self-contained, dependency-free quantum simulator suitable for
quantum-inspired neural computation in Q-SPEACE. Mirrors the API of
``cellular_speace/speace_core/cellular_brain/quantum/quantum_state.py``
so that Q-SPEACE can run standalone or be merged upstream.
"""
from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np


@dataclass
class MeasurementResult:
    """Outcome of a quantum measurement on one or more qubits."""

    bitstring: str
    probability: float
    collapsed_state: QuantumState


class QuantumState:
    """Complex state vector for n qubits (shape (2**n,), normalized)."""

    __slots__ = ("num_qubits", "amplitudes", "_rng")

    def __init__(
        self,
        num_qubits: int,
        initial_state: int | None = None,
        seed: int | None = None,
    ) -> None:
        if num_qubits < 1:
            raise ValueError("num_qubits must be >= 1")
        if num_qubits > 16:
            raise ValueError("num_qubits must be <= 16 for prototype use")
        self.num_qubits = num_qubits
        size = 1 << num_qubits
        amps = np.zeros(size, dtype=np.complex128)
        if initial_state is None:
            amps[0] = 1.0 + 0j
        elif 0 <= initial_state < size:
            amps[initial_state] = 1.0 + 0j
        else:
            raise ValueError(f"initial_state {initial_state} out of range [0, {size})")
        self.amplitudes = amps
        self._rng = np.random.default_rng(seed)

    @classmethod
    def from_amplitudes(
        cls, amplitudes: Iterable[complex], seed: int | None = None
    ) -> QuantumState:
        amps = np.array(list(amplitudes), dtype=np.complex128)
        if amps.ndim != 1:
            raise ValueError("amplitudes must be 1D")
        size = amps.shape[0]
        if size == 0 or (size & (size - 1)) != 0:
            raise ValueError(f"length {size} is not a power of 2")
        n = int(math.log2(size))
        norm = np.sqrt(np.sum(np.abs(amps) ** 2))
        if norm == 0:
            raise ValueError("zero vector cannot be normalized")
        obj = cls.__new__(cls)
        obj.num_qubits = n
        obj.amplitudes = amps / norm
        obj._rng = np.random.default_rng(seed)
        return obj

    @classmethod
    def tensor_product(
        cls, a: QuantumState, b: QuantumState, seed: int | None = None
    ) -> QuantumState:
        obj = cls.__new__(cls)
        obj.num_qubits = a.num_qubits + b.num_qubits
        obj.amplitudes = np.kron(a.amplitudes, b.amplitudes)
        obj._rng = np.random.default_rng(seed)
        return obj

    @classmethod
    def equal_superposition(
        cls, num_qubits: int, seed: int | None = None
    ) -> QuantumState:
        zero = np.array([1.0, 1.0], dtype=np.complex128) / math.sqrt(2.0)
        amps = zero.copy()
        for _ in range(num_qubits - 1):
            amps = np.kron(amps, zero)
        obj = cls.__new__(cls)
        obj.num_qubits = num_qubits
        obj.amplitudes = amps
        obj._rng = np.random.default_rng(seed)
        obj.normalize()
        return obj

    def normalize(self) -> None:
        norm = np.sqrt(np.sum(np.abs(self.amplitudes) ** 2))
        if norm > 0:
            self.amplitudes = self.amplitudes / norm

    def apply_unitary(self, unitary: np.ndarray) -> None:
        u = np.asarray(unitary, dtype=np.complex128)
        if u.shape != (self.amplitudes.shape[0],) * 2:
            raise ValueError("unitary shape incompatible with state size")
        diff = u.conj().T @ u - np.eye(u.shape[0], dtype=np.complex128)
        if np.max(np.abs(diff)) > 1e-6:
            raise ValueError("matrix is not unitary (tolerance 1e-6)")
        self.amplitudes = u @ self.amplitudes

    def apply_lindblad(
        self,
        jump_operators: list[tuple[int, np.ndarray]],
        rates: list[float],
        dt: float = 0.01,
    ) -> None:
        """Stochastic Lindblad evolution via Monte Carlo wavefunction method.

        For each jump operator L_k (2x2 matrix acting on qubit ``q``) with
        rate ``rates[k]``:
          1. Compute jump probability  p_k = rates[k] * dt * <psi|L_k^dag L_k|psi>
          2. If a random sample falls below p_k, apply L_k and renormalise.
        When no jump occurs the state is evolved under the non-Hermitian
        effective Hamiltonian  H_eff = -(i/2) Σ_k rates[k] * L_k^dag L_k.

        This reproduces the average Lindblad master equation over many
        trajectories.
        """
        n = self.num_qubits
        dim = 1 << n
        jump_prob = 0.0
        effective_h = np.zeros((dim, dim), dtype=np.complex128)

        def _kron_op(mat_2x2: np.ndarray, qubit: int) -> np.ndarray:
            op = np.array([1.0], dtype=np.complex128)
            for i in range(n):
                op = np.kron(op, mat_2x2 if i == qubit else np.eye(2, dtype=np.complex128))
            return op.reshape(dim, dim)

        for (q, l_mat), rate in zip(jump_operators, rates, strict=True):
            if rate <= 0:
                continue
            l_mat = np.asarray(l_mat, dtype=np.complex128)
            l_dag = l_mat.conj().T
            l_op = _kron_op(l_mat, q)
            l_dag_l_op = _kron_op(l_dag @ l_mat, q)

            exp_val = np.vdot(self.amplitudes, l_dag_l_op @ self.amplitudes)
            jump_prob += rate * dt * float(np.real(exp_val))
            effective_h -= 0.5j * rate * l_dag_l_op

        if self._rng.random() < min(jump_prob, 1.0):
            r = self._rng.random() * jump_prob
            cumulative = 0.0
            for (q, l_mat), rate in zip(jump_operators, rates, strict=True):
                if rate <= 0:
                    continue
                l_mat = np.asarray(l_mat, dtype=np.complex128)
                l_op = _kron_op(l_mat, q)
                l_dag_l_op = _kron_op(l_mat.conj().T @ l_mat, q)
                exp_val = np.vdot(self.amplitudes, l_dag_l_op @ self.amplitudes)
                cumulative += rate * dt * float(np.real(exp_val))
                if r <= cumulative:
                    self.amplitudes = l_op @ self.amplitudes
                    break
            self.normalize()
        else:
            u_eff = np.eye(dim, dtype=np.complex128) + effective_h * dt
            self.amplitudes = u_eff @ self.amplitudes
            self.normalize()

    def measure(self, qubit_index: int | None = None) -> MeasurementResult:
        if qubit_index is None:
            return self._measure_all()
        if not (0 <= qubit_index < self.num_qubits):
            raise ValueError(f"qubit_index {qubit_index} out of range")
        return self._measure_qubit(qubit_index)

    def measure_many(self, qubit_indices: Iterable[int]) -> list[MeasurementResult]:
        return [self.measure(q) for q in qubit_indices]

    def probabilities(self) -> np.ndarray:
        return np.abs(self.amplitudes) ** 2

    def phi_proxy(self, partition: int | None = None) -> float:
        """Proxy for integrated information Φ (IIT-inspired).

        Uses the quantum mutual information between two halves of the
        qubit register as a stand-in for informational integration.
        For a partition at qubit ``k``, the proxy is:
          Φ ≈ I(A:B) = S(ρ_A) + S(ρ_B) - S(ρ_AB)
        where S is the von Neumann entropy of the reduced density matrix.

        A value > 1.0 indicates significant integration (the whole is
        more than the sum of the parts). The maximum is bounded by
        2 * min(|A|, |B|) (in bits).
        """
        n = self.num_qubits
        if n < 2:
            return 0.0
        k = partition if partition is not None else n // 2
        k = max(1, min(k, n - 1))
        dim_a = 1 << k
        dim_b = 1 << (n - k)
        rho = np.outer(self.amplitudes, self.amplitudes.conj()).reshape(
            dim_a, dim_b, dim_a, dim_b
        )
        rho_a = np.trace(rho, axis1=1, axis2=3)
        rho_b = np.trace(rho, axis1=0, axis2=2)
        evals_a = np.linalg.eigvalsh(rho_a)
        evals_b = np.linalg.eigvalsh(rho_b)
        evals_ab = np.linalg.eigvalsh(
            np.outer(self.amplitudes, self.amplitudes.conj())
        )

        def entropy(evals):
            clipped = np.maximum(np.real(evals), 1e-12)
            return -np.sum(clipped * np.log2(clipped))

        s_a = entropy(evals_a)
        s_b = entropy(evals_b)
        s_ab = entropy(evals_ab)
        return float(max(0.0, s_a + s_b - s_ab))

    def is_entangled_with(self, other: QuantumState) -> bool:
        joint = np.kron(self.amplitudes, other.amplitudes)
        rho = np.outer(joint, joint.conj())
        sv = np.linalg.svd(rho, compute_uv=False)
        tol = 1e-6
        rank = int(np.sum(sv > tol * sv.max()))
        return rank > 1

    def fidelity_with(self, other: QuantumState) -> float:
        if self.amplitudes.shape != other.amplitudes.shape:
            raise ValueError("fidelity requires same-dimension states")
        inner = np.vdot(self.amplitudes, other.amplitudes)
        return float(np.abs(inner) ** 2)

    def to_density_matrix(self) -> np.ndarray:
        return np.outer(self.amplitudes, self.amplitudes.conj())

    def copy(self) -> QuantumState:
        obj = self.__new__(self.__class__)
        obj.num_qubits = self.num_qubits
        obj.amplitudes = self.amplitudes.copy()
        obj._rng = self._rng
        return obj

    def __repr__(self) -> str:
        nonzero = []
        for idx, amp in enumerate(self.amplitudes):
            if abs(amp) > 1e-9:
                nonzero.append(f"|{idx:0{self.num_qubits}b}>:{amp:.3f}")
        body = " + ".join(nonzero) if nonzero else "0"
        return f"QuantumState(n={self.num_qubits}, {body})"

    def _measure_all(self) -> MeasurementResult:
        probs = self.probabilities()
        outcome = int(self._rng.choice(len(probs), p=probs))
        prob = float(probs[outcome])
        new = QuantumState(num_qubits=self.num_qubits)
        new.amplitudes = np.zeros_like(self.amplitudes)
        new.amplitudes[outcome] = 1.0 + 0j
        bitstring = format(outcome, f"0{self.num_qubits}b")
        return MeasurementResult(bitstring=bitstring, probability=prob, collapsed_state=new)

    def _measure_qubit(self, qubit_index: int) -> MeasurementResult:
        probs = self.probabilities()
        p0 = 0.0
        for idx, p in enumerate(probs):
            bit = (idx >> (self.num_qubits - 1 - qubit_index)) & 1
            if bit == 0:
                p0 += p
        outcome_zero = self._rng.random() < p0
        new_amps = np.zeros_like(self.amplitudes)
        for idx, amp in enumerate(self.amplitudes):
            bit = (idx >> (self.num_qubits - 1 - qubit_index)) & 1
            target = (bit == 0) if outcome_zero else (bit == 1)
            if target:
                new_amps[idx] = amp
        norm = np.sqrt(np.sum(np.abs(new_amps) ** 2))
        if norm > 0:
            new_amps = new_amps / norm
        new = QuantumState(num_qubits=self.num_qubits)
        new.amplitudes = new_amps
        bit = "0" if outcome_zero else "1"
        prob = p0 if outcome_zero else (1.0 - p0)
        return MeasurementResult(bitstring=bit, probability=float(prob), collapsed_state=new)
