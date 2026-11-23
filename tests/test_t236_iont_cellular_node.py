"""T236: Tests for IoNT Cellular Node (SPEACE Macro Mini) contract, DLT ledger, twin, MCP & CLI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from q_speace.bcel.catalog import BCELCatalog
from q_speace.cli import app
from q_speace.economy.mcp_server import _dispatch
from q_speace.singularity import (
    DLTSwarmLedger,
    EpigeneticFaultError,
    IoNTCellularNodeTwin,
    IoNTNodeProfile,
    PhaseTransitionEvaluator,
    assess_iont_cellular_node,
    build_iont_node_telemetry_bridge,
    build_singularity_framework_manifest,
)


def _nominal_iont(**overrides: Any) -> IoNTNodeProfile:
    base: dict[str, Any] = {
        "node_id": "cell-node-01",
        "scale_tier": "SIMULATION_DIGITAL_TWIN",
        "sensor_count": 16,
        "actuator_count": 2,
        "swarm_agent_count": 6,
        "dlt_quorum_ratio": 0.67,
        "layer0_hardware_interlock_present": True,
        "layer0_halt_latency_ms": 2.0,
        "dlt_in_motor_loop": False,
        "energy_harvesting_ratio": 0.40,
        "power_budget_mw": 500.0,
        "measured_power_mw": 200.0,
        "packet_loss_rate": 0.02,
        "sensor_causal_grounding_error": 0.01,
        "containment_verified": True,
        "t217_independent_review_passed": True,
        "sandboxed": True,
    }
    base.update(overrides)
    return IoNTNodeProfile(**base)


def test_iont_node_assessment_safety_gates_and_allopoietic_floor() -> None:
    # 1. Compliant sandboxed twin node admitted for MCP advisory only (never actuation).
    ok = assess_iont_cellular_node(_nominal_iont())
    assert ok.admitted_for_mcp_advisory is True
    assert ok.layer0_interlock_compliant is True
    assert ok.dlt_separation_compliant is True
    assert ok.containment_compliant is True
    assert ok.advisory_only is True
    assert ok.mcp_actuation_permitted is False
    assert ok.self_approval_permitted is False
    assert ok.estimated_allopoietic_dependence >= 0.50  # conservative floor for digital twin
    assert "delegation_granularity" in ok.recommended_epigenetic_adjustments

    # 2. Missing Layer-0 interlock with actuators -> refused.
    no_l0 = assess_iont_cellular_node(_nominal_iont(layer0_hardware_interlock_present=False))
    assert no_l0.admitted_for_mcp_advisory is False
    assert "layer0_hardware_interlock_missing" in no_l0.failed_checks

    # 3. Putting DLT in real-time motor loop -> refused.
    dlt_motor = assess_iont_cellular_node(_nominal_iont(dlt_in_motor_loop=True))
    assert dlt_motor.admitted_for_mcp_advisory is False
    assert "dlt_in_realtime_motor_loop_prohibited" in dlt_motor.failed_checks

    # 4. Physical benchtop node without T217 independent review or slow >5ms halt -> refused.
    unreviewed = assess_iont_cellular_node(
        _nominal_iont(
            scale_tier="BENCHTOP_MICRO_IOT_MEMS",
            sandboxed=False,
            t217_independent_review_passed=False,
            layer0_halt_latency_ms=15.0,
        )
    )
    assert unreviewed.admitted_for_mcp_advisory is False
    assert "t217_independent_review_required_for_physical_node" in unreviewed.failed_checks
    assert any("layer0_halt_latency_exceeded" in c for c in unreviewed.failed_checks)

    # 5. Noisy / power-stressed IoNT link produces advisory epigenetic adjustments.
    stressed = assess_iont_cellular_node(
        _nominal_iont(
            measured_power_mw=450.0,
            packet_loss_rate=0.20,
            sensor_causal_grounding_error=0.05,
        )
    )
    assert "energy_throttling" in stressed.recommended_epigenetic_adjustments
    assert "verification_depth" in stressed.recommended_epigenetic_adjustments
    assert "sensor_causal_grounding_error_exceeded" in stressed.failed_checks


def test_iont_telemetry_bridge_dlt_swarm_ledger_and_sandbox_twin() -> None:
    # 1. Telemetry bridge projects IoNT measurements cleanly into PhaseTransitionEvaluator.
    prof = _nominal_iont()
    tel = build_iont_node_telemetry_bridge(
        prof,
        timescale_decoupling_ratio=16.0,
        autocatalytic_k=1.4,
        independent_validation_rate=0.98,
        semantic_entropy_drift=0.015,
        net_verified_improvement=0.04,
        consecutive_verified_cycles=4,
        sevo=2.3,
        sevo_window_mean=2.2,
    )
    verdict = PhaseTransitionEvaluator().evaluate(tel)
    assert verdict.stage == "STAGE_2_BOUNDED_RECURSIVE"
    assert verdict.physical_actuation_permitted is False

    # 2. DLT Swarm Ledger enforces quorum, anti-self-approval, and monotonic epoch anti-replay.
    ledger = DLTSwarmLedger(quorum_ratio=0.67)
    blk = ledger.commit_governance_event(
        epoch=1,
        proposer_id="agent-plan",
        approver_ids=("agent-sense", "agent-safety", "agent-audit"),
        payload={"event": "cycle_1"},
    )
    assert blk.height == 1 and ledger.verify_chain() is True

    # Self-approval is stripped so 2 independent approvers < ceil(3 * 0.67) = 3 -> blocked.
    with pytest.raises(EpigeneticFaultError, match="quorum not reached"):
        ledger.commit_governance_event(
            epoch=2,
            proposer_id="agent-plan",
            approver_ids=("agent-plan", "agent-sense", "agent-safety"),
            payload={"event": "self_approve"},
        )

    # Stale epoch replay blocked even with full independent quorum.
    with pytest.raises(EpigeneticFaultError, match="epoch replay blocked"):
        ledger.commit_governance_event(
            epoch=1,
            proposer_id="agent-plan",
            approver_ids=("agent-sense", "agent-safety", "agent-audit"),
            payload={"event": "replay"},
        )

    # 3. Sandboxed Digital Twin enforces sandboxed=True and executes clean advisory cycle.
    with pytest.raises(EpigeneticFaultError, match="sandboxed=True"):
        IoNTCellularNodeTwin(_nominal_iont(sandboxed=False))

    twin = IoNTCellularNodeTwin(prof)
    assessment, twin_verdict, chain_ok = twin.run_advisory_cycle()
    assert assessment.admitted_for_mcp_advisory is True
    assert twin_verdict.stage == "STAGE_2_BOUNDED_RECURSIVE"
    assert chain_ok is True


def test_iont_mcp_dispatch_manifest_bcel_and_cli(tmp_path: Path) -> None:
    # 1. Manifest section & BCEL entries.
    sec = build_singularity_framework_manifest(section="iont_cellular_nodes")
    assert sec["iont_cellular_nodes"]["spec"] == "T236"
    assert sec["iont_cellular_nodes"]["mcp_actuation_permitted"] is False

    catalog = BCELCatalog()
    assert catalog.is_functional("IoNT cellular node 4-layer advisory architecture (T236)")
    assert (
        catalog.get(
            "Biological cellular organism and DLT-driven motor reflex metaphor (T236)"
        ).classification
        == "accidental"
    )

    # 2. MCP tool dispatch is finite-JSON serializable and non-actuating.
    payload = {
        "node_id": "mcp-cell-01",
        "scale_tier": "SIMULATION_DIGITAL_TWIN",
        "sensor_count": 10,
        "actuator_count": 2,
        "swarm_agent_count": 4,
        "dlt_quorum_ratio": 0.67,
        "layer0_hardware_interlock_present": True,
        "layer0_halt_latency_ms": 2.0,
        "dlt_in_motor_loop": False,
        "energy_harvesting_ratio": 0.35,
        "power_budget_mw": 400.0,
        "measured_power_mw": 150.0,
        "packet_loss_rate": 0.01,
        "sensor_causal_grounding_error": 0.01,
    }
    res = _dispatch("iont_node_assess", payload)
    assert res["admitted_for_mcp_advisory"] is True
    assert res["mcp_actuation_permitted"] is False
    json.dumps(res, allow_nan=False)

    # 3. CLI qspace singularity iont-assess (admitted -> exit 0, unsafe -> exit 3).
    runner = CliRunner()
    ok_file = tmp_path / "ok_node.json"
    ok_file.write_text(json.dumps(payload), encoding="utf-8")
    r_ok = runner.invoke(app, ["singularity", "iont-assess", "--profile", str(ok_file)])
    assert r_ok.exit_code == 0, r_ok.output

    bad_file = tmp_path / "bad_node.json"
    bad_file.write_text(
        json.dumps(
            {**payload, "dlt_in_motor_loop": True, "layer0_hardware_interlock_present": False}
        ),
        encoding="utf-8",
    )
    r_bad = runner.invoke(app, ["singularity", "iont-assess", "--profile", str(bad_file)])
    assert r_bad.exit_code == 3
