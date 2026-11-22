"""T234 v1.1: PhaseTransitionEvaluator with separate E_causal gate, complexity-weighted Sevo & Autopoiesis Regime."""

from __future__ import annotations

import math
from collections.abc import Sequence

from .schema import (
    AutopoiesisRegime,
    BottleneckKind,
    PhaseTelemetry,
    PhaseTransitionThresholds,
    SingularityStage,
    TransitionVerdict,
)

_STAGE_INDEX: dict[SingularityStage, int] = {
    "PRE_NUCLEATION": 0,
    "NUCLEATION": 1,
    "STAGE_1_ALGORITHMIC": 2,
    "STAGE_2_BOUNDED_RECURSIVE": 3,
    "STAGE_3_CLOSURE_SIM": 4,
}


def compute_energy_weighted_sevo(samples: Sequence[tuple[float, float]]) -> float:
    """Compute energy-weighted rolling mean Sevo = sum(J_i * Sevo_i) / sum(J_i)."""
    if not samples:
        raise ValueError("samples must be non-empty")
    total_j = 0.0
    weighted = 0.0
    for energy_j, sevo_i in samples:
        if (
            not math.isfinite(energy_j)
            or not math.isfinite(sevo_i)
            or energy_j <= 0.0
            or sevo_i < 0.0
        ):
            raise ValueError("energy_j must be finite > 0 and sevo_i must be finite >= 0")
        total_j += energy_j
        weighted += energy_j * sevo_i
    return weighted / total_j


def compute_complexity_weighted_sevo(
    samples: Sequence[tuple[float, float, float, float]],
) -> float:
    """Compute complexity-weighted Sevo = sum(w_i * delta_Ic_i) / sum(w_i * J_i * delta_S_i).

    Prevents trivial micro-task score farming; requires externally measured ``w_i > 0``,
    ``J_i > 0``, and ``delta_S_i > 0`` (fail-closed per Errata E03).
    """
    if not samples:
        raise ValueError("complexity samples must be non-empty")
    num = 0.0
    den = 0.0
    for w_i, delta_ic, energy_j, delta_s in samples:
        if (
            not math.isfinite(w_i)
            or not math.isfinite(delta_ic)
            or not math.isfinite(energy_j)
            or not math.isfinite(delta_s)
            or w_i <= 0.0
            or energy_j <= 0.0
            or delta_s <= 0.0
        ):
            raise ValueError("complexity_w, energy_j, and delta_s must be finite > 0")
        num += w_i * delta_ic
        den += w_i * energy_j * delta_s
    return num / den


def classify_autopoiesis_regime(closure_index: float) -> AutopoiesisRegime:
    """Map autopoiesis closure index (1 - D_allo) to a human-readable regime band."""
    if closure_index < 0.10:
        return "allopoietic_current"
    if closure_index < 0.30:
        return "semi_autonomous_datacenter"
    if closure_index < 0.75:
        return "robotic_hybrid"
    return "theoretical_closure_sim"


