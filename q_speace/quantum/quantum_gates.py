"""QuantumGates — factory of standard unitary gates for QuantumState.

All gates are returned as dense 2^n x 2^n complex matrices. Mirrors the
API of ``cellular_speace/.../quantum_gates.py``.
"""
from __future__ import annotations

import math
from enum import StrEnum

import numpy as np


class GateType(StrEnum):
    H = "H"
    X = "X"
    Y = "Y"
    Z = "Z"
    S = "S"
    T = "T"
    CNOT = "CNOT"
    RX = "RX"
    RY = "RY"
    RZ = "RZ"
    SWAP = "SWAP"


_I2 = np.eye(2, dtype=np.complex128)
_H = (1.0 / math.sqrt(2.0)) * np.array([[1, 1], [1, -1]], dtype=np.complex128)
_X = np.array([[0, 1], [1, 0]], dtype=np.complex128)
_Y = np.array([[0, -1j], [1j, 0]], dtype=np.complex128)
_Z = np.array([[1, 0], [0, -1]], dtype=np.complex128)
_S = np.array([[1, 0], [0, 1j]], dtype=np.complex128)
_T = np.array([[1, 0], [0, np.exp(1j * math.pi / 4)]], dtype=np.complex128)


class QuantumGates:
    """Factory of standard quantum gates as dense unitary matrices."""

    @staticmethod
    def single_qubit(
        gate: GateType, num_qubits: int, target: int, angle: float | None = None
    ) -> np.ndarray:
        if not (0 <= target < num_qubits):
            raise ValueError(f"target {target} out of range [0, {num_qubits})")
        base = QuantumGates._base_single(gate, angle)
        mats = [_I2] * num_qubits
        mats[target] = base
        result = mats[0]
        for m in mats[1:]:
            result = np.kron(result, m)
        return result

    @staticmethod
    def two_qubit(
        gate: GateType,
        num_qubits: int,
        control: int,
        target: int,
        angle: float | None = None,
    ) -> np.ndarray:
        if not (0 <= control < num_qubits) or not (0 <= target < num_qubits):
            raise ValueError(f"control/target out of range: c={control} t={target}")
        if control == target:
            raise ValueError("control and target must differ")
        if gate == GateType.CNOT:
            return QuantumGates._cnot(num_qubits, control, target)
        if gate == GateType.SWAP:
            return QuantumGates._swap(num_qubits, control, target)
        if gate in (GateType.RX, GateType.RY, GateType.RZ):
            return QuantumGates._controlled_rotation(
                num_qubits, control, target, gate, angle or 0.0
            )
        raise ValueError(f"two-qubit gate {gate} not supported")

    @staticmethod
    def _base_single(gate: GateType, angle: float | None) -> np.ndarray:
        if gate == GateType.H:
            return _H.copy()
        if gate == GateType.X:
            return _X.copy()
        if gate == GateType.Y:
            return _Y.copy()
        if gate == GateType.Z:
            return _Z.copy()
        if gate == GateType.S:
            return _S.copy()
        if gate == GateType.T:
            return _T.copy()
        if gate == GateType.RX:
            return QuantumGates._rx(angle or 0.0)
        if gate == GateType.RY:
            return QuantumGates._ry(angle or 0.0)
        if gate == GateType.RZ:
            return QuantumGates._rz(angle or 0.0)
        raise ValueError(f"single-qubit gate {gate} not supported")

    @staticmethod
    def _rx(theta: float) -> np.ndarray:
        c = math.cos(theta / 2.0)
        s = math.sin(theta / 2.0)
        return np.array([[c, -1j * s], [-1j * s, c]], dtype=np.complex128)

    @staticmethod
    def _ry(theta: float) -> np.ndarray:
        c = math.cos(theta / 2.0)
        s = math.sin(theta / 2.0)
        return np.array([[c, -s], [s, c]], dtype=np.complex128)

    @staticmethod
    def _rz(theta: float) -> np.ndarray:
        half = theta / 2.0
        return np.array(
            [
                [complex(math.cos(-half), math.sin(-half)), 0],
                [0, complex(math.cos(half), math.sin(half))],
            ],
            dtype=np.complex128,
        )

    @staticmethod
    def _cnot(num_qubits: int, control: int, target: int) -> np.ndarray:
        size = 1 << num_qubits
        mat = np.zeros((size, size), dtype=np.complex128)
        for idx in range(size):
            c_bit = (idx >> (num_qubits - 1 - control)) & 1
            if c_bit == 1:
                flipped = idx ^ (1 << (num_qubits - 1 - target))
                mat[flipped, idx] = 1.0 + 0j
            else:
                mat[idx, idx] = 1.0 + 0j
        return mat

    @staticmethod
    def _swap(num_qubits: int, a: int, b: int) -> np.ndarray:
        c1 = QuantumGates._cnot(num_qubits, a, b)
        c2 = QuantumGates._cnot(num_qubits, b, a)
        return c1 @ c2 @ c1

    @staticmethod
    def _controlled_rotation(
        num_qubits: int, control: int, target: int, gate: GateType, angle: float
    ) -> np.ndarray:
        size = 1 << num_qubits
        if gate == GateType.RX:
            base = QuantumGates._rx(angle)
        elif gate == GateType.RY:
            base = QuantumGates._ry(angle)
        else:
            base = QuantumGates._rz(angle)
        mat = np.zeros((size, size), dtype=np.complex128)
        for idx in range(size):
            c_bit = (idx >> (num_qubits - 1 - control)) & 1
            t_bit = (idx >> (num_qubits - 1 - target)) & 1
            if c_bit == 0:
                mat[idx, idx] = 1.0 + 0j
            else:
                row = idx ^ (1 << (num_qubits - 1 - target))
                mat[row, idx] = base[1 - t_bit, t_bit]
        return mat
