"""Tests for the backend abstraction and Quantum Inspire cQASM serialization."""
from __future__ import annotations

from q_speace.quantum import BrainQuantumCircuit, GateType
from q_speace.quantum.backends import build, to_cqasm
from q_speace.quantum.backends.quantum_inspire_backend import QuantumInspireBackend


def _bell() -> BrainQuantumCircuit:
    circ = BrainQuantumCircuit("bell")
    circ.add_qubit("a")
    circ.add_qubit("b")
    circ.add_gate(GateType.H, target="a")
    circ.add_gate(GateType.CNOT, control="a", target="b")
    circ.add_gate(GateType.RY, target="b", angle=0.5)
    return circ


def test_cqasm_serialization_v3_default():
    cqasm = to_cqasm(_bell())
    assert cqasm.startswith("version 3.0")
    assert "qubit[2] q" in cqasm
    assert "bit[2] b" in cqasm
    assert "init q[0]" in cqasm
    assert "init q[1]" in cqasm
    assert "H q[0]" in cqasm
    assert "CNOT q[0], q[1]" in cqasm
    assert "Ry(0.5000) q[1]" in cqasm
    assert "b[0] = measure q[0]" in cqasm
    assert "b[1] = measure q[1]" in cqasm


def test_cqasm_serialization_v1_legacy():
    cqasm = to_cqasm(_bell(), version="1.0")
    assert cqasm.startswith("version 1.0")
    assert "qubits 2" in cqasm
    assert "H q[0]" in cqasm
    assert "CNOT q[0], q[1]" in cqasm
    assert "Ry(0.5000) q[1]" in cqasm
    assert "measure q[0]" in cqasm
    assert "measure q[1]" in cqasm
    assert "measure_all" not in cqasm


def test_cqasm_serialization_v3():
    cqasm = to_cqasm(_bell(), version="3.0")
    assert cqasm.startswith("version 3.0")
    assert "qubit[2] q" in cqasm
    assert "bit[2] b" in cqasm
    assert "init q[0]" in cqasm
    assert "init q[1]" in cqasm
    assert "b[0] = measure q[0]" in cqasm
    assert "b[1] = measure q[1]" in cqasm


def test_selector_default_numpy():
    backend = build("numpy")
    assert backend.name == "numpy"
    result = backend.run(_bell())
    assert len(result) == 2


def test_selector_falls_back_to_numpy_without_token(monkeypatch):
    monkeypatch.delenv("QI_TOKEN", raising=False)
    monkeypatch.delenv("QI_URL", raising=False)
    # Missing SDK or token -> build() must fall back to numpy, not raise.
    backend = build("quantum-inspire")
    assert backend.name == "numpy"
    assert backend.run(_bell())  # runs locally


def test_quantum_inspire_requires_token(monkeypatch):
    monkeypatch.delenv("QI_TOKEN", raising=False)
    monkeypatch.delenv("QI_URL", raising=False)
    bi = QuantumInspireBackend()
    try:
        bi.run(_bell())
        assert False, "expected RuntimeError without token"
    except RuntimeError as exc:
        assert "QI_TOKEN" in str(exc)


def test_qiskit_backend_imports():
    from q_speace.quantum.backends import QiskitBackend

    assert QiskitBackend.name == "qiskit"


def test_qiskit_falls_back_to_numpy_without_sdk():
    backend = build("qiskit")
    assert backend.name == "numpy"
    assert backend.run(_bell())


def test_qiskit_backend_raises_without_sdk():
    from q_speace.quantum.backends import QiskitBackend

    bk = QiskitBackend()
    try:
        bk.run(_bell())
        assert False, "expected RuntimeError without qiskit"
    except RuntimeError as exc:
        assert "qiskit" in str(exc).lower()