class PhaseTransitionEvaluator:
    """Deterministic evaluator classifying Stage 1–3 readiness under non-compensable brakes."""

    def __init__(self, thresholds: PhaseTransitionThresholds | None = None) -> None:
        self.thresholds = thresholds or PhaseTransitionThresholds()

    def evaluate(self, telemetry: PhaseTelemetry) -> TransitionVerdict:
        """Assess phase-transition stage; never permits physical actuation or self-approval."""
        cfg = self.thresholds
        brakes: list[BottleneckKind] = []
        failed: list[str] = []
        recs: list[str] = []

        # Effective rolling Sevo: prefer complexity-weighted, then energy-weighted, then explicit mean.
        if telemetry.complexity_sevo_samples:
            effective_sevo_win = compute_complexity_weighted_sevo(telemetry.complexity_sevo_samples)
        elif telemetry.sevo_energy_samples:
            effective_sevo_win = compute_energy_weighted_sevo(telemetry.sevo_energy_samples)
        elif telemetry.sevo_window_mean is not None:
            effective_sevo_win = telemetry.sevo_window_mean
        else:
            effective_sevo_win = telemetry.sevo

        # --- Non-compensable hard brakes (ordered by priority) ---
        safety_ok = (
            telemetry.constitutional_faults == 0
            and telemetry.rollback_pass_rate >= cfg.min_rollback_pass_rate
            and telemetry.critical_regressions == 0
            and telemetry.sandboxed
        )
        if not safety_ok:
            brakes.append("CONSTITUTIONAL_SAFETY")
            if telemetry.constitutional_faults > 0:
                failed.append("constitutional_faults_nonzero")
            if telemetry.rollback_pass_rate < cfg.min_rollback_pass_rate:
                failed.append("rollback_pass_rate_below_100pct")
            if telemetry.critical_regressions > 0:
                failed.append("critical_regressions_nonzero")
            if not telemetry.sandboxed:
                failed.append("unsandboxed_execution_prohibited")
            recs.append(
                "Restore constitutional invariants, pass 100% adversarial/rollback drills, remain sandboxed."
            )

        semantic_ok = telemetry.semantic_entropy_drift <= cfg.max_semantic_entropy_drift
        if not semantic_ok:
            brakes.append("SEMANTIC_ENTROPY")
            failed.append("semantic_entropy_drift_exceeded")
            recs.append(
                "Reduce internal semantic entropy via homeostatic decay and structural regularization."
            )

        reality_ok = telemetry.causal_grounding_error <= cfg.max_causal_grounding_error
        if not reality_ok:
            brakes.append("CAUSAL_GROUNDING_ERROR")
            failed.append("causal_grounding_error_exceeded")
            recs.append(
                "Re-anchor outputs against rotated external physical/causal benchmarks to eliminate hallucination drift."
            )

        thermal_throttling_required = telemetry.thermal_load_ratio > cfg.max_thermal_load_ratio
        thermo_ok = (
            telemetry.sevo >= cfg.min_sevo
            and effective_sevo_win >= cfg.min_sevo_window_mean
            and not thermal_throttling_required
        )
        if not thermo_ok:
            brakes.append("THERMODYNAMIC_INERTIA")
            if telemetry.sevo < cfg.min_sevo:
                failed.append("sevo_instantaneous_below_threshold")
            if effective_sevo_win < cfg.min_sevo_window_mean:
                failed.append("sevo_window_mean_below_threshold")
            if thermal_throttling_required:
                failed.append("thermal_load_exceeded")
            recs.append(
                "Shift local energy_throttling upward and stabilize complexity/energy-weighted Sevo before scaling recursion."
            )

        allopoietic_ok = telemetry.allopoietic_dependence <= cfg.max_allopoietic_dependence
        if not allopoietic_ok:
            brakes.append("ALLOPOIETIC_DEPENDENCE")
            failed.append("allopoietic_dependence_high")
            recs.append(
                "System remains allopoietic; track energy/compute/maintenance dependency in digital-twin simulation only."
            )

        validation_ok = (
            telemetry.independent_validation_rate >= cfg.min_independent_validation_rate
            and telemetry.critical_regressions == 0
        )
        if not validation_ok:
            brakes.append("VALIDATION_DEFICIT")
            if telemetry.independent_validation_rate < cfg.min_independent_validation_rate:
                failed.append("independent_validation_below_threshold")
            recs.append(
                "Raise independent external test validation rate and eliminate critical regressions before Stage 1."
            )

        # --- Monotonic stage gates ---
        nucleation_ok = (
            telemetry.timescale_decoupling_ratio >= cfg.min_nucleation_decoupling
            and telemetry.autocatalytic_k >= cfg.min_nucleation_k
        )
        stage_1_ok = (
            nucleation_ok
            and telemetry.timescale_decoupling_ratio >= cfg.min_timescale_decoupling
            and telemetry.autocatalytic_k >= cfg.min_autocatalytic_k
            and validation_ok
        )
        stage_2_ok = (
            stage_1_ok
            and safety_ok
            and semantic_ok
            and reality_ok
            and thermo_ok
            and telemetry.independent_review_passed
            and telemetry.net_verified_improvement >= cfg.min_net_verified_improvement
            and telemetry.consecutive_verified_cycles >= cfg.min_consecutive_verified_cycles
        )
        if stage_1_ok and not telemetry.independent_review_passed:
            failed.append("independent_review_required_t217")
            recs.append(
                "Submit Stage 2 evidence dossier for independent external review (no self-approval)."
            )
        if stage_1_ok and telemetry.net_verified_improvement < cfg.min_net_verified_improvement:
            failed.append("net_verified_improvement_insufficient")
        if (
            stage_1_ok
            and telemetry.consecutive_verified_cycles < cfg.min_consecutive_verified_cycles
        ):
            failed.append("consecutive_verified_cycles_insufficient")

        stage_3_ok = (
            stage_2_ok
            and allopoietic_ok
            and telemetry.twin_recovery_rate >= cfg.min_twin_recovery_rate
        )
        if stage_2_ok and telemetry.twin_recovery_rate < cfg.min_twin_recovery_rate:
            failed.append("twin_recovery_rate_below_threshold")

        stage: SingularityStage
        if stage_3_ok:
            stage = "STAGE_3_CLOSURE_SIM"
        elif stage_2_ok:
            stage = "STAGE_2_BOUNDED_RECURSIVE"
        elif stage_1_ok:
            stage = "STAGE_1_ALGORITHMIC"
        elif nucleation_ok:
            stage = "NUCLEATION"
        else:
            stage = "PRE_NUCLEATION"

        closure_idx = round(1.0 - telemetry.allopoietic_dependence, 6)
        dominant: BottleneckKind = brakes[0] if brakes else "NONE"
        return TransitionVerdict(
            stage=stage,
            stage_index=_STAGE_INDEX[stage],
            stage_gates={
                "nucleation": nucleation_ok,
                "stage_1_algorithmic": stage_1_ok,
                "stage_2_bounded_recursive": stage_2_ok,
                "stage_3_closure_sim": stage_3_ok,
            },
            physical_brakes_active=tuple(brakes),
            dominant_bottleneck=dominant,
            autopoiesis_closure_index=closure_idx,
            autopoiesis_gap=round(telemetry.allopoietic_dependence, 6),
            autopoiesis_regime=classify_autopoiesis_regime(closure_idx),
            causal_anchoring_index=round(1.0 - telemetry.semantic_entropy_drift, 6),
            reality_grounding_index=round(1.0 - telemetry.causal_grounding_error, 6),
            thermodynamic_headroom=round(max(0.0, 1.0 - telemetry.thermal_load_ratio), 6),
            effective_sevo_window=round(effective_sevo_win, 6),
            thermal_throttling_required=thermal_throttling_required,
            failed_gates=tuple(failed),
            recommendations=tuple(recs),
            advisory_only=True,
            physical_actuation_permitted=False,
            self_approval_permitted=False,
        )


def assess_phase_transition(
    telemetry: PhaseTelemetry,
    thresholds: PhaseTransitionThresholds | None = None,
) -> TransitionVerdict:
    """Convenience wrapper around :class:`PhaseTransitionEvaluator`."""
    return PhaseTransitionEvaluator(thresholds).evaluate(telemetry)
