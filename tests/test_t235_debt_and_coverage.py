"""T235: Regression tests for controlled-rotation unitarity fix, low-coverage core modules & singularity CLI."""

from __future__ import annotations

import asyncio
import json
import math
import subprocess
import sys
import types
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import pytest
from typer.testing import CliRunner

from q_speace.aacm.pr_helper import create_pr
from q_speace.cli import app
from q_speace.quantum.backends.qiskit_backend import QiskitBackend
from q_speace.quantum.entanglement_registry import EntanglementRegistry
from q_speace.quantum.quantum_brain_simulator import BrainQuantumCircuit
from q_speace.quantum.quantum_gates import GateType, QuantumGates
from q_speace.spiking_brain.client import HTTPSpikingBrainClient
from q_speace.spiking_brain.interface import LifecycleState, SpikingBrainUnavailableError


def test_quantum_gates_all_single_and_controlled_rotations_are_unitary() -> None:
    # Single-qubit gates on 2 qubits
    for g in (
        GateType.H,
        GateType.X,
        GateType.Y,
        GateType.Z,
        GateType.S,
        GateType.T,
        GateType.RX,
        GateType.RY,
        GateType.RZ,
    ):
        u = QuantumGates.single_qubit(g, 2, target=1, angle=math.pi / 3)
        assert np.allclose(u.conj().T @ u, np.eye(4)), f"non-unitary single gate {g}"

    with pytest.raises(ValueError, match="out of range"):
        QuantumGates.single_qubit(GateType.H, 2, target=2)
    with pytest.raises(ValueError, match="not supported"):
        QuantumGates.single_qubit(GateType.CNOT, 2, target=0)

    # Two-qubit gates including newly fixed CRX, CRY, CRZ (must be unitary!)
    for g2 in (GateType.CNOT, GateType.SWAP, GateType.RX, GateType.RY, GateType.RZ):
        u2 = QuantumGates.two_qubit(g2, 2, control=0, target=1, angle=math.pi / 4)
        assert np.allclose(u2.conj().T @ u2, np.eye(4)), f"non-unitary two-qubit gate {g2}"

    # Verify CRZ applies phase e^{+i theta/2} to |11> and e^{-i theta/2} to |10>
    theta = math.pi / 2
    crz = QuantumGates.two_qubit(GateType.RZ, 2, control=0, target=1, angle=theta)
    assert np.isclose(crz[0, 0], 1.0)
    assert np.isclose(crz[1, 1], 1.0)
    assert np.isclose(crz[2, 2], np.exp(-1j * theta / 2))
    assert np.isclose(crz[3, 3], np.exp(1j * theta / 2))

    with pytest.raises(ValueError, match="out of range"):
        QuantumGates.two_qubit(GateType.CNOT, 2, control=3, target=0)
    with pytest.raises(ValueError, match="must differ"):
        QuantumGates.two_qubit(GateType.CNOT, 2, control=1, target=1)
    with pytest.raises(ValueError, match="not supported"):
        QuantumGates.two_qubit(GateType.H, 2, control=0, target=1)


