"""T242: Tech-debt regression tests for fail-closed guards and lowest-coverage core modules."""

from __future__ import annotations

import asyncio
import json
import math
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pytest

from q_speace.bcel.catalog import BCELCatalog
from q_speace.earth_feed import EarthFeed, EarthSignals
from q_speace.experiments import context_decay, online_agent
from q_speace.genome.quantum_genes import QuantumGeneSet
from q_speace.quantum.backends import selector
from q_speace.quantum.backends.base import NumpyBackend
from q_speace.self_improvement_cortex import benchmark
from q_speace.self_improvement_cortex.evolutionary_memory import EvolutionaryMemory, MemoryEntry
from q_speace.spiking.bridge import SpikeQuantumBridge
from q_speace.spiking.linear import SpikeEncodedLinear


def test_t242_evolutionary_memory_fail_closed_and_full_api() -> None:
    with pytest.raises(ValueError, match="max_entries"):
        EvolutionaryMemory(max_entries=0)
    with pytest.raises(ValueError, match="outcome must be finite"):
        MemoryEntry("m", "sig", "r", 1, "t", {}, {}, math.nan)
    with pytest.raises(ValueError, match="metrics_before"):
        MemoryEntry("m", "sig", "r", 1, "t", {"a": math.inf}, {}, 0.1)
    with pytest.raises(ValueError, match="metrics_after"):
        MemoryEntry("m", "sig", "r", 1, "t", {}, {"a": -math.inf}, 0.1)

    mem = EvolutionaryMemory(max_entries=2)
    assert mem.success_rate() == 0.0
    e1 = MemoryEntry("m1", "s1", "r", 1, "t1", {"x": 0.5}, {"x": 0.8}, 0.3)
    e2 = MemoryEntry("m2", "s1", "r", 1, "t2", {"x": 0.8}, {"x": 0.4}, -0.4)
    e3 = MemoryEntry("m3", "s2", "r", 2, "t3", {}, {}, 0.5)
    mem.store(e1)
    mem.store(e2)
    mem.store(e3)  # evicts e1 because max_entries=2
    assert mem.count() == 2
    assert len(mem.all()) == 2
    assert mem.best_for_level(2)[0].mutation_id == "m3"
    assert mem.has_failed_before("s1", "t2") is True
    assert mem.success_rate(level=2) == 1.0
    assert mem.success_rate(level=1) == 0.0
    mem.clear()
    assert mem.count() == 0


def test_t242_earth_feed_linear_and_bridge_fail_closed_and_edges(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # EarthSignals validation
    with pytest.raises(ValueError, match="kp must be finite"):
        EarthSignals(kp=math.nan, sunspot=0.5, tide=0.5)
    with pytest.raises(ValueError, match="sunspot must be finite"):
        EarthSignals(kp=0.5, sunspot=1.5, tide=0.5)

    # EarthFeed._fetch_real happy path + bad payload + non-finite Kp -> synthetic fallback
    class _Resp:
        def __init__(self, payload: Any) -> None:
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> Any:
            return self._payload

    fake_httpx = types.ModuleType("httpx")
    fake_httpx.get = lambda *_a, **_kw: _Resp([{"Kp": 4.5}])  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "httpx", fake_httpx)
    sig = EarthFeed(use_network=True).fetch(tick=3)
    assert sig.kp == pytest.approx(0.5)

    fake_httpx.get = lambda *_a, **_kw: _Resp([])  # type: ignore[attr-defined]
    assert 0.0 <= EarthFeed(use_network=True).fetch(tick=3).kp <= 1.0

    fake_httpx.get = lambda *_a, **_kw: _Resp([{"Kp": "nan"}])  # type: ignore[attr-defined]
    assert 0.0 <= EarthFeed(use_network=True).fetch(tick=3).kp <= 1.0

    # SpikeEncodedLinear group quantization + fail-closed checks
    with pytest.raises(ValueError, match="in_features"):
        SpikeEncodedLinear(0, 4)
    with pytest.raises(ValueError, match="k must be finite"):
        SpikeEncodedLinear(4, 2, k=0.0)
    with pytest.raises(ValueError, match="group_size"):
        SpikeEncodedLinear(4, 2, group_size=3)

    layer = SpikeEncodedLinear(4, 2, group_size=2, seed=7)
    assert layer.quantized_weight.shape == (2, 4)
    assert layer.quantization_error() >= 0.0
    with pytest.raises(ValueError, match="at least 1 dimension"):
        layer.forward(np.array(1.0))
    out = layer.forward(np.array([0.2, -0.4, 0.5, 0.1]))
    assert out.shape == (2,)

    # SpikeQuantumBridge fail-closed & padding branches
    bridge = SpikeQuantumBridge(seed=42)
    enc = bridge.encode(np.array([1.0, -2.0, 0.5, 0.0]))
    assert enc.spikes.shape == (4,)
    with pytest.raises(ValueError, match="non-empty"):
        bridge.to_state(np.array([]))
    with pytest.raises(ValueError, match="finite"):
        bridge.to_state(np.array([1.0, math.nan]))
    with pytest.raises(ValueError, match="16-qubit"):
        bridge.to_state(np.ones((1 << 16) + 1))
    with pytest.raises(ValueError, match="non-empty"):
        bridge.to_qca_rotations(np.array([]))
    with pytest.raises(ValueError, match="finite"):
        bridge.to_qca_rotations(np.array([1.0, math.inf]))
    with pytest.raises(ValueError, match="num_cells"):
        bridge.to_qca_rotations(np.array([1.0, 2.0]), num_cells=0)
    padded = bridge.to_qca_rotations(np.array([1.0, 2.0]), num_cells=4)
    assert padded.shape == (4,) and padded[1] == pytest.approx(math.pi) and padded[3] == 0.0


