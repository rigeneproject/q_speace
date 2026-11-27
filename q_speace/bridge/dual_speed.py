"""Dual-Speed Cognitive Loop & Out-of-Band TDM Consolidation (T251 §4.2).

Implements the bifurcated execution dispatcher connecting ``SpikingBrainCortex``
to ``SymbolicGroundingAdapter``, ``SemanticEpisodicMemory``, ``StructuralCausalDAG``,
``GOAPPlanner``, and ``CostAwareRouter`` while enforcing Invariants G1–G4:

- **Tier 1 (``fast`` path)**: low-latency inference + ``TruthEngine`` + ``ActionDegradationGate``
  + lightweight ``ILF`` update. Guaranteed zero SQLite reads/writes, zero causal DAG
  rebuilds, and zero ``GOAPPlanner`` $A^*$ expansions.
- **Tier 2 (``slow`` path)**: full deliberative stack triggered by variational free-energy
  surprise, low calibrated confidence (covering tick-0 cold start), ``ActionDegradationGate``
  escalation, or explicit symbolic/causal planning payloads.
- **Tier 3 (``maintenance`` path)**: stimulus-free ``TDMMaintenanceScheduler`` ticks
  flushing pending episodes and running ``SemanticEpisodicMemory.consolidate()``,
  ``GraphEdgePruner.step()``, ``HypothesisStack.prune_weak()``, and ``SkillLibrary.prune()``
  completely off the synchronous response path.
"""

from __future__ import annotations

import json
import math
import time
from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from typing import Any, Literal

from ..aacm.plasticity import GraphEdgePruner
from ..metabolism.cognitive_cost_model import QuantumOperation
from ..routing import CostAwareRouter, GOAPPlanner, UtilityDriveSystem
from ..self_improvement_cortex.skill_library import SkillLibrary
from ..spiking.causal import CausalEdge
from ..spiking.reasoning import SymbolicGraphReasoner, TDMMaintenanceScheduler, TDMOperatingMode
from ..spiking_brain.cortex import SpikingBrainCortex
from ..spiking_brain.memory import SemanticEpisodicMemory, WorkingMemory
from ..spiking_brain.truth_engine import (
    ActionDegradationGate,
    ActionMode,
    CycleObservation,
    CyclePrediction,
    ObservationDigest,
    StructuralPredictiveCoder,
    TruthEngine,
)
from ..spiking_brain.types import ThinkResult
from .grounding import (
    GroundedPayload,
    SymbolicGroundingAdapter,
    apply_belief_revision,
    compute_effective_retracted_facts,
)
from .simulated_sensor import run_coro_isolated
from .typed_nl_pipeline import (
    ClausePolarityAuditor,
    TypedMultiRoleNLGroundingPipeline,
    _extract_json_dicts,
    _strip_echoed_gloss,
)

RoutingTier = Literal["fast", "slow"]
TurnGroundingStatus = Literal[
    "skipped_fast",
    "grounded_clean",
    "quarantined",
    "rejected_unknown_symbol",
    "rejected_schema",
]

_SYMBOLIC_JSON_MARKERS: tuple[str, ...] = (
    '"proposed_edges"',
    '"goal_predicates"',
    '"proposed_action"',
    '"observed_facts"',
)

_NL_REVISION_OR_NEGATION_CUES: tuple[str, ...] = (
    "rettifica",
    "contrordine",
    "correzione",
    "aggiornamento dal turno",
    "nota operatore",
    "non ",
    "né ",
    "nessun",
    "nessuna",
    "niente ",
    "invece",
    "però",
    "perso ",
    "persa ",
    "guasto",
)


@dataclass(frozen=True)
class DualSpeedNLRevisionRecord:
    """Audit record returned by ``DualSpeedCognitiveLoop.step_nl_belief_revision`` (T259)."""

    request_id: str
    tier_selected: RoutingTier
    escalated_after_fast: bool
    escalation_reasons: tuple[str, ...]
    raw_llm_output: str
    grounded: GroundedPayload
    revised_belief_state: frozenset[str]
    effective_retracted_facts: frozenset[str]
    llm_tokens_out: int
    latency_ms: float
    modeled_energy_j: float


