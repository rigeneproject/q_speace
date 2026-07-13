"""QuantumBrainSimulator — named-role quantum circuits.

A circuit maps logical roles (e.g. "memory", "decision") to qubit
indices, applies single/two-qubit gates, and measures at the end.
"""
from __future__ import annotations

from dataclasses import dataclass

from .quantum_gates import GateType, QuantumGates
from .quantum_state import QuantumState


@dataclass
class _GateOp:
    gate: GateType
    target: str | None = None
    control: str | None = None
    angle: float | None = None


class BrainQuantumCircuit:
    """A named-role quantum circuit."""

    def __init__(self, name: str = "circuit") -> None:
        self.name = name
        self._roles: list[str] = []
        self._role_index: dict[str, int] = {}
        self._gates: list[_GateOp] = []

    @property
    def num_qubits(self) -> int:
        return len(self._roles)

    def add_qubit(self, role: str) -> int:
        if role in self._role_index:
            return self._role_index[role]
        idx = len(self._roles)
        self._roles.append(role)
        self._role_index[role] = idx
        return idx

    def add_gate(
        self,
        gate: GateType,
        target: str | None = None,
        control: str | None = None,
        angle: float | None = None,
    ) -> None:
        self._gates.append(_GateOp(gate=gate, target=target, control=control, angle=angle))

    def role_of(self, qubit_index: int) -> str:
        return self._roles[qubit_index]

    def gates(self) -> list[_GateOp]:
        return list(self._gates)


class QuantumBrainSimulator:
    """Runs BrainQuantumCircuit objects on a numpy QuantumState."""

    def __init__(self, seed: int | None = None) -> None:
        self._seed = seed

    def run(
        self, circuit: BrainQuantumCircuit, measure_all: bool = True
    ) -> list[tuple[str, str]]:
        n = circuit.num_qubits
        if n == 0:
            return []
        state = QuantumState(num_qubits=n, seed=self._seed)
        for op in circuit.gates():
            if op.control is not None:
                c = circuit._role_index[op.control]
                t = circuit._role_index[op.target]
                u = QuantumGates.two_qubit(op.gate, n, c, t, angle=op.angle)
            else:
                t = circuit._role_index[op.target]
                u = QuantumGates.single_qubit(op.gate, n, t, angle=op.angle)
            state.apply_unitary(u)
        results: list[tuple[str, str]] = []
        if measure_all:
            mr = state.measure()
            for i, bit in enumerate(mr.bitstring):
                results.append((circuit.role_of(i), bit))
        return results

    def state(self, circuit: BrainQuantumCircuit) -> QuantumState:
        n = circuit.num_qubits
        state = QuantumState(num_qubits=n, seed=self._seed)
        for op in circuit.gates():
            if op.control is not None:
                u = QuantumGates.two_qubit(
                    op.gate, n, circuit._role_index[op.control],
                    circuit._role_index[op.target], angle=op.angle,
                )
            else:
                u = QuantumGates.single_qubit(
                    op.gate, n, circuit._role_index[op.target], angle=op.angle
                )
            state.apply_unitary(u)
        return state
