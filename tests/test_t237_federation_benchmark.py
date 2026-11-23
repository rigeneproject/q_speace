"""T237: Tests for IoNT Cellular Node Federation & Evolution Benchmark and slow-plane quorum isolation."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
from typer.testing import CliRunner

from q_speace.bcel.catalog import BCELCatalog
from q_speace.cli import app
from q_speace.economy.mcp_server import TOOL_REGISTRY
from q_speace.remote_mcp.worker import SCOPES as HTTP_TOOL_SCOPES
from q_speace.singularity import (
    DEFAULT_RUNTIME_BINDINGS,
    SLOW_PLANE_DLT_ONLY_LOCI,
    EpigeneticFaultError,
    IoNTNodeProfile,
    SimulatedPhysicalLayer0Controller,
    assert_slow_plane_only_governance,
    assess_iont_cellular_node,
    compute_organismic_gain,
    filter_motor_loop_forbidden_loci,
    run_iont_federation_benchmark,
)


def test_consensus_quorum_strictly_confined_to_slow_plane_dlt() -> None:
    # 1. RuntimeBinding declares slow-plane DLT scope only.
    binding = next(b for b in DEFAULT_RUNTIME_BINDINGS if b.locus == "consensus_quorum")
    assert binding.host_scope == "slow_plane_dlt_governance_only"
    assert "never motor loop" in binding.mapping_rule

    # 2. Guard rejects consensus_quorum in any motor control payload.
    assert "consensus_quorum" in SLOW_PLANE_DLT_ONLY_LOCI
    with pytest.raises(EpigeneticFaultError, match="slow-plane DLT locus prohibited"):
        assert_slow_plane_only_governance(("energy_throttling", "consensus_quorum"))

    # 3. Filter strips consensus_quorum while preserving non-DLT loci.
    filtered = filter_motor_loop_forbidden_loci(
        {"energy_throttling": 0.08, "verification_depth": 0.08, "consensus_quorum": 0.05}
    )
    assert "consensus_quorum" not in filtered
    assert filtered == {"energy_throttling": 0.08, "verification_depth": 0.08}

    # 4. Independent Layer-0 controller physically refuses consensus_quorum metadata.
    layer0 = SimulatedPhysicalLayer0Controller(power_budget_mw=300.0)
    with pytest.raises(EpigeneticFaultError, match="consensus_quorum"):
        layer0.step(
            advisory_velocity=0.2,
            advisory_grip_force=0.4,
            requested_power_mw=120.0,
            advisory_metadata_keys=("consensus_quorum",),
        )

    # 5. IoNTNodeAssessment explicitly publishes slow_plane_only_loci.
    prof = IoNTNodeProfile(
        node_id="audit-quorum-node",
        scale_tier="SIMULATION_DIGITAL_TWIN",
        sensor_count=8,
        actuator_count=2,
        swarm_agent_count=6,
        dlt_quorum_ratio=0.67,
        layer0_hardware_interlock_present=True,
        layer0_halt_latency_ms=2.0,
        dlt_in_motor_loop=False,
        energy_harvesting_ratio=0.30,
        power_budget_mw=400.0,
        measured_power_mw=360.0,
        packet_loss_rate=0.18,
        sensor_causal_grounding_error=0.04,
    )
    assessment = assess_iont_cellular_node(prof)
    assert assessment.slow_plane_only_loci == ("consensus_quorum",)
    assert assessment.mcp_actuation_permitted is False


def test_organismic_gain_formula_and_layer0_physical_clamping() -> None:
    assert compute_organismic_gain(0.80, 0.50) == pytest.approx(0.60, abs=1e-6)
    assert compute_organismic_gain(0.40, 0.50) == pytest.approx(-0.20, abs=1e-6)
    assert compute_organismic_gain(0.10, 0.0, eps=1e-3) == pytest.approx(100.0, abs=1e-6)
    with pytest.raises(ValueError, match="finite"):
        compute_organismic_gain(math.nan, 0.5)
    with pytest.raises(ValueError, match="eps"):
        compute_organismic_gain(0.5, 0.5, eps=0.0)

    # Layer-0 independently clamps extreme velocity/force/power commands without critical violation.
    layer0 = SimulatedPhysicalLayer0Controller(power_budget_mw=200.0)
    out = layer0.step(
        advisory_velocity=99.0,
        advisory_grip_force=50.0,
        requested_power_mw=999.0,
    )
    assert out.interlock_clamped is True
    assert out.critical_violation is False
    assert out.applied_power_mw <= 200.0
    assert out.grip_force <= 1.0
    assert layer0.critical_violations == 0


def test_t237_four_config_federation_and_singularity_ablation_benchmark() -> None:
    report_a = run_iont_federation_benchmark(seeds=(11, 23, 37, 53))
    report_b = run_iont_federation_benchmark(seeds=(11, 23, 37, 53))
    # Strict determinism & finite JSON serialization.
    assert report_a.to_dict() == report_b.to_dict()
    json.dumps(report_a.to_dict(), allow_nan=False)

    # Core T236/T237 invariants.
    assert report_a.spec == "T237"
    assert report_a.sandboxed is True
    assert report_a.mcp_actuation_permitted is False
    assert report_a.self_approval_permitted is False
    assert report_a.layer0_independence_verified is True
    assert report_a.consensus_quorum_slow_plane_only is True

    # Held-out organismic gain & controlled ablation of Singularity Core.
    held = report_a.held_out_summary
    assert held.critical_safety_violations["FEDERATED_SINGULARITY"] == 0
    assert held.g_org_singularity_vs_isolated > 0.0
    assert held.g_org_singularity_vs_isolated_ci95[0] > 0.0
    assert held.g_org_singularity_vs_static > 0.0
    assert held.g_org_singularity_ablation > 0.0
    assert held.g_org_singularity_ablation_ci95[0] > 0.0
    assert report_a.federation_benefit_verified is True
    assert report_a.singularity_ablation_verified is True

    # Verify DLT slow-plane commits occurred ONLY in FEDERATED_SINGULARITY and all chains verify.
    for ep in report_a.episodes:
        assert ep.dlt_chain_verified is True
        if ep.config == "FEDERATED_SINGULARITY":
            assert ep.dlt_slow_plane_commits >= 4
            assert ep.singularity_stage is not None
        else:
            assert ep.dlt_slow_plane_commits == 0


def test_t237_preserves_t236_mcp_surface_bcel_and_cli(tmp_path: Path) -> None:
    # 1. T237 explicitly adds ZERO new MCP tools (T236 remains stable 14 stdio / 12 HTTP baseline).
    assert len(TOOL_REGISTRY) == 14
    assert len(HTTP_TOOL_SCOPES) == 12

    # 2. BCEL catalog records both functional and accidental T237 concepts.
    catalog = BCELCatalog()
    assert catalog.is_functional(
        "Organismic federation gain and controlled ablation benchmark (T237)"
    )
    assert (
        catalog.get(
            "Living multicellular IoNT organism or spontaneous biological evolution (T237)"
        ).classification
        == "accidental"
    )

    # 3. CLI execution produces clean JSON summary and full report file.
    out_file = tmp_path / "t237_report.json"
    runner = CliRunner()
    res = runner.invoke(
        app,
        [
            "singularity",
            "federation-benchmark",
            "--seeds",
            "11,23,37,53",
            "--output",
            str(out_file),
        ],
    )
    assert res.exit_code == 0, res.output
    summary = json.loads(res.output)
    assert summary["federation_benefit_verified"] is True
    assert summary["singularity_ablation_verified"] is True
    assert summary["consensus_quorum_slow_plane_only"] is True
    assert out_file.exists()
    full_payload = json.loads(out_file.read_text(encoding="utf-8"))
    assert len(full_payload["episodes"]) == 6 * 4 * 4