@dataclass(frozen=True)
class DualSpeedTurnRecord:
    """Immutable per-turn telemetry & audit record (T251 §4.3)."""

    request_id: str
    tier_selected: RoutingTier
    escalation_reasons: tuple[str, ...]
    free_energy_surprise: float
    calibrated_confidence: float
    action_mode: ActionMode
    grounding_status: TurnGroundingStatus
    promoted_edges_count: int
    quarantined_edges_count: int
    cycle_conflicts_count: int
    rejected_symbols_count: int
    planned_actions: tuple[str, ...]
    causal_prediction: dict[str, float]
    episodic_hits: int
    approved: bool
    answer_text: str
    latency_ms: float
    modeled_energy_j: float
    sevo: float
    registry_digest: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MaintenanceReport:
    """Telemetry returned by one out-of-band ``idle_tick`` call."""

    tick: int
    mode: TDMOperatingMode
    flushed_episodes: int
    archived_episodes: int
    consolidated_episodes: int
    pruned_edges: tuple[tuple[str, str], ...]
    abandoned_hypotheses: int
    pruned_skills: tuple[str, ...]


def _looks_like_symbolic_payload(text: str) -> bool:
    if not text or "{" not in text:
        return False
    return any(marker in text for marker in _SYMBOLIC_JSON_MARKERS)


