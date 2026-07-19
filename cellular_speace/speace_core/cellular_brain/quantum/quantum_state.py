"""QuantumState — n-qubit complex state vector with numpy backend.

This is a small, dependency-free quantum simulator suitable for
cognitive/quantum-inspired neural computations. It supports:
  - n-qubit state vectors of shape (2**n,)
  - Unitary gate application via matrix multiplication
  - Probabilistic measurement with collapse
  - Tensor product composition of two states
  - Entanglement helpers

The state is stored as a complex128 numpy array, normalized so that
sum(|amp|^2) == 1.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

import numpy as np


@dataclass
class MeasurementResult:
    """Outcome of a quantum measurement on one or more qubits."""
    bitstring: str
    probability: float
    collapsed_state: "QuantumState"


class QuantumState:
    """Complex state vector for n qubits.

    The internal `amplitudes` is a numpy ndarray of shape (2**n,)
    normalized so that sum(|amp|^2) == 1.
    """

    __slots__ = ("num_qubits", "amplitudes", "_rng")

    def __init__(
        self,
        num_qubits: int,
        initial_state: Optional[int] = None,
        seed: Optional[int] = None,
    ) -> None:
        if num_qubits < 1:
            raise ValueError("num_qubits must be >= 1")
        if num_qubits > 16:
            # 2**16 = 65536 amplitudes; still tractable on numpy.
            # Above 16 the state becomes too large for prototyping.
            raise ValueError("num_qubits must be <= 16 for prototype use")
        self.num_qubits = num_qubits
        size = 1 << num_qubits
        amps = np.zeros(size, dtype=np.complex128)
        if initial_state is None:
            amps[0] = 1.0 + 0j  # |0...0>
        elif 0 <= initial_state < size:
            amps[initial_state] = 1.0 + 0j
        else:
            raise ValueError(
                f"initial_state {initial_state} out of range [0, {size})"
            )
        self.amplitudes = amps
        self._rng = np.random.default_rng(seed)

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    @classmethod
    def from_amplitudes(
        cls,
        amplitudes: Iterable[complex],
        seed: Optional[int] = None,
    ) -> "QuantumState":
        """Build a QuantumState from a complex iterable, auto-normalized."""
        amps = np.array(list(amplitudes), dtype=np.complex128)
        if amps.ndim != 1:
            raise ValueError("amplitudes must be 1D")
        size = amps.shape[0]
        if size == 0 or (size & (size - 1)) != 0:
            raise ValueError(
                f"length {size} is not a power of 2"
            )
        n = int(math.log2(size))
        norm = np.sqrt(np.sum(np.abs(amps) ** 2))
        if norm == 0:
            raise ValueError("zero vector cannot be normalized")
        amps = amps / norm
        obj = cls.__new__(cls)
        obj.num_qubits = n
        obj.amplitudes = amps
        obj._rng = np.random.default_rng(seed)
        return obj

    @classmethod
    def tensor_product(
        cls,
        a: "QuantumState",
        b: "QuantumState",
        seed: Optional[int] = None,
    ) -> "QuantumState":
        """Compute |a> ⊗ |b> (Kronecker product of amplitudes)."""
        amps = np.kron(a.amplitudes, b.amplitudes)
        obj = cls.__new__(cls)
        obj.num_qubits = a.num_qubits + b.num_qubits
        obj.amplitudes = amps
        obj._rng = np.random.default_rng(seed)
        return obj

    @classmethod
    def equal_superposition(
        cls,
        num_qubits: int,
        seed: Optional[int] = None,
    ) -> "QuantumState":
        """Build (|0> + |1>) ^ n / sqrt(2^n)."""
        # Build the n=1 equal superposition directly, then tensor up.
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

    # ------------------------------------------------------------------
    # Manipulation
    # ------------------------------------------------------------------

    def normalize(self) -> None:
        norm = np.sqrt(np.sum(np.abs(self.amplitudes) ** 2))
        if norm > 0:
            self.amplitudes = self.amplitudes / norm

    def apply_unitary(self, unitary: np.ndarray) -> None:
        """Apply a 2^n x 2^n unitary matrix to the state."""
        u = np.asarray(unitary, dtype=np.complex128)
        if u.shape != (self.amplitudes.shape[0],) * 2:
            raise ValueError(
                f"unitary shape {u.shape} incompatible with "
                f"state size {self.amplitudes.shape[0]}"
            )
        # Optional unitarity check (cheap for small n, so we run it).
        diff = u.conj().T @ u - np.eye(u.shape[0], dtype=np.complex128)
        if np.max(np.abs(diff)) > 1e-6:
            raise ValueError("matrix is not unitary (within tolerance 1e-6)")
        self.amplitudes = u @ self.amplitudes

    def measure(self, qubit_index: Optional[int] = None) -> MeasurementResult:
        """Measure one qubit (or all qubits if qubit_index is None).

        Collapses the state to a definite outcome.
        """
        if qubit_index is None:
            return self._measure_all()
        if not (0 <= qubit_index < self.num_qubits):
            raise ValueError(
                f"qubit_index {qubit_index} out of range "
                f"[0, {self.num_qubits})"
            )
        return self._measure_qubit(qubit_index)

    def measure_many(
        self,
        qubit_indices: Iterable[int],
    ) -> List[MeasurementResult]:
        """Measure a list of qubits sequentially (each collapses)."""
        return [self.measure(q) for q in qubit_indices]

    def probabilities(self) -> np.ndarray:
        """Return |amp|^2 for each basis state."""
        return np.abs(self.amplitudes) ** 2

    def is_entangled_with(self, other: "QuantumState") -> bool:
        """Check entanglement via Schmidt rank.

        Treats self as the joint state of a bipartite system where
        self has (n_a + n_b) qubits and other.num_qubits = n_b.
        Reshapes the state vector into a (2**n_a x 2**n_b) matrix
        and performs SVD; rank > 1 indicates entanglement.
        """
        total = self.num_qubits
        n_b = other.num_qubits
        n_a = total - n_b
        if n_a < 1 or n_b < 1:
            return False
        dim_a = 1 << n_a
        dim_b = 1 << n_b
        if self.amplitudes.shape[0] != dim_a * dim_b:
            joint = np.kron(self.amplitudes, other.amplitudes)
            if joint.shape[0] != dim_a * dim_b:
                return False
            psi = joint.reshape(dim_a, dim_b)
        else:
            psi = self.amplitudes.reshape(dim_a, dim_b)
        sv = np.linalg.svd(psi, compute_uv=False)
        tol = 1e-6
        rank = int(np.sum(sv > tol * sv.max()))
        return rank > 1

    def fidelity_with(self, other: "QuantumState") -> float:
        """|<self|other>|^2 fidelity with another pure state."""
        if self.amplitudes.shape != other.amplitudes.shape:
            raise ValueError(
                "fidelity requires same-dimension states "
                f"({self.amplitudes.shape} vs {other.amplitudes.shape})"
            )
        inner = np.vdot(self.amplitudes, other.amplitudes)
        return float(np.abs(inner) ** 2)

    def to_density_matrix(self) -> np.ndarray:
        return np.outer(self.amplitudes, self.amplitudes.conj())

    def copy(self) -> "QuantumState":
        obj = self.__new__(self.__class__)
        obj.num_qubits = self.num_qubits
        obj.amplitudes = self.amplitudes.copy()
        obj._rng = self._rng
        return obj

    def __repr__(self) -> str:
        # Show only non-zero amplitudes to keep repr compact.
        nonzero = []
        for idx, amp in enumerate(self.amplitudes):
            if abs(amp) > 1e-9:
                nonzero.append(f"|{idx:0{self.num_qubits}b}>:{amp:.3f}")
        body = " + ".join(nonzero) if nonzero else "0"
        return f"QuantumState(n={self.num_qubits}, {body})"

    # ------------------------------------------------------------------
    # Internal measurement
    # ------------------------------------------------------------------

    def _measure_all(self) -> MeasurementResult:
        probs = self.probabilities()
        outcome = int(self._rng.choice(len(probs), p=probs))
        prob = float(probs[outcome])
        new = QuantumState(num_qubits=self.num_qubits, seed=None)
        new.amplitudes = np.zeros_like(self.amplitudes)
        new.amplitudes[outcome] = 1.0 + 0j
        bitstring = format(outcome, f"0{self.num_qubits}b")
        return MeasurementResult(bitstring=bitstring, probability=prob, collapsed_state=new)

    def _measure_qubit(self, qubit_index: int) -> MeasurementResult:
        # Probability that qubit q is |0> = sum of probs where bit q == 0
        probs = self.probabilities()
        p0 = 0.0
        for idx, p in enumerate(probs):
            bit = (idx >> (self.num_qubits - 1 - qubit_index)) & 1
            if bit == 0:
                p0 += p
        r = self._rng.random()
        outcome_zero = r < p0
        # Project state
        new_amps = np.zeros_like(self.amplitudes)
        for idx, amp in enumerate(self.amplitudes):
            bit = (idx >> (self.num_qubits - 1 - qubit_index)) & 1
            target = (bit == 0) if outcome_zero else (bit == 1)
            if target:
                new_amps[idx] = amp
        # Renormalize
        norm = np.sqrt(np.sum(np.abs(new_amps) ** 2))
        if norm > 0:
            new_amps = new_amps / norm
        new = QuantumState(num_qubits=self.num_qubits, seed=None)
        new.amplitudes = new_amps
        bit = "0" if outcome_zero else "1"
        prob = p0 if outcome_zero else (1.0 - p0)
        return MeasurementResult(bitstring=bit, probability=float(prob), collapsed_state=new)
