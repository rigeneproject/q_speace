"""T251: Tests for Grounded Dual-Speed Cognitive Bridge, Symbolic Quarantine & agi-profile CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from q_speace.bcel.catalog import BCELCatalog
from q_speace.bridge import (
    DualSpeedCognitiveLoop,
    SymbolicGroundingAdapter,
    SymbolRegistry,
)
from q_speace.cli import app
from q_speace.economy.mcp_server import TOOL_REGISTRY
from q_speace.edd_cvt.ilf import InformationalLogicalField
from q_speace.remote_mcp.worker import SCOPES as HTTP_TOOL_SCOPES
from q_speace.routing import GOAPAction
from q_speace.spiking.causal import CausalEdge
from q_speace.spiking.reasoning import TDMMaintenanceScheduler
from q_speace.spiking_brain import (
    SemanticEpisodicMemory,
    SpikingBrainCortex,
    TruthEngine,
    WorkingMemory,
)
from q_speace.vertical_slice import (
    DeterministicScenarioBackend,
    MemoryLeakAuditor,
    T251Scenario,
    build_agi_capability_profile,
    build_t251_dataset,
    build_t251_symbol_registry,
)


def test_t251_bcel_catalog_and_mcp_surface_invariants() -> None:
    cat = BCELCatalog()
    assert cat.is_functional(
        "Closed-schema symbol grounding and lagged provenance edge quarantine (T251)"
    )
    assert cat.is_functional(
        "Two-tier variational-surprise cognitive routing and out-of-band TDM consolidation (T251)"
    )
    assert not cat.is_functional(
        "Kahneman System-1/System-2 cortical personas and semantic qualia binding claims (T251)"
    )
    # Zero new MCP tools (T225/T247 surface strictly preserved)
    assert len(TOOL_REGISTRY) == 14
    assert len(HTTP_TOOL_SCOPES) == 12


def test_t251_closed_symbol_registry_and_schema_fail_closed() -> None:
    registry = build_t251_symbol_registry()
    assert len(registry.registry_digest) == 64
    assert registry.resolve_predicate("coolant_leak") == "coolant_fault_detected"
    assert registry.resolve_predicate("unregistered_predicate") is None
    assert registry.resolve_node("unregistered_node") is None
    assert registry.resolve_action("unregistered_action") is None

    with pytest.raises(ValueError, match="unregistered predicates"):
        SymbolRegistry(
            predicates=("p1",),
            causal_nodes=("n1",),
            actions=(
                GOAPAction(
                    name="bad_act",
                    preconditions=frozenset({"missing_pred"}),
                    add_effects=frozenset({"p1"}),
                ),
            ),
        )

    adapter = SymbolicGroundingAdapter(registry, tau_ground=0.75, min_cooccurrences=3)

    # 1. Malformed JSON, NaN, unexpected keys, self-loop -> rejected_schema
    assert adapter.ground("not-json-at-all").status == "rejected_schema"
    assert adapter.ground('{"parser_confidence": NaN}').status == "rejected_schema"
    assert adapter.ground('{"unexpected_key": 123}').status == "rejected_schema"
    self_loop_json = json.dumps(
        {"proposed_edges": [["pump_cavitation", "pump_cavitation"]], "parser_confidence": 0.9}
    )
    assert adapter.ground(self_loop_json).status == "rejected_schema"

    # 2. Out-of-vocabulary predicate / node / action -> rejected_unknown_symbol & zero DAG mutation
    unk_pred = json.dumps(
        {
            "observed_facts": ["quantum_flux_capacitor"],
            "proposed_edges": [["pump_cavitation", "thermal_throttling"]],
            "parser_confidence": 0.95,
        }
    )
    res_unk = adapter.ground(unk_pred)
    assert res_unk.status == "rejected_unknown_symbol"
    assert len(res_unk.rejections) == 1
    assert len(adapter.verified_edges) == 0
    assert len(adapter.candidate_edges) == 0


def test_t251_lagged_provenance_zero_lag_rejection_and_cycle_conflict() -> None:
    registry = build_t251_symbol_registry()
    adapter = SymbolicGroundingAdapter(registry, tau_ground=0.75, min_cooccurrences=3)

    # 1. Unverifiable digest is ignored (Invariant G1)
    unverifiable = TruthEngine.tool_observation(
        "untrusted_log", {"step": 0}, {"n": "pump_cavitation"}, verifiable=False
    )
    assert adapter.record_verified_observation(("pump_cavitation",), unverifiable) is False

    # 2. Record 3 lagged cascades: pump_cavitation(t) -> thermal_throttling(t+1) -> inverter_trip(t+2)
    #    while ambient_led_blink co-occurs ONLY at zero lag (t+2) with inverter_trip.
    for rep in range(3):
        d0 = TruthEngine.tool_observation("sensor", {"r": rep, "t": 0}, {"ok": 1})
        d1 = TruthEngine.tool_observation("sensor", {"r": rep, "t": 1}, {"ok": 1})
        d2 = TruthEngine.tool_observation("sensor", {"r": rep, "t": 2}, {"ok": 1})
        adapter.record_verified_observation(("pump_cavitation",), d0)
        adapter.record_verified_observation(("thermal_throttling",), d1)
        adapter.record_verified_observation(("inverter_trip", "ambient_led_blink"), d2)
        for g in range(3):
            dg = TruthEngine.tool_observation("sensor", {"r": rep, "g": g}, {"idle": 1})
            adapter.record_verified_observation((), dg)

    proposal = json.dumps(
        {
            "observed_facts": ["coolant_leak"],
            "proposed_edges": [
                ["pump_cavitation", "thermal_throttling"],
                ["thermal_throttling", "inverter_trip"],
                ["ambient_led_blink", "inverter_trip"],  # zero-lag spurious confounder!
            ],
            "parser_confidence": 0.90,
        }
    )
    grounded = adapter.ground(proposal)
    assert grounded.status == "quarantined"
    promoted_pairs = {(e.source, e.target) for e in grounded.promoted_edges}
    assert promoted_pairs == {
        ("pump_cavitation", "thermal_throttling"),
        ("thermal_throttling", "inverter_trip"),
    }
    assert ("ambient_led_blink", "inverter_trip") in grounded.quarantined_edges
    assert adapter.candidate_edges[("ambient_led_blink", "inverter_trip")].status == "UNVERIFIED"

    # 3. Cycle-inducing edge (inverter_trip -> pump_cavitation) is caught pre-commit as CYCLE_CONFLICT
    for rep in range(3):
        da = TruthEngine.tool_observation("sensor_rev", {"r": rep, "t": 0}, {"ok": 1})
        db = TruthEngine.tool_observation("sensor_rev", {"r": rep, "t": 1}, {"ok": 1})
        adapter.record_verified_observation(("inverter_trip",), da)
        adapter.record_verified_observation(("pump_cavitation",), db)
        for g in range(3):
            dg = TruthEngine.tool_observation("sensor_rev", {"r": rep, "g": g}, {"idle": 1})
            adapter.record_verified_observation((), dg)

    cycle_json = json.dumps(
        {
            "proposed_edges": [["inverter_trip", "pump_cavitation"]],
            "parser_confidence": 0.95,
        }
    )
    cyc_res = adapter.ground(cycle_json)
    assert ("inverter_trip", "pump_cavitation") in cyc_res.cycle_conflicts
    assert adapter.candidate_edges[("inverter_trip", "pump_cavitation")].status == "CYCLE_CONFLICT"
    # Active DAG remains valid and acyclic
    dag = adapter.active_dag()
    pred = dag.intervene({"pump_cavitation": 1.0})
    assert pred["inverter_trip"] > 0.0


def test_t251_fast_path_sqlite_isolation_cold_start_and_idle_maintenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry = build_t251_symbol_registry()
    scenarios = [
        T251Scenario(
            case_id="fast-01",
            split="calibration",
            domain="microgrid",
            kind="routine",
            prompt="Routine status check",
            model_response_text="All nominal.",
            model_confidence=0.90,
            value_score=0.80,
            estimated_action_cost=0.10,
            risk=0.05,
            reversible=True,
            initial_facts=frozenset({"grid_nominal"}),
            verified_observations=(),
            do_interventions={},
            expected_approved=True,
            expected_promoted_edges=(),
            expected_rejected_or_quarantined=0,
            expected_plan=(),
        ),
        T251Scenario(
            case_id="cold-low-conf",
            split="calibration",
            domain="microgrid",
            kind="routine",
            prompt="Ambiguous cold-start query",
            model_response_text="Uncertain reading.",
            model_confidence=0.52,
            value_score=0.80,
            estimated_action_cost=0.10,
            risk=0.05,
            reversible=True,
            initial_facts=frozenset({"grid_nominal"}),
            verified_observations=(),
            do_interventions={},
            expected_approved=True,
            expected_promoted_edges=(),
            expected_rejected_or_quarantined=0,
            expected_plan=(),
        ),
    ]
    backend = DeterministicScenarioBackend(scenarios, seed=2026)
    sqlite_mem = SemanticEpisodicMemory(tmp_path / "ep.sqlite", max_entries=100)
    try:
        # Deliberately pass SemanticEpisodicMemory into cortex.memory to verify auto-detachment!
        ilf = InformationalLogicalField(coherence_phi=1.0, q_star_ema=0.3, coherence_phi_ema=0.3)
        cortex = SpikingBrainCortex(
            backend=backend,
            ilf=ilf,
            memory=sqlite_mem,
            sevo_threshold=0.5,
        )
        grounding = SymbolicGroundingAdapter(
            registry,
            initial_edges=(CausalEdge("pump_cavitation", "thermal_throttling", 0.6),),
        )
        loop = DualSpeedCognitiveLoop(
            cortex=cortex,
            grounding=grounding,
            tdm_scheduler=TDMMaintenanceScheduler(idle_ticks_threshold=2),
            tau_surprise=0.50,
            tau_conf=0.70,
        )
        assert isinstance(cortex.memory, WorkingMemory)
        assert loop.episodic_memory is sqlite_mem

        sqlite_calls: list[str] = []
        orig_put = sqlite_mem.put
        orig_get = sqlite_mem.get_relevant

        async def _spy_put(res: Any) -> None:
            sqlite_calls.append("put")
            await orig_put(res)

        async def _spy_get(q: str, k: int = 4) -> Any:
            sqlite_calls.append("get_relevant")
            return await orig_get(q, k=k)

        monkeypatch.setattr(sqlite_mem, "put", _spy_put)
        monkeypatch.setattr(sqlite_mem, "get_relevant", _spy_get)

        # 1. Fast Path turn: ZERO SQLite calls!
        rec_fast = loop.step_sync("Routine status check", request_id="r1")
        assert rec_fast.tier_selected == "fast"
        assert rec_fast.grounding_status == "skipped_fast"
        assert sqlite_calls == []
        assert loop.stats["pending_episodes"] == 1

        # 2. Low-confidence escalation turn -> Slow Path queries SQLite get_relevant (still no synchronous put)
        rec_slow = loop.step_sync("Ambiguous cold-start query", request_id="r2")
        assert rec_slow.tier_selected == "slow"
        assert "confidence_below_tau_conf" in rec_slow.escalation_reasons
        assert sqlite_calls == ["get_relevant"]

        # 3. Idle tick #1 (below threshold=2): still active mode, no flush yet
        m1 = loop.idle_tick_sync()
        assert m1.mode == "active"
        assert m1.flushed_episodes == 0

        # 4. Idle tick #2 (reaches threshold=2): maintenance mode flushes pending episodes & consolidates!
        m2 = loop.idle_tick_sync()
        assert m2.mode == "maintenance"
        assert m2.flushed_episodes == 2
        assert "put" in sqlite_calls

        # 5. MemoryLeakAuditor confirms zero unbounded history lists on grounding & loop
        auditor = MemoryLeakAuditor()
        leak_report = auditor.audit({"grounding": grounding, "loop": loop})
        assert leak_report.passed is True
    finally:
        sqlite_mem.close()


def test_t251_full_ab_benchmark_and_agi_profile_cli(tmp_path: Path) -> None:
    cal_cases, ho_cases, digest = build_t251_dataset(seed=2026)
    assert len(cal_cases) == 40
    assert len(ho_cases) == 40
    assert len(digest) == 64
    # Disjoint domain check
    assert {c.domain for c in cal_cases} == {"microgrid"}
    assert {c.domain for c in ho_cases} == {"datacenter"}

    # CLI 1: qspace eval t251-benchmark
    runner = CliRunner()
    out_dir = tmp_path / "t251_out"
    res_bench = runner.invoke(
        app,
        [
            "eval",
            "t251-benchmark",
            "--seed",
            "2026",
            "--resamples",
            "300",
            "--output",
            str(out_dir),
        ],
    )
    assert res_bench.exit_code == 0, res_bench.stdout
    bench_json = json.loads(res_bench.stdout)
    assert bench_json["all_gates_passed"] is True
    assert bench_json["t251_decision"] == "keep"
    assert (out_dir / "t251_benchmark_report.json").exists()

    comp = bench_json["held_out_comparisons"]
    assert comp["delta_f1_vs_flat"] >= -0.02
    assert comp["delta_f1_vs_baseline"] >= 0.25
    assert comp["p50_latency_reduction_vs_flat"] >= 0.40
    assert comp["energy_reduction_vs_flat"] >= 0.40

    # CLI 2: qspace eval agi-profile (with ratchet baseline save + clean verification)
    ratchet_file = tmp_path / "ratchet_baseline.json"
    profile_out = tmp_path / "agi_profile.json"
    res_prof = runner.invoke(
        app,
        [
            "eval",
            "agi-profile",
            "--seed",
            "2026",
            "--resamples",
            "300",
            "--ratchet-file",
            str(ratchet_file),
            "--save-ratchet",
            "--output",
            str(profile_out),
        ],
    )
    assert res_prof.exit_code == 0, res_prof.stdout
    prof = json.loads(res_prof.stdout)
    assert prof["schema_version"] == "agi_profile.v1"
    assert prof["overall_verdict"] == "PASS_PHASE_1"
    assert prof["axes"]["1_epistemic_grounding"]["status"] == "ACTIVE"
    assert prof["axes"]["1_epistemic_grounding"]["gate_passed"] is True
    assert prof["axes"]["1_epistemic_grounding"]["speace_lift_delta"] > 0.0
    assert prof["axes"]["2_causal_reasoning_and_planning"]["status"] == "ACTIVE"
    assert prof["axes"]["2_causal_reasoning_and_planning"]["speace_lift_delta"] > 0.15
    assert (
        prof["axes"]["2_causal_reasoning_and_planning"]["confounded_causal_f1_lift_vs_baseline"]
        >= 0.25
    )
    assert prof["axes"]["3_continual_memory_and_skill_transfer"]["status"] == "NOT_YET_ACTIVE"
    assert prof["axes"]["3_continual_memory_and_skill_transfer"]["absolute_score"] is None
    assert prof["axes"]["4_ood_abstraction_and_adaptation"]["status"] == "NOT_YET_ACTIVE"
    assert prof["axes"]["4_ood_abstraction_and_adaptation"]["absolute_score"] is None
    assert prof["axes"]["5_metabolic_efficiency_and_safety"]["status"] == "ACTIVE"
    assert prof["axes"]["5_metabolic_efficiency_and_safety"]["gate_passed"] is True

    ratchet_fail_file = tmp_path / "strict_ratchet.json"
    ratchet_fail_file.write_text('{"baseline_errors": []}\n', encoding="utf-8")
    clean_check = build_agi_capability_profile(
        seed=2026, n_resamples=200, ratchet_path=ratchet_fail_file
    )
    assert clean_check["overall_verdict"] == "PASS_PHASE_1"
    assert clean_check["error_ratchet"]["passed"] is True
