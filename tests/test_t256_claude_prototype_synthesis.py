"""Tests for T256 — BCEL Synthesis of Useful Elements from SPEACE PROTOTIPO CLAUDE."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import numpy as np
import pytest
from typer.testing import CliRunner

from q_speace import (
    BatchRoleDeliberationCodec,
    BCELCatalog,
    CognitiveRegime,
    ContractSpec,
    CVStrategySelector,
    EdgeKind,
    FieldConstraint,
    HomeodynaBalanceController,
    HystereticLoadBalancer,
    KineticaRegimeController,
    MyelinationRegistry,
    PlasticAstrocyteSyncytium,
    TypedComputationalDAG,
    compute_mip_integration,
)
from q_speace.cli import app
from q_speace.singularity import (
    BoundedGossipProtocol,
    GossipEnvelope,
    PeerNodeRecord,
    PeerState,
    SwarmSelfHealer,
    verify_mcp_surface_bounds,
)


def test_t256_bcel_catalog_entries() -> None:
    catalog = BCELCatalog()
    concepts = {eq.concept: eq for eq in catalog.all()}

    expected_functional = [
        "Plastic regional astrocyte gap-junction syncytium and donor-floor metabolic buffering (T256)",
        "Declarative ExecutionTicket contracts and multi-port Kahn computational DAG (T256)",
        "Kinetica cognitive-regime FSM, Homeodyna overload rerouting, and adaptive path myelination (T256)",
        "Small-system Minimum Information Partition coupling index, CV strategy switching, and bounded-TTL gossip (T256)",
    ]
    for key in expected_functional:
        assert key in concepts
        assert concepts[key].classification == "functional"

    acc_key = (
        "Unsanitized eval() contract predicates, consciousness_index labels, "
        "and host-CPU phi coupling (T256)"
    )
    assert acc_key in concepts
    assert concepts[acc_key].classification == "accidental"


def test_t256_modules_contain_zero_eval_or_exec() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    module_paths = [
        repo_root / "q_speace" / "metabolism" / "astrocyte_syncytium.py",
        repo_root / "q_speace" / "aacm" / "typed_dag.py",
        repo_root / "q_speace" / "spiking" / "morphogenesis.py",
        repo_root / "q_speace" / "edd_cvt" / "mip_integration.py",
        repo_root / "q_speace" / "singularity" / "swarm_gossip.py",
        repo_root / "q_speace" / "spiking_brain" / "myelination.py",
    ]
    for path in module_paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in {"eval", "exec"}, f"Forbidden {node.func.id} in {path}"


def test_plastic_astrocyte_syncytium_wave_plasticity_and_mass_conservation() -> None:
    sync = PlasticAstrocyteSyncytium("test_sync", prune_threshold=0.12, donor_floor=0.30)
    sync.add_node("a_front", "frontal", metabolic_reserve=0.90, local_coherence=0.80)
    sync.add_node("a_hippo", "memory", metabolic_reserve=0.40, local_coherence=0.50)
    sync.add_node("a_stem", "stem", metabolic_reserve=0.85, local_coherence=0.60)
    sync.connect("a_front", "a_hippo", permeability=0.50)
    sync.connect("a_hippo", "a_stem", permeability=0.14)

    wave = sync.propagate_wave("a_front", phi=0.85)
    assert set(wave.keys()) == {"a_front", "a_hippo", "a_stem"}
    assert (
        wave["a_front"]["activity_wave"]
        > wave["a_hippo"]["activity_wave"]
        > wave["a_stem"]["activity_wave"]
    )

    # High phi strengthens junctions
    res_hi = sync.reorganize([0.82, 0.85, 0.80])
    assert res_hi["strengthened"] == 2

    # Repeated low phi weakens and prunes the weak junction (0.19 - 0.05 = 0.14, then 0.14 - 0.05 = 0.09 < 0.12)
    res_weaken = sync.reorganize([0.20, 0.25, 0.22], step_delta=0.05)
    assert res_weaken["weakened"] == 2
    res_prune = sync.reorganize([0.20, 0.25, 0.22], step_delta=0.05)
    assert res_prune["pruned"] == 1
    assert len(sync.junctions) == 1

    # Mass-conserving donor-floor redistribution
    before_mass = sum(n.metabolic_reserve for n in sync.nodes.values())
    transferred = sync.redistribute_reserves(["a_hippo"], ["a_front", "a_stem"])
    after_mass = sum(n.metabolic_reserve for n in sync.nodes.values())
    assert transferred > 0.0
    assert abs(before_mass - after_mass) < 1e-12
    assert sync.nodes["a_front"].metabolic_reserve >= 0.30
    assert sync.nodes["a_stem"].metabolic_reserve >= 0.30


def test_typed_computational_dag_contracts_cycles_and_subgraphs() -> None:
    dag = TypedComputationalDAG("pipeline")
    c_sense = ContractSpec(
        name="sensor_contract",
        input_constraints={
            "raw": FieldConstraint(expected_type="float", min_value=0.0, max_value=10.0)
        },
        output_constraints={"scaled": FieldConstraint(expected_type="float", min_value=0.0)},
    )
    c_fuse = ContractSpec(
        name="fusion_contract",
        input_constraints={"in_val": FieldConstraint(expected_type="float", min_value=0.0)},
        output_constraints={
            "verdict": FieldConstraint(expected_type="str", allowed_values=("ok", "warn"))
        },
    )

    dag.add_node("sense", lambda d: {"scaled": float(d["raw"]) * 2.0}, contract=c_sense)
    dag.add_node(
        "fuse",
        lambda d: {"verdict": "warn" if float(d["in_val"]) > 5.0 else "ok"},
        contract=c_fuse,
    )
    dag.add_node("audit", lambda d: {"logged": d.get("status_in", "none")})

    dag.connect("sense", "fuse", source_port="scaled", target_port="in_val", weight=1.5)
    dag.connect("fuse", "audit", source_port="verdict", target_port="status_in")
    # Feedback edges do not break acyclicity on forward DATA/CONTROL graph
    dag.connect("audit", "sense", kind=EdgeKind.FEEDBACK)

    # Forward cycle is rejected fail-closed without corrupting DAG
    with pytest.raises(ValueError, match="cycle"):
        dag.connect("audit", "sense", kind=EdgeKind.DATA)

    # Valid full run: raw=2.0 -> scaled=4.0 -> weighted in_val=6.0 -> verdict="warn"
    tickets = dag.execute({"sense": {"raw": 2.0}})
    assert tickets["sense"].status == "completed"
    assert tickets["fuse"].outputs == {"verdict": "warn"}
    assert tickets["audit"].outputs == {"logged": "warn"}

    # Bool rejected when float expected -> upstream failure skips downstream nodes
    bad_tickets = dag.execute({"sense": {"raw": True}})
    assert bad_tickets["sense"].status == "input_validation_failed"
    assert bad_tickets["fuse"].status == "skipped_upstream_failure"
    assert bad_tickets["audit"].status == "skipped_upstream_failure"

    # Subgraph execution only runs sense -> fuse
    sub = dag.execute({"sense": {"raw": 1.0}}, start_nodes=["sense"], end_nodes=["fuse"])
    assert set(sub.keys()) == {"sense", "fuse"}
    assert sub["fuse"].outputs == {"verdict": "ok"}


def test_kinetica_and_homeodyna_controllers() -> None:
    kin = KineticaRegimeController()
    assert kin.current_regime == CognitiveRegime.IDLE

    t1 = kin.step("task_start", phi=0.75, resource_usage=0.40)
    assert t1 is not None and t1.to_regime == CognitiveRegime.REACTIVE_PARSING

    # Overload diverts complex_reasoning transition into EMERGENCY
    t_emerg = kin.step("complex_reasoning", phi=0.75, resource_usage=0.95)
    assert t_emerg is not None and t_emerg.to_regime == CognitiveRegime.EMERGENCY
    assert kin.config_for().exploration_rate == 0.0

    # Stabilized returns to REACTIVE, then DELIBERATIVE, while low phi blocks META_COGNITION
    kin.step("stabilized", phi=0.70, resource_usage=0.35)
    kin.step("complex_reasoning", phi=0.70, resource_usage=0.45)
    assert kin.step("self_reflection", phi=0.45, resource_usage=0.40) is None
    t_meta = kin.step("self_reflection", phi=0.72, resource_usage=0.40)
    assert t_meta is not None and t_meta.to_regime == CognitiveRegime.META_COGNITION

    hom = HomeodynaBalanceController()
    ev = hom.evaluate(phi=0.35, excitation=0.90, inhibition=0.20, resource_usage=0.96)
    assert ev.balance_score < 0.30
    assert "stabilize" in ev.recommended_actions
    assert "reconfigure" in ev.recommended_actions
    assert "prune" in ev.recommended_actions

    rerouted = hom.reroute_path(["n_in", "n_hot", "n_out"], "n_hot", ["n_in", "n_spare"])
    assert rerouted == ("n_in", "n_spare", "n_out")


def test_mip_integration_and_cv_strategy_selector() -> None:
    rng = np.random.default_rng(123)
    shared = rng.normal(0.0, 1.0, size=(80, 1))
    coupled = 0.90 * shared + 0.10 * rng.normal(0.0, 1.0, size=(80, 6))
    indep = rng.normal(0.0, 1.0, size=(80, 6))

    mip_c = compute_mip_integration(coupled)
    mip_i = compute_mip_integration(indep)
    assert mip_c.mode == "exact_mip"
    assert mip_c.evaluated_partitions == 31  # 2^(6-1) - 1
    assert mip_c.mip_coupling_index > mip_i.mip_coupling_index + 0.25

    # Disconnected block-diagonal connectivity forces zero cross-cut coupling on block split
    block_conn = np.zeros((4, 4), dtype=np.float64)
    block_conn[0, 1] = block_conn[1, 0] = 1.0
    block_conn[2, 3] = block_conn[3, 2] = 1.0
    mip_disc = compute_mip_integration(coupled[:, :4], connectivity=block_conn)
    assert mip_disc.mip_coupling_index == 0.0

    # Large n > 10 uses fast bisection proxy cleanly
    mip_large = compute_mip_integration(rng.normal(size=(40, 12)))
    assert mip_large.mode == "bisection_proxy"

    # CVStrategySelector switches away from volatile/declining strategy
    sel = CVStrategySelector(confidence_threshold=0.70)
    sel.observe(0.90, strategy="exploitation")
    for r in (0.80, 0.50, 0.20, 0.05):
        chosen = sel.observe(r, strategy="exploration")
    assert chosen != "exploration"


def test_bounded_gossip_and_swarm_self_healer() -> None:
    gossip = BoundedGossipProtocol("node_0", fanout=2, seed=7)
    env = GossipEnvelope("m1", "heartbeat", "node_origin", created_at_s=10.0, ttl=2)

    fwd, targets = gossip.prepare_forward(
        env, ["node_0", "node_origin", "node_a", "node_b", "node_c"]
    )
    assert fwd is not None and fwd.ttl == 1
    assert len(targets) == 2
    assert "node_0" not in targets and "node_origin" not in targets

    # Duplicate envelope is dropped
    dup_fwd, dup_targets = gossip.prepare_forward(env, ["node_a", "node_b"])
    assert dup_fwd is None and dup_targets == ()

    healer = SwarmSelfHealer(stale_timeout_s=10.0, failure_misses=2)
    healer.register_peer(
        PeerNodeRecord("cortex_1", role="cortex", last_heartbeat_s=0.0, load=0.30),
        standby_node_id="standby_1",
    )
    healer.register_peer(
        PeerNodeRecord("standby_1", role="cortex", last_heartbeat_s=25.0, load=0.15)
    )
    healer.register_peer(PeerNodeRecord("relay_1", role="relay", last_heartbeat_s=0.0, load=0.20))

    # First audit marks silent nodes STALE; second audit marks FAILED and emits RepairPlans
    assert healer.audit_liveness(now_s=15.0) == ()
    assert healer.peers["cortex_1"].state == PeerState.STALE
    plans = {p.failed_node_id: p for p in healer.audit_liveness(now_s=26.0)}
    assert plans["cortex_1"].strategy == "replace"
    assert plans["cortex_1"].selected_targets == ("standby_1",)
    assert plans["relay_1"].strategy == "reroute"


def test_myelination_load_balancer_and_batch_codec() -> None:
    reg = MyelinationRegistry(prune_threshold=0.06, idle_timeout_s=100.0)
    for step in range(4):
        w = reg.activate("planner", "executor", phi=0.85, now_s=float(step))
    assert w > 0.30
    reg.activate("weak_a", "weak_b", phi=0.20, now_s=0.0, initial_weight=0.08)
    pruned = reg.decay_unused(now_s=250.0)
    assert ("weak_a", "weak_b") in pruned
    assert reg.top_priority_paths(1)[0][0:2] == ("planner", "executor")

    lb = HystereticLoadBalancer(recovery_cooldown_s=20.0, recovery_step=0.40)
    snap_over = lb.evaluate(
        {"cpu": 0.98, "memory": 0.97, "network": 0.96, "energy": 0.96, "attention": 0.96},
        now_s=10.0,
    )
    assert snap_over.level == "overloaded"
    assert snap_over.throttled is True
    assert snap_over.throttle_factor == pytest.approx(0.30)

    # Before cooldown expires, throttle remains held; after cooldown in light load it recovers
    snap_early = lb.evaluate({"cpu": 0.10, "memory": 0.10}, now_s=20.0)
    assert snap_early.throttle_factor == pytest.approx(0.30)
    snap_rec1 = lb.evaluate({"cpu": 0.10, "memory": 0.10}, now_s=35.0)
    assert snap_rec1.throttle_factor == pytest.approx(0.70)
    snap_rec2 = lb.evaluate({"cpu": 0.10, "memory": 0.10}, now_s=60.0)
    assert snap_rec2.throttled is False and snap_rec2.throttle_factor == pytest.approx(1.0)

    codec = BatchRoleDeliberationCodec()
    prompt = codec.build_prompt("Diagnose drift", context={"phi": 0.82})
    assert "QUERY: Diagnose drift" in prompt and "--- PLANNER ---" in prompt
    parsed = codec.parse_response("--- PLANNER ---\nStep 1\n--- CRITIC ---\nSafe\n")
    assert parsed["planner"] == "Step 1"
    assert parsed["critic"] == "Safe"
    assert parsed["executor"] == "[executor:missing]"


def test_cli_mip_audit_and_frozen_mcp_surface() -> None:
    runner = CliRunner()
    res = runner.invoke(app, ["quantum", "mip-audit", "--nodes", "5", "--samples", "48"])
    assert res.exit_code == 0, res.output
    payload = json.loads(res.stdout)
    assert payload["coupled_exceeds_independent"] is True
    assert payload["mode"] == "exact_mip"
    assert payload["evaluated_partitions"] == 15

    # Verify frozen 12-tool HTTP MCP contract is completely untouched
    mcp_check = verify_mcp_surface_bounds()
    assert mcp_check["passed"] is True
    assert mcp_check["http_tool_count"] == 12
