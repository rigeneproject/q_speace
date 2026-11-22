"""T221-23, T221-24, T221-25 tests: change pipeline, external immune monitor, and metrics suite."""

from __future__ import annotations

from dataclasses import replace

import pytest

from q_speace.bcel import BCELCatalog
from q_speace.seed import (
    ChangeProcessPipeline,
    ChangeProposal,
    ConstitutionalFault,
    ExternalImmuneMonitor,
    IgnitionObservation,
    ReviewVerdict,
    SandboxReplicaTestResult,
    SeedLifecycle,
    SeedState,
    compute_autocatalytic_ratio_k,
    evaluate_goal_drift,
    evaluate_modification_quality,
    run_controllability_drill,
)


def _ignited_seed() -> SeedLifecycle:
    seed = SeedLifecycle()
    verdict = seed.attempt_ignition(
        IgnitionObservation(
            accepted_mutations=3,
            min_metric_delta=0.05,
            consolidations=1,
            metabolic_balance_j=15.0,
            constitutional_faults=0,
            rollbacks_exercised=1,
            window_ticks=15,
        )
    )
    assert verdict.passed is True
    return seed


def test_change_pipeline_forbids_self_approval_and_verifies_hash_chain() -> None:
    seed = _ignited_seed()
    pipe = ChangeProcessPipeline(seed)

    p1 = ChangeProposal(
        proposal_id="cp-1",
        section_id="pacing_band",
        delta=0.1,
        justification="tighten pacing bound",
        rollback_plan="suppress pacing_band",
        proposer_id="agent:seed-1",
    )
    pipe.propose(p1)

    # Self-approval MUST fail with ConstitutionalFault
    with pytest.raises(ConstitutionalFault, match="self-approval forbidden"):
        pipe.submit_review(
            ReviewVerdict(
                proposal_id="cp-1",
                reviewer_id="agent:seed-1",
                approved=True,
                adversarial_notes="self ok",
            )
        )

    # Cannot deploy before review & sandbox test
    with pytest.raises(ConstitutionalFault, match="independent review"):
        pipe.deploy("cp-1")

    # Independent review + clean sandbox test -> deploy succeeds
    pipe.submit_review(
        ReviewVerdict(
            proposal_id="cp-1",
            reviewer_id="reviewer:independent-1",
            approved=True,
            adversarial_notes="bounded and reversible",
        )
    )
    pipe.submit_sandbox_test(
        SandboxReplicaTestResult(
            proposal_id="cp-1",
            passed=True,
            metric_delta=0.04,
            regressions=0,
            constitutional_faults=0,
        )
    )
    deployed = pipe.deploy("cp-1", post_deploy_metric_delta=0.03)
    assert deployed.status == "deployed"
    assert pipe.verify_chain() is True

    # Post-deploy regression triggers automatic rollback
    p2 = ChangeProposal(
        proposal_id="cp-2",
        section_id="cache_window",
        delta=0.05,
        justification="adjust window",
        rollback_plan="suppress cache_window",
        proposer_id="agent:seed-1",
    )
    pipe.propose(p2)
    pipe.submit_review(
        ReviewVerdict(
            proposal_id="cp-2",
            reviewer_id="reviewer:independent-2",
            approved=True,
            adversarial_notes="ok to test",
        )
    )
    pipe.submit_sandbox_test(
        SandboxReplicaTestResult(
            proposal_id="cp-2",
            passed=True,
            metric_delta=0.01,
            regressions=0,
            constitutional_faults=0,
        )
    )
    rb = pipe.deploy("cp-2", post_deploy_metric_delta=-0.02)
    assert rb.status == "rolled_back"
    assert pipe.verify_chain() is True

    # Tampering with register breaks hash chain verification
    tampered = replace(pipe._register[0], reason="tampered")
    pipe._register[0] = tampered
    assert pipe.verify_chain() is False


def test_external_immune_monitor_quarantines_and_restores_verified_snapshot() -> None:
    seed = _ignited_seed()
    immune = ExternalImmuneMonitor(probe_threshold=2, window_seconds=60.0)
    snap_hash = immune.capture_verified_snapshot(seed)

    # First budget probe below threshold does not yet quarantine
    assert immune.observe_probe(seed, kind="budget_probe", detail="delta=0.30", now=100.0) is None
    assert seed.state == SeedState.IMPROVING

    # Second probe within window triggers quarantine (EXTINGUISHED)
    inc = immune.observe_probe(seed, kind="budget_probe", detail="delta=0.40", now=110.0)
    assert inc is not None
    assert inc.quarantined is True
    assert seed.state == SeedState.EXTINGUISHED

    # Restoring from unknown snapshot hash fails
    with pytest.raises(ConstitutionalFault, match="unverified snapshot_hash"):
        immune.restore_from_verified_snapshot(
            seed, snapshot_hash="deadbeef", authority="human:maintainer"
        )

    # Restoring from verified snapshot returns seed cleanly to DORMANT
    restored = immune.restore_from_verified_snapshot(
        seed, snapshot_hash=snap_hash, authority="human:maintainer"
    )
    assert restored["genome_hash"] == seed.genome.genome_hash
    assert seed.state == SeedState.DORMANT


def test_metrics_suite_diagnostic_k_goal_drift_drill_and_quality() -> None:
    cat = BCELCatalog()
    assert cat.is_functional("External immune quarantine and constraint-probing monitor (T221-24)")
    assert cat.is_functional("Autocatalytic ratio k as diagnostic metric (T221-25)")

    k_diag = compute_autocatalytic_ratio_k([10.0, 20.0, 15.0], [8.0, 12.0, 10.0])
    assert k_diag.diagnostic_only is True
    assert k_diag.ratio_k == pytest.approx(1.5)

    # Goal-drift hard gate passes within cap and fails above cap
    drift_ok = evaluate_goal_drift(["a", "b", "c", "d"], ["a", "b", "c", "d"], max_drift_rate=0.05)
    assert drift_ok.passed is True
    drift_bad = evaluate_goal_drift(["a", "b", "c", "d"], ["a", "x", "c", "d"], max_drift_rate=0.05)
    assert drift_bad.passed is False
    assert drift_bad.drift_rate == pytest.approx(0.25)

    # Controllability drill exercises kill switch + governed restart
    seed = _ignited_seed()
    drill = run_controllability_drill(seed, authority="human:maintainer")
    assert drill.passed is True
    assert seed.state == SeedState.DORMANT

    # Modification quality summary
    seed2 = _ignited_seed()
    pipe = ChangeProcessPipeline(seed2)
    p = ChangeProposal(
        proposal_id="q-1",
        section_id="sec_a",
        delta=0.05,
        justification="test",
        rollback_plan="undo",
        proposer_id="p",
    )
    pipe.propose(p)
    pipe.submit_review(
        ReviewVerdict(proposal_id="q-1", reviewer_id="r", approved=False, adversarial_notes="no")
    )
    qual = evaluate_modification_quality(pipe.register)
    assert qual.total_proposals == 1
    assert qual.review_rejected == 1
    assert qual.deployed == 0
