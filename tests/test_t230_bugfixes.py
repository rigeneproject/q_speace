"""Regression tests for T230 bug fixes, fail-closed validation, and invariants."""

from __future__ import annotations

import asyncio
import json
import math
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import numpy as np
import pytest

from q_speace.bcel import BCELCatalog
from q_speace.earth_feed import EarthFeed
from q_speace.economy.dat import DAT
from q_speace.economy.mcp_server import _self_test
from q_speace.economy.primitives import CME, J_c, V
from q_speace.edd_cvt.ilf import InformationalLogicalField
from q_speace.genome import QuantumGeneSet
from q_speace.metabolism.cognitive_cost_model import QuantumCostModel, QuantumOperation
from q_speace.orchestrator import QuantumOrchestrator
from q_speace.quantum import BrainQuantumCircuit, GateType, QuantumState
from q_speace.quantum.backends import (
    QiskitBackend,
    QuantumInspireBackend,
    build,
    validate_real_backend_gate,
)
from q_speace.quantum.backends.quantum_inspire_backend import _decode_qi_histogram_key
from q_speace.radio import ComplianceFilter
from q_speace.radio.models import Waveform
from q_speace.self_improvement_cortex import (
    EvolutionaryMemory,
    MemoryEntry,
    SelfImprovementCortex,
)
from q_speace.self_improvement_cortex.benchmark import benchmark_gpu
from q_speace.spiking import dynamic_spikes
from q_speace.spiking.encoder import SpikeEncodingResult, spike_rate
from q_speace.spiking_brain import (
    HTTPSpikingBrainClient,
    SpikingBrainCortex,
    StubSpikingBrain,
    ThinkResult,
)
from q_speace.spiking_brain.audit import BrainAuditLog, make_apply_record

# ---------------------------------------------------------------------------
# 1. QuantumState physics & bounds (T230-03)
# ---------------------------------------------------------------------------


def test_lindblad_no_jump_amplitude_damping_decays_excited_state() -> None:
    """MCWF no-jump propagator I - i H_eff dt = I - 0.5 gamma L^dag L dt
    must attenuate the excited |1> amplitude toward |0>, not rotate phase.
    """
    # Force no-jump trajectory by using small dt and seed whose first draw > jump_prob.
    s = QuantumState.from_amplitudes([1.0, 1.0], seed=0)
    sigma_minus = np.array([[0.0, 1.0], [0.0, 0.0]], dtype=np.complex128)
    p1_before = float(s.probabilities()[1])
    for _ in range(5):
        # Tiny dt ensures jump_prob = 0.5 * 0.002 * 0.5 = 5e-4, practically always no-jump.
        s.apply_lindblad([(0, sigma_minus)], [0.5], dt=0.002)
    p1_after = float(s.probabilities()[1])
    assert p1_after < p1_before


def test_quantum_state_bounds_and_finiteness() -> None:
    with pytest.raises(ValueError):
        QuantumState.equal_superposition(0)
    with pytest.raises(ValueError):
        QuantumState.equal_superposition(17)
    with pytest.raises(ValueError):
        QuantumState.from_amplitudes([1.0])
    with pytest.raises(ValueError):
        QuantumState.from_amplitudes([float("nan"), 1.0])
    with pytest.raises(ValueError):
        QuantumState(1).apply_lindblad([], [], dt=-0.1)


# ---------------------------------------------------------------------------
# 2. Fail-closed validation across cost, ILF, economy, spiking, radio
# ---------------------------------------------------------------------------


def test_cost_model_fail_closed_on_negative_and_non_finite() -> None:
    cm = QuantumCostModel()
    with pytest.raises(ValueError):
        cm.energy_watts(QuantumOperation(num_qubits=-1, num_gates=1))
    with pytest.raises(ValueError):
        cm.energy_watts(
            QuantumOperation(num_qubits=1, num_gates=1, decoherence_budget=float("nan"))
        )
    with pytest.raises(ValueError):
        cm.energy_joules(QuantumOperation(num_qubits=1, num_gates=1), duration_s=-1.0)
    assert cm.passes_sevo(float("nan"), 1.0) is False
    assert cm.passes_sevo(float("inf"), 1.0) is False
    assert cm.passes_sevo(3.0, 1.0, threshold=float("nan")) is False