class DualSpeedCognitiveLoop:
    """Grounded two-speed cognitive dispatcher with isolated idle consolidation (T251)."""

    # Additional modeled cognitive energy (Joules) incurred by full Slow-Path deliberation
    # (calibrated to ~1 deliberative 32-token pass: 32 * 3 = 96 base gates + 8 per step/hit).
    SLOW_DELIBERATION_GATES_BASE = 96
    SLOW_DELIBERATION_GATES_PER_EXPANSION = 8

    def __init__(
        self,
        *,
        cortex: SpikingBrainCortex,
        grounding: SymbolicGroundingAdapter,
        planner: GOAPPlanner | None = None,
        truth_engine: TruthEngine | None = None,
        degradation_gate: ActionDegradationGate | None = None,
        episodic_memory: SemanticEpisodicMemory | None = None,
        cost_router: CostAwareRouter | None = None,
        drives: UtilityDriveSystem | None = None,
        reasoner: SymbolicGraphReasoner | None = None,
        predictive_coder: StructuralPredictiveCoder | None = None,
        tdm_scheduler: TDMMaintenanceScheduler | None = None,
        edge_pruner: GraphEdgePruner | None = None,
        skill_library: SkillLibrary | None = None,
        tau_surprise: float = 0.35,
        tau_conf: float = 0.70,
        tau_cycle_surprise: float = 0.45,
        force_slow_mode: bool = False,
        nl_pipeline: TypedMultiRoleNLGroundingPipeline | None = None,
    ) -> None:
        for name, val in (
            ("tau_surprise", tau_surprise),
            ("tau_conf", tau_conf),
            ("tau_cycle_surprise", tau_cycle_surprise),
        ):
            if not math.isfinite(val) or val < 0.0:
                raise ValueError(f"{name} must be finite and >= 0 (got {val!r})")
        if tau_conf > 1.0:
            raise ValueError("tau_conf must be <= 1.0")

        self.cortex = cortex
        self.grounding = grounding
        self.planner = planner or GOAPPlanner(grounding.registry.actions, simulate_only=True)
        if not self.planner.simulate_only:
            raise ValueError("DualSpeedCognitiveLoop requires planner.simulate_only=True")

        self.truth_engine = truth_engine or cortex.truth_engine or TruthEngine()
        if self.cortex.truth_engine is None:
            self.cortex.truth_engine = self.truth_engine

        self.degradation_gate = degradation_gate or ActionDegradationGate()

        # Invariant G3: guarantee cortex.memory on the hot path is pure in-memory WorkingMemory,
        # detaching any SQLite SemanticEpisodicMemory into self.episodic_memory.
        self.episodic_memory: SemanticEpisodicMemory | None
        if isinstance(self.cortex.memory, SemanticEpisodicMemory):
            detached_sqlite = self.cortex.memory
            self.cortex.memory = WorkingMemory(capacity=64)
            self.episodic_memory = episodic_memory or detached_sqlite
        else:
            self.episodic_memory = episodic_memory

        self.cost_router = cost_router
        self.drives = drives or UtilityDriveSystem()
        self.reasoner = reasoner
        self.predictive_coder = predictive_coder
        self.tdm_scheduler = tdm_scheduler or TDMMaintenanceScheduler(idle_ticks_threshold=2)
        self.edge_pruner = edge_pruner or GraphEdgePruner()
        self.skill_library = skill_library or SkillLibrary()

        self.tau_surprise = float(tau_surprise)
        self.tau_conf = float(tau_conf)
        self.tau_cycle_surprise = float(tau_cycle_surprise)
        self.force_slow_mode = bool(force_slow_mode)
        self.nl_pipeline = nl_pipeline or TypedMultiRoleNLGroundingPipeline(
            self.grounding.registry,
            tau_ground=self.grounding.tau_ground,
        )

        self._pending_episodes: deque[ThinkResult] = deque(maxlen=128)
        self._turn_records: deque[DualSpeedTurnRecord] = deque(maxlen=256)
        self._edge_ages: dict[tuple[str, str], int] = {
            (e.source, e.target): 0 for e in self.grounding.verified_edges
        }
        self._active_pairs_since_maint: set[tuple[str, str]] = set()
        self._fast_count = 0
        self._slow_count = 0
        self._maintenance_runs = 0

    @property
    def turn_records(self) -> tuple[DualSpeedTurnRecord, ...]:
        return tuple(self._turn_records)

    @property
    def stats(self) -> dict[str, int]:
        return {
            "fast_turns": self._fast_count,
            "slow_turns": self._slow_count,
            "maintenance_runs": self._maintenance_runs,
            "pending_episodes": len(self._pending_episodes),
        }

    async def step(
        self,
        prompt: str,
        *,
        request_id: str = "req-0",
        n_tokens: int = 32,
        agent_id: str = "spiking_brain",
        value_score: float = 0.75,
        estimated_action_cost: float = 0.20,
        risk: float = 0.10,
        reversible: bool = True,
        initial_facts: frozenset[str] = frozenset(),
        requires_causal_or_planning: bool = False,
        do_interventions: Mapping[str, float] | None = None,
        verified_observations: Sequence[tuple[Sequence[str], ObservationDigest]] = (),
        cycle_prediction: CyclePrediction | None = None,
    ) -> DualSpeedTurnRecord:
        """Execute one synchronous cognitive turn via ``fast`` or ``slow`` path."""
        t0 = time.perf_counter()

        # Mark active stimulus tick on TDM scheduler (never triggers maintenance here).
        self.tdm_scheduler.step(has_stimulus=True)

        # --- Tier 1: Fast Path ---
        report = await self.cortex.tick(prompt, n_tokens=n_tokens, agent_id=agent_id)
        raw_text = report.result.text if report.result is not None else ""
        raw_conf = (
            float(report.confidence)
            if math.isfinite(report.confidence) and 0.0 <= report.confidence <= 1.0
            else 0.0
        )

        obs_digests = tuple(obs_d for _nodes, obs_d in verified_observations)
        epistemic = self.truth_engine.assess(
            raw_text or prompt,
            observations=obs_digests,
            base_confidence=raw_conf,
        )
        cal_conf = float(epistemic.adjusted_confidence) if report.approved else 0.0

        gate_mode = self.degradation_gate.select(
            value_score=value_score,
            energy_cost=estimated_action_cost,
            risk=risk,
            reversible=reversible,
        )
        if not report.approved or not epistemic.approved:
            action_mode: ActionMode = "refuse"
        else:
            action_mode = gate_mode

        fe_surprise = float(self.cortex.ilf.variational_free_energy())

        cycle_surprise_val = 0.0
        if self.predictive_coder is not None and cycle_prediction is not None:
            obs_snapshot = CycleObservation(
                actual_action=action_mode,
                actual_risk="high" if risk >= 0.5 else "low",
                actual_energy_mode=" frugal" if estimated_action_cost <= 0.3 else "intensive",
                active_modules=frozenset({"cortex", "truth_engine", "degradation_gate", "ilf"}),
            )
            cycle_surprise_val = self.predictive_coder.evaluate(
                cycle_prediction, obs_snapshot
            ).surprise

        if report.approved and report.result is not None and epistemic.approved:
            self._pending_episodes.append(report.result)

        # Evaluate escalation predicates (fast -> slow)
        reasons: list[str] = []
        has_symbolic = _looks_like_symbolic_payload(raw_text) or _looks_like_symbolic_payload(
            prompt
        )
        if self.force_slow_mode:
            reasons.append("forced_slow_pipeline")
        if fe_surprise > self.tau_surprise:
            reasons.append("variational_free_energy_exceeded")
        if cycle_surprise_val > self.tau_cycle_surprise:
            reasons.append("structural_cycle_surprise_exceeded")
        if report.approved and epistemic.approved and cal_conf < self.tau_conf:
            reasons.append("confidence_below_tau_conf")
        if action_mode == "plan":
            reasons.append("action_degradation_plan_required")
        if (
            requires_causal_or_planning
            or bool(do_interventions)
            or bool(verified_observations)
            or has_symbolic
        ):
            reasons.append("symbolic_or_causal_deliberation_required")

        # Hard-refused adversarial overclaims/traps do not waste deliberative compute unless forced
        should_escalate = bool(reasons) and (action_mode != "refuse" or self.force_slow_mode)

        base_energy_j = float(report.energy_w) if math.isfinite(report.energy_w) else 0.0
        sevo_val = float(report.sevo) if math.isfinite(report.sevo) else 0.0

        if not should_escalate:
            self._fast_count += 1
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            approved_turn = bool(report.approved and epistemic.approved and action_mode != "refuse")
            rec = DualSpeedTurnRecord(
                request_id=request_id,
                tier_selected="fast",
                escalation_reasons=(),
                free_energy_surprise=fe_surprise,
                calibrated_confidence=cal_conf,
                action_mode=action_mode,
                grounding_status="skipped_fast",
                promoted_edges_count=0,
                quarantined_edges_count=0,
                cycle_conflicts_count=0,
                rejected_symbols_count=0,
                planned_actions=(),
                causal_prediction={},
                episodic_hits=0,
                approved=approved_turn,
                answer_text=raw_text if approved_turn else "",
                latency_ms=elapsed_ms,
                modeled_energy_j=base_energy_j,
                sevo=sevo_val,
                registry_digest=self.grounding.registry.registry_digest,
            )
            self._turn_records.append(rec)
            return rec

        # --- Tier 2: Slow Path (Deliberative Neuro-Symbolic Pipeline) ---
        self._slow_count += 1
        episodic_hits = 0
        if self.episodic_memory is not None:
            relevant = await self.episodic_memory.get_relevant(prompt, k=4)
            episodic_hits = len(relevant)

        payload_source = raw_text if _looks_like_symbolic_payload(raw_text) else prompt
        if _looks_like_symbolic_payload(payload_source) or verified_observations:
            grounded = self.grounding.ground(
                payload_source,
                calibrated_confidence=cal_conf,
                verified_observations=verified_observations,
            )
            g_status: TurnGroundingStatus = grounded.status
        else:
            # Plain-text slow escalation (e.g., low confidence or high surprise on text query):
            # no ungrounded state mutation occurs; active DAG & initial_facts remain intact.
            grounded = None
            g_status = "grounded_clean"

        promoted_n = len(grounded.promoted_edges) if grounded is not None else 0
        quarantined_n = len(grounded.quarantined_edges) if grounded is not None else 0
        cycles_n = len(grounded.cycle_conflicts) if grounded is not None else 0
        rejected_n = len(grounded.rejections) if grounded is not None else 0

        if grounded is not None:
            for edge in grounded.promoted_edges:
                pair = (edge.source, edge.target)
                self._edge_ages.setdefault(pair, 0)
                self._active_pairs_since_maint.add(pair)

        # Reject execution if grounding violated closed vocabulary or schema
        grounding_rejected = g_status in ("rejected_unknown_symbol", "rejected_schema")
        if grounding_rejected:
            action_mode = "refuse"

        # Evaluate causal intervention on verified StructuralCausalDAG (if nodes exist)
        causal_pred: dict[str, float] = {}
        if not grounding_rejected and self.grounding.registry.causal_nodes:
            dag = self.grounding.active_dag()
            if do_interventions:
                valid_do = {
                    canon: float(val)
                    for raw_k, val in do_interventions.items()
                    if (canon := self.grounding.registry.resolve_node(raw_k)) is not None
                }
                causal_pred = dag.intervene(valid_do) if valid_do else dag.predict()
            else:
                causal_pred = dag.predict()

        # Run bounded simulate_only GOAP planner when goal predicates exist
        planned_names: tuple[str, ...] = ()
        plan_steps = 0
        active_facts = set(initial_facts)
        if grounded is not None and not grounding_rejected:
            active_facts |= set(grounded.observed_facts)
            if grounded.goal_predicates:
                plan = self.planner.plan(frozenset(active_facts), grounded.goal_predicates)
                if plan is not None:
                    planned_names = tuple(a.name for a in plan)
                    plan_steps = len(plan)
            elif grounded.proposed_action is not None:
                if grounded.proposed_action.preconditions.issubset(active_facts):
                    planned_names = (grounded.proposed_action.name,)
                    plan_steps = 1
                else:
                    # Missing precondition -> search multi-step plan to satisfy preconditions
                    sub_plan = self.planner.plan(
                        frozenset(active_facts), grounded.proposed_action.preconditions
                    )
                    if sub_plan is not None:
                        planned_names = (*(a.name for a in sub_plan), grounded.proposed_action.name)
                        plan_steps = len(planned_names)

        # Optional CostAwareRouter & SymbolicGraphReasoner pass in Slow Path
        if self.cost_router is not None and not grounding_rejected:
            drive_levels = self.drives.step(
                {
                    "exploration": min(1.0, fe_surprise),
                    "safety": min(1.0, risk),
                    "accuracy": max(0.0, 1.0 - cal_conf),
                    "energy_conservation": min(1.0, estimated_action_cost),
                }
            )
            self.cost_router.route(active_facts, drive_levels)

        if self.reasoner is not None and causal_pred:
            top_node = max(causal_pred.items(), key=lambda kv: abs(kv[1]))[0]
            self.reasoner.forward_chain(top_node, max_hops=2)

        # Account for the two additional Slow-Path deliberative stages
        # (Stage A: episodic retrieval + structured grounding; Stage B: causal DAG + GOAP synthesis)
        slow_op = QuantumOperation(
            num_qubits=self.cortex.BRAIN_NUM_QUBITS,
            num_gates=self.SLOW_DELIBERATION_GATES_BASE
            + self.SLOW_DELIBERATION_GATES_PER_EXPANSION * (plan_steps + episodic_hits + 1),
            entanglement_depth=self.cortex.BRAIN_ENTANGLEMENT_DEPTH,
            decoherence_budget=max(1.0 - cal_conf, 0.0),
        )
        delib_stages = 2.0 if (episodic_hits > 0 or plan_steps > 0 or grounded is not None) else 1.5
        delib_energy_j = delib_stages * float(self.cortex.cost.energy_watts(slow_op))
        total_energy_j = base_energy_j + delib_energy_j

        approved_slow = bool(
            report.approved
            and epistemic.approved
            and not grounding_rejected
            and action_mode != "refuse"
        )
        final_answer = (
            (grounded.answer_text if grounded is not None and grounded.answer_text else raw_text)
            if approved_slow
            else ""
        )

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        rec = DualSpeedTurnRecord(
            request_id=request_id,
            tier_selected="slow",
            escalation_reasons=tuple(reasons),
            free_energy_surprise=fe_surprise,
            calibrated_confidence=cal_conf,
            action_mode=action_mode,
            grounding_status=g_status,
            promoted_edges_count=promoted_n,
            quarantined_edges_count=quarantined_n,
            cycle_conflicts_count=cycles_n,
            rejected_symbols_count=rejected_n,
            planned_actions=planned_names,
            causal_prediction=causal_pred,
            episodic_hits=episodic_hits,
            approved=approved_slow,
            answer_text=final_answer,
            latency_ms=elapsed_ms,
            modeled_energy_j=total_energy_j,
            sevo=sevo_val,
            registry_digest=self.grounding.registry.registry_digest,
        )
        self._turn_records.append(rec)
        return rec

    def step_sync(self, prompt: str, **kwargs: Any) -> DualSpeedTurnRecord:
        """Deadlock-free synchronous wrapper around :meth:`step`."""
        return run_coro_isolated(lambda: self.step(prompt, **kwargs))

    async def idle_tick(self) -> MaintenanceReport:
        """Advance one stimulus-free tick; run consolidation only in ``maintenance`` mode."""
        sched = self.tdm_scheduler.step(has_stimulus=False)
        for pair in list(self._edge_ages):
            self._edge_ages[pair] += 1

        if sched.mode != "maintenance":
            return MaintenanceReport(
                tick=sched.tick,
                mode=sched.mode,
                flushed_episodes=0,
                archived_episodes=0,
                consolidated_episodes=0,
                pruned_edges=(),
                abandoned_hypotheses=0,
                pruned_skills=(),
            )

        self._maintenance_runs += 1

        # 1. Out-of-band SQLite episodic flush, archival & deduplication
        flushed = 0
        archived = 0
        consolidated = 0
        if self.episodic_memory is not None:
            while self._pending_episodes:
                ep = self._pending_episodes.popleft()
                await self.episodic_memory.put(ep)
                flushed += 1
            archived = self.episodic_memory.archive_expired()
            consolidated = self.episodic_memory.consolidate()
        else:
            self._pending_episodes.clear()

        # 2. Out-of-band conservative graph edge decay & pruning
        current_edges = [(e.source, e.target, e.weight) for e in self.grounding.verified_edges]
        kept_triples, pruned_pairs = self.edge_pruner.step(
            current_edges,
            self._edge_ages,
            active_pairs=self._active_pairs_since_maint,
        )
        if pruned_pairs or kept_triples:
            asym_lookup = {(e.source, e.target): e.asymmetry for e in self.grounding.verified_edges}
            rebuilt: dict[tuple[str, str], CausalEdge] = {}
            for u, v, w in kept_triples:
                rebuilt[(u, v)] = CausalEdge(
                    source=u,
                    target=v,
                    weight=max(w, 1e-4),
                    asymmetry=asym_lookup.get((u, v), 1.0),
                )
            self.grounding._verified_edges = rebuilt
            for p in pruned_pairs:
                self._edge_ages.pop(p, None)
        self._active_pairs_since_maint.clear()

        # 3. HypothesisStack & SkillLibrary pruning
        abandoned = self.grounding.hypothesis_stack.prune_weak()
        pruned_skills = tuple(self.skill_library.prune())

        return MaintenanceReport(
            tick=sched.tick,
            mode=sched.mode,
            flushed_episodes=flushed,
            archived_episodes=archived,
            consolidated_episodes=consolidated,
            pruned_edges=tuple(pruned_pairs),
            abandoned_hypotheses=abandoned,
            pruned_skills=pruned_skills,
        )

    def idle_tick_sync(self) -> MaintenanceReport:
        """Deadlock-free synchronous wrapper around :meth:`idle_tick`."""
        return run_coro_isolated(self.idle_tick)

    def assess_nl_escalation(
        self,
        operator_message: str,
        *,
        risk: float = 0.10,
        free_energy_surprise: float | None = None,
    ) -> tuple[RoutingTier, tuple[str, ...]]:
        """Pre-route natural-language telemetry into ``fast`` or ``slow`` tier (T259)."""
        reasons: list[str] = []
        fe_val = (
            float(free_energy_surprise)
            if free_energy_surprise is not None
            else float(self.cortex.ilf.variational_free_energy())
        )
        msg_low = " " + operator_message.lower() + " "
        if self.force_slow_mode:
            reasons.append("forced_slow_pipeline")
        if fe_val > self.tau_surprise:
            reasons.append("variational_free_energy_exceeded")
        if risk >= 0.50:
            reasons.append("high_action_risk")
        if any(cue in msg_low for cue in _NL_REVISION_OR_NEGATION_CUES):
            reasons.append("non_monotonic_linguistic_cue")
        return ("slow" if reasons else "fast", tuple(reasons))

    async def step_nl_belief_revision(
        self,
        *,
        operator_message: str,
        prior_state: frozenset[str],
        predicate_glosses: Mapping[str, str],
        request_id: str = "nl-0",
        fast_max_tokens: int = 80,
        slow_max_tokens: int = 256,
        risk: float = 0.10,
        agent_id: str = "spiking_brain",
    ) -> DualSpeedNLRevisionRecord:
        """Execute adaptive two-speed natural-language belief revision (T259).

        - ``fast`` tier: single-line affirmative JSON extraction (SQLite-free), verified by
          :class:`ClausePolarityAuditor` + :class:`SymbolicGroundingAdapter`; escalates fail-closed
          to ``slow`` if grounding is non-clean, empty, or contains hidden negations.
        - ``slow`` tier: full 4-node :class:`TypedMultiRoleNLGroundingPipeline`
          (``EXTRACTOR + CRITIC`` + ``ExecutionTicket`` contracts + ``mutex_pairs``).
        """
        t0 = time.perf_counter()
        self.tdm_scheduler.step(has_stimulus=True)
        pre_tier, pre_reasons = self.assess_nl_escalation(operator_message, risk=risk)

        total_tokens = 0
        total_energy = 0.0
        escalated_after_fast = False
        reasons = list(pre_reasons)

        if pre_tier == "fast":
            gloss_lines = "\n".join(
                f"- {pred}: {desc}" for pred, desc in sorted(predicate_glosses.items())
            )
            fast_prompt = (
                "Task: Extract EVERY active allowed predicate mentioned in the nominal Italian report "
                "(ignore distractor/test units, never invent names).\n"
                f"Allowed predicates:\n{gloss_lines}\n"
                f'Report: "{operator_message}"\n'
                'Output ONE JSON line ONLY: {"observed_facts": ["..."]}'
            )
            rep_fast = await self.cortex.tick(
                fast_prompt, n_tokens=fast_max_tokens, agent_id=agent_id
            )
            raw_fast = rep_fast.result.text if rep_fast.result is not None else ""
            tok_fast = int(rep_fast.result.n_tokens) if rep_fast.result is not None else 0
            total_tokens += tok_fast
            total_energy += float(rep_fast.energy_w) if math.isfinite(rep_fast.energy_w) else 0.0

            cands_obs: list[str] = []
            cands_ret: list[str] = []
            for obj in _extract_json_dicts(raw_fast):
                if isinstance(obj.get("observed_facts"), list):
                    cands_obs.extend(
                        _strip_echoed_gloss(str(v))
                        for v in obj["observed_facts"]
                        if isinstance(v, str)
                    )
                if isinstance(obj.get("retracted_facts"), list):
                    cands_ret.extend(
                        _strip_echoed_gloss(str(v))
                        for v in obj["retracted_facts"]
                        if isinstance(v, str)
                    )

            kept_obs, kept_ret, _drop, reclass = ClausePolarityAuditor.audit_candidates(
                operator_message=operator_message,
                prior_state=prior_state,
                predicate_glosses=predicate_glosses,
                candidate_observed=cands_obs,
                candidate_retracted=cands_ret,
            )
            valid_obs = [
                p for p in kept_obs if self.grounding.registry.resolve_predicate(p) is not None
            ]
            valid_ret = [
                p for p in kept_ret if self.grounding.registry.resolve_predicate(p) is not None
            ]
            audited_json = json.dumps(
                {
                    "observed_facts": sorted(set(valid_obs)),
                    "retracted_facts": sorted(set(valid_ret)),
                }
            )
            g_fast = self.grounding.ground(audited_json, calibrated_confidence=rep_fast.confidence)

            if (
                g_fast.status == "grounded_clean"
                and bool(g_fast.observed_facts)
                and not reclass
                and rep_fast.confidence >= min(0.55, self.tau_conf)
            ):
                self._fast_count += 1
                if rep_fast.result is not None:
                    self._pending_episodes.append(rep_fast.result)
                eff_ret = compute_effective_retracted_facts(
                    prior_state, g_fast, registry=self.grounding.registry
                )
                s_rev = apply_belief_revision(prior_state, g_fast, registry=self.grounding.registry)
                return DualSpeedNLRevisionRecord(
                    request_id=request_id,
                    tier_selected="fast",
                    escalated_after_fast=False,
                    escalation_reasons=(),
                    raw_llm_output=raw_fast,
                    grounded=g_fast,
                    revised_belief_state=s_rev,
                    effective_retracted_facts=eff_ret,
                    llm_tokens_out=total_tokens,
                    latency_ms=round((time.perf_counter() - t0) * 1000.0, 3),
                    modeled_energy_j=round(total_energy, 3),
                )

            escalated_after_fast = True
            reasons.append("fast_pass_incomplete_or_ambiguous")

        # --- Slow Tier: Full T257 TypedMultiRoleNLGroundingPipeline ---
        self._slow_count += 1
        slow_prompt = self.nl_pipeline.build_prompt(
            operator_message=operator_message,
            prior_state=prior_state,
            predicate_glosses=predicate_glosses,
        )
        rep_slow = await self.cortex.tick(slow_prompt, n_tokens=slow_max_tokens, agent_id=agent_id)
        raw_slow = rep_slow.result.text if rep_slow.result is not None else ""
        tok_slow = int(rep_slow.result.n_tokens) if rep_slow.result is not None else 0
        total_tokens += tok_slow
        total_energy += float(rep_slow.energy_w) if math.isfinite(rep_slow.energy_w) else 0.0
        if rep_slow.result is not None:
            self._pending_episodes.append(rep_slow.result)

        pipe_res = self.nl_pipeline.run(
            raw_llm_output=raw_slow,
            operator_message=operator_message,
            prior_state=prior_state,
            predicate_glosses=predicate_glosses,
            calibrated_confidence=rep_slow.confidence,
            coherence_phi=float(self.cortex.ilf.coherence_phi),
        )
        return DualSpeedNLRevisionRecord(
            request_id=request_id,
            tier_selected="slow",
            escalated_after_fast=escalated_after_fast,
            escalation_reasons=tuple(reasons),
            raw_llm_output=raw_slow,
            grounded=pipe_res.grounded,
            revised_belief_state=pipe_res.revised_belief_state,
            effective_retracted_facts=pipe_res.effective_retracted_facts,
            llm_tokens_out=total_tokens,
            latency_ms=round((time.perf_counter() - t0) * 1000.0, 3),
            modeled_energy_j=round(total_energy, 3),
        )


__all__ = [
    "DualSpeedCognitiveLoop",
    "DualSpeedNLRevisionRecord",
    "DualSpeedTurnRecord",
    "MaintenanceReport",
    "RoutingTier",
    "TurnGroundingStatus",
]
