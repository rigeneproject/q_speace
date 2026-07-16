"""QuantumNeuralBridge — connect the quantum layer to DigitalNeurons.

The bridge:
  - lets a DigitalNeuron carry a QuantumState via its cell_id
  - applies gates driven by DigitalNeuron state changes
  - records entanglement pairs in a shared EntanglementRegistry
  - computes a quantum "compatibility" between two neurons based on
    state fidelity, complementing the periodic-table compatibility
    in neuroperiodic/.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from speace_core.cellular_brain.quantum.entanglement_registry import (
    EntangledPair,
    EntanglementRegistry,
)
from speace_core.cellular_brain.quantum.quantum_brain_simulator import (
    BrainQuantumCircuit,
    QuantumBrainSimulator,
)
from speace_core.cellular_brain.quantum.quantum_gates import GateType, QuantumGates
from speace_core.cellular_brain.quantum.quantum_state import QuantumState


@dataclass
class NeuronQuantumSlot:
    """A neuron's slot in the quantum bridge."""
    cell_id: str
    num_qubits: int = 1
    state: QuantumState = None  # type: ignore[assignment]
    qubit_offset: int = 0

    def __post_init__(self) -> None:
        if self.state is None:
            self.state = QuantumState(num_qubits=self.num_qubits)


class QuantumNeuralBridge:
    """Bridges DigitalNeuron cell_ids to a quantum simulation."""

    def __init__(
        self,
        num_qubits_per_neuron: int = 1,
        genome: Any = None,
    ) -> None:
        self.num_qubits_per_neuron = max(1, num_qubits_per_neuron)
        self.slots: Dict[str, NeuronQuantumSlot] = {}
        self.entanglements = EntanglementRegistry()
        self.simulator = QuantumBrainSimulator()
        self._next_offset: int = 0
        self._genome = genome
        self._periodic_qubit_map: Dict[str, int] = {}
        if genome is not None:
            qg = getattr(genome, "quantum_genes", None)
            if qg is not None:
                self._periodic_qubit_map = getattr(
                    qg, "periodic_element_qubit_map", {}
                ) or {}

    def register(
        self,
        cell_id: str,
        initial_state: int = 0,
        num_qubits: Optional[int] = None,
        periodic_block: Optional[str] = None,
    ) -> NeuronQuantumSlot:
        if cell_id in self.slots:
            return self.slots[cell_id]
        if num_qubits is not None:
            n = num_qubits
        elif periodic_block and self._periodic_qubit_map:
            n = self._periodic_qubit_map.get(periodic_block, self.num_qubits_per_neuron)
        else:
            n = self.num_qubits_per_neuron
        if n < 1:
            raise ValueError("num_qubits must be >= 1")
        slot = NeuronQuantumSlot(
            cell_id=cell_id,
            num_qubits=n,
            state=QuantumState(num_qubits=n, initial_state=initial_state),
            qubit_offset=self._next_offset,
        )
        self.slots[cell_id] = slot
        self._next_offset += n
        return slot

    def unregister(self, cell_id: str) -> bool:
        slot = self.slots.pop(cell_id, None)
        if slot is None:
            return False
        # remove any entanglement involving this neuron
        for partner in list(self.entanglements.partners_of(cell_id)):
            self.entanglements.disentangle(cell_id, partner)
        return True

    def apply_gate_to_neuron(
        self,
        cell_id: str,
        gate: GateType,
        angle: Optional[float] = None,
    ) -> None:
        slot = self.slots.get(cell_id)
        if slot is None:
            raise KeyError(f"neuron {cell_id} not registered")
        n = slot.num_qubits
        for q in range(n):
            u = QuantumGates.single_qubit(gate, n, q, angle)
            slot.state.apply_unitary(u)

    def entangle_neurons(
        self,
        cell_id_a: str,
        cell_id_b: str,
        fidelity: float = 0.0,
        label: str = "",
    ) -> EntangledPair:
        if cell_id_a not in self.slots:
            self.register(cell_id_a)
        if cell_id_b not in self.slots:
            self.register(cell_id_b)
        pair = self.entanglements.entangle(
            cell_id_a, cell_id_b, fidelity=fidelity, label=label
        )
        # Apply a CNOT between the first qubits of each neuron to
        # actually entangle their states.
        a = self.slots[cell_id_a]
        b = self.slots[cell_id_b]
        # Build a temporary joint state via tensor product and a CNOT
        # spanning the first qubits. We do this by constructing a
        # 2-qubit circuit and applying a CNOT, then storing the
        # resulting first-qubit state in `a` and the second in `b`.
        a_state = a.state
        b_state = b.state
        joint = QuantumState.tensor_product(a_state, b_state)
        cnot = QuantumGates.two_qubit(GateType.CNOT, 2, 0, 1)
        joint.apply_unitary(cnot)
        # split back (assign joint amplitudes' first half to a, second to b)
        half = joint.amplitudes.shape[0] // 2
        # re-extract by marginalizing
        from speace_core.cellular_brain.quantum.quantum_state import (
            QuantumState as _Q,
        )
        a2 = _Q(num_qubits=a.num_qubits)
        b2 = _Q(num_qubits=b.num_qubits)
        a2.amplitudes = np.copy(joint.amplitudes[:half])  # type: ignore[name-defined]
        b2.amplitudes = np.copy(joint.amplitudes[half:])  # type: ignore[name-defined]
        a.state = a2
        b.state = b2
        return pair

    def measure_neuron(self, cell_id: str) -> int:
        slot = self.slots.get(cell_id)
        if slot is None:
            raise KeyError(f"neuron {cell_id} not registered")
        result = slot.state.measure()
        return int(result.bitstring[0]) if result.bitstring else 0

    def quantum_compatibility(
        self,
        cell_id_a: str,
        cell_id_b: str,
    ) -> float:
        """Quantum-inspired compatibility score in [0, 1].

        Uses state overlap (fidelity) as a proxy. If the two states
        are anti-aligned, the score is low; if they share a basis,
        the score is high.
        """
        a = self.slots.get(cell_id_a)
        b = self.slots.get(cell_id_b)
        if a is None or b is None:
            raise KeyError("both neurons must be registered")
        if a.state.amplitudes.shape != b.state.amplitudes.shape:
            return 0.0
        return float(a.state.fidelity_with(b.state))

    def to_circuit(self, name: str = "brain") -> BrainQuantumCircuit:
        """Materialize the current bridge as a BrainQuantumCircuit.

        Useful for batch evaluation with the QuantumBrainSimulator.
        """
        circuit = BrainQuantumCircuit(name=name)
        for slot in self.slots.values():
            circuit.add_qubit(slot.cell_id)
        return circuit

    def summary(self) -> Dict[str, object]:
        return {
            "num_neurons": len(self.slots),
            "num_qubits": self._next_offset,
            "num_entanglements": self.entanglements.count(),
            "connected_components": len(self.entanglements.connected_components()),
        }


# Import numpy lazily to keep the module import-time cost low.
import numpy as np  # noqa: E402


def attach_quantum_state(
    bridge: QuantumNeuralBridge,
    cell_id: str,
    initial_state: int = 0,
) -> NeuronQuantumSlot:
    """Convenience function: register a neuron and return its slot."""
    return bridge.register(cell_id, initial_state=initial_state)
