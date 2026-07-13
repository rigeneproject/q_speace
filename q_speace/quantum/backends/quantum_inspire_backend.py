"""Quantum Inspire backend (task T5).

Serializes a BrainQuantumCircuit to cQASM 3.0 (Quantum Inspire's native
language) and, if the QI SDK + credentials are present, submits it to the
cloud. The SDK is lazy-imported so the rest of Q-SPEACE keeps working
without it.

Human action required before this backend is usable:
  1. Create an account at https://compute.quantum-inspire.com/projects/
  2. Generate an API token.
  3. Set environment variables:  QI_URL and QI_TOKEN
  4. Install the SDK:  pip install quantum-inspire-sdk  (or qilib)
"""
from __future__ import annotations

import os

from .base import QuantumBackend


def to_cqasm(circuit, version: str = "1.0") -> str:
    """Serialize a BrainQuantumCircuit to a cQASM program.

    version="1.0" (default) emits cQASM 1.0 compatible with the Quantum
    Inspire QX emulator (per-qubit ``measure q[i]``). version="3.0" emits
    cQASM 3.0 with ``measure_all``.
    """
    if version not in ("1.0", "3.0"):
        raise ValueError("version must be '1.0' or '3.0'")
    n = circuit.num_qubits
    lines = [f"version {version}\n", f"qubits {n}\n"]
    for op in circuit.gates():
        g = op.gate.value if hasattr(op.gate, "value") else str(op.gate)
        if op.control is not None:
            c = circuit._role_index[op.control]
            t = circuit._role_index[op.target]
            if g == "CNOT":
                lines.append(f"CNOT q[{c}], q[{t}]")
            elif g == "SWAP":
                lines.append(f"SWAP q[{c}], q[{t}]")
            elif g in ("RX", "RY", "RZ"):
                ang = op.angle if op.angle is not None else 0.0
                lines.append(f"{g}({ang:.6f}) q[{c}], q[{t}]")
            else:
                raise ValueError(f"unsupported two-qubit gate {g}")
        else:
            t = circuit._role_index[op.target]
            if g in ("H", "X", "Y", "Z", "S", "T"):
                lines.append(f"{g} q[{t}]")
            elif g in ("RX", "RY", "RZ"):
                ang = op.angle if op.angle is not None else 0.0
                lines.append(f"{g}({ang:.6f}) q[{t}]")
            else:
                raise ValueError(f"unsupported single-qubit gate {g}")
    if version == "3.0":
        lines.append("measure_all")
    else:
        for i in range(n):
            lines.append(f"measure q[{i}]")
    return "\n".join(lines) + "\n"


class QuantumInspireBackend(QuantumBackend):
    """Submits cQASM to Quantum Inspire cloud (requires SDK + token)."""

    name = "quantum-inspire"

    def __init__(self, project_name: str = "q-space", backend_type: str = "QX-sim") -> None:
        self.project_name = project_name
        self.backend_type = backend_type
        self._qi = None

    def _ensure_sdk(self):
        if self._qi is not None:
            return self._qi
        url = os.environ.get("QI_URL")
        token = os.environ.get("QI_TOKEN")
        if not token:
            raise RuntimeError(
                "Quantum Inspire backend requires QI_TOKEN (and QI_URL). "
                "Create an account at https://compute.quantum-inspire.com/projects/ "
                "and set the environment variables."
            )
        try:
            from quantum_inspire.api import QuantumInspireAPI  # type: ignore
        except ImportError as exc:  # pragma: no cover - depends on SDK
            raise RuntimeError(
                "Quantum Inspire SDK not installed. Run: pip install quantum-inspire-sdk"
            ) from exc
        self._qi = QuantumInspireAPI(url or "https://api.quantum-inspire.com", token)
        return self._qi

    def run(self, circuit, shots: int = 1024) -> list[tuple[str, str]]:
        qi = self._ensure_sdk()
        cqasm = to_cqasm(circuit)
        # The exact submission call depends on the installed SDK version.
        # We expose the program and let the SDK execute it; results are
        # mapped back to (role, bit) pairs.
        result = qi.execute_qasm(cqasm, backend_type=self.backend_type, number_of_shots=shots)
        counts = result.get("histogram", {}) if isinstance(result, dict) else {}
        # Return the most probable outcome mapped to roles.
        if not counts:
            return [(circuit.role_of(i), "0") for i in range(circuit.num_qubits)]
        top = max(counts, key=lambda k: counts[k])
        bits = format(int(top), f"0{circuit.num_qubits}b")
        return [(circuit.role_of(i), bits[i]) for i in range(circuit.num_qubits)]
