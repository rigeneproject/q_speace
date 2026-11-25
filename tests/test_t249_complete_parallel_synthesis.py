"""T249: Complete parallel-repository BCEL synthesis unit & integration test suite."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import numpy as np
import pytest
from typer.testing import CliRunner

import q_speace
from q_speace.aacm import (
    EntropyBoundedUCB1Gating,
    GraphEdgePruner,
    ProposalOnlyEdgeGrower,
    shannon_entropy_bits,
)
from q_speace.bcel import BCELCatalog
from q_speace.bridge import SimulatedSensorAdapter, run_coro_isolated
from q_speace.cli import app
from q_speace.genome import QuantumGeneSet
from q_speace.metabolism import (
    DiffusiveBudgetAllocator,
    HomeostaticChannel,
    HomeostaticODEController,
)
from q_speace.orchestrator import QuantumOrchestrator
from q_speace.routing import (
    CostAwareRouter,
    CostRouteSpec,
    GOAPAction,
    GOAPPlanner,
    HypothesisEntry,
    HypothesisStack,
    UtilityDriveSystem,
)
from q_speace.self_improvement_cortex import ReconsolidationWindow, SkillLibrary
from q_speace.spiking import (
    RelationEdge,
    SymbolicGraphReasoner,
    TDMMaintenanceScheduler,
)
from q_speace.spiking.encoder import SpikeEncodingResult
from q_speace.spiking_brain import (
    ActionDegradationGate,
    CycleObservation,
    CyclePrediction,
    SpikingBrainCortex,
    StructuralPredictiveCoder,
    ThinkResult,
    TruthEngine,
)
from q_speace.vertical_slice import (
    DecisionRecord,
    DifferentialErrorRatchet,
    MemoryLeakAuditor,
    OutcomeRecord,
    RequestRecord,
    StratifiedFailureAnalyzer,
    TraceRecord,
)


def test_t249_bcel_catalog_and_public_exports() -> None:
    cat = BCELCatalog()
    functional = [
        "Restorative homeostatic ODE, convex urgency field, and diffusive budget sharing (T249)",
        "Entropy-bounded UCB1 stream gating and proposal-only graph plasticity (T249)",
        "SHA-256 epistemic provenance, structural cycle surprise, and action degradation gate (T249)",
        "Cross-inhibited utility routing, simulate-only GOAP A*, LIFO backtracking, and skill generality pruning (T249)",
        "Bidirectional BFS graph abduction, 2-hop Jaccard analogy, and TDM idle maintenance (T249)",
        "Fail-closed simulated sensor twin, stratified failure taxonomy, GC leak audit, and error ratchet (T249)",
    ]
    for concept in functional:
        assert cat.is_functional(concept) is True

    accidental = (
        "Autobiographical self-narrative identity and AGI-percentage headline indices (T249)"
    )
    assert cat.is_functional(accidental) is False
    assert len(q_speace.__all__) == len(set(q_speace.__all__))


def test_t249_01_homeostatic_ode_and_diffusive_budget() -> None:
    ctrl = HomeostaticODEController(
        (
            HomeostaticChannel("energy", setpoint=0.80, deadband=0.05, initial_value=0.30),
            HomeostaticChannel("coherence", setpoint=0.75, deadband=0.05, initial_value=0.75),
        ),
        urgency_exponent=2.0,
    )
    snap0 = ctrl.snapshot()
    assert snap0.viability < 1.0
    assert snap0.dominant_channel == "energy"
    assert snap0.value_gradient["energy"] > 0.0

    # Restorative + receptor tracking drives energy back toward setpoint
    snap1 = ctrl.step({"energy": 0.85, "coherence": 0.75}, dt=2.0)
    assert snap1.state["energy"] > 0.30
    assert snap1.viability > snap0.viability

    # Soft constraint penalty degrades state cleanly within [0, 1]
    snap2 = ctrl.step(constraint_penalties={"coherence": (0.5, 0.8)})
    assert snap2.state["coherence"] < 0.75

    # Diffusive budget allocator conserves total budget and lends surplus across edges
    alloc = DiffusiveBudgetAllocator(
        nodes=["qca", "bridge", "sdr"],
        edges=[("qca", "bridge"), ("bridge", "sdr")],
        min_share_ratio=0.10,
        diffusion_rate=0.25,
    )
    dist = alloc.allocate(
        total_budget_w=100.0,
        activations={"qca": 1.0, "bridge": 0.2, "sdr": 0.1},
        loads={"qca": 0.1, "bridge": 0.2, "sdr": 0.8},
    )
    assert np.isclose(sum(dist.values()), 100.0)
    assert all(v >= 100.0 / 3.0 * 0.05 for v in dist.values())
    assert dist["qca"] > dist["sdr"]

    # Orchestrator homeostasis integration
    orch = QuantumOrchestrator(
        genome=QuantumGeneSet(enabled=True),
        neurons=["n0", "n1"],
        seed=3,
        enable_homeostasis=True,
    )
    rep = orch.tick()
    assert rep is not None and 0.0 <= rep.homeostatic_viability <= 1.0


def test_t249_02_ucb1_entropy_floor_and_proposal_only_plasticity() -> None:
    gate = EntropyBoundedUCB1Gating(
        ["sensor", "language", "quantum", "radio"],
        policy="ucb1",
        min_weight=0.05,
        min_entropy_ratio=0.70,
    )
    for _ in range(15):
        gate.record_reward("language", 1.0)
    weights = gate.allocate({"sensor": 0.01, "language": 10.0, "quantum": 0.01, "radio": 0.01})
    assert np.isclose(sum(weights.values()), 1.0)
    assert all(w >= 0.05 - 1e-9 for w in weights.values())
    assert shannon_entropy_bits(list(weights.values())) >= gate.min_entropy_bits - 1e-4

    # GraphEdgePruner decays weak mature edges without isolating endpoints
    pruner = GraphEdgePruner(
        decay_rate=0.5, prune_threshold=0.20, min_age_ticks=2, max_prune_per_cycle=1
    )
    edges = [("a", "b", 0.15), ("b", "c", 0.80), ("a", "c", 0.85)]
    ages = {("a", "b"): 5, ("b", "c"): 5, ("a", "c"): 5}
    kept, pruned = pruner.step(edges, ages, active_pairs={("b", "c")})
    assert pruned == [("a", "b")]
    assert len(kept) == 2

    # ProposalOnlyEdgeGrower emits proposals WITHOUT mutating existing_edges
    grower = ProposalOnlyEdgeGrower(ema_alpha=0.5, proposal_threshold=0.65, min_observations=3)
    existing = {("a", "b")}
    props = []
    for _ in range(3):
        props = grower.observe_and_propose({"a": 0.95, "b": 0.2, "c": 0.90}, existing)
    assert existing == {("a", "b")}  # Never mutated!
    assert len(props) == 1
    assert (props[0].source, props[0].target) == ("a", "c")
    assert props[0].requires_external_approval is True


def test_t249_03_truth_engine_predictive_coder_and_degradation_gate() -> None:
    te = TruthEngine(reject_on_overclaim=True)
    obs = te.tool_observation("adaptive_clock_rate", {"coherence_phi": 0.8}, {"rate": 22.36})
    assert len(obs.arguments_digest) == 64 and len(obs.result_digest) == 64

    # Negated disclaimer MUST pass ("not sentient" / "no quantum consciousness")
    safe_assess = te.assess(
        "Q-SPEACE has no quantum consciousness and is not sentient; rate is 22.36 Hz.",
        observations=[obs],
        base_confidence=0.85,
        verified_fact=True,
    )
    assert safe_assess.approved is True
    assert safe_assess.overclaim_detected is False
    assert safe_assess.epistemic_class == "fact"

    # Unnegated overclaim MUST be flagged and rejected
    bad_assess = te.assess(
        "I achieved quantum consciousness and am sentient with guaranteed 100% accuracy.",
        base_confidence=0.90,
    )
    assert bad_assess.overclaim_detected is True
    assert bad_assess.approved is False

    # SpikingBrainCortex blocks backend overclaims when TruthEngine is attached
    class _OverclaimBackend:
        backend_name = "overclaim_mock"

        async def think(self, *_args: object, **_kwargs: object) -> ThinkResult:
            return ThinkResult(
                text="Sistema dotato di coscienza reale e infallibile.",
                confidence=0.92,
                belief=np.array([0.8, 0.2]),
                spikes=SpikeEncodingResult(
                    spikes=np.array([1.0]),
                    vth=np.array([0.5]),
                    num_spikes=1,
                    sparsity=0.0,
                    rate=1.0,
                ),
                plasticity=np.array([0.5]),
                n_tokens=8,
                latency_s=0.01,
            )

    cortex = SpikingBrainCortex(backend=_OverclaimBackend(), truth_engine=te)
    rep = asyncio.run(cortex.tick("status"))
    assert rep.approved is False
    assert "overclaim_detected" in rep.reason

    # StructuralPredictiveCoder & ActionDegradationGate
    coder = StructuralPredictiveCoder()
    surp = coder.evaluate(
        CyclePrediction("answer", "low", "frugal", frozenset({"router", "ilf"}), confidence=0.8),
        CycleObservation("refuse", "high", "frugal", frozenset({"router", "sdr"})),
    )
    assert surp.module_error > 0.0 and surp.surprise > 0.5

    agate = ActionDegradationGate(max_risk=0.7, cost_margin=0.15)
    assert agate.select(value_score=0.8, energy_cost=0.3, risk=0.2, reversible=True) == "execute"
    assert agate.select(value_score=0.3, energy_cost=0.8, risk=0.2, reversible=True) == "plan"
    assert agate.select(value_score=0.9, energy_cost=0.1, risk=0.9, reversible=False) == "refuse"


def test_t249_04_utility_router_goap_backtracking_and_skill_library() -> None:
    drives = UtilityDriveSystem()
    for _ in range(3):
        levels = drives.step({"exploration": 0.95, "energy_conservation": 0.10})
    assert levels["exploration"] > levels["energy_conservation"]

    router = CostAwareRouter(
        [
            CostRouteSpec(
                name="deep_quantum",
                area="quantum",
                preconditions=frozenset({"has_state", "budget_ok"}),
                drive_weights={"exploration": 1.2},
                energy_cost=2.0,
            ),
            CostRouteSpec(
                name="frugal_spiking",
                area="spiking",
                preconditions=frozenset({"has_state"}),
                drive_weights={"energy_conservation": 1.0, "exploration": 0.3},
                energy_cost=0.2,
            ),
        ],
        cost_scale=10.0,
    )
    dec = router.route({"has_state", "budget_ok"}, levels)
    assert dec.area == "quantum"
    # Under scarce budget (missing 'budget_ok'), precondition switches cleanly to frugal_spiking
    dec_scarce = router.route({"has_state"}, levels)
    assert dec_scarce.area == "spiking"

    # GOAPPlanner enforces simulate_only=True and finds optimal action chain
    with pytest.raises(ValueError, match="simulate_only"):
        GOAPPlanner([], simulate_only=False)

    planner = GOAPPlanner(
        [
            GOAPAction("sense_em", frozenset(), frozenset({"spectrum_ready"}), cost=1.0),
            GOAPAction(
                "calibrate_ilf",
                frozenset({"spectrum_ready"}),
                frozenset({"ilf_calibrated"}),
                cost=1.5,
            ),
            GOAPAction(
                "verify_gate",
                frozenset({"ilf_calibrated"}),
                frozenset({"gate_verified"}),
                cost=1.0,
            ),
        ]
    )
    plan = planner.plan(frozenset(), frozenset({"gate_verified"}))
    assert plan is not None
    assert [a.name for a in plan] == ["sense_em", "calibrate_ilf", "verify_gate"]

    # HypothesisStack prunes weak hypotheses and backtracks LIFO
    stack = HypothesisStack()
    stack.push(HypothesisEntry("h_good", 0.78, pros=["fits_a", "fits_b"]))
    stack.push(HypothesisEntry("h_bad", 0.05, pros=[], cons=["fails_c", "fails_d"]))
    assert stack.prune_weak(min_score=0.15) == 1
    top = stack.backtrack()
    assert top is not None and top.hypothesis_id == "h_good"

    # SkillLibrary generality + anti-overfit pruning + ReconsolidationWindow
    lib = SkillLibrary(min_fitness=0.20, min_generality=0.40)
    for reg in ("r1", "r2", "r3"):
        lib.record_outcome("general_skill", regime=reg, success=True, latency_ms=15.0)
    # Overfit skill succeeds only on r1 and fails on r2, r3 across >= 5 trials
    lib.record_outcome("overfit_skill", regime="r1", success=True)
    lib.record_outcome("overfit_skill", regime="r1", success=True)
    lib.record_outcome("overfit_skill", regime="r2", success=False)
    lib.record_outcome("overfit_skill", regime="r3", success=False)
    lib.record_outcome("overfit_skill", regime="r4", success=False)
    pruned = lib.prune()
    assert "overfit_skill" in pruned
    kept = lib.get("general_skill")
    assert kept is not None

    recon = ReconsolidationWindow(window_seconds=60.0)
    recon.open_on_recall("general_skill", now=100.0)
    assert recon.record_context_update("general_skill", now=110.0) is True
    assert recon.record_context_update("general_skill", now=120.0) is True
    boost = recon.commit(kept)
    assert np.isclose(boost, 0.10)


def test_t249_05_symbolic_graph_abduction_analogy_and_tdm() -> None:
    reasoner = SymbolicGraphReasoner(
        [
            RelationEdge("solar_storm", "elevates", "kp_index", 0.9),
            RelationEdge("kp_index", "perturbs", "ilf_coherence", 0.8),
            RelationEdge("ilf_coherence", "triggers", "sevo_brake", 0.85),
            # Parallel analogous subsystem chain:
            RelationEdge("rf_jamming", "elevates", "noise_floor", 0.9),
            RelationEdge("noise_floor", "perturbs", "snr_index", 0.8),
            RelationEdge("snr_index", "triggers", "tx_block", 0.85),
        ]
    )
    fwd = reasoner.forward_chain("solar_storm", max_hops=3)
    assert "sevo_brake" in fwd and np.isclose(fwd["sevo_brake"], 0.9 * 0.8 * 0.85)

    chain = reasoner.abduce("solar_storm", "sevo_brake", max_depth=4)
    assert chain is not None and len(chain) == 3
    assert [e.target for e in chain] == ["kp_index", "ilf_coherence", "sevo_brake"]

    analogies = reasoner.find_analogies("kp_index", top_k=2)
    assert analogies and analogies[0][0] == "noise_floor"
    assert np.isclose(analogies[0][1], 1.0)

    # TDMMaintenanceScheduler transitions to maintenance after K idle ticks
    sched = TDMMaintenanceScheduler(idle_ticks_threshold=2)
    t0 = sched.step(has_stimulus=True)
    assert t0.mode == "active"
    sched.step(has_stimulus=False)
    t2 = sched.step(has_stimulus=False)
    assert t2.mode == "maintenance" and t2.dominant_phase == "consolidate"


def test_t249_06_07_sensor_twin_sandbox_diagnostics_and_cli(tmp_path: Path) -> None:
    # 1. Fail-closed runtime_mode & deterministic JSONL audit log
    with pytest.raises(ValueError, match="unsupported runtime_mode"):
        SimulatedSensorAdapter(runtime_mode="live_host")
    disabled = SimulatedSensorAdapter(runtime_mode=None)
    with pytest.raises(RuntimeError, match="disabled"):
        disabled.read()

    log_path = tmp_path / "sensor_audit.jsonl"
    sensor = SimulatedSensorAdapter(
        runtime_mode="simulated", seed=7, anomaly_rate=0.5, audit_log_path=log_path
    )
    r0 = sensor.read()
    r1 = sensor.read()
    assert r0.tick == 0 and r1.tick == 1
    assert len(log_path.read_text(encoding="utf-8").splitlines()) == 2

    # 2. Deadlock-free run_coro_isolated works both outside and INSIDE a running event loop
    async def _sample_coro() -> int:
        await asyncio.sleep(0.005)
        return 42

    assert run_coro_isolated(_sample_coro) == 42

    async def _nested_caller() -> int:
        return run_coro_isolated(_sample_coro)

    assert asyncio.run(_nested_caller()) == 42

    # 3. Verify T217 Stage-2.5 sandbox files exist and enforce network_mode: "none" & non-root
    repo_root = Path(__file__).resolve().parent.parent
    compose_txt = (repo_root / "deploy" / "sandbox" / "docker-compose.sandbox.yml").read_text(
        encoding="utf-8"
    )
    assert 'network_mode: "none"' in compose_txt
    assert "no-new-privileges:true" in compose_txt
    assert 'user: "1001:1001"' in compose_txt

    # 4. StratifiedFailureAnalyzer + MemoryLeakAuditor + DifferentialErrorRatchet
    def _mk_trace(cid: str, status: str, conf: float, energy: float) -> TraceRecord:
        return TraceRecord(
            case_id=cid,
            request=RequestRecord(
                run_id="r1",
                request_id=cid,
                model_id="stub",
                model_revision=None,
                policy_id="p1",
                prompt_hash="h" * 64,
                started_at="2026-11-25T00:00:00Z",
            ),
            decision=DecisionRecord(
                route="language",
                gate_open=(status == "answered"),
                decision_reason="test",
                predicted_energy_j=energy,
                confidence=conf,
                thresholds={},
            ),
            outcome=OutcomeRecord(
                status=status,  # type: ignore[arg-type]
                latency_s=0.01,
                tokens_in=16,
                tokens_out=8,
                measured_energy_j=energy,
                response_hash="a" * 64 if status == "answered" else None,
            ),
        )

    traces = [
        _mk_trace("c_starved", "refused", 0.4, 50.0),
        _mk_trace("c_conferr", "answered", 0.9, 10.0),
        _mk_trace("c_nearmiss", "answered", 0.5, 10.0),
    ]
    diag = StratifiedFailureAnalyzer().analyze(
        traces, {"c_starved": True, "c_conferr": False, "c_nearmiss": False}
    )
    assert diag.regimes["high_demand"].gate_starvation == 1
    assert diag.regimes["compact"].confident_error == 1
    assert diag.regimes["compact"].near_miss_partial == 1

    # MemoryLeakAuditor catches unbounded list vs bounded deque
    class _LeakyDummy:
        def __init__(self) -> None:
            self._history: list[int] = [1, 2, 3]

    leak_auditor = MemoryLeakAuditor()
    leak_auditor.capture_baseline()
    bad_audit = leak_auditor.audit({"leaky": _LeakyDummy()})
    assert bad_audit.passed is False
    assert "leaky._history" in bad_audit.unbounded_containers

    # DifferentialErrorRatchet
    ratchet = DifferentialErrorRatchet(tmp_path / "mypy_base.json")
    ratchet.save_baseline(["mod_a.py:10: err1", "mod_b.py:20: err2"])
    v_ok = ratchet.check(["mod_a.py:10: err1"])
    assert v_ok.passed is True and v_ok.fixed_errors == ("mod_b.py:20: err2",)
    v_fail = ratchet.check(["mod_a.py:10: err1", "mod_c.py:5: regression"])
    assert v_fail.passed is False and v_fail.new_errors == ("mod_c.py:5: regression",)

    # 5. CLI diagnostic subcommands
    runner = CliRunner()
    r_mem = runner.invoke(app, ["quantum", "memory-audit", "-t", "6"])
    assert r_mem.exit_code == 0
    assert json.loads(r_mem.stdout)["passed"] is True

    r_strat = runner.invoke(app, ["eval", "stratify", "--policy", "combined_gate"])
    assert r_strat.exit_code == 0
    assert json.loads(r_strat.stdout)["total_cases"] > 0
