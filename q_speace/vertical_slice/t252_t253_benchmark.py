"""T252–T253 Preregistered Experiential Transfer & Selective Repair Benchmark.

Evaluates SPEACE across 2 calibration problem families (``F1_thermal_lock``,
``F2_staging_pipeline``) and 3 held-out unseen problem families
(``F3_quorum_handoff``, ``F4_cryo_purification``, ``F5_containment_airlock``),
enforcing SHA-256 preregistration locks via ``q_speace.spiking.prereg_lock``:

- **Phase 1 (Acquisition & Role Re-Binding in A)**: extracts role-parameterized
  macro-skills from solved traces and re-executes on novel object bindings in A.
- **Phase 2 (Analogical Transfer in Non-Isomorphic B — EXPERIENTIAL vs AMNESIC)**:
  symbols and operators change completely, 3 distractor entities + distractor
  operators are injected, and step 1 requires a local precondition refinement
  absent in A. Both arms can learn during B.
- **Phase 3a/3b (Mid-Step Rule Mutation from Identical Pre-Shift Checkpoint —
  SELECTIVE_REPAIR vs GLOBAL_REPLAN)**: compares weakest-precondition local
  splicing against global replanning, then tests the reconsolidated skill on a
  subsequent unseen variant (Phase 3b).
- **Phase 3c (Suffix-Invalidating Negative Controls — Anti-Einstellung)**:
  verifies that ``SELECTIVE_REPAIR`` abandons the broken macro-skill and replans
  onto a standby recovery path when the suffix is invalidated, whereas
  ``STUBBORN_REUSE_CONTROL`` fails.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np

from ..routing import GOAPAction
from ..self_improvement_cortex.macro_skills import (
    EmpiricalOperatorModel,
    ExperientialCognitiveAgent,
    StatefulPlanningEnvironment,
    format_structured_atom,
)
from ..spiking.prereg_lock import verify_lock
from ..spiking.reasoning import RelationEdge
from .evaluator import paired_bootstrap_ci


@dataclass(frozen=True)
class FamilyVocabulary:
    """Disjoint domain vocabulary for Source (A) and Target (B) of one problem family."""

    family_id: str
    split: Literal["calibration", "held_out"]
    # Source Domain A vocabulary
    domain_a: str
    link_rel_a: str
    ops_a: tuple[str, str, str, str]
    fluents_a: tuple[str, str, str, str, str]  # (alert, s1, s2, s3, goal)
    # Target Domain B vocabulary (zero lexical overlap with Domain A!)
    domain_b: str
    link_rel_b: str
    prep_op_b: str
    prep_fluent_b: str
    ops_b: tuple[str, str, str, str]
    fluents_b: tuple[str, str, str, str, str]  # (trigger, b1, b2, b3, goal_b)
    # Phase 3a local repair bridge vocabulary in B
    latch_fluent_b: str
    bridge_ops_b: tuple[str, str]
    bridge_mid_fluent_b: str
    # Phase 3c standby failover vocabulary in B (when primary suffix is invalidated)
    standby_ops_b: tuple[str, str, str]


PROBLEM_FAMILIES: tuple[FamilyVocabulary, ...] = (
    # --- Calibration Families (n = 2) ---
    FamilyVocabulary(
        family_id="F1_thermal_lock",
        split="calibration",
        domain_a="microgrid_loop",
        link_rel_a="pipes_to",
        ops_a=("isolate_valve", "bleed_pressure", "prime_impeller", "engage_cooling"),
        fluents_a=("overheat", "isolated", "depressurized", "primed", "loop_nominal"),
        domain_b="battery_busbar",
        link_rel_b="conducts_to",
        prep_op_b="release_pin",
        prep_fluent_b="pin_released",
        ops_b=("open_contactor", "discharge_rail", "balance_cell", "close_bus"),
        fluents_b=("surge_detected", "contactor_open", "rail_discharged", "balanced", "bus_online"),
        latch_fluent_b="cell_drift_latched",
        bridge_ops_b=("trim_shunt", "confirm_balance"),
        bridge_mid_fluent_b="shunt_trimmed",
        standby_ops_b=("arm_aux_pack", "sync_aux_phase", "cutover_aux_bus"),
    ),
    FamilyVocabulary(
        family_id="F2_staging_pipeline",
        split="calibration",
        domain_a="ingest_queue",
        link_rel_a="streams_to",
        ops_a=("quiesce_topic", "drain_offset", "compact_segment", "resume_broker"),
        fluents_a=("lag_spike", "quiesced", "drained", "compacted", "stream_healthy"),
        domain_b="artifact_signer",
        link_rel_b="publishes_to",
        prep_op_b="unlock_hsm_slot",
        prep_fluent_b="hsm_unlocked",
        ops_b=("freeze_manifest", "hash_payload", "seal_attestation", "promote_release"),
        fluents_b=("tamper_flag", "frozen", "hashed", "sealed", "release_live"),
        latch_fluent_b="nonce_skew_latched",
        bridge_ops_b=("resync_clock_source", "reissue_digest"),
        bridge_mid_fluent_b="clock_resynced",
        standby_ops_b=("mount_cold_mirror", "verify_mirror_sig", "activate_mirror_release"),
    ),
    # --- Held-Out Families (n = 3, strictly disjoint from calibration) ---
    FamilyVocabulary(
        family_id="F3_quorum_handoff",
        split="held_out",
        domain_a="consensus_shard",
        link_rel_a="replicates_to",
        ops_a=("fence_epoch", "flush_wal", "transfer_lease", "commit_view"),
        fluents_a=("split_risk", "epoch_fenced", "wal_flushed", "lease_held", "cluster_coherent"),
        domain_b="orbital_transponder",
        link_rel_b="relays_beam_to",
        prep_op_b="acquire_beacon",
        prep_fluent_b="beacon_locked",
        ops_b=("mute_uplink", "slew_gimbal", "handover_carrier", "illuminate_spot"),
        fluents_b=(
            "doppler_alert",
            "uplink_muted",
            "gimbal_aligned",
            "carrier_locked",
            "service_restored",
        ),
        latch_fluent_b="polarization_skew",
        bridge_ops_b=("rotate_feedhorn", "lock_carrier_pll"),
        bridge_mid_fluent_b="feedhorn_rotated",
        standby_ops_b=("wake_spare_dish", "align_spare_uplink", "route_spare_spot"),
    ),
    FamilyVocabulary(
        family_id="F4_cryo_purification",
        split="held_out",
        domain_a="helium_cryostat",
        link_rel_a="feeds_manifold",
        ops_a=("close_bellows", "evacuate_trap", "chill_stage", "stabilize_kelvin"),
        fluents_a=("boiloff_warn", "bellows_shut", "trap_evacuated", "stage_chilled", "cryo_ready"),
        domain_b="litho_reticle_chamber",
        link_rel_b="ducts_gas_to",
        prep_op_b="arm_interlock_shutter",
        prep_fluent_b="shutter_armed",
        ops_b=("seal_loadlock", "scrub_outgas", "ionize_purge", "open_exposure"),
        fluents_b=(
            "particle_alarm",
            "loadlock_sealed",
            "outgas_scrubbed",
            "purge_ionized",
            "wafer_online",
        ),
        latch_fluent_b="filter_backpressure",
        bridge_ops_b=("pulse_backflush", "reverify_purity"),
        bridge_mid_fluent_b="backflush_done",
        standby_ops_b=("engage_bypass_bay", "Condition_bypass_vacuum", "enable_bypass_wafer"),
    ),
    FamilyVocabulary(
        family_id="F5_containment_airlock",
        split="held_out",
        domain_a="biosafety_vestibule",
        link_rel_a="vents_into",
        ops_a=("latch_inner_door", "mist_peroxide", "aerate_chamber", "unlatch_outer"),
        fluents_a=("aerosol_flag", "inner_latched", "misted", "aerated", "transfer_complete"),
        domain_b="subsea_rov_dock",
        link_rel_b="couples_hatch_to",
        prep_op_b="engage_clamp_ring",
        prep_fluent_b="clamp_engaged",
        ops_b=("seat_collar", "equalize_ballast", "dewater_trunk", "open_moonpool"),
        fluents_b=("pressure_delta", "collar_seated", "ballast_equal", "trunk_dry", "rov_deployed"),
        latch_fluent_b="hydrate_plug_latched",
        bridge_ops_b=("inject_glycol", "confirm_trunk_dry"),
        bridge_mid_fluent_b="glycol_injected",
        standby_ops_b=("winch_deck_crane", "release_tether_latch", "launch_via_crane"),
    ),
)


def verify_t252_preregistration(prereg_path: Path | None = None) -> dict[str, Any]:
    """Load and cryptographically verify both locked sections in ``T252_T253_PREREG.json``."""
    default_path = Path(__file__).resolve().parent.parent.parent / "docs" / "T252_T253_PREREG.json"
    path = prereg_path or default_path
    if not path.exists():
        raise FileNotFoundError(f"Missing preregistration file: {path}")

    raw = json.loads(path.read_text(encoding="utf-8"))
    pre_cal = raw.get("pre_calibration", {})
    pre_eval = raw.get("pre_evaluation", {})
    if not verify_lock(pre_cal):
        raise ValueError("Preregistration lock verification FAILED for pre_calibration")
    if not verify_lock(pre_eval):
        raise ValueError("Preregistration lock verification FAILED for pre_evaluation")
    return dict(raw)


def _build_domain_a_instance(
    vocab: FamilyVocabulary,
    *,
    ep_idx: int,
) -> tuple[frozenset[str], frozenset[str], list[GOAPAction], list[RelationEdge]]:
    """Construct a Source Domain A problem instance with 3 chain entities + 2 decoys."""
    u0 = f"a{ep_idx}_src"
    u1 = f"a{ep_idx}_mid"
    u2 = f"a{ep_idx}_dst"
    d0 = f"a{ep_idx}_dec0"
    d1 = f"a{ep_idx}_dec1"

    alert, s1, s2, s3, goal_f = vocab.fluents_a
    op1, op2, op3, op4 = vocab.ops_a
    lnk = vocab.link_rel_a

    edges = [
        RelationEdge(u0, lnk, u1, 1.0),
        RelationEdge(u1, lnk, u2, 1.0),
        RelationEdge(d0, lnk, d1, 1.0),
    ]

    init = frozenset(
        {
            format_structured_atom(alert, (u0,)),
            format_structured_atom(lnk, (u0, u1)),
            format_structured_atom(lnk, (u1, u2)),
            format_structured_atom(alert, (d0,)),
            format_structured_atom(lnk, (d0, d1)),
        }
    )
    goal = frozenset({format_structured_atom(goal_f, (u2,))})

    actions: list[GOAPAction] = []
    # True 4-step relational chain on (u0, u1, u2) plus decoy chain on (d0, d1)
    for x, y in ((u0, u1), (d0, d1)):
        actions.append(
            GOAPAction(
                name=format_structured_atom(op1, (x, y)),
                preconditions=frozenset(
                    {format_structured_atom(alert, (x,)), format_structured_atom(lnk, (x, y))}
                ),
                add_effects=frozenset({format_structured_atom(s1, (y,))}),
                cost=1.0,
            )
        )
    actions.append(
        GOAPAction(
            name=format_structured_atom(op2, (u1, u2)),
            preconditions=frozenset(
                {format_structured_atom(s1, (u1,)), format_structured_atom(lnk, (u1, u2))}
            ),
            add_effects=frozenset({format_structured_atom(s2, (u1,))}),
            cost=1.0,
        )
    )
    actions.append(
        GOAPAction(
            name=format_structured_atom(op3, (u1, u2)),
            preconditions=frozenset({format_structured_atom(s2, (u1,))}),
            add_effects=frozenset({format_structured_atom(s3, (u2,))}),
            cost=1.0,
        )
    )
    actions.append(
        GOAPAction(
            name=format_structured_atom(op4, (u2,)),
            preconditions=frozenset({format_structured_atom(s3, (u2,))}),
            add_effects=frozenset({format_structured_atom(goal_f, (u2,))}),
            cost=1.0,
        )
    )
    # Extra decoy operators increasing uninformed A* branching
    for dec in (d0, d1, u0):
        for k in range(3):
            actions.append(
                GOAPAction(
                    name=format_structured_atom(f"diag_probe_{k}", (dec,)),
                    preconditions=frozenset(),
                    add_effects=frozenset({format_structured_atom(f"probed_{k}", (dec,))}),
                    cost=1.0,
                )
            )
    return init, goal, actions, edges


def _build_domain_b_instance(
    vocab: FamilyVocabulary,
    *,
    ep_idx: int,
    needs_local_refinement: bool = True,
    sub_regime_suffix: str = "",
) -> tuple[
    frozenset[str],
    frozenset[str],
    list[GOAPAction],
    list[RelationEdge],
    tuple[str, str, str],
    tuple[str, str, str],
]:
    """Construct Target Domain B instance with renamed vocabulary, 3 distractors & standby path."""
    b0 = f"b{ep_idx}_n0"
    b1 = f"b{ep_idx}_n1"
    b2 = f"b{ep_idx}_n2"
    # 3 distractor entities with non-goal 1-hop / isolated topology
    dist0 = f"b{ep_idx}_dist0"
    dist1 = f"b{ep_idx}_dist1"
    dist2 = f"b{ep_idx}_dist2"
    # Standby failover nodes for Phase 3c
    sb0 = f"b{ep_idx}_sb0"
    sb1 = f"b{ep_idx}_sb1"

    trig, f1, f2, f3, goal_b = vocab.fluents_b
    op1, op2, op3, op4 = (
        tuple(f"{op}{sub_regime_suffix}" for op in vocab.ops_b)
        if sub_regime_suffix
        else vocab.ops_b
    )
    lnk = vocab.link_rel_b
    prep_op = f"{vocab.prep_op_b}{sub_regime_suffix}" if sub_regime_suffix else vocab.prep_op_b
    prep_fl = vocab.prep_fluent_b

    # Graph topology: b0 -> b1 -> b2 (2-hop chain to goal entity b2); distractors lack 2-hop goal path
    edges = [
        RelationEdge(b0, lnk, b1, 1.0),
        RelationEdge(b1, lnk, b2, 1.0),
        RelationEdge(dist0, lnk, dist1, 1.0),
        RelationEdge(sb0, "standby_for", b2, 0.8),
    ]

    base_facts = {
        format_structured_atom(trig, (b0,)),
        format_structured_atom(lnk, (b0, b1)),
        format_structured_atom(lnk, (b1, b2)),
        format_structured_atom("channel_intact", (b1,)),
        format_structured_atom(trig, (dist0,)),
        format_structured_atom(lnk, (dist0, dist1)),
        format_structured_atom("standby_ready", (sb0,)),
    }
    if not needs_local_refinement:
        base_facts.add(format_structured_atom(prep_fl, (b0,)))

    init = frozenset(base_facts)
    goal = frozenset({format_structured_atom(goal_b, (b2,))})

    actions: list[GOAPAction] = []

    # Non-isomorphic local refinement step required before op1(b0, b1)
    actions.append(
        GOAPAction(
            name=format_structured_atom(prep_op, (b0,)),
            preconditions=frozenset({format_structured_atom(trig, (b0,))}),
            add_effects=frozenset({format_structured_atom(prep_fl, (b0,))}),
            cost=1.0,
        )
    )

    # Primary 4-step chain in B
    actions.append(
        GOAPAction(
            name=format_structured_atom(op1, (b0, b1)),
            preconditions=frozenset(
                {
                    format_structured_atom(trig, (b0,)),
                    format_structured_atom(lnk, (b0, b1)),
                    format_structured_atom(prep_fl, (b0,)),
                }
            ),
            add_effects=frozenset({format_structured_atom(f1, (b1,))}),
            cost=1.0,
        )
    )
    actions.append(
        GOAPAction(
            name=format_structured_atom(op2, (b1, b2)),
            preconditions=frozenset(
                {format_structured_atom(f1, (b1,)), format_structured_atom(lnk, (b1, b2))}
            ),
            add_effects=frozenset({format_structured_atom(f2, (b1,))}),
            cost=1.0,
        )
    )
    actions.append(
        GOAPAction(
            name=format_structured_atom(op3, (b1, b2)),
            preconditions=frozenset(
                {
                    format_structured_atom(f2, (b1,)),
                    format_structured_atom("channel_intact", (b1,)),
                }
            ),
            add_effects=frozenset({format_structured_atom(f3, (b2,))}),
            cost=1.0,
        )
    )
    actions.append(
        GOAPAction(
            name=format_structured_atom(op4, (b2,)),
            preconditions=frozenset({format_structured_atom(f3, (b2,))}),
            add_effects=frozenset({format_structured_atom(goal_b, (b2,))}),
            cost=1.0,
        )
    )

    # Local recovery bridge operators for Phase 3a (only applicable when latch_fluent_b is present)
    b_op1, b_op2 = vocab.bridge_ops_b
    actions.append(
        GOAPAction(
            name=format_structured_atom(b_op1, (b1,)),
            preconditions=frozenset({format_structured_atom(vocab.latch_fluent_b, (b1,))}),
            add_effects=frozenset({format_structured_atom(vocab.bridge_mid_fluent_b, (b1,))}),
            cost=1.0,
        )
    )
    actions.append(
        GOAPAction(
            name=format_structured_atom(b_op2, (b1,)),
            preconditions=frozenset({format_structured_atom(vocab.bridge_mid_fluent_b, (b1,))}),
            add_effects=frozenset({format_structured_atom(f2, (b1,))}),
            del_effects=frozenset({format_structured_atom(vocab.latch_fluent_b, (b1,))}),
            cost=1.0,
        )
    )

    # Standby 3-step failover path for Phase 3c (higher cost=1.8 so primary is preferred when healthy)
    sb_op1, sb_op2, sb_op3 = vocab.standby_ops_b
    actions.append(
        GOAPAction(
            name=format_structured_atom(sb_op1, (sb0,)),
            preconditions=frozenset({format_structured_atom("standby_ready", (sb0,))}),
            add_effects=frozenset({format_structured_atom("standby_armed", (sb0,))}),
            cost=1.8,
        )
    )
    actions.append(
        GOAPAction(
            name=format_structured_atom(sb_op2, (sb0, sb1)),
            preconditions=frozenset({format_structured_atom("standby_armed", (sb0,))}),
            add_effects=frozenset({format_structured_atom("standby_synced", (sb1,))}),
            cost=1.8,
        )
    )
    actions.append(
        GOAPAction(
            name=format_structured_atom(sb_op3, (sb1, b2)),
            preconditions=frozenset({format_structured_atom("standby_synced", (sb1,))}),
            add_effects=frozenset({format_structured_atom(goal_b, (b2,))}),
            cost=1.8,
        )
    )

    # Distractor operators on (dist0, dist1, dist2) creating realistic A* search branching
    for d_ent in (dist0, dist1, dist2):
        for step_k in range(3):
            pre_d = (
                frozenset()
                if step_k == 0
                else frozenset({format_structured_atom(f"dist_stage_{step_k - 1}", (d_ent,))})
            )
            actions.append(
                GOAPAction(
                    name=format_structured_atom(f"distractor_op_{step_k}", (d_ent,)),
                    preconditions=pre_d,
                    add_effects=frozenset(
                        {format_structured_atom(f"dist_stage_{step_k}", (d_ent,))}
                    ),
                    cost=0.9,
                )
            )

    return init, goal, actions, edges, (b0, b1, b2), (dist0, dist1, dist2)


@dataclass(frozen=True)
class FamilyBenchmarkSummary:
    """Per-family aggregated outcomes across Phases 1, 2, 3a, 3b, and 3c."""

    family_id: str
    split: str
    phase1_rebind_success_rate: float
    phase1_rebind_expansions: int
    phase2_experiential_success_rate: float
    phase2_amnesic_success_rate: float
    phase2_experiential_expansions: int
    phase2_amnesic_expansions: int
    phase2_distractor_rejection_rate: float
    phase3a_selective_repair_success_rate: float
    phase3a_global_replan_success_rate: float
    phase3a_selective_expansions: int
    phase3a_global_expansions: int
    phase3b_variant_spliced_expansions: int
    phase3b_variant_unrepaired_expansions: int
    phase3c_selective_abandon_accuracy: float
    phase3c_selective_recovery_rate: float
    phase3c_stubborn_success_rate: float


def _evaluate_family(
    vocab: FamilyVocabulary,
    *,
    alpha_local: float,
    tau_analogy: float,
    episodes_per_family: int = 4,
) -> tuple[FamilyBenchmarkSummary, list[float], list[float], list[float], list[float]]:
    """Run all 3 experimental phases on ``vocab`` and return metrics + per-episode score vectors."""
    # --- Phase 1: Acquisition in A (ep 0) & Re-binding on new objects in A (eps 1..K) ---
    init_a0, goal_a0, acts_a0, edges_a0 = _build_domain_a_instance(vocab, ep_idx=0)
    agent_a = ExperientialCognitiveAgent(
        arm_name="SPEACE_EXPERIENTIAL",
        operator_model=EmpiricalOperatorModel(acts_a0),
        alpha_local=alpha_local,
        tau_analogy=tau_analogy,
    )
    env_a0 = StatefulPlanningEnvironment(init_a0, acts_a0)
    rep_a0 = agent_a.solve_episode(
        env_a0,
        domain=vocab.domain_a,
        goal_state=goal_a0,
        domain_edges=edges_a0,
        consolidate_on_success=True,
        consolidate_skill_id=f"skill_{vocab.family_id}_A",
    )
    assert rep_a0.goal_reached

    rebind_successes = 0
    rebind_expansions = 0
    for ep in range(1, episodes_per_family + 1):
        init_ak, goal_ak, acts_ak, edges_ak = _build_domain_a_instance(vocab, ep_idx=ep)
        agent_a.operator_model = EmpiricalOperatorModel(acts_ak)
        env_ak = StatefulPlanningEnvironment(init_ak, acts_ak)
        rep_ak = agent_a.solve_episode(
            env_ak,
            domain=vocab.domain_a,
            goal_state=goal_ak,
            domain_edges=edges_ak,
            consolidate_on_success=False,
        )
        if rep_ak.goal_reached:
            rebind_successes += 1
        rebind_expansions += rep_ak.planner_expansions

    # --- Phase 2: Transfer to Non-Isomorphic B (EXPERIENTIAL vs AMNESIC) ---
    # Each of the `episodes_per_family` trials runs an independent 2-episode trajectory in B:
    # - Episode B.0: initial encounter in B (with 3 distractors + local refinement);
    # - Episode B.1: follow-up instance in B (verifying that AMNESIC also learns during B!).
    p2_exp_succ = 0
    p2_amn_succ = 0
    p2_exp_expansions = 0
    p2_amn_expansions = 0
    p2_distractors_ok = 0

    per_ep_axis3_exp: list[float] = []
    per_ep_axis3_amn: list[float] = []
    trained_exp_b: ExperientialCognitiveAgent | None = None

    for trial in range(episodes_per_family):
        exp_trial = agent_a.clone_from_checkpoint(
            new_arm_name="SPEACE_EXPERIENTIAL",
            repair_mode="selective",
        )
        amn_trial = ExperientialCognitiveAgent(
            arm_name="SPEACE_AMNESIC",
            operator_model=EmpiricalOperatorModel(()),
            alpha_local=alpha_local,
            tau_analogy=tau_analogy,
        )

        trial_exp_expansions = 0
        trial_amn_expansions = 0
        trial_exp_ok = True
        trial_amn_ok = True
        trial_dist_ok = True

        for sub_ep in range(2):
            ep_id = trial * 10 + sub_ep
            init_b, goal_b, acts_b, edges_b, _chain_b, dist_b = _build_domain_b_instance(
                vocab,
                ep_idx=ep_id,
                needs_local_refinement=True,
            )
            exp_trial.operator_model = EmpiricalOperatorModel(acts_b)
            amn_trial.operator_model = EmpiricalOperatorModel(acts_b)

            rep_exp = exp_trial.solve_episode(
                StatefulPlanningEnvironment(init_b, acts_b),
                domain=vocab.domain_b,
                goal_state=goal_b,
                domain_edges=edges_b,
                consolidate_on_success=True,
            )
            rep_amn = amn_trial.solve_episode(
                StatefulPlanningEnvironment(init_b, acts_b),
                domain=vocab.domain_b,
                goal_state=goal_b,
                domain_edges=edges_b,
                consolidate_on_success=True,
            )

            trial_exp_ok = trial_exp_ok and rep_exp.goal_reached
            trial_amn_ok = trial_amn_ok and rep_amn.goal_reached
            trial_exp_expansions += rep_exp.planner_expansions
            trial_amn_expansions += rep_amn.planner_expansions

            if sub_ep == 0 and not (
                rep_exp.analogy_trace is not None
                and rep_exp.analogy_trace.verification_passed
                and set(dist_b).issubset(set(rep_exp.analogy_trace.distractors_rejected))
            ):
                trial_dist_ok = False

        p2_exp_succ += int(trial_exp_ok)
        p2_amn_succ += int(trial_amn_ok)
        p2_exp_expansions += trial_exp_expansions
        p2_amn_expansions += trial_amn_expansions
        p2_distractors_ok += int(trial_dist_ok)

        per_ep_axis3_exp.append(
            (1.0 / (1.0 + trial_exp_expansions / 12.0)) if trial_exp_ok else 0.0
        )
        per_ep_axis3_amn.append(
            (1.0 / (1.0 + trial_amn_expansions / 12.0)) if trial_amn_ok else 0.0
        )
        trained_exp_b = exp_trial

    assert trained_exp_b is not None
    exp_agent_b = trained_exp_b

    # --- Phase 3: Rule Shift in B from Identical Pre-Shift Checkpoint ---
    p3a_sel_succ = 0
    p3a_glo_succ = 0
    p3a_sel_exp = 0
    p3a_glo_exp = 0
    p3b_spliced_exp = 0
    p3b_unrep_exp = 0
    p3c_abandon_ok = 0
    p3c_sel_recov = 0
    p3c_stub_succ = 0

    per_ep_axis4_sel: list[float] = []
    per_ep_axis4_ctrl: list[float] = []

    for ep in range(episodes_per_family):
        init_s, goal_s, acts_s, edges_s, (b0, b1, b2), _dist_s = _build_domain_b_instance(
            vocab, ep_idx=100 + ep, needs_local_refinement=True
        )
        exp_agent_b.operator_model = EmpiricalOperatorModel(acts_s)

        # Fork two identical clones BEFORE rule shift (neither knows which rule mutates!)
        clone_selective = exp_agent_b.clone_from_checkpoint(
            new_arm_name="SPEACE_SELECTIVE_REPAIR",
            repair_mode="selective",
        )
        clone_global = exp_agent_b.clone_from_checkpoint(
            new_arm_name="SPEACE_GLOBAL_REPLAN",
            repair_mode="global_replan",
        )

        # Phase 3a: Repairable mid-step rule mutation on op2(b1, b2)
        op2_name = format_structured_atom(vocab.ops_b[1], (b1, b2))
        mutated_op2_repairable = GOAPAction(
            name=op2_name,
            preconditions=frozenset(
                {
                    format_structured_atom(vocab.fluents_b[1], (b1,)),
                    format_structured_atom(vocab.link_rel_b, (b1, b2)),
                }
            ),
            add_effects=frozenset({format_structured_atom(vocab.latch_fluent_b, (b1,))}),
            cost=1.0,
        )
        env_base_3a = StatefulPlanningEnvironment(init_s, acts_s)
        env_base_3a.mutate_rule(mutated_op2_repairable)
        env_sel_3a = env_base_3a.clone()
        env_glo_3a = env_base_3a.clone()

        rep_sel_3a = clone_selective.solve_episode(
            env_sel_3a,
            domain=vocab.domain_b,
            goal_state=goal_s,
            domain_edges=edges_s,
            consolidate_on_success=True,
        )
        rep_glo_3a = clone_global.solve_episode(
            env_glo_3a,
            domain=vocab.domain_b,
            goal_state=goal_s,
            domain_edges=edges_s,
            consolidate_on_success=False,
        )
        p3a_sel_succ += int(rep_sel_3a.goal_reached)
        p3a_glo_succ += int(rep_glo_3a.goal_reached)
        p3a_sel_exp += rep_sel_3a.planner_expansions
        p3a_glo_exp += rep_glo_3a.planner_expansions

        # Phase 3b: Subsequent unseen variant (new entities 200+ep) under the mutated rule!
        init_v, goal_v, acts_v, edges_v, (_v0, v1, v2), _dist_v = _build_domain_b_instance(
            vocab, ep_idx=200 + ep, needs_local_refinement=True
        )
        op2_v_name = format_structured_atom(vocab.ops_b[1], (v1, v2))
        mutated_op2_v = GOAPAction(
            name=op2_v_name,
            preconditions=frozenset(
                {
                    format_structured_atom(vocab.fluents_b[1], (v1,)),
                    format_structured_atom(vocab.link_rel_b, (v1, v2)),
                }
            ),
            add_effects=frozenset({format_structured_atom(vocab.latch_fluent_b, (v1,))}),
            cost=1.0,
        )
        # Update operator definitions for the new variant entities (where op2 on v1,v2 also has the new rule)
        acts_v_updated = [mutated_op2_v if a.name == op2_v_name else a for a in acts_v]
        clone_selective.operator_model = EmpiricalOperatorModel(acts_v_updated)
        unrepaired_ctrl = exp_agent_b.clone_from_checkpoint(
            new_arm_name="SPEACE_GLOBAL_REPLAN_VARIANT",
            repair_mode="global_replan",
        )
        unrepaired_ctrl.operator_model = EmpiricalOperatorModel(acts_v)

        env_v_sel = StatefulPlanningEnvironment(init_v, acts_v)
        env_v_sel.mutate_rule(mutated_op2_v)
        env_v_unrep = env_v_sel.clone()

        rep_v_sel = clone_selective.solve_episode(
            env_v_sel,
            domain=vocab.domain_b,
            goal_state=goal_v,
            domain_edges=edges_v,
            consolidate_on_success=False,
        )
        rep_v_unrep = unrepaired_ctrl.solve_episode(
            env_v_unrep,
            domain=vocab.domain_b,
            goal_state=goal_v,
            domain_edges=edges_v,
            consolidate_on_success=False,
        )
        p3b_spliced_exp += rep_v_sel.planner_expansions
        p3b_unrep_exp += rep_v_unrep.planner_expansions

        # Phase 3c: Anti-Einstellung Negative Control (Suffix-Invalidating Rule Shift!)
        clone_sel_3c = exp_agent_b.clone_from_checkpoint(
            new_arm_name="SPEACE_SELECTIVE_REPAIR_3C",
            repair_mode="selective",
        )
        clone_stubborn_3c = exp_agent_b.clone_from_checkpoint(
            new_arm_name="STUBBORN_REUSE_CONTROL",
            repair_mode="stubborn_reuse",
        )
        mutated_op2_blocker = GOAPAction(
            name=op2_name,
            preconditions=frozenset(
                {
                    format_structured_atom(vocab.fluents_b[1], (b1,)),
                    format_structured_atom(vocab.link_rel_b, (b1, b2)),
                }
            ),
            add_effects=frozenset({format_structured_atom("terminal_fault", (b1,))}),
            del_effects=frozenset({format_structured_atom("channel_intact", (b1,))}),
            cost=1.0,
        )
        env_base_3c = StatefulPlanningEnvironment(init_s, acts_s)
        env_base_3c.mutate_rule(mutated_op2_blocker)

        rep_sel_3c = clone_sel_3c.solve_episode(
            env_base_3c.clone(),
            domain=vocab.domain_b,
            goal_state=goal_s,
            domain_edges=edges_s,
            consolidate_on_success=False,
        )
        rep_stub_3c = clone_stubborn_3c.solve_episode(
            env_base_3c.clone(),
            domain=vocab.domain_b,
            goal_state=goal_s,
            domain_edges=edges_s,
            consolidate_on_success=False,
        )
        abandoned_correctly = rep_sel_3c.repair_decision == "ABANDON_MACRO_AND_REPLAN"
        p3c_abandon_ok += int(abandoned_correctly)
        p3c_sel_recov += int(rep_sel_3c.goal_reached)
        p3c_stub_succ += int(rep_stub_3c.goal_reached)

        # Composite Axis-4 episode score: combines 3a repair efficiency, 3b variant transfer, and 3c anti-Einstellung
        s_3a_sel = (
            1.0 / (1.0 + rep_sel_3a.planner_expansions / 12.0) if rep_sel_3a.goal_reached else 0.0
        )
        s_3a_glo = (
            1.0 / (1.0 + rep_glo_3a.planner_expansions / 12.0) if rep_glo_3a.goal_reached else 0.0
        )
        s_3b_sel = (
            1.0 / (1.0 + rep_v_sel.planner_expansions / 12.0) if rep_v_sel.goal_reached else 0.0
        )
        s_3b_glo = (
            1.0 / (1.0 + rep_v_unrep.planner_expansions / 12.0) if rep_v_unrep.goal_reached else 0.0
        )
        s_3c_sel = 1.0 if (abandoned_correctly and rep_sel_3c.goal_reached) else 0.0
        s_3c_ctrl = 0.5 * (1.0 if rep_stub_3c.goal_reached else 0.0) + 0.5 * s_3a_glo

        per_ep_axis4_sel.append((s_3a_sel + s_3b_sel + s_3c_sel) / 3.0)
        per_ep_axis4_ctrl.append((s_3a_glo + s_3b_glo + s_3c_ctrl) / 3.0)

    k = float(episodes_per_family)
    summary = FamilyBenchmarkSummary(
        family_id=vocab.family_id,
        split=vocab.split,
        phase1_rebind_success_rate=rebind_successes / k,
        phase1_rebind_expansions=rebind_expansions,
        phase2_experiential_success_rate=p2_exp_succ / k,
        phase2_amnesic_success_rate=p2_amn_succ / k,
        phase2_experiential_expansions=p2_exp_expansions,
        phase2_amnesic_expansions=p2_amn_expansions,
        phase2_distractor_rejection_rate=p2_distractors_ok / k,
        phase3a_selective_repair_success_rate=p3a_sel_succ / k,
        phase3a_global_replan_success_rate=p3a_glo_succ / k,
        phase3a_selective_expansions=p3a_sel_exp,
        phase3a_global_expansions=p3a_glo_exp,
        phase3b_variant_spliced_expansions=p3b_spliced_exp,
        phase3b_variant_unrepaired_expansions=p3b_unrep_exp,
        phase3c_selective_abandon_accuracy=p3c_abandon_ok / k,
        phase3c_selective_recovery_rate=p3c_sel_recov / k,
        phase3c_stubborn_success_rate=p3c_stub_succ / k,
    )
    return summary, per_ep_axis3_exp, per_ep_axis3_amn, per_ep_axis4_sel, per_ep_axis4_ctrl


def run_t252_t253_campaign(
    *,
    seed: int = 2026,
    n_resamples: int = 1000,
    prereg_path: Path | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    """Verify preregistration locks, calibrate on F1–F2, and evaluate once on held-out F3–F5."""
    prereg = verify_t252_preregistration(prereg_path)
    cal_ids = set(prereg["pre_calibration"]["calibration_families"])
    ho_ids = set(prereg["pre_evaluation"]["held_out_families"])
    eps_per_fam = int(prereg["pre_evaluation"]["episodes_per_family"])

    cal_fams = [f for f in PROBLEM_FAMILIES if f.family_id in cal_ids]
    ho_fams = [f for f in PROBLEM_FAMILIES if f.family_id in ho_ids]

    # 1. Calibrate (alpha_local, tau_analogy) exclusively on calibration families F1, F2
    best_obj = -1.0
    best_alpha = 0.25
    best_tau = 0.50
    for alpha_c in prereg["pre_calibration"]["parameter_grid"]["alpha_local"]:
        for tau_c in prereg["pre_calibration"]["parameter_grid"]["tau_analogy"]:
            cal_runs = [
                _evaluate_family(
                    f, alpha_local=float(alpha_c), tau_analogy=float(tau_c), episodes_per_family=3
                )[0]
                for f in cal_fams
            ]
            if any(r.phase2_experiential_success_rate < 1.0 for r in cal_runs):
                continue
            if any(r.phase3a_selective_repair_success_rate < 1.0 for r in cal_runs):
                continue
            if any(r.phase3c_selective_abandon_accuracy < 1.0 for r in cal_runs):
                continue
            p2_red = 1.0 - (
                sum(r.phase2_experiential_expansions for r in cal_runs)
                / max(sum(r.phase2_amnesic_expansions for r in cal_runs), 1)
            )
            p3_red = 1.0 - (
                sum(r.phase3a_selective_expansions for r in cal_runs)
                / max(sum(r.phase3a_global_expansions for r in cal_runs), 1)
            )
            score = 0.5 * p2_red + 0.5 * p3_red
            if score > best_obj:
                best_obj = score
                best_alpha = float(alpha_c)
                best_tau = float(tau_c)

    # 2. Evaluate ONCE on held-out unseen problem families F3, F4, F5
    ho_summaries: list[FamilyBenchmarkSummary] = []
    axis3_exp_vec: list[float] = []
    axis3_amn_vec: list[float] = []
    axis4_sel_vec: list[float] = []
    axis4_ctrl_vec: list[float] = []

    for fam in ho_fams:
        s_fam, v3_e, v3_a, v4_s, v4_c = _evaluate_family(
            fam,
            alpha_local=best_alpha,
            tau_analogy=best_tau,
            episodes_per_family=eps_per_fam,
        )
        ho_summaries.append(s_fam)
        axis3_exp_vec.extend(v3_e)
        axis3_amn_vec.extend(v3_a)
        axis4_sel_vec.extend(v4_s)
        axis4_ctrl_vec.extend(v4_c)

    p1_succ = float(np.mean([s.phase1_rebind_success_rate for s in ho_summaries]))
    p1_exp_total = sum(s.phase1_rebind_expansions for s in ho_summaries)

    p2_exp_total = sum(s.phase2_experiential_expansions for s in ho_summaries)
    p2_amn_total = sum(s.phase2_amnesic_expansions for s in ho_summaries)
    p2_exp_red = 1.0 - (p2_exp_total / max(p2_amn_total, 1))
    p2_dist_rej = float(np.mean([s.phase2_distractor_rejection_rate for s in ho_summaries]))

    p3a_sel_total = sum(s.phase3a_selective_expansions for s in ho_summaries)
    p3a_glo_total = sum(s.phase3a_global_expansions for s in ho_summaries)
    p3a_exp_red = 1.0 - (p3a_sel_total / max(p3a_glo_total, 1))

    p3b_spl_total = sum(s.phase3b_variant_spliced_expansions for s in ho_summaries)
    p3b_unr_total = sum(s.phase3b_variant_unrepaired_expansions for s in ho_summaries)
    p3b_exp_red = 1.0 - (p3b_spl_total / max(p3b_unr_total, 1))

    p3c_abandon_acc = float(np.mean([s.phase3c_selective_abandon_accuracy for s in ho_summaries]))
    p3c_recovery_rate = float(np.mean([s.phase3c_selective_recovery_rate for s in ho_summaries]))
    p3c_stubborn_rate = float(np.mean([s.phase3c_stubborn_success_rate for s in ho_summaries]))

    axis3_ci = paired_bootstrap_ci(axis3_amn_vec, axis3_exp_vec, n_resamples=n_resamples, seed=seed)
    axis4_ci = paired_bootstrap_ci(
        axis4_ctrl_vec, axis4_sel_vec, n_resamples=n_resamples, seed=seed
    )

    gates = {
        "preregistration_locks_verified": True,
        "phase1_rebind_success_100pct": p1_succ >= 1.0 and p1_exp_total == 0,
        "phase2_transfer_expansion_reduction_ge_50pct": p2_exp_red >= 0.50,
        "phase2_distractor_rejection_100pct": p2_dist_rej >= 1.0,
        "phase2_bootstrap_ci95_strictly_positive": axis3_ci[1] > 0.0,
        "phase3a_selective_repair_reduction_ge_40pct": p3a_exp_red >= 0.40,
        "phase3b_spliced_variant_reduction_ge_80pct": p3b_exp_red >= 0.80,
        "phase3c_anti_einstellung_abandon_100pct": p3c_abandon_acc >= 1.0
        and p3c_recovery_rate >= 1.0,
        "phase3c_stubborn_reuse_fails_as_expected": p3c_stubborn_rate == 0.0,
        "phase3_bootstrap_ci95_strictly_positive": axis4_ci[1] > 0.0,
    }
    all_passed = all(gates.values())

    report: dict[str, Any] = {
        "spec": "T252_T253",
        "seed": seed,
        "preregistration_locks": {
            "pre_calibration_sha256": prereg["pre_calibration"]["lock_sha256"],
            "pre_evaluation_sha256": prereg["pre_evaluation"]["lock_sha256"],
            "verified": True,
        },
        "calibrated_parameters": {
            "alpha_local": best_alpha,
            "tau_analogy": best_tau,
        },
        "held_out_families": [asdict(s) for s in ho_summaries],
        "held_out_aggregate": {
            "phase1_rebind_success_rate": round(p1_succ, 4),
            "phase1_rebind_total_expansions": p1_exp_total,
            "phase2_experiential_total_expansions": p2_exp_total,
            "phase2_amnesic_total_expansions": p2_amn_total,
            "phase2_expansion_reduction_ratio": round(p2_exp_red, 4),
            "phase2_distractor_rejection_rate": round(p2_dist_rej, 4),
            "phase3a_selective_repair_expansions": p3a_sel_total,
            "phase3a_global_replan_expansions": p3a_glo_total,
            "phase3a_repair_expansion_reduction_ratio": round(p3a_exp_red, 4),
            "phase3b_spliced_variant_expansions": p3b_spl_total,
            "phase3b_unrepaired_variant_expansions": p3b_unr_total,
            "phase3b_variant_expansion_reduction_ratio": round(p3b_exp_red, 4),
            "phase3c_anti_einstellung_abandon_accuracy": round(p3c_abandon_acc, 4),
            "phase3c_selective_recovery_rate": round(p3c_recovery_rate, 4),
            "phase3c_stubborn_reuse_success_rate": round(p3c_stubborn_rate, 4),
            "axis3_experiential_mean": round(float(np.mean(axis3_exp_vec)), 4),
            "axis3_amnesic_mean": round(float(np.mean(axis3_amn_vec)), 4),
            "axis3_lift_ci95": [round(x, 4) for x in axis3_ci],
            "axis4_selective_mean": round(float(np.mean(axis4_sel_vec)), 4),
            "axis4_control_mean": round(float(np.mean(axis4_ctrl_vec)), 4),
            "axis4_lift_ci95": [round(x, 4) for x in axis4_ci],
        },
        "acceptance_gates": gates,
        "all_gates_passed": all_passed,
        "t252_t253_decision": "keep" if all_passed else "revise",
    }

    if output_dir is not None:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "t252_t253_benchmark_report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
    return report


__all__ = [
    "FamilyBenchmarkSummary",
    "FamilyVocabulary",
    "PROBLEM_FAMILIES",
    "run_t252_t253_campaign",
    "verify_t252_preregistration",
]
