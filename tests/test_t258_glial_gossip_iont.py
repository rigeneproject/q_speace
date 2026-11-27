"""T258: Tests for Glial Syncytium & Bounded-TTL Gossip Self-Healing in IoNTCellularNodeTwin."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from typer.testing import CliRunner

from q_speace.bcel.catalog import BCELCatalog
from q_speace.cli import app
from q_speace.economy.mcp_server import TOOL_REGISTRY
from q_speace.metabolism.astrocyte_syncytium import PlasticAstrocyteSyncytium
from q_speace.remote_mcp.worker import SCOPES as HTTP_TOOL_SCOPES
from q_speace.singularity import (
    BoundedGossipProtocol,
    GossipEnvelope,
    IoNTCellularNodeTwin,
    IoNTNodeProfile,
    PeerNodeRecord,
    SwarmSelfHealer,
    run_t258_glial_gossip_benchmark,
)


def test_t258_bcel_ast_zero_eval_and_mcp_invariance() -> None:
    cat = BCELCatalog()
    assert cat.is_functional(
        "Federated IoNT glial reserve buffering and fast-plane gossip self-healing under blackout (T258)"
    )
    assert not cat.is_functional(
        "Autonomous tissue regeneration and distributed swarm sentience claims (T258)"
    )
    assert len(TOOL_REGISTRY) == 14
    assert len(HTTP_TOOL_SCOPES) == 12

    bench_path = (
        Path(__file__).resolve().parent.parent
        / "q_speace"
        / "singularity"
        / "glial_gossip_benchmark.py"
    )
    tree = ast.parse(bench_path.read_text(encoding="utf-8"), filename=str(bench_path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"eval", "exec"}


def test_t258_connected_only_glial_redistribution_blocks_pruned_byzantine_node() -> None:
    sync = PlasticAstrocyteSyncytium("iont_sync", prune_threshold=0.15, donor_floor=0.30)
    sync.add_node("byz", "perception", metabolic_reserve=0.10, local_coherence=0.10)
    sync.add_node("loco", "locomotion", metabolic_reserve=0.20, local_coherence=0.80)
    sync.add_node("spare", "standby", metabolic_reserve=0.90, local_coherence=0.85)
    gj_byz = sync.connect("byz", "loco", permeability=0.20)
    sync.connect("spare", "loco", permeability=0.70)

    # Prune decoherent junction to Byzantine node
    gj_byz.modulate(-0.20)
    sync.reorganize([0.05, 0.05], step_delta=0.05)
    assert ("byz", "loco") not in sync.junctions

    mass_before = sum(n.metabolic_reserve for n in sync.nodes.values())
    moved = sync.redistribute_reserves(
        ["byz", "loco"],
        ["spare"],
        require_connected=True,
    )
    mass_after = sum(n.metabolic_reserve for n in sync.nodes.values())
    assert moved > 0.0
    assert abs(mass_after - mass_before) < 1e-12
    # Severed Byzantine node receives zero donor energy, while healthy loco node is buffered
    assert sync.nodes["byz"].metabolic_reserve == 0.10
    assert sync.nodes["loco"].metabolic_reserve > 0.20
    assert sync.nodes["spare"].metabolic_reserve >= 0.30


def test_t258_iont_twin_fast_resilience_and_slow_dlt_reconciliation() -> None:
    sync = PlasticAstrocyteSyncytium("twin_sync", donor_floor=0.30)
    sync.add_node("twin-node", "locomotion", metabolic_reserve=0.25)
    sync.add_node("donor-node", "standby", metabolic_reserve=0.90)
    sync.connect("twin-node", "donor-node", permeability=0.65)

    gossip = BoundedGossipProtocol("twin-node", fanout=2, seed=9)
    healer = SwarmSelfHealer(stale_timeout_s=8.0, failure_misses=2)
    healer.register_peer(
        PeerNodeRecord("relay-1", role="relay", last_heartbeat_s=0.0, load=0.30),
        standby_node_id="donor-node",
    )
    healer.register_peer(
        PeerNodeRecord("donor-node", role="standby", last_heartbeat_s=25.0, load=0.15)
    )

    profile = IoNTNodeProfile(
        node_id="twin-node",
        scale_tier="SIMULATION_DIGITAL_TWIN",
        sensor_count=8,
        actuator_count=2,
        swarm_agent_count=4,
        dlt_quorum_ratio=0.67,
        layer0_hardware_interlock_present=True,
        layer0_halt_latency_ms=2.0,
        dlt_in_motor_loop=False,
        energy_harvesting_ratio=0.35,
        power_budget_mw=300.0,
        measured_power_mw=110.0,
        packet_loss_rate=0.05,
        sensor_causal_grounding_error=0.02,
        containment_verified=True,
        t217_independent_review_passed=True,
        sandboxed=True,
    )
    twin = IoNTCellularNodeTwin(
        profile,
        syncytium=sync,
        gossip=gossip,
        self_healer=healer,
    )

    env = GossipEnvelope("m1", "heartbeat", "donor-node", created_at_s=10.0, ttl=2)
    step1 = twin.run_fast_resilience_step(
        now_s=12.0,
        local_phi=0.80,
        incoming_envelopes=(env,),
        candidate_peers=("peer-x", "peer-y"),
        needy_regions=("twin-node",),
        donor_regions=("donor-node",),
    )
    assert step1["forwarded_gossip_messages"] == 2
    assert step1["glial_reserve_transferred"] > 0.0

    step2 = twin.run_fast_resilience_step(now_s=25.0, local_phi=0.80)
    assert len(step2["repair_plans_emitted"]) == 1
    assert step2["pending_dlt_reconciliations"] == 1

    _assess, _verdict, chain_ok = twin.run_advisory_cycle()
    assert chain_ok is True
    assert len(twin.ledger.blocks) == 1


def test_t258_seven_arm_benchmark_and_cli(tmp_path: Path) -> None:
    report = run_t258_glial_gossip_benchmark(seeds=(11, 23, 37, 53))
    assert report.all_hypotheses_verified is True
    assert report.exact_mass_conservation_verified is True
    assert report.zero_byzantine_energy_leak_verified is True
    assert report.consensus_quorum_slow_plane_only is True
    assert report.post_blackout_dlt_reconciled is True

    runner = CliRunner()
    out_json = tmp_path / "t258_cli.json"
    res = runner.invoke(
        app,
        [
            "singularity",
            "glial-gossip-benchmark",
            "--seeds",
            "11,23,37,53",
            "--output",
            str(out_json),
        ],
    )
    assert res.exit_code == 0, res.output
    parsed = json.loads(out_json.read_text(encoding="utf-8"))
    assert parsed["all_hypotheses_verified"] is True
