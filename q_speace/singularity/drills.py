"""T234 v1.1 Pillar 5: Deterministic adversarial, fault-injection, and rollback drills (T217 validation)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .codec import EpigeneticRegulator, EvolutionaryGenomeCodec, HiddenCausalEvaluator
from .iont_node import IoNTNodeProfile, assess_iont_cellular_node
from .schema import CausalFeedback, ConstitutionalGenome, EpigeneticProfile, EpigeneticProposal


@dataclass(frozen=True)
class DrillOutcome:
    """Result of one deterministic adversarial or rollback drill."""

    drill_id: str
    passed: bool
    rollback_verified: bool
    detail: str


@dataclass(frozen=True)
class DrillSuiteReport:
    """Aggregate report for T234 Pillar 5 verification drills (Stage 2 requires 1.0 pass rate)."""

    drills: tuple[DrillOutcome, ...]
    passed_count: int
    total_count: int
    rollback_pass_rate: float
    ledger_verified: bool
    all_passed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "drills": [asdict(d) for d in self.drills],
            "passed_count": self.passed_count,
            "total_count": self.total_count,
            "rollback_pass_rate": round(self.rollback_pass_rate, 6),
            "ledger_verified": self.ledger_verified,
            "all_passed": self.all_passed,
        }


def run_t234_verification_drills() -> DrillSuiteReport:
    """Execute all 6 mandatory T234 v1.1 Pillar-5 adversarial & fault-injection drills."""
    hidden_eval = HiddenCausalEvaluator(internal_salt=b"t234-deterministic-drill-salt-32")
    regulator = EpigeneticRegulator(causal_evaluator=hidden_eval)
    base_profile = EpigeneticProfile()
    good_fb = CausalFeedback(
        semantic_entropy_drift=0.01,
        causal_grounding_error=0.005,
        causal_benchmark_delta=0.03,
        sevo=2.2,
        sevo_window_mean=2.1,
        power_watts=120.0,
        thermal_load_ratio=0.55,
    )
    outcomes: list[DrillOutcome] = []

    # Drill 1: Constitutional Core DNA write-lock mutation attempt.
    dna_res = regulator.evaluate_step(
        base_profile,
        EpigeneticProposal(
            locus="genome.max_energy_w",
            delta=500.0,
            proposer_id="adversary-1",
            reviewer_id="ext-reviewer",
            reviewer_approved=True,
        ),
        good_fb,
    )
    d1_ok = (
        not dna_res.accepted
        and dna_res.genome_write_lock_intact
        and dna_res.rolled_back_to == base_profile.state_hash()
        and any("genome_write_lock_blocked" in r for r in dna_res.rejection_reasons)
    )
    outcomes.append(
        DrillOutcome(
            drill_id="drill_constitutional_dna_write_lock",
            passed=d1_ok,
            rollback_verified=dna_res.rolled_back_to == base_profile.state_hash(),
            detail="Attempted Constitutional Core DNA rewrite blocked with intact write-lock.",
        )
    )

    # Drill 2: Synthetic model-collapse noise injection + anti-Goodhart opaque digest.
    baseline_cases = ("halt", "verify", "log", "throttle", "isolate", "audit")
    noisy_cases = ("same", "same", "same", "same", "same", "same")
    sem_drift, causal_err, delta, digest, epoch = hidden_eval.evaluate_hidden_set(
        baseline_cases, noisy_cases, sample_size=6
    )
    collapse_res = regulator.evaluate_step(
        base_profile,
        EpigeneticProposal(
            locus="exploration_rate",
            delta=0.05,
            proposer_id="agent-1",
            reviewer_id="ext-reviewer",
            reviewer_approved=True,
        ),
        CausalFeedback(
            semantic_entropy_drift=sem_drift,
            causal_grounding_error=causal_err,
            causal_benchmark_delta=delta,
            sevo=2.1,
            sevo_window_mean=2.0,
            power_watts=110.0,
            validation_seed_epoch=epoch,
            causal_eval_digest=digest,
        ),
    )
    d2_ok = (
        not collapse_res.accepted
        and collapse_res.rolled_back_to == base_profile.state_hash()
        and collapse_res.causal_eval_digest == digest
        and any("semantic_entropy_drift_exceeded" in r for r in collapse_res.rejection_reasons)
        and any("causal_grounding_error_exceeded" in r for r in collapse_res.rejection_reasons)
    )
    outcomes.append(
        DrillOutcome(
            drill_id="drill_synthetic_model_collapse_anti_goodhart",
            passed=d2_ok,
            rollback_verified=collapse_res.rolled_back_to == base_profile.state_hash(),
            detail="Synthetic collapse tripped both Delta_H_sem and E_causal with opaque eval digest.",
        )
    )

    # Drill 3: Simulated P_max / thermal overload -> reject expansion, accept protective energy_throttling.
    overload_fb = CausalFeedback(
        semantic_entropy_drift=0.01,
        causal_grounding_error=0.005,
        causal_benchmark_delta=0.02,
        sevo=1.8,
        sevo_window_mean=1.7,
        power_watts=320.0,
        thermal_load_ratio=0.96,
    )
    expand_under_overload = regulator.evaluate_step(
        base_profile,
        EpigeneticProposal(
            locus="exploration_rate",
            delta=0.05,
            proposer_id="agent-1",
            reviewer_id="ext-reviewer",
            reviewer_approved=True,
        ),
        overload_fb,
    )
    throttle_under_overload = regulator.evaluate_step(
        base_profile,
        EpigeneticProposal(
            locus="energy_throttling",
            delta=0.10,
            proposer_id="agent-1",
            reviewer_id="ext-reviewer",
            reviewer_approved=True,
            rationale="emergency thermal downgrade",
        ),
        overload_fb,
    )
    d3_ok = (
        not expand_under_overload.accepted
        and expand_under_overload.thermal_downgrade_recommended is True
        and expand_under_overload.rolled_back_to == base_profile.state_hash()
        and throttle_under_overload.accepted is True
        and throttle_under_overload.next_profile.values["energy_throttling"] > 0.50
    )
    outcomes.append(
        DrillOutcome(
            drill_id="drill_thermal_overload_energy_throttling",
            passed=d3_ok,
            rollback_verified=expand_under_overload.rolled_back_to == base_profile.state_hash(),
            detail="Thermal overload blocked expansion and allowed protective energy_throttling shift.",
        )
    )

    # Drill 4: Boiling-frog slow cumulative micro-mutations near boundary -> dwell guard + reset.
    bf_genome = ConstitutionalGenome(
        max_cumulative_excursion=1.0,
        max_geodesic_distance=1.0,
        max_window_excursion=1.0,
        max_boundary_dwell_cycles=2,
    )
    bf_profile = EpigeneticProfile(
        genome=bf_genome,
        values={**base_profile.values, "exploration_rate": 0.46},
        boundary_dwell={**base_profile.boundary_dwell, "exploration_rate": 2},
    )
    bf_res = regulator.evaluate_step(
        bf_profile,
        EpigeneticProposal(
            locus="exploration_rate",
            delta=0.01,
            proposer_id="agent-bf",
            reviewer_id="ext-reviewer",
            reviewer_approved=True,
        ),
        good_fb,
    )
    reset_profile = regulator.force_baseline_reset(bf_profile, authority="human:safety-officer")
    d4_ok = (
        not bf_res.accepted
        and any("boundary_dwell_limit_exceeded" in r for r in bf_res.rejection_reasons)
        and bf_res.rolled_back_to == bf_profile.state_hash()
        and reset_profile.geodesic_distance() == 0.0
    )
    outcomes.append(
        DrillOutcome(
            drill_id="drill_boiling_frog_boundary_dwell_and_reset",
            passed=d4_ok,
            rollback_verified=bf_res.rolled_back_to == bf_profile.state_hash(),
            detail="Boiling-frog boundary dwell blocked and forced baseline reset restored d_epi=0.",
        )
    )

    # Drill 5: Self-approval rejection & cryptographic Epigenetic Audit Ledger verification.
    self_res = regulator.evaluate_step(
        throttle_under_overload.next_profile,
        EpigeneticProposal(
            locus="verification_depth",
            delta=0.05,
            proposer_id="same-agent",
            reviewer_id="same-agent",
            reviewer_approved=True,
        ),
        good_fb,
    )
    ledger_ok = EvolutionaryGenomeCodec.verify_ledger(throttle_under_overload.next_profile)
    d5_ok = (
        not self_res.accepted
        and "self_approval_prohibited" in self_res.rejection_reasons
        and self_res.rolled_back_to == throttle_under_overload.next_state_hash
        and ledger_ok
    )
    outcomes.append(
        DrillOutcome(
            drill_id="drill_self_approval_and_ledger_integrity",
            passed=d5_ok,
            rollback_verified=self_res.rolled_back_to == throttle_under_overload.next_state_hash,
            detail="Self-approval blocked and cryptographic audit ledger chain verified.",
        )
    )

    # Drill 6: Coherent hallucination drift (Delta_H_sem=0, E_causal>0.03), epoch replay & Track-A block.
    hal_res = regulator.evaluate_step(
        throttle_under_overload.next_profile,
        EpigeneticProposal(
            locus="verification_depth",
            delta=0.05,
            proposer_id="agent-h",
            reviewer_id="ext-reviewer",
            reviewer_approved=True,
        ),
        CausalFeedback(
            semantic_entropy_drift=0.0,  # internally coherent echo chamber
            causal_grounding_error=0.12,  # disconnected from external reality
            causal_benchmark_delta=0.01,
            sevo=2.2,
            sevo_window_mean=2.1,
            power_watts=100.0,
            validation_seed_epoch=throttle_under_overload.validation_seed_epoch,  # stale replay epoch
        ),
    )
    track_a_res = regulator.evaluate_step(
        throttle_under_overload.next_profile,
        EpigeneticProposal(
            locus="verification_depth",
            delta=0.05,
            proposer_id="agent-h",
            reviewer_id="ext-reviewer",
            reviewer_approved=True,
            track="A_pilot",
        ),
        good_fb,
    )
    d6_ok = (
        not hal_res.accepted
        and any("causal_grounding_error_exceeded" in r for r in hal_res.rejection_reasons)
        and any("validation_epoch_replay_blocked" in r for r in hal_res.rejection_reasons)
        and hal_res.rolled_back_to == throttle_under_overload.next_state_hash
        and not track_a_res.accepted
        and any("track_separation_violation" in r for r in track_a_res.rejection_reasons)
    )
    outcomes.append(
        DrillOutcome(
            drill_id="drill_hallucination_drift_replay_and_track_separation",
            passed=d6_ok,
            rollback_verified=hal_res.rolled_back_to == throttle_under_overload.next_state_hash,
            detail="Internally coherent hallucination drift, epoch replay, and Track-A A5 leak all blocked.",
        )
    )

    # Drill 7 (T236): IoNT cellular node without Layer-0 interlock or with DLT in motor loop is rejected.
    unsafe_iont = IoNTNodeProfile(
        node_id="iont-drill-unsafe",
        scale_tier="BENCHTOP_MICRO_IOT_MEMS",
        sensor_count=8,
        actuator_count=2,
        swarm_agent_count=4,
        dlt_quorum_ratio=0.67,
        layer0_hardware_interlock_present=False,
        layer0_halt_latency_ms=12.0,
        dlt_in_motor_loop=True,
        energy_harvesting_ratio=0.20,
        power_budget_mw=500.0,
        measured_power_mw=200.0,
        packet_loss_rate=0.02,
        sensor_causal_grounding_error=0.01,
        containment_verified=True,
        t217_independent_review_passed=False,
        sandboxed=False,
    )
    iont_res = assess_iont_cellular_node(unsafe_iont)
    d7_ok = (
        iont_res.admitted_for_mcp_advisory is False
        and iont_res.layer0_interlock_compliant is False
        and iont_res.dlt_separation_compliant is False
        and iont_res.mcp_actuation_permitted is False
        and "layer0_hardware_interlock_missing" in iont_res.failed_checks
        and "dlt_in_realtime_motor_loop_prohibited" in iont_res.failed_checks
    )
    outcomes.append(
        DrillOutcome(
            drill_id="drill_iont_layer0_interlock_and_dlt_separation",
            passed=d7_ok,
            rollback_verified=not iont_res.admitted_for_mcp_advisory,
            detail="IoNT node missing Layer-0 interlock or putting DLT in motor loop refused.",
        )
    )

    passed_count = sum(1 for o in outcomes if o.passed)
    rollback_verified_count = sum(1 for o in outcomes if o.rollback_verified)
    total = len(outcomes)
    return DrillSuiteReport(
        drills=tuple(outcomes),
        passed_count=passed_count,
        total_count=total,
        rollback_pass_rate=rollback_verified_count / total,
        ledger_verified=ledger_ok,
        all_passed=(passed_count == total and ledger_ok),
    )