def test_qiskit_backend_translation_little_endian_reversal_and_empty_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded_ops: list[tuple[str, tuple[Any, ...]]] = []

    class FakeQuantumCircuit:
        def __init__(self, n: int, c: int) -> None:
            self.n = n
            self.c = c

        def __getattr__(self, name: str) -> Any:
            def _op(*args: Any) -> None:
                recorded_ops.append((name, args))

            return _op

    class FakeResult:
        def __init__(self, counts: dict[str, int]) -> None:
            self._counts = counts

        def get_counts(self, _qc: Any) -> dict[str, int]:
            return self._counts

    class FakeJob:
        def __init__(self, counts: dict[str, int]) -> None:
            self._counts = counts

        def result(self) -> FakeResult:
            return FakeResult(self._counts)

    counts_box: dict[str, dict[str, int]] = {"counts": {"10": 900, "00": 124}}

    class FakeAerSimulator:
        def __init__(self, **kwargs: Any) -> None:
            self.kwargs = kwargs
            self.last_shots: int | None = None

        def run(self, _qc: Any, shots: int = 1024) -> FakeJob:
            self.last_shots = shots
            return FakeJob(counts_box["counts"])

    fake_qiskit = types.ModuleType("qiskit")
    fake_qiskit.QuantumCircuit = FakeQuantumCircuit  # type: ignore[attr-defined]
    fake_aer = types.ModuleType("qiskit_aer")
    fake_aer.AerSimulator = FakeAerSimulator  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "qiskit", fake_qiskit)
    monkeypatch.setitem(sys.modules, "qiskit_aer", fake_aer)

    circ = BrainQuantumCircuit("qiskit-test")
    circ.add_qubit("q0")
    circ.add_qubit("q1")
    for g, t in (
        (GateType.H, "q0"),
        (GateType.X, "q1"),
        (GateType.Y, "q0"),
        (GateType.Z, "q1"),
        (GateType.S, "q0"),
        (GateType.T, "q1"),
    ):
        circ.add_gate(g, target=t)
    circ.add_gate(GateType.RX, target="q0", angle=0.5)
    circ.add_gate(GateType.RY, target="q1", angle=0.3)
    circ.add_gate(GateType.RZ, target="q0", angle=0.2)
    circ.add_gate(GateType.CNOT, target="q1", control="q0")
    circ.add_gate(GateType.SWAP, target="q1", control="q0")
    circ.add_gate(GateType.RZ, target="q1", control="q0", angle=0.4)

    backend = QiskitBackend(shots=256, seed=7)
    res = backend.run(circ)
    # Little-endian "10" (c1=1, c0=0) reverses to q0="0", q1="1"
    assert res == [("q0", "0"), ("q1", "1")]
    assert backend._aer.last_shots == 256
    op_names = [name for name, _ in recorded_ops]
    for expected in (
        "h",
        "x",
        "y",
        "z",
        "s",
        "t",
        "rx",
        "ry",
        "rz",
        "cx",
        "swap",
        "crz",
        "measure",
    ):
        assert expected in op_names

    # Empty counts falls back safely to all-"0"
    counts_box["counts"] = {}
    assert backend.run(circ, shots=64) == [("q0", "0"), ("q1", "0")]
    assert backend._aer.last_shots == 64


def test_entanglement_registry_disentangle_errors_and_clear() -> None:
    reg = EntanglementRegistry()
    with pytest.raises(ValueError, match="with itself"):
        reg.entangle("a", "a")
    p = reg.entangle("a", "b", fidelity=0.95)
    assert p.involves("a") is True
    with pytest.raises(KeyError, match="not in pair"):
        p.other("z")
    reg.entangle("b", "c", fidelity=0.90)
    assert len(reg.all_pairs()) == 2
    assert reg.disentangle("a", "b") is True
    assert reg.disentangle("a", "b") is False
    assert reg.is_entangled("a", "b") is False
    assert reg.is_entangled("b", "c") is True
    reg.clear()
    assert reg.count() == 0


