"""T259 — Adaptive Dual-Speed Natural-Language Belief Revision Benchmark.

Evaluates the unification of ``DualSpeedCognitiveLoop`` (``T251``) and
``TypedMultiRoleNLGroundingPipeline`` (``T257``) across a balanced 18-episode
held-out Italian workload (9 routine affirmative dispatches ``R0-N1..N3`` +
9 mid-episode corrections/emergencies/negations ``R1-P1, R2, R3`` across
unseen families ``F3, F4, F5``):

  1. ``ALWAYS_FAST_SINGLE_SHOT``: compact single-pass extraction everywhere.
  2. ``ALWAYS_SLOW_T257``: multi-role ``EXTRACTOR + CRITIC`` everywhere.
  3. ``ADAPTIVE_DUAL_SPEED_T259``: ``DualSpeedCognitiveLoop.step_nl_belief_revision``
     routing routine affirmative dispatches through ``fast`` and corrections/negations
     through ``slow``.
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

from ..bridge.dual_speed import DualSpeedCognitiveLoop
from ..bridge.grounding import SymbolicGroundingAdapter, apply_belief_revision
from ..bridge.simulated_sensor import run_coro_isolated
from ..bridge.typed_nl_pipeline import TypedMultiRoleNLGroundingPipeline
from ..edd_cvt.ilf import InformationalLogicalField
from ..metabolism.cognitive_cost_model import QuantumCostModel, QuantumOperation
from ..self_improvement_cortex.macro_skills import (
    EmpiricalOperatorModel,
    StatefulPlanningEnvironment,
    format_structured_atom,
)
from ..spiking_brain.cortex import SpikingBrainCortex
from ..spiking_brain.factory import make_spiking_brain
from ..spiking_brain.truth_engine import TruthEngine
from ..spiking_brain.types import ThinkResult
from .evaluator import paired_bootstrap_ci
from .t252_t253_benchmark import PROBLEM_FAMILIES, _build_domain_b_instance
from .t255_nl_live_benchmark import (
    SimulatedNLTransducerBackend,
    T255NLEpisode,
    _build_episode_symbol_registry,
    _format_extraction_prompt,
    _relevant_dynamic_facts,
    _set_f1,
    _train_source_domain_agents,
    build_t255_nl_episodes,
)


@dataclass(frozen=True)
class T259EpisodeTrace:
    """Audit trace of one episode under Always-Fast, Always-Slow, or Adaptive Dual-Speed."""

    episode_id: str
    family_id: str
    workload_kind: str  # "routine_affirmative" | "complex_revision"
    arm: str
    tier_selected: str
    escalated_after_fast: bool
    extraction_f1: float
    retraction_f1: float
    repair_decision: str
    safe_end_to_end_success: bool
    invalid_actions_attempted: int
    planner_expansions: int
    llm_tokens_out: int
    wall_latency_ms: float
    modeled_energy_j: float


def build_t259_mixed_nl_workload() -> list[tuple[str, T255NLEpisode]]:
    """Build 18 balanced held-out NL episodes (9 routine affirmative + 9 complex revision)."""
    held_fams = [f for f in PROBLEM_FAMILIES if f.split == "held_out"]
    base_t255 = build_t255_nl_episodes()

    routine_texts: dict[str, Any] = {
        "F3_quorum_handoff": lambda n0, n1, d0: [
            (
                "N1",
                f"Dispaccio telemetrico regolare: allarme doppler attivo su {n0} e canale primario "
                f"su {n1} integro (modulo {d0} isolato per collaudo).",
            ),
            (
                "N2",
                f"Stato iniziale confermato dalla sala controllo: allarme doppler su {n0} attivo, "
                f"canale primario {n1} integro; {d0} è solo un modulo di test.",
            ),
            (
                "N3",
                f"Avvio procedura antenna nominale: rilevato allarme doppler attivo su {n0} con "
                f"canale primario {n1} integro ({d0} scollegato).",
            ),
        ],
        "F4_cryo_purification": lambda n0, n1, d0: [
            (
                "N1",
                f"Telemetria camera bianca regolare: allarme particolato iniziale attivo su {n0} "
                f"e condotto primario su {n1} integro (collettore {d0} fuori linea).",
            ),
            (
                "N2",
                f"Rapporto turno nominale: allarme particolato su {n0} presente e condotto primario "
                f"{n1} integro; il ramo {d0} è solo un test.",
            ),
            (
                "N3",
                f"Avvio ciclo purificazione standard: allarme particolato attivo su {n0}, condotto "
                f"primario su {n1} integro ({d0} in manutenzione).",
            ),
        ],
        "F5_containment_airlock": lambda n0, n1, d0: [
            (
                "N1",
                f"Dispaccio ponte sottomarino regolare: differenziale di pressione attivo su {n0} "
                f"e portello primario su {n1} integro (boccaporto {d0} chiuso per test).",
            ),
            (
                "N2",
                f"Stato iniziale confermato dai sensori: differenziale di pressione su {n0} attivo "
                f"con portello primario {n1} integro; {d0} irrilevante.",
            ),
            (
                "N3",
                f"Avvio sequenza nominale ROV: differenziale di pressione attivo su {n0} e portello "
                f"primario su {n1} integro ({d0} isolato per collaudo).",
            ),
        ],
    }

    workload: list[tuple[str, T255NLEpisode]] = []

    # 1. Add 9 routine affirmative dispatches (3 unseen phrasings per held-out family)
    for fam_idx, vocab in enumerate(held_fams):
        ep_num = 50 + fam_idx
        init_b, goal_b, acts_b, edges_b, (n0, n1, n2), (d0, _d1, _d2) = _build_domain_b_instance(
            vocab, ep_idx=ep_num, needs_local_refinement=True
        )
        sb0 = f"b{ep_num}_sb0"
        trig, f1, f2, _f3, _g = vocab.fluents_b
        latch_fl = vocab.latch_fluent_b
        mutex_b = (
            (format_structured_atom(latch_fl, (n1,)), format_structured_atom(f2, (n1,))),
            (
                format_structured_atom("terminal_fault", (n1,)),
                format_structured_atom("channel_intact", (n1,)),
            ),
        )
        ref_ep = next(e for e in base_t255 if e.family_id == vocab.family_id)
        sb_ready = format_structured_atom("standby_ready", (sb0,))
        prior_r0 = init_b - {
            format_structured_atom(trig, (n0,)),
            format_structured_atom(trig, (d0,)),
            sb_ready,
        }
        obs_r0 = frozenset(
            {
                format_structured_atom(trig, (n0,)),
                format_structured_atom("channel_intact", (n1,)),
            }
        )
        true_r0 = prior_r0 | obs_r0
        for tag, msg in routine_texts[vocab.family_id](n0, n1, d0):
            workload.append(
                (
                    "routine_affirmative",
                    T255NLEpisode(
                        episode_id=f"{vocab.family_id}-R0-{tag}",
                        family_id=vocab.family_id,
                        domain_b=vocab.domain_b,
                        category="negated_alarm_with_distractors",
                        paraphrase_group=f"{vocab.family_id}-R0",
                        paraphrase_variant=tag,
                        nl_operator_message=msg,
                        prior_assumed_state=prior_r0,
                        true_world_state=true_r0,
                        oracle_observed_facts=obs_r0,
                        oracle_retracted_facts=frozenset(),
                        goal_state=goal_b,
                        predicate_glosses=ref_ep.predicate_glosses,
                        domain_actions=tuple(acts_b),
                        nominal_domain_actions=tuple(acts_b),
                        domain_edges=tuple(edges_b),
                        expected_repair_decision="NO_REPAIR_NEEDED",
                        domain_mutex_pairs=mutex_b,
                    ),
                )
            )

    # 2. Add 9 complex revision/emergency/negation episodes (R1-P1, R2-ABANDON, R3-NEGATION per family)
    for ep in base_t255:
        if ep.paraphrase_variant in {"P1", "SINGLE"}:
            workload.append(("complex_revision", ep))

    return workload


class _SimulatedDualSpeedNLBackend(SimulatedNLTransducerBackend):
    """Offline CI transducer mirroring real 3B single-pass retraction omission vs multi-role."""

    def think(
        self,
        prompt: str,
        coherence_phi: float = 1.0,
        n_tokens: int = 160,
        history: Sequence[ThinkResult] | None = None,
    ) -> ThinkResult:
        base = super().think(
            prompt, coherence_phi=coherence_phi, n_tokens=n_tokens, history=history
        )
        if "--- EXTRACTOR ---" in prompt:
            return base
        # Single-pass prompt without multi-role framing omits non-monotonic retractions
        matched_ep = next((e for e in self._episodes if e.nl_operator_message in prompt), None)
        if matched_ep is not None and matched_ep.oracle_retracted_facts:
            txt = json.dumps(
                {
                    "observed_facts": sorted(matched_ep.oracle_observed_facts),
                    "retracted_facts": [],
                }
            )
            return ThinkResult(
                text=txt,
                confidence=base.confidence,
                belief=base.belief,
                spikes=base.spikes,
                plasticity=base.plasticity,
                n_tokens=min(n_tokens, max(10, len(txt) // 4)),
                latency_s=0.0004,
                metadata=base.metadata,
            )
        return base


def run_t259_dual_speed_nl_benchmark(
    *,
    live_brain: bool = False,
    endpoint: str | None = None,
    timeout_s: float = 60.0,
    fast_max_tokens: int = 80,
    slow_max_tokens: int = 256,
    seed: int = 2026,
    n_resamples: int = 1000,
    output_path: Path | None = None,
) -> dict[str, Any]:
    """Run the 3-arm T259 Dual-Speed NL benchmark (Always-Fast vs Always-Slow vs Adaptive)."""
    workload = build_t259_mixed_nl_workload()
    all_eps = [ep for _, ep in workload]
    trained = _train_source_domain_agents()
    cost_model = QuantumCostModel()

    if live_brain or endpoint:
        if endpoint:
            os.environ["Q_SPEACE_BRAIN_ENDPOINT"] = endpoint
        if not os.environ.get("Q_SPEACE_BRAIN_ENDPOINT", "").strip():
            os.environ["Q_SPEACE_BRAIN_ENDPOINT"] = "http://localhost:8002"
        backend: Any = make_spiking_brain(timeout_s=timeout_s, seed=seed)
    else:
        backend = _SimulatedDualSpeedNLBackend(all_eps, seed=seed)

    fast_traces: list[T259EpisodeTrace] = []
    slow_traces: list[T259EpisodeTrace] = []
    adap_traces: list[T259EpisodeTrace] = []

    async def _run_all() -> None:
        await backend.load()
        try:
            for wk_kind, ep in workload:
                base_ag = trained[ep.family_id]

                # --- Arm 1: ALWAYS_FAST_SINGLE_SHOT ---
                t0_f = time.perf_counter()
                ilf_f = InformationalLogicalField(
                    coherence_phi=0.85, q_star_ema=0.5, coherence_phi_ema=0.5
                )
                cortex_f = SpikingBrainCortex(
                    backend=backend,
                    ilf=ilf_f,
                    truth_engine=TruthEngine(),
                    sevo_threshold=0.5,
                    min_coherence_phi=0.01,
                    min_confidence=0.05,
                )
                reg_f = _build_episode_symbol_registry(ep, with_mutex=False)
                adapter_f = SymbolicGroundingAdapter(reg_f, tau_ground=0.70)
                rep_f = await cortex_f.tick(
                    _format_extraction_prompt(ep), n_tokens=max(fast_max_tokens, 96)
                )
                txt_f = rep_f.result.text if rep_f.result is not None else ""
                tok_f = int(rep_f.result.n_tokens) if rep_f.result is not None else 0
                g_f = adapter_f.ground(txt_f, calibrated_confidence=rep_f.confidence)
                s_rev_f = apply_belief_revision(ep.prior_assumed_state, g_f)
                ag_f = base_ag.clone_from_checkpoint(
                    new_arm_name="ALWAYS_FAST_SINGLE_SHOT", repair_mode="selective"
                )
                ag_f.operator_model = EmpiricalOperatorModel(ep.domain_actions)
                exec_f = ag_f.execute_from_revised_belief(
                    StatefulPlanningEnvironment(ep.true_world_state, ep.domain_actions),
                    revised_belief_state=s_rev_f,
                    domain=ep.domain_b,
                    goal_state=ep.goal_state,
                    domain_edges=ep.domain_edges,
                    mapping_actions=ep.nominal_domain_actions,
                )
                lat_f = (time.perf_counter() - t0_f) * 1000.0
                e_f = float(rep_f.energy_w) + float(
                    cost_model.energy_watts(
                        QuantumOperation(
                            num_qubits=4,
                            num_gates=24 + 6 * exec_f.planner_expansions,
                            entanglement_depth=2,
                            decoherence_budget=0.10,
                        )
                    )
                )
                fast_traces.append(
                    T259EpisodeTrace(
                        episode_id=ep.episode_id,
                        family_id=ep.family_id,
                        workload_kind=wk_kind,
                        arm="ALWAYS_FAST_SINGLE_SHOT",
                        tier_selected="fast",
                        escalated_after_fast=False,
                        extraction_f1=round(
                            _set_f1(
                                _relevant_dynamic_facts(s_rev_f, ep),
                                _relevant_dynamic_facts(ep.true_world_state, ep),
                            ),
                            4,
                        ),
                        retraction_f1=round(
                            _set_f1(g_f.retracted_facts, ep.oracle_retracted_facts), 4
                        ),
                        repair_decision=exec_f.repair_decision,
                        safe_end_to_end_success=exec_f.safe_execution,
                        invalid_actions_attempted=exec_f.invalid_actions_attempted,
                        planner_expansions=exec_f.planner_expansions,
                        llm_tokens_out=tok_f,
                        wall_latency_ms=round(lat_f, 3),
                        modeled_energy_j=round(e_f, 3),
                    )
                )

                # --- Arm 2: ALWAYS_SLOW_T257 ---
                t0_s = time.perf_counter()
                ilf_s = InformationalLogicalField(
                    coherence_phi=0.85, q_star_ema=0.5, coherence_phi_ema=0.5
                )
                cortex_s = SpikingBrainCortex(
                    backend=backend,
                    ilf=ilf_s,
                    truth_engine=TruthEngine(),
                    sevo_threshold=0.5,
                    min_coherence_phi=0.01,
                    min_confidence=0.05,
                )
                reg_s = _build_episode_symbol_registry(ep, with_mutex=True)
                pipe_s = TypedMultiRoleNLGroundingPipeline(reg_s, tau_ground=0.70)
                prompt_s = pipe_s.build_prompt(
                    operator_message=ep.nl_operator_message,
                    prior_state=ep.prior_assumed_state,
                    predicate_glosses=ep.predicate_glosses,
                )
                rep_s = await cortex_s.tick(prompt_s, n_tokens=slow_max_tokens)
                txt_s = rep_s.result.text if rep_s.result is not None else ""
                tok_s = int(rep_s.result.n_tokens) if rep_s.result is not None else 0
                res_s = pipe_s.run(
                    raw_llm_output=txt_s,
                    operator_message=ep.nl_operator_message,
                    prior_state=ep.prior_assumed_state,
                    predicate_glosses=ep.predicate_glosses,
                    calibrated_confidence=rep_s.confidence,
                    coherence_phi=float(ilf_s.coherence_phi),
                )
                ag_s = base_ag.clone_from_checkpoint(
                    new_arm_name="ALWAYS_SLOW_T257", repair_mode="selective"
                )
                ag_s.operator_model = EmpiricalOperatorModel(ep.domain_actions)
                exec_s = ag_s.execute_from_revised_belief(
                    StatefulPlanningEnvironment(ep.true_world_state, ep.domain_actions),
                    revised_belief_state=res_s.revised_belief_state,
                    domain=ep.domain_b,
                    goal_state=ep.goal_state,
                    domain_edges=ep.domain_edges,
                    mapping_actions=ep.nominal_domain_actions,
                )
                lat_s = (time.perf_counter() - t0_s) * 1000.0
                e_s = float(rep_s.energy_w) + float(
                    cost_model.energy_watts(
                        QuantumOperation(
                            num_qubits=4,
                            num_gates=48 + 6 * exec_s.planner_expansions,
                            entanglement_depth=2,
                            decoherence_budget=0.08,
                        )
                    )
                )
                slow_traces.append(
                    T259EpisodeTrace(
                        episode_id=ep.episode_id,
                        family_id=ep.family_id,
                        workload_kind=wk_kind,
                        arm="ALWAYS_SLOW_T257",
                        tier_selected="slow",
                        escalated_after_fast=False,
                        extraction_f1=round(
                            _set_f1(
                                _relevant_dynamic_facts(res_s.revised_belief_state, ep),
                                _relevant_dynamic_facts(ep.true_world_state, ep),
                            ),
                            4,
                        ),
                        retraction_f1=round(
                            _set_f1(res_s.effective_retracted_facts, ep.oracle_retracted_facts), 4
                        ),
                        repair_decision=exec_s.repair_decision,
                        safe_end_to_end_success=exec_s.safe_execution,
                        invalid_actions_attempted=exec_s.invalid_actions_attempted,
                        planner_expansions=exec_s.planner_expansions,
                        llm_tokens_out=tok_s,
                        wall_latency_ms=round(lat_s, 3),
                        modeled_energy_j=round(e_s, 3),
                    )
                )

                # --- Arm 3: ADAPTIVE_DUAL_SPEED_T259 ---
                t0_a = time.perf_counter()
                ilf_a = InformationalLogicalField(
                    coherence_phi=0.85, q_star_ema=0.5, coherence_phi_ema=0.5
                )
                cortex_a = SpikingBrainCortex(
                    backend=backend,
                    ilf=ilf_a,
                    truth_engine=TruthEngine(),
                    sevo_threshold=0.5,
                    min_coherence_phi=0.01,
                    min_confidence=0.05,
                )
                reg_a = _build_episode_symbol_registry(ep, with_mutex=True)
                loop_a = DualSpeedCognitiveLoop(
                    cortex=cortex_a,
                    grounding=SymbolicGroundingAdapter(reg_a, tau_ground=0.70),
                    tau_surprise=0.35,
                    tau_conf=0.55,
                )
                rec_a = await loop_a.step_nl_belief_revision(
                    operator_message=ep.nl_operator_message,
                    prior_state=ep.prior_assumed_state,
                    predicate_glosses=ep.predicate_glosses,
                    request_id=ep.episode_id,
                    fast_max_tokens=fast_max_tokens,
                    slow_max_tokens=slow_max_tokens,
                )
                ag_a = base_ag.clone_from_checkpoint(
                    new_arm_name="ADAPTIVE_DUAL_SPEED_T259", repair_mode="selective"
                )
                ag_a.operator_model = EmpiricalOperatorModel(ep.domain_actions)
                exec_a = ag_a.execute_from_revised_belief(
                    StatefulPlanningEnvironment(ep.true_world_state, ep.domain_actions),
                    revised_belief_state=rec_a.revised_belief_state,
                    domain=ep.domain_b,
                    goal_state=ep.goal_state,
                    domain_edges=ep.domain_edges,
                    mapping_actions=ep.nominal_domain_actions,
                )
                lat_a = (time.perf_counter() - t0_a) * 1000.0
                base_gates = 24 if rec_a.tier_selected == "fast" else 48
                e_a = float(rec_a.modeled_energy_j) + float(
                    cost_model.energy_watts(
                        QuantumOperation(
                            num_qubits=4,
                            num_gates=base_gates + 6 * exec_a.planner_expansions,
                            entanglement_depth=2,
                            decoherence_budget=0.08,
                        )
                    )
                )
                adap_traces.append(
                    T259EpisodeTrace(
                        episode_id=ep.episode_id,
                        family_id=ep.family_id,
                        workload_kind=wk_kind,
                        arm="ADAPTIVE_DUAL_SPEED_T259",
                        tier_selected=rec_a.tier_selected,
                        escalated_after_fast=rec_a.escalated_after_fast,
                        extraction_f1=round(
                            _set_f1(
                                _relevant_dynamic_facts(rec_a.revised_belief_state, ep),
                                _relevant_dynamic_facts(ep.true_world_state, ep),
                            ),
                            4,
                        ),
                        retraction_f1=round(
                            _set_f1(rec_a.effective_retracted_facts, ep.oracle_retracted_facts), 4
                        ),
                        repair_decision=exec_a.repair_decision,
                        safe_end_to_end_success=exec_a.safe_execution,
                        invalid_actions_attempted=exec_a.invalid_actions_attempted,
                        planner_expansions=exec_a.planner_expansions,
                        llm_tokens_out=rec_a.llm_tokens_out,
                        wall_latency_ms=round(lat_a, 3),
                        modeled_energy_j=round(e_a, 3),
                    )
                )
        finally:
            await backend.shutdown()

    run_coro_isolated(_run_all, timeout_s=max(240.0, len(workload) * timeout_s * 3.5))

    def _summarize(rows: Sequence[T259EpisodeTrace]) -> dict[str, Any]:
        safe_v = [1.0 if r.safe_end_to_end_success else 0.0 for r in rows]
        fast_n = sum(1 for r in rows if r.tier_selected == "fast")
        return {
            "n_episodes": len(rows),
            "safe_end_to_end_success_rate": round(float(np.mean(safe_v)), 4),
            "fast_tier_share": round(fast_n / max(1, len(rows)), 4),
            "fast_turns": fast_n,
            "slow_turns": len(rows) - fast_n,
            "escalated_after_fast_count": sum(1 for r in rows if r.escalated_after_fast),
            "mean_extraction_f1": round(float(np.mean([r.extraction_f1 for r in rows])), 4),
            "total_invalid_actions": sum(r.invalid_actions_attempted for r in rows),
            "total_planner_expansions": sum(r.planner_expansions for r in rows),
            "total_llm_tokens_out": sum(r.llm_tokens_out for r in rows),
            "mean_wall_latency_ms": round(float(np.mean([r.wall_latency_ms for r in rows])), 3),
            "routine_mean_latency_ms": round(
                float(
                    np.mean(
                        [
                            r.wall_latency_ms
                            for r in rows
                            if r.workload_kind == "routine_affirmative"
                        ]
                    )
                ),
                3,
            ),
            "total_modeled_energy_j": round(float(np.sum([r.modeled_energy_j for r in rows])), 3),
        }

    sum_fast = _summarize(fast_traces)
    sum_slow = _summarize(slow_traces)
    sum_adap = _summarize(adap_traces)

    safe_fast_vec = [1.0 if r.safe_end_to_end_success else 0.0 for r in fast_traces]
    safe_adap_vec = [1.0 if r.safe_end_to_end_success else 0.0 for r in adap_traces]
    lift_adap_vs_fast = paired_bootstrap_ci(
        safe_fast_vec, safe_adap_vec, n_resamples=n_resamples, seed=seed
    )

    tok_red = 1.0 - (sum_adap["total_llm_tokens_out"] / max(1, sum_slow["total_llm_tokens_out"]))
    lat_red = 1.0 - (sum_adap["mean_wall_latency_ms"] / max(1e-6, sum_slow["mean_wall_latency_ms"]))
    routine_lat_red = 1.0 - (
        sum_adap["routine_mean_latency_ms"] / max(1e-6, sum_slow["routine_mean_latency_ms"])
    )

    gates_ok = (
        sum_adap["safe_end_to_end_success_rate"] >= sum_slow["safe_end_to_end_success_rate"]
        and sum_adap["safe_end_to_end_success_rate"] > sum_fast["safe_end_to_end_success_rate"]
        and sum_adap["total_invalid_actions"] == 0
        and tok_red >= 0.25
    )

    report: dict[str, Any] = {
        "spec": "T259",
        "seed": seed,
        "live_brain_used": bool(live_brain or endpoint),
        "n_episodes": len(workload),
        "conditions": {
            "ALWAYS_FAST_SINGLE_SHOT": sum_fast,
            "ALWAYS_SLOW_T257": sum_slow,
            "ADAPTIVE_DUAL_SPEED_T259": sum_adap,
        },
        "comparisons": {
            "safe_success_lift_adaptive_vs_always_fast": [round(x, 4) for x in lift_adap_vs_fast],
            "accuracy_delta_adaptive_vs_always_slow": round(
                sum_adap["safe_end_to_end_success_rate"] - sum_slow["safe_end_to_end_success_rate"],
                4,
            ),
            "token_reduction_adaptive_vs_always_slow": round(tok_red, 4),
            "mean_latency_reduction_adaptive_vs_always_slow": round(lat_red, 4),
            "routine_latency_reduction_adaptive_vs_always_slow": round(routine_lat_red, 4),
        },
        "all_gates_passed": gates_ok,
        "all_traces": {
            "ADAPTIVE_DUAL_SPEED_T259": [asdict(r) for r in adap_traces],
            "ALWAYS_SLOW_T257": [asdict(r) for r in slow_traces],
            "ALWAYS_FAST_SINGLE_SHOT": [asdict(r) for r in fast_traces],
        },
    }

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
            + "\n",
            encoding="utf-8",
        )
    return report


__all__ = [
    "T259EpisodeTrace",
    "build_t259_mixed_nl_workload",
    "run_t259_dual_speed_nl_benchmark",
]