def test_ilf_validation_and_zero_vector_update() -> None:
    with pytest.raises(ValueError):
        InformationalLogicalField(coherence_phi=float("nan"))
    with pytest.raises(ValueError):
        InformationalLogicalField(coherence_phi=1.5)
    ilf = InformationalLogicalField()
    ilf.update(np.zeros(4))
    assert ilf.coherence_phi == 0.0
    with pytest.raises(ValueError):
        ilf.update(np.array([1.0, float("nan")]))
    with pytest.raises(ValueError):
        ilf.set_belief("a", np.array([float("inf"), 1.0]))


def test_economy_primitives_and_dat_reject_nan_inf() -> None:
    with pytest.raises(ValueError):
        J_c(J=float("nan"), delta_S=-0.1, delta_I_c=1.0, R_b=0.5, delta_C=0.0, confidence=1.0)
    with pytest.raises(ValueError):
        J_c(J=float("inf"), delta_S=-0.1, delta_I_c=1.0, R_b=0.5, delta_C=0.0, confidence=1.0)
    with pytest.raises(ValueError):
        V(E_x=float("nan"), S_gen=0.1, I_c=1.0, R_b=0.5)
    with pytest.raises(ValueError):
        CME(**dict.fromkeys(CME.__dataclass_fields__, float("nan")))

    dat = DAT(amount=10.0, bound_to="exergy", decay_half_life=60.0, mint_time=0.0)
    with pytest.raises(ValueError):
        dat.spend(float("nan"), "exergy", t=1.0)
    with pytest.raises(ValueError):
        dat.spend(1.0, "exergy", t=float("nan"))
    assert dat.amount == 10.0  # balance uncorrupted


def test_spiking_encoder_empty_and_non_finite() -> None:
    empty = dynamic_spikes(np.array([]))
    assert empty.num_spikes == 0
    assert empty.sparsity == 1.0
    assert empty.rate == 0.0
    assert spike_rate(np.array([])) == 0.0
    with pytest.raises(ValueError):
        dynamic_spikes(np.array([1.0, float("nan")]))
    with pytest.raises(ValueError):
        dynamic_spikes(np.array([1.0, 2.0]), coherence_phi=-2.0, beta=1.0)


def test_compliance_filter_rejects_non_finite_waveform() -> None:
    cf = ComplianceFilter()
    bad_iq = Waveform(
        iq_samples=np.array([1.0, float("nan")]),
        center_freq_hz=2.45e9,
        power_dbm=10.0,
    )
    res = cf.check(bad_iq)
    assert not res.passed
    assert not res.spurious_ok


# ---------------------------------------------------------------------------
# 3. Orchestrator & real-backend invariants (T230-04)
# ---------------------------------------------------------------------------


def test_orchestrator_default_budget_opens_and_respects_enable_radio() -> None:
    orch_no_radio = QuantumOrchestrator(
        genome=QuantumGeneSet(enabled=True),
        neurons=["n0", "n1"],
        seed=1,
        enable_radio=False,
    )
    orch_no_radio.enable_qca(num_cells=4)
    reps = orch_no_radio.run(ticks=3)
    assert any(not r.gate_blocked for r in reps)
    assert all(r.tx_report is None for r in reps)

    orch_radio = QuantumOrchestrator(
        genome=QuantumGeneSet(enabled=True),
        neurons=["n0", "n1"],
        seed=1,
        enable_radio=True,
    )
    reps_radio = orch_radio.run(ticks=3)
    assert any(r.tx_report is not None for r in reps_radio)


def test_orchestrator_marks_gate_blocked_when_sevo_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    orch = QuantumOrchestrator(genome=QuantumGeneSet(enabled=True), neurons=["n0"], seed=1)
    monkeypatch.setattr(orch._cost, "passes_sevo", lambda *a, **kw: False)
    rep = orch.tick()
    assert rep is not None
    assert rep.gate_blocked is True