def test_t242_backend_selector_and_cortex_benchmark(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # selector branches: missing QI_TOKEN, ImportError, configured real backend gate
    monkeypatch.delenv("QI_TOKEN", raising=False)
    assert selector._quantum_inspire_configured() is False
    assert isinstance(selector.build("quantum-inspire"), NumpyBackend)
    assert "numpy" in selector.available()

    monkeypatch.setenv("QI_TOKEN", "dummy-token")
    monkeypatch.setitem(sys.modules, "quantum_inspire", None)
    monkeypatch.setitem(sys.modules, "quantum_inspire.api", None)
    monkeypatch.setitem(sys.modules, "quantum_inspire.credentials", None)
    assert selector._quantum_inspire_configured() is False

    # Configured real backend requires genome + non-ideal noise_model + gates
    monkeypatch.setattr(selector, "_qiskit_configured", lambda: True)
    with pytest.raises(ValueError, match="QuantumGeneSet"):
        selector.build("qiskit")
    with pytest.raises(ValueError, match="non-ideal"):
        selector.build("qiskit", genome=QuantumGeneSet(enabled=True, noise_model="ideal"))
    with pytest.raises(ValueError, match="energy gate"):
        selector.build("qiskit", genome=QuantumGeneSet(enabled=True, noise_model="depolarizing"))
    with pytest.raises(ValueError, match="Sevo gate"):
        selector.build(
            "qiskit",
            genome=QuantumGeneSet(enabled=True, noise_model="depolarizing"),
            energy_gate_passed=True,
        )

    # benchmark_gpu validation, numpy fallback, mock Qiskit GPU/CPU fallback, print_report
    with pytest.raises(ValueError, match="min_qubits"):
        benchmark.benchmark_gpu(min_qubits=0, max_qubits=2)
    with pytest.raises(ValueError, match="max_qubits"):
        benchmark.benchmark_gpu(min_qubits=3, max_qubits=2)
    with pytest.raises(ValueError, match="trials"):
        benchmark.benchmark_gpu(min_qubits=2, max_qubits=2, trials=0)

    class _FakeQC:
        def __init__(self, n: int) -> None:
            self.n = n

        def h(self, _i: int) -> None:
            return None

        def cx(self, _a: int, _b: int) -> None:
            return None

        def measure_all(self) -> None:
            return None

    class _FakeSim:
        def __init__(self, *, method: str, device: str) -> None:
            self.device = device

        def run(self, _qc: Any, shots: int = 256) -> Any:
            if self.device == "GPU":
                raise RuntimeError("no GPU driver")
            return SimpleNamespace(result=lambda: {"0": shots})

    fake_qiskit = types.ModuleType("qiskit")
    fake_qiskit.QuantumCircuit = _FakeQC  # type: ignore[attr-defined]
    fake_aer = types.ModuleType("qiskit_aer")
    fake_aer.AerSimulator = _FakeSim  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "qiskit", fake_qiskit)
    monkeypatch.setitem(sys.modules, "qiskit_aer", fake_aer)
    res_cpu = benchmark.benchmark_gpu(min_qubits=2, max_qubits=2, trials=1)
    assert res_cpu["device"] == ["cpu"]
    benchmark.print_report(res_cpu)
    benchmark.print_report({"qubits": [2], "time_s": [0.01], "device": ["gpu"]})
    out_txt = capsys.readouterr().out
    assert "GPU available" in out_txt and "GPU not used" in out_txt


