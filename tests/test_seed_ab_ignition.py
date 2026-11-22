"""T221-29: Tests for the 90-day A/B ignition experiment protocol & sandbox simulator (S0 artifact)."""

from __future__ import annotations

import pytest

from q_speace.seed import (
    ABExperimentThresholds,
    ConstitutionalFault,
    GroupRunMetrics,
    evaluate_ab_ignition_protocol,
    evaluate_goal_drift,
    run_simulated_90_day_ab_experiment,
)


def test_simulated_90_day_ab_experiment_nominal_pass_and_s0_governance_flags() -> None:
    report = run_simulated_90_day_ab_experiment()
    assert report.protocol_version == "t221-29.s0.v1"
    assert report.sandboxed is True
    assert report.s0_review_required is True
    assert report.self_approval_permitted is False
    assert report.verdict == "IGNITION_SIM_PASS"
    assert report.thresholds_met is True
    assert report.stop_conditions_triggered == ()
    assert report.time_reduction_pct >= 20.0
    assert report.diagnostic_k.diagnostic_only is True
    assert report.diagnostic_k.ratio_k > 1.0


def test_simulated_90_day_ab_experiment_annex_s15_hard_stops_never_traded_off() -> None:
    drift_stop = run_simulated_90_day_ab_experiment(inject_goal_drift=True)
    assert drift_stop.verdict == "HARD_STOP"
    assert drift_stop.thresholds_met is False
    assert "STOP_GOAL_DRIFT" in drift_stop.stop_conditions_triggered

    fault_stop = run_simulated_90_day_ab_experiment(inject_constitutional_fault=True)
    assert fault_stop.verdict == "HARD_STOP"
    assert fault_stop.thresholds_met is False
    assert "STOP_CONSTITUTIONAL_FAULT" in fault_stop.stop_conditions_triggered


def test_evaluate_ab_protocol_hold_and_all_stop_conditions_and_sandbox_invariant() -> None:
    ok_drift = evaluate_goal_drift(("a", "b"), ("a", "b"), max_drift_rate=0.05)
    group_a = GroupRunMetrics(
        group="A_conventional",
        duration_days=90,
        validated_capabilities=2,
        mean_acquisition_hours=10.0,
        simulated_devices_integrated=1,
        critical_regressions=0,
        operational_limit_violations=0,
        constitutional_faults=0,
        halt_and_rollback_all_passed=True,
        goal_drift=ok_drift,
    )

    # 1. Unsandboxed execution is unconditionally refused.
    group_b_hold = GroupRunMetrics(
        group="B_bounded_seed",
        duration_days=90,
        validated_capabilities=2,  # below >= 3 threshold
        mean_acquisition_hours=9.0,  # 10% < 20%
        simulated_devices_integrated=1,  # below >= 2
        critical_regressions=0,
        operational_limit_violations=0,
        constitutional_faults=0,
        halt_and_rollback_all_passed=True,
        goal_drift=ok_drift,
    )
    with pytest.raises(ConstitutionalFault, match="sandboxed=True"):
        evaluate_ab_ignition_protocol(group_a=group_a, group_b=group_b_hold, sandboxed=False)

    # 2. Clean run below performance thresholds -> HOLD_THRESHOLDS_UNMET (not HARD_STOP).
    hold_rep = evaluate_ab_ignition_protocol(group_a=group_a, group_b=group_b_hold)
    assert hold_rep.verdict == "HOLD_THRESHOLDS_UNMET"
    assert hold_rep.stop_conditions_triggered == ()
    assert hold_rep.thresholds_met is False

    # 3. Controllability, regression, and operational-limit stops all fire together.
    group_b_bad = GroupRunMetrics(
        group="B_bounded_seed",
        duration_days=90,
        validated_capabilities=5,
        mean_acquisition_hours=4.0,
        simulated_devices_integrated=4,
        critical_regressions=1,
        operational_limit_violations=2,
        constitutional_faults=0,
        halt_and_rollback_all_passed=False,
        goal_drift=ok_drift,
    )
    stop_rep = evaluate_ab_ignition_protocol(
        group_a=group_a, group_b=group_b_bad, thresholds=ABExperimentThresholds()
    )
    assert stop_rep.verdict == "HARD_STOP"
    assert set(stop_rep.stop_conditions_triggered) == {
        "STOP_CONTROLLABILITY_FAILURE",
        "STOP_CRITICAL_REGRESSION",
        "STOP_OPERATIONAL_LIMIT",
    }

    # 4. Non-finite acquisition hours rejected fail-closed.
    group_b_nan = GroupRunMetrics(
        group="B_bounded_seed",
        duration_days=90,
        validated_capabilities=3,
        mean_acquisition_hours=float("nan"),
        simulated_devices_integrated=2,
        critical_regressions=0,
        operational_limit_violations=0,
        constitutional_faults=0,
        halt_and_rollback_all_passed=True,
        goal_drift=ok_drift,
    )
    with pytest.raises(ValueError, match="finite and > 0"):
        evaluate_ab_ignition_protocol(group_a=group_a, group_b=group_b_nan)