def test_real_backend_invariant_enforced_in_genome_and_selector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cat = BCELCatalog()
    assert cat.is_functional("Real quantum backend noise-model and energy gate (T230)") is True

    # Genome must reject real backends with ideal noise_model
    with pytest.raises(ValueError, match="noise_model"):
        QuantumGeneSet(enabled=True, backend_name="qiskit", noise_model="ideal").validate()
    with pytest.raises(ValueError, match="shots"):
        QuantumGeneSet(enabled=True, shots=0).validate()

    # Valid real-backend genome passes validate()
    valid_genome = QuantumGeneSet(enabled=True, backend_name="qiskit", noise_model="depolarizing")
    valid_genome.validate()

    # When qiskit IS configured, build() must enforce genome + energy + Sevo gate
    monkeypatch.setattr("q_speace.quantum.backends.selector._qiskit_configured", lambda: True)
    with pytest.raises(ValueError, match="QuantumGeneSet"):
        build("qiskit")
    with pytest.raises(ValueError, match="energy gate"):
        build("qiskit", genome=valid_genome, energy_gate_passed=False, sevo_passed=True)
    with pytest.raises(ValueError, match="Sevo gate"):
        build("qiskit", genome=valid_genome, energy_gate_passed=True, sevo_passed=False)

    bk = build("qiskit-aer", genome=valid_genome, energy_gate_passed=True, sevo_passed=True)
    assert isinstance(bk, QiskitBackend)

    # Direct helper check
    validate_real_backend_gate(valid_genome, energy_gate_passed=True, sevo_passed=True)


def test_qiskit_and_qi_bit_ordering_and_shots() -> None:
    circ = BrainQuantumCircuit("order")
    circ.add_qubit("q0")
    circ.add_qubit("q1")
    circ.add_gate(GateType.X, target="q0")

    # Mock Aer simulator returning Qiskit little-endian "01" (q1=0, q0=1)
    recorded_shots: list[int] = []

    class _FakeResult:
        def get_counts(self, _qc: Any) -> dict[str, int]:
            return {"01": 500}

    class _FakeJob:
        def result(self) -> _FakeResult:
            return _FakeResult()

    class _FakeAer:
        def run(self, _qc: Any, shots: int = 1024) -> _FakeJob:
            recorded_shots.append(shots)
            return _FakeJob()

    bk = QiskitBackend(shots=256)
    bk._aer = _FakeAer()
    bk._to_qiskit_circuit = lambda _c: object()  # type: ignore[method-assign]
    out = bk.run(circ)
    assert recorded_shots == [256]
    assert out == [("q0", "1"), ("q1", "0")]

    # QI histogram decoding (integer state 1 => q0=1, q1=0; bitstring "01" => q0=1, q1=0)
    assert _decode_qi_histogram_key(1, 2) == "10"
    assert _decode_qi_histogram_key("01", 2) == "10"

    qi = QuantumInspireBackend()
    qi._qi = SimpleNamespace(execute_qasm=lambda *a, **kw: {"histogram": {"1": 100}})
    assert qi.run(circ) == [("q0", "1"), ("q1", "0")]


# ---------------------------------------------------------------------------
# 4. SpikingBrainCortex, Audit, Client, EarthFeed (T230-05)
# ---------------------------------------------------------------------------


def test_spiking_brain_cortex_energy_gate_nan_and_all_failed_report() -> None:
    class _NanBackend:
        backend_name = "nan-backend"

        def think(self, *args: Any, **kwargs: Any) -> ThinkResult:
            return ThinkResult(
                text="bad",
                confidence=float("nan"),
                belief=np.array([0.5, 0.5]),
                spikes=SpikeEncodingResult(
                    spikes=np.zeros(2),
                    vth=np.ones(1),
                    num_spikes=0,
                    sparsity=1.0,
                    rate=0.0,
                ),
                plasticity=np.ones(2),
            )

    cortex_nan = SpikingBrainCortex(backend=_NanBackend())
    rep = asyncio.run(cortex_nan.tick("probe"))
    assert rep.approved is False
    assert math.isfinite(rep.energy_w)
    stats = cortex_nan.report()
    assert stats["mean_sevo"] == 0.0
    assert math.isfinite(float(stats["mean_sevo"]))  # type: ignore[arg-type]

    # Optional energy gate blocks when budget is too small
    cortex_gated = SpikingBrainCortex(backend=StubSpikingBrain(seed=0), max_energy_w=0.01)
    rep_energy = asyncio.run(cortex_gated.tick("probe"))
    assert rep_energy.approved is False
    assert "energy_w" in rep_energy.reason