def test_t242_online_agent_fail_closed_and_mocked_e2e(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Budget validation
    with pytest.raises(ValueError, match="invalid_tool_limit"):
        online_agent.Budget(tool_limit=-1)
    with pytest.raises(ValueError, match="invalid_energy_limit"):
        online_agent.Budget(energy_limit=math.nan)
    with pytest.raises(ValueError, match="invalid_tool_attempts"):
        online_agent.Budget(tool_attempts=-1)
    with pytest.raises(ValueError, match="invalid_reserved_energy"):
        online_agent.Budget(reserved_energy=-0.1)

    # RFC 8259 non-finite JSON rejected by Adapter.call
    class _NanSession:
        async def call_tool(self, _name: str, _args: dict[str, Any]) -> Any:
            return SimpleNamespace(
                isError=False,
                content=[SimpleNamespace(type="text", text='{"rate": NaN}')],
            )

    with pytest.raises(ValueError, match="non_finite_json_constant"):
        asyncio.run(
            online_agent.Adapter(_NanSession(), online_agent.Budget(), []).call(
                "adaptive_clock_rate", {"coherence_phi": 0.5}
            )
        )

    # Mock full online_agent.main() path (both passing and failure summary without leaking creds)
    async def _ok_connect(_creds: Path, events: list[dict[str, Any]]) -> dict[str, Any]:
        events.append({"event": "mock_ok"})
        return {"prediction": "sensor_fault", "reference_match": True}

    out_ok = tmp_path / "run_ok"
    monkeypatch.setattr(online_agent, "connect", _ok_connect)
    monkeypatch.setattr(sys, "argv", ["online_agent", "--output", str(out_ok)])
    online_agent.main()
    assert json.loads((out_ok / "summary.json").read_text(encoding="utf-8"))["status"] == "passed"

    async def _fail_connect(_creds: Path, _events: list[dict[str, Any]]) -> dict[str, Any]:
        raise RuntimeError("secret-token-must-not-appear")

    out_fail = tmp_path / "run_fail"
    monkeypatch.setattr(online_agent, "connect", _fail_connect)
    monkeypatch.setattr(sys, "argv", ["online_agent", "--output", str(out_fail)])
    with pytest.raises(SystemExit) as exc:
        online_agent.main()
    assert exc.value.code == 1
    fail_text = (out_fail / "summary.json").read_text(encoding="utf-8")
    assert "secret-token-must-not-appear" not in fail_text
    assert json.loads(fail_text)["status"] == "failed"


def test_t242_context_decay_develop_tamper_and_evaluate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError, match="archive must be non-empty"):
        context_decay.audit_development(())

    # Fast deterministic end-to-end develop -> freeze -> tamper check -> evaluate
    monkeypatch.setattr(context_decay, "DEVELOPMENT", 2)
    monkeypatch.setattr(context_decay, "EVALUATION", 2)
    monkeypatch.setattr(
        context_decay,
        "audit_development",
        lambda archive: {
            "groups": {"all": {"n": len(archive), "means": [0.1], "winner": context_decay.GRID[0]}},
            "grid": context_decay.GRID,
            "global_excess_loss": 0.0,
            "open_evaluation": True,
        },
    )

    exp_dir = tmp_path / "t229_fast"
    asyncio.run(context_decay.develop(exp_dir))
    assert (exp_dir / "freeze.json").exists()

    # Tampering with archive.json is caught by sealed_inputs()
    orig_archive = (exp_dir / "archive.json").read_bytes()
    (exp_dir / "archive.json").write_text("[]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Input changed since freeze"):
        context_decay.sealed_inputs(exp_dir)
    (exp_dir / "archive.json").write_bytes(orig_archive)

    # Full evaluation runs cleanly on frozen archive and writes completion.json
    asyncio.run(context_decay.evaluate(exp_dir))
    comp = json.loads((exp_dir / "evaluation" / "completion.json").read_text(encoding="utf-8"))
    assert comp["episodes"] == 2
    assert BCELCatalog().is_functional(
        "Fail-closed numeric and RFC 8259 input guards across core and experiment modules (T242)"
    )
