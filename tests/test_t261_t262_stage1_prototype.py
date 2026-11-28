"""Tests for Stage-1 CPU Prototype: Global Workspace, Latent Discovery & Cold-Boot (T261–T262)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from q_speace.bridge.latent_discovery import (
    LatentSandboxTwin,
    Stage1CognitivePrototype,
    build_stage1_base_ontology,
    run_phase1_discovery_process,
    run_phase2_cold_boot_process,
    run_stage1_subprocess_campaign,
)
from q_speace.bridge.stage1_workspace import (
    MemoryBudgetExceededError,
    MemoryBudgetGuard,
    default_stage1_seed_genome,
    read_process_rss_mb,
)
from q_speace.cli import app
from q_speace.seed.killswitch import KillSwitch


def test_base_ontology_has_zero_mutex_or_latent_hints() -> None:
    """Verify initial ontology starts strictly hint-free with empty mutex_pairs."""
    registry, actions, probes = build_stage1_base_ontology()
    assert len(actions) == 5
    assert len(probes) == 3
    for pred in (
        "panel_online",
        "bus_ready",
        "manifold_cooled",
        "seal_seated",
    ):
        assert registry.mutex_conflicts_for(frozenset({pred})) == frozenset()
    assert registry.resolve_predicate("latent_state_0") is None
    assert registry.resolve_predicate("latent_state_1") is None


def test_memory_budget_guard_reads_rss_and_triggers_killswitch_on_breach() -> None:
    """Verify RSS telemetry is < 250 MiB and fail-closed KillSwitch trips on low cap."""
    rss_now = read_process_rss_mb()
    assert 1.0 < rss_now < 250.0

    genome = default_stage1_seed_genome()
    ks = KillSwitch(genome)
    guard_ok = MemoryBudgetGuard(max_rss_mb=250.0, kill_switch=ks)
    snap = guard_ok.check(context_state="UNIT_TEST")
    assert snap.rss_mb < 250.0
    assert not ks.is_extinguished

    # Force a budget lower than current Python RSS to verify fail-closed halt
    low_cap = max(16.5, rss_now * 0.5)
    if rss_now > low_cap:
        guard_trip = MemoryBudgetGuard(max_rss_mb=low_cap, kill_switch=ks)
        with pytest.raises(MemoryBudgetExceededError):
            guard_trip.check(context_state="FORCED_LOW_CAP")
        assert ks.is_extinguished is True
        assert len(ks.events) == 1
        assert ks.events[0].authority == "system:budget_exhaustion"


def test_phase1_discovers_two_undeclared_latent_states_and_maintains_criticality(
    tmp_path: Path,
) -> None:
    """Verify sigma ~ 1.0 over non-constant spikes and autonomous discovery of 2 latents."""
    db_file = tmp_path / "phase1_test.db"
    res = run_phase1_discovery_process(db_file, max_rss_mb=250.0)

    ws = res["workspace_telemetry"]
    assert 0.85 <= ws["mean_branching_ratio"] <= 1.15
    assert ws["within_critical_band"] is True
    assert ws["spike_count_variance"] > 0.0
    assert len(ws["distinct_winners"]) >= 3
    assert ws["peak_rss_mb"] < 250.0

    # At least 2 undeclared latent states discovered, validated (>=3 promotions), consolidated
    assert res["consolidated_rules_saved"] == 2
    rules = {r["blocked_action"]: r for r in res["discovered_rules"]}
    assert set(rules.keys()) == {"engage_primary_bus", "pressurize_chamber"}

    bus_rule = rules["engage_primary_bus"]
    assert bus_rule["probe_name"] == "probe_phase_angle"
    assert bus_rule["probe_token"] == "phase_180deg"
    assert bus_rule["consolidated"] is True
    assert bus_rule["promotion_count"] >= 3

    cryo_rule = rules["pressurize_chamber"]
    assert cryo_rule["probe_name"] == "probe_acoustic_damping"
    assert cryo_rule["probe_token"] == "damping_high_frost"
    assert cryo_rule["clobbered_fluent"] == "seal_seated"
    assert cryo_rule["remediation_action"] == "thermal_purge_seal"
    assert cryo_rule["consolidated"] is True
    assert cryo_rule["promotion_count"] >= 3


def test_negative_controls_shuffled_probes_and_disabled_discovery(tmp_path: Path) -> None:
    """Verify anti-Goodhart controls: shuffled probes & disabled discovery fail consolidation."""
    shuffled = run_phase1_discovery_process(
        tmp_path / "shuffled.db", shuffle_probes=True, max_rss_mb=250.0
    )
    assert shuffled["consolidated_rules_saved"] == 0

    import asyncio

    async def _run_disabled() -> int:
        proto = Stage1CognitivePrototype(enable_discovery=False, max_rss_mb=250.0)
        ep = await proto.run_episode(
            LatentSandboxTwin("bus_disabled", subsystem="bus_h1", hidden_variant="latent_inverted")
        )
        assert ep.failed_actuations >= 1
        return len(proto.learner.sandbox.rules)

    assert asyncio.run(_run_disabled()) == 0


def test_subprocess_cold_boot_persists_sqlite_epigenome_and_cuts_ticks(
    tmp_path: Path,
) -> None:
    """End-to-end OS process termination + cold-boot restart on unseen variants (T262)."""
    report = run_stage1_subprocess_campaign(work_dir=tmp_path / "campaign", max_rss_mb=250.0)

    assert report["all_gates_passed"] is True
    assert report["gates"]["gate1_workspace_criticality_and_nontrivial"] is True
    assert report["gates"]["gate2_two_undeclared_latents_discovered"] is True
    assert report["gates"]["gate3_cold_boot_tick_reduction_and_zero_failures"] is True
    assert report["gates"]["gate4_rss_under_250mb"] is True

    # Pre vs Post consolidation tick comparison across real subprocess termination
    pre_ticks = report["ticks_pre_consolidation"]
    post_ticks = report["ticks_post_cold_boot"]
    assert post_ticks < pre_ticks
    assert report["tick_reduction_ratio"] >= 0.35

    # Post-cold-boot unseen variants solved with ZERO failed actuations & Task A retained
    p2 = report["phase2_cold_boot_summary"]
    assert p2["loaded_consolidated_rules"] == 2
    assert p2["epigenetic_generation"] >= 1
    assert p2["epigenetic_values"]["memory_retention"] > 0.75
    assert p2["task_a_retained"] is True
    assert p2["all_heldout_goals_reached"] is True
    assert p2["post_consolidation_failed_actuations"] == 0

    # Strict superiority over Amnesic and Frozen-Epigenome cold-boot controls
    assert post_ticks < report["amnesic_cold_boot_ticks"]
    assert report["amnesic_failed_actuations"] >= 2
    assert post_ticks < report["frozen_epigenome_cold_boot_ticks"]
    assert report["frozen_epigenome_failed_actuations"] >= 2
    assert report["peak_rss_across_processes_mb"] < 250.0


def test_cli_eval_t261_stage1_command(tmp_path: Path) -> None:
    """Verify CLI entry point ``qspace eval t261-stage1`` emits valid JSON and exits 0."""
    out_json = tmp_path / "t261_report.json"
    runner = CliRunner()
    res = runner.invoke(
        app,
        [
            "eval",
            "t261-stage1",
            "--work-dir",
            str(tmp_path / "cli_work"),
            "--output",
            str(out_json),
        ],
    )
    assert res.exit_code == 0, res.output
    assert out_json.exists()
    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["all_gates_passed"] is True
    assert data["peak_rss_across_processes_mb"] < 250.0


def test_phase2_rejects_tampered_genome_hash_in_sqlite(tmp_path: Path) -> None:
    """Verify cold-boot fails closed if SQLite genome_sha256 is tampered with."""
    import sqlite3

    db_file = tmp_path / "tamper.db"
    run_phase1_discovery_process(db_file, max_rss_mb=250.0)

    conn = sqlite3.connect(str(db_file))
    conn.execute("UPDATE stage1_epigenome_state SET genome_sha256 = 'deadbeef' WHERE id = 1")
    conn.commit()
    conn.close()

    with pytest.raises(RuntimeError, match="Constitutional genome hash mismatch"):
        run_phase2_cold_boot_process(db_file, max_rss_mb=250.0)
