"""Qiskit/Aer backend (task T5).

Converts a BrainQuantumCircuit to a Qiskit QuantumCircuit and executes it
via AerSimulator (statevector or shot-based). The SDK is lazy-imported so
the rest of Q-SPEACE keeps working without it; if Qiskit is unavailable the
backend raises a clear install message.
"""
from __future__ import annotations

from .base import QuantumBackend


class QiskitBackend(QuantumBackend):
    """Executes circuits via Qiskit AerSimulator (statevector / shot-based)."""

    name = "qiskit"

    def __init__(
        self, shots: int = 1024, backend_type: str = "aer_simulator", seed: int = None
    ) -> None:
        self._shots = shots
        self._backend_type = backend_type
        self._seed = seed
        self._aer = None

    def _ensure_qiskit(self):
        if self._aer is not None:
            return self._aer
        try:
            from qiskit import QuantumCircuit as QKCircuit  # type: ignore
            from qiskit_aer import AerSimulator  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                "Qiskit backend requires qiskit and qiskit-aer. "
                "Run: pip install q-speace[qiskit]"
            ) from exc
        self._QKCircuit = QKCircuit
        self._aer = AerSimulator(method="statevector", seed_simulator=self._seed)
        return self._aer

    def _to_qiskit_circuit(self, circuit):
        self._ensure_qiskit()
        n = circuit.num_qubits
        qc = self._QKCircuit(n, n)
        for op in circuit.gates():
            g = op.gate.value if hasattr(op.gate, "value") else str(op.gate)
            if op.control is not None:
                c = circuit._role_index[op.control]
                t = circuit._role_index[op.target]
                if g == "CNOT":
                    qc.cx(c, t)
                elif g == "SWAP":
                    qc.swap(c, t)
                elif g in ("RX", "RY", "RZ"):
                    ang = op.angle if op.angle is not None else 0.0
                    getattr(qc, f"cr{g[1:].lower()}")(ang, c, t)
                else:
                    raise ValueError(f"unsupported two-qubit gate {g}")
            else:
                t = circuit._role_index[op.target]
                if g == "H":
                    qc.h(t)
                elif g == "X":
                    qc.x(t)
                elif g == "Y":
                    qc.y(t)
                elif g == "Z":
                    qc.z(t)
                elif g == "S":
                    qc.s(t)
                elif g == "T":
                    qc.t(t)
                elif g in ("RX", "RY", "RZ"):
                    ang = op.angle if op.angle is not None else 0.0
                    getattr(qc, g.lower())(ang, t)
                else:
                    raise ValueError(f"unsupported single-qubit gate {g}")
        for i in range(n):
            qc.measure(i, i)
        return qc

    def run(self, circuit, shots: int = 1024) -> list[tuple[str, str]]:
        aer = self._ensure_qiskit()
        qc = self._to_qiskit_circuit(circuit)
        result = aer.run(qc, shots=shots or self._shots).result()
        counts = result.get_counts(qc)
        if not counts:
            return [(circuit.role_of(i), "0") for i in range(circuit.num_qubits)]
        top = max(counts, key=lambda k: counts[k])
        return [(circuit.role_of(i), top[i]) for i in range(circuit.num_qubits)]