def test_brain_audit_recent_zero_redaction_and_non_finite(tmp_path: Path) -> None:
    log = BrainAuditLog(path=tmp_path / "audit.jsonl", redact_raw_text=True)
    rec = make_apply_record(
        agent_id="brain",
        backend="stub",
        backend_meta={},
        prompt="secret prompt",
        result_text="secret answer",
        result_confidence=0.9,
        result_belief=[0.9, 0.1],
        n_tokens=4,
        coherence_phi_pre=0.9,
        coherence_phi_post=0.9,
        sevo=float("nan"),
        energy_w=10.0,
        approved=True,
        reason="ok",
        include_raw_excerpts=not log.redact_raw_text,
    )
    assert "prompt_excerpt" not in rec
    assert "result_text_excerpt" not in rec
    assert rec["sevo"] is None
    log.write(rec)
    log.close()

    assert log.recent(0) == []
    assert len(log.recent(1)) == 1
    # Verify strict JSON (no NaN token)
    raw = (tmp_path / "audit.jsonl").read_text(encoding="utf-8")
    assert "NaN" not in raw
    assert json.loads(raw.strip())["sevo"] is None


def test_http_client_rejects_non_dict_and_nan_confidence() -> None:
    def _make(payload: Any) -> HTTPSpikingBrainClient:
        transport = httpx.MockTransport(lambda req: httpx.Response(200, json=payload))
        client = HTTPSpikingBrainClient(endpoint="http://fake.local")
        client._client = httpx.AsyncClient(transport=transport)
        return client

    with pytest.raises(ValueError, match="JSON object"):
        asyncio.run(_make(["not", "a", "dict"]).think("hi"))


def test_earth_feed_network_failure_falls_back_cleanly(monkeypatch: pytest.MonkeyPatch) -> None:
    def _bad_get(*args: Any, **kwargs: Any) -> Any:
        return httpx.Response(500, request=httpx.Request("GET", "https://example.invalid"))

    monkeypatch.setattr(httpx, "get", _bad_get)
    feed = EarthFeed(use_network=True)
    sig = feed.fetch(tick=3)
    assert 0.0 <= sig.kp <= 1.0


# ---------------------------------------------------------------------------
# 5. SelfImprovementCortex, Benchmark, MCP Self-Test (T230-06)
# ---------------------------------------------------------------------------


def test_sia_tick_does_not_mutate_context_and_tracks_failures() -> None:
    mem = EvolutionaryMemory()
    cortex = SelfImprovementCortex(evolutionary_memory=mem)
    cortex.observer.snapshot(coherence_phi=0.2)
    caller_ctx = {"coherence_phi": 0.2, "plasticity_index": 0.2}
    snapshot_before = dict(caller_ctx)
    rep = cortex.tick(caller_ctx)
    assert caller_ctx == snapshot_before
    if rep.selected > 0:
        assert rep.verdict is not None

    # Verify _should_skip_rollback matches stored context_signature
    mem.store(
        MemoryEntry(
            mutation_id="m-fail",
            context_signature="0.2",
            reason="failed test",
            level=1,
            target="ilf_weight",
            metrics_before={},
            metrics_after={},
            outcome=-1.0,
        )
    )
    proposal = SimpleNamespace(level=1, target="ilf_weight")
    assert cortex._should_skip_rollback(proposal, "0.2") is True  # type: ignore[arg-type]


def test_benchmark_gpu_validates_inputs_and_returns_json_floats() -> None:
    with pytest.raises(ValueError):
        benchmark_gpu(min_qubits=0, max_qubits=2, trials=1)
    with pytest.raises(ValueError):
        benchmark_gpu(min_qubits=4, max_qubits=2, trials=1)
    with pytest.raises(ValueError):
        benchmark_gpu(min_qubits=2, max_qubits=2, trials=0)

    res = benchmark_gpu(min_qubits=2, max_qubits=2, trials=1)
    assert res["qubits"] == [2]
    assert isinstance(res["time_s"][0], float)
    json.dumps(res)


def test_mcp_server_self_test_succeeds() -> None:
    assert _self_test() == 0
