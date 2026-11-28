"""T263 — regression tests for Stage-1 cold-boot memory retention and belief retraction."""

from __future__ import annotations

import asyncio
from pathlib import Path

from q_speace.bridge import latent_discovery as ld
from q_speace.vertical_slice import t263_stage1_adversarial_battery as bat


def test_consolidated_rule_survives_repeated_use_after_cold_boot(tmp_path: Path) -> None:
    """Bug T263-1: loaded rules must not de-consolidate after their first post-boot use."""
    db = tmp_path / "retain.db"
    ld.run_phase1_discovery_process(db, max_rss_mb=250.0)
    twins = [
        ld.LatentSandboxTwin(
            f"bus_rep_{i}",
            subsystem="bus_h1",
            hidden_variant="latent_inverted",
            distractor_seed=20 + i,
        )
        for i in range(4)
    ]

    async def _go() -> list[ld.EpisodeRunMetrics]:
        p = ld.Stage1CognitivePrototype(db_path=db, cold_boot_require_consolidated=True)
        out = [await p.run_episode(t) for t in twins]
        assert p.store is not None
        p.store.close()
        return out

    eps = asyncio.run(_go())
    assert [e.failed_actuations for e in eps] == [0, 0, 0, 0]
    assert all(e.activated_latent_ids for e in eps)


def test_spurious_distractor_rule_is_retracted_and_replaced() -> None:
    """T263-2: a falsified distractor hypothesis is withdrawn and the true probe is learned."""
    proto = ld.Stage1CognitivePrototype(db_path=None)

    async def _go() -> None:
        for t in bat._random_stream(5):  # seed 5 locked onto probe_ambient_hum before the fix
            await proto.run_episode(t)

    asyncio.run(_go())
    bus_rules = [
        r for r in proto.learner.sandbox.rules.values() if r.blocked_action == "engage_primary_bus"
    ]
    assert bus_rules, "expected a bus rule"
    assert all(r.probe_name == "probe_phase_angle" for r in bus_rules)
    assert any(sig[2] == "probe_ambient_hum" for sig in proto.learner.retracted_signatures)


def test_battery_sigma_and_transfer_findings_are_reproducible(tmp_path: Path) -> None:
    """Documented limits stay measurable: sigma gate, workspace attribution, transfer."""
    e1 = bat.e1_sigma_gate_discrimination()
    assert e1["slow_growth_x1p12"]["in_band_0p85_1p15"] is True  # gate is not discriminative
    e2 = bat.e2_workspace_attribution(tmp_path)
    assert e2["fixed_k_behaviour_identical"] is True
    assert e2["no_spikes_behaviour_identical"] is True
    e34 = bat.e3_e4_recall_and_transfer(tmp_path)
    assert e34["E3a_known_surface"]["memory_helps"] is True
    assert e34["E4_new_device_same_mechanism"]["memory_helps"] is False