def test_aacm_pr_helper_success_failure_and_missing_gh(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # 1. gh not installed
    monkeypatch.setattr("q_speace.aacm.pr_helper._gh_available", lambda: False)
    r_missing = create_pr(tmp_path, title="t", body="b")
    assert r_missing.opened is False and r_missing.skipped_reason == "gh not installed"

    # 2. gh pr create succeeds
    monkeypatch.setattr("q_speace.aacm.pr_helper._gh_available", lambda: True)

    def _fake_ok(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        if args[:2] == ("pr", "view"):
            return subprocess.CompletedProcess(args, 1, "", "no pull requests found")
        return subprocess.CompletedProcess(
            args, 0, "https://github.com/rigeneproject/q_speace/pull/42\n", ""
        )

    monkeypatch.setattr("q_speace.aacm.pr_helper._run_gh", _fake_ok)
    r_ok = create_pr(tmp_path, title="Fix", body="Body", draft=True)
    assert r_ok.opened is True
    assert r_ok.url == "https://github.com/rigeneproject/q_speace/pull/42"

    # 3. gh pr create fails
    def _fake_fail(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args, 1, "", "auth required")

    monkeypatch.setattr("q_speace.aacm.pr_helper._run_gh", _fake_fail)
    r_fail = create_pr(tmp_path, title="Fix", body="Body", draft=False)
    assert r_fail.opened is False and "gh pr create failed" in (r_fail.skipped_reason or "")


def test_http_spiking_brain_client_lifecycle_and_error_paths() -> None:
    async def _exercise() -> None:
        # 1. Healthy mock transport
        def _handler_ok(request: httpx.Request) -> httpx.Response:
            if request.url.path == "/health":
                return httpx.Response(200, json={"status": "ok"})
            if request.url.path == "/think":
                return httpx.Response(
                    200,
                    json={
                        "text": "verified answer",
                        "tokens": 5,
                        "confidence": 0.9,
                        "spike_sparsity": 0.65,
                        "latency_ms": 12.0,
                        "path": "fp8",
                    },
                )
            return httpx.Response(404)

        client = HTTPSpikingBrainClient("http://sidecar.test")
        assert client.backend == "http://sidecar.test"
        assert client.memory is None
        assert client.lifecycle_state() == LifecycleState.LOAD
        client._client = httpx.AsyncClient(transport=httpx.MockTransport(_handler_ok))
        await client.load()
        assert client.lifecycle_state() == LifecycleState.READY
        res = await client.think("ping", coherence_phi=0.8, n_tokens=16)
        assert res.text == "verified answer"
        assert res.confidence == pytest.approx(0.9)
        await client.shutdown()
        assert client.lifecycle_state() == LifecycleState.SHUTDOWN

        # 2. Unreachable /health raises SpikingBrainUnavailableError
        def _handler_503(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, text="down")

        bad = HTTPSpikingBrainClient("http://sidecar.test")
        bad._client = httpx.AsyncClient(transport=httpx.MockTransport(_handler_503))
        with pytest.raises(SpikingBrainUnavailableError):
            await bad.load()
        await bad.aclose()

    asyncio.run(_exercise())


def test_cli_singularity_manifest_drills_and_assess(tmp_path: Path) -> None:
    runner = CliRunner()

    # 1. manifest (valid section & invalid section)
    r_man = runner.invoke(app, ["singularity", "manifest", "--section", "invariants"])
    assert r_man.exit_code == 0, r_man.output
    parsed_man = json.loads(r_man.output)
    assert parsed_man["framework_id"] == "q_speace.singularity.v1"
    assert parsed_man["invariants"]["no_self_approval"] is True

    r_bad_sec = runner.invoke(app, ["singularity", "manifest", "--section", "bogus"])
    assert r_bad_sec.exit_code == 2

    # 2. drills (6/6 pass -> exit 0)
    r_drills = runner.invoke(app, ["singularity", "drills"])
    assert r_drills.exit_code == 0, r_drills.output
    parsed_drills = json.loads(r_drills.output)
    assert parsed_drills["all_passed"] is True
    assert parsed_drills["rollback_pass_rate"] == 1.0

    # 3. assess (valid JSON file + missing file)
    tel_path = tmp_path / "telemetry.json"
    tel_path.write_text(
        json.dumps(
            {
                "timescale_decoupling_ratio": 16.0,
                "autocatalytic_k": 1.4,
                "independent_validation_rate": 0.98,
                "semantic_entropy_drift": 0.01,
                "causal_grounding_error": 0.01,
                "net_verified_improvement": 0.05,
                "consecutive_verified_cycles": 4,
                "allopoietic_dependence": 0.85,
                "sevo": 2.2,
                "thermal_load_ratio": 0.55,
                "independent_review_passed": True,
            }
        ),
        encoding="utf-8",
    )
    r_ass = runner.invoke(app, ["singularity", "assess", "--telemetry", str(tel_path)])
    assert r_ass.exit_code == 0, r_ass.output
    verdict = json.loads(r_ass.output)
    assert verdict["stage"] == "STAGE_2_BOUNDED_RECURSIVE"
    assert verdict["physical_actuation_permitted"] is False

    r_missing = runner.invoke(
        app, ["singularity", "assess", "--telemetry", str(tmp_path / "nope.json")]
    )
    assert r_missing.exit_code == 2
