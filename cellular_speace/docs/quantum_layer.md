# SPEACE — Quantum Layer

**Status**: implemented in `speace_core/cellular_brain/quantum/`
**Tests**: 60 tests passing (`tests/quantum/`)
**Dependencies**: numpy only (no Qiskit / Cirq)

## Why

The existing `resonance/` module provides *metaphorical* quantum
primitives (Pauli exclusion of cognitive states, wave-particle
duality, frequency bands, phase locking). For more rigorous
quantum-inspired computations, SPEACE now includes a **concrete
computational quantum layer**: complex state vectors, unitary
gates, entanglement tracking, measurement, and a brain-circuit
abstraction.

## Architecture

```
speace_core.cellular_brain.quantum
  ├── quantum_state.py            # QuantumState (n-qubit complex vector)
  ├── quantum_gates.py            # QuantumGates factory
  ├── entanglement_registry.py    # EntanglementRegistry
  ├── quantum_brain_simulator.py  # QuantumBrainSimulator
  └── quantum_neural_bridge.py    # QuantumNeuralBridge
```

### QuantumState

- `num_qubits`: 1..16 (max 2^16 amplitudes)
- `amplitudes`: complex128 numpy array, shape `(2**n,)`, normalized
- Construction:
  - `QuantumState(num_qubits=3, initial_state=5)` → basis state `|101>`
  - `QuantumState.equal_superposition(num_qubits=3)` → `(|0>+|1>)^3/sqrt(8)`
  - `QuantumState.from_amplitudes([1, 1, 0, 0])` → custom vector
  - `QuantumState.tensor_product(a, b)` → joint state
- Manipulation:
  - `apply_unitary(U)` — applies a 2^n × 2^n unitary, validates unitarity
  - `normalize()` — re-normalize amplitudes
  - `measure(qubit_index=None)` — probabilistic measurement with collapse
  - `probabilities()` — returns |amp|^2 array
  - `fidelity_with(other)` — overlap |<self|other>|^2
  - `to_density_matrix()` — pure-state density matrix

### QuantumGates

`QuantumGates.single_qubit(gate, num_qubits, target, angle=None)` returns
a full 2^n × 2^n unitary. Supported single-qubit gates:

| Gate  | Description                          |
|-------|--------------------------------------|
| H     | Hadamard                             |
| X     | Pauli-X (NOT)                        |
| Y     | Pauli-Y                              |
| Z     | Pauli-Z                              |
| S     | Phase                                |
| T     | T gate (π/8 phase)                   |
| RX(θ) | Rotation around X                    |
| RY(θ) | Rotation around Y                    |
| RZ(θ) | Rotation around Z                    |

Two-qubit gates via `QuantumGates.two_qubit(gate, num_qubits, control, target)`:
- CNOT
- SWAP (= CNOT · CNOT · CNOT)
- Controlled-RX/RY/RZ

All gates are verified unitary before application (tolerance 1e-6).

### EntanglementRegistry

Tracks (entity_a, entity_b) pairs. Provides:
- `entangle(a, b, fidelity, label)` / `disentangle(a, b)`
- `pairs_of(entity)` / `partners_of(entity)` / `degree(entity)`
- `connected_components()` — components of the entanglement graph
- `is_entangled(a, b)`

### QuantumBrainSimulator

Runs a `BrainQuantumCircuit` (named-role quantum circuit). Roles
are mapped to qubit indices. Supports initial states, single- and
two-qubit gates, and end-of-circuit measurement.

```python
from speace_core.cellular_brain.quantum import (
    BrainQuantumCircuit, GateType, QuantumBrainSimulator
)

circ = BrainQuantumCircuit(name="hippocampal_memory")
circ.add_qubit("memory")
circ.add_qubit("decision")
circ.add_gate(GateType.H, target="memory")
circ.add_gate(GateType.CNOT, target="decision", control="memory")

sim = QuantumBrainSimulator()
measurements = sim.run(circ)
# measurements: [("memory", "0"), ("decision", "0")]
```

### QuantumNeuralBridge

Bridges `DigitalNeuron` cell_ids to a `QuantumState`. Each neuron
carries a slot in a global qubit space. The bridge:
- registers/unregisters neurons
- applies gates driven by neuron state
- records entanglements (CNOT creates a pair in the registry)
- computes a quantum "compatibility" via state fidelity

```python
from speace_core.cellular_brain.quantum import QuantumNeuralBridge

bridge = QuantumNeuralBridge(num_qubits_per_neuron=1)
bridge.register("hippocampus_0", initial_state=0)
bridge.register("prefrontal_0", initial_state=0)
bridge.entangle_neurons("hippocampus_0", "prefrontal_0")
print(bridge.summary())
# {'num_neurons': 2, 'num_qubits': 2, 'num_entanglements': 1, 'connected_components': 1}
```

## Performance and limits

- State vector size: `2**num_qubits` complex128 amplitudes
  - n=10 → 1024 amplitudes (small)
  - n=12 → 4096 amplitudes (medium)
  - n=14 → 16384 (large)
  - n=16 → 65536 (limit, ~1 MB per state)
- Gate application: O(2^(2n)) for a full single-qubit gate via
  tensor expansion. Acceptable up to n≈10.
- Use the quantum layer for **small cognitive circuits**, not as
  a replacement for the rest of SPEACE.

## Differences from `resonance/`

`resonance/` works on continuous wave / phase quantities (no complex
amplitudes, no measurement collapse). `quantum/` works on complex
discrete state vectors (true quantum states). They are complementary:
use `resonance/` for oscillations and phase coupling, use `quantum/`
for true quantum gates and entanglement.

## Tests

- `test_quantum_state.py` (22 tests): construction, normalization,
  measurement, fidelity, density matrix
- `test_quantum_gates.py` (15 tests): unitarity, H^2=I, CNOT→Bell,
  SWAP, rotations
- `test_entanglement.py` (12 tests): registry, components, removal

Run with:

```bash
pytest tests/quantum/ -v
```
