"""QuantumBrainSimulator — orchestrate a small quantum brain circuit.

A BrainQuantumCircuit maps logical "qubit roles" to physical qubit
indices and stores an associated QuantumState. The simulator:
  - applies gates specified by role
  - tracks entanglement between roles
  - returns measurement outcomes

This is intended for cognitive / quantum-inspired experiments where
small (4-8 qubit) circuits are mixed with the rest of the SPEACE
brain. It is not a competitor to Qiskit.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from speace_core.cellular_brain.quantum.quantum_gates import GateType, QuantumGates
from speace_core.cellular_brain.quantum.quantum_state import QuantumState


@dataclass
class GateInstruction:
    """A single gate in a brain quantum circuit.

    `target` is the role name (e.g. "memory", "decision").
    `control` is required only for two-qubit gates.
    """
    gate: GateType
    target: str
    control: Optional[str] = None
    angle: Optional[float] = None


@dataclass
class BrainQuantumCircuit:
    """A small quantum circuit with named qubit roles."""
    name: str
    roles: List[str] = field(default_factory=list)
    instructions: List[GateInstruction] = field(default_factory=list)
    state: Optional[QuantumState] = None
    initial_states: Dict[str, int] = field(default_factory=dict)

    def add_qubit(self, role: str, initial: int = 0) -> None:
        if role in self.roles:
            raise ValueError(f"role {role} already exists")
        self.roles.append(role)
        self.initial_states[role] = initial

    def add_gate(
        self,
        gate: GateType,
        target: str,
        control: Optional[str] = None,
        angle: Optional[float] = None,
    ) -> None:
        if target not in self.roles:
            raise ValueError(f"unknown target role {target}")
        if control is not None and control not in self.roles:
            raise ValueError(f"unknown control role {control}")
        self.instructions.append(
            GateInstruction(gate=gate, target=target, control=control, angle=angle)
        )


class QuantumBrainSimulator:
    """Runs BrainQuantumCircuits and produces measurements.

    Design choices:
      - All circuits use a single shared QuantumState. Roles are
        mapped to qubit indices in registration order.
      - Entanglement between two roles is inferred when a two-qubit
        gate is applied between them; the simulator also provides an
        explicit entangle() method to record user-asserted pairs.
    """

    def __init__(self) -> None:
        self.entanglements: List[Tuple[str, str]] = []

    def run(
        self,
        circuit: BrainQuantumCircuit,
        measure: bool = True,
    ) -> Optional[List[Tuple[str, str]]]:
        """Execute all instructions; return measurements if `measure`."""
        if not circuit.roles:
            circuit.state = None
            return None
        circuit.state = QuantumState(
            num_qubits=len(circuit.roles),
        )
        for role, init in circuit.initial_states.items():
            if init not in (0, 1):
                continue
            idx = circuit.roles.index(role)
            if init == 1:
                x = QuantumGates.single_qubit(GateType.X, len(circuit.roles), idx)
                circuit.state.apply_unitary(x)
        for ins in circuit.instructions:
            self._apply(circuit, ins)
        if not measure:
            return None
        return self.measure_all(circuit)

    def measure_all(
        self,
        circuit: BrainQuantumCircuit,
    ) -> List[Tuple[str, str]]:
        if circuit.state is None:
            return []
        result = circuit.state.measure()
        out: List[Tuple[str, str]] = []
        for i, role in enumerate(circuit.roles):
            bit = result.bitstring[i] if i < len(result.bitstring) else "0"
            out.append((role, bit))
        return out

    def entangle(self, role_a: str, role_b: str) -> None:
        if role_a == role_b:
            raise ValueError("cannot entangle a role with itself")
        if (role_a, role_b) not in self.entanglements and (role_b, role_a) not in self.entanglements:
            self.entanglements.append((role_a, role_b))

    def _apply(self, circuit: BrainQuantumCircuit, ins: GateInstruction) -> None:
        n = len(circuit.roles)
        target_idx = circuit.roles.index(ins.target)
        if ins.control is None:
            if ins.gate in (GateType.H, GateType.X, GateType.Y, GateType.Z,
                            GateType.S, GateType.T, GateType.RX,
                            GateType.RY, GateType.RZ):
                u = QuantumGates.single_qubit(ins.gate, n, target_idx, ins.angle)
                circuit.state.apply_unitary(u)
            else:
                raise ValueError(f"gate {ins.gate} requires a control qubit")
        else:
            control_idx = circuit.roles.index(ins.control)
            u = QuantumGates.two_qubit(
                ins.gate, n, control_idx, target_idx, ins.angle
            )
            circuit.state.apply_unitary(u)
            if ins.gate in (GateType.CNOT,):
                self.entangle(ins.control, ins.target)
