"""Role-Parameterized Macro-Skills, Relational Analogy Transfer & Selective Repair (T252–T253).

Implements the functional experiential learning and repair stack specified in
``docs/T252_T253_EXPERIENTIAL_TRANSFER_AND_REPAIR_SPEC.md``:

1. **Macro-Skill Lifting (T252 Phase 1)**: compresses solved ``GOAPAction`` plans
   during ``TDMMaintenanceScheduler`` consolidation into role-parameterized
   templates (``RoleParameterizedMacroSkill``) with structural transition
   signatures and 2-hop graph topology profiles.
2. **Cross-Domain Structural Analogy & Micro-Bridging (T252 Phase 2)**: maps
   both operator schemas and entity roles onto unseen target domains containing
   renamed symbols, distractor subgraphs, and local precondition refinements,
   emitting a verifiable ``AnalogyAuditTrace``.
3. **Credit-Localized Selective Repair & Anti-Einstellung Gate (T253 Phase 3)**:
   detects step-level transition discrepancies ``(Delta_minus, Delta_plus)`` coupled
   with ``InformationalLogicalField.variational_free_energy()``, updates an
   ``EmpiricalOperatorModel``, computes backward weakest-precondition kernels
   ``W_k``, splices a sub-budget local bridge when ``W_k`` remains valid, and
   explicitly abandons the macro-skill (``ABANDON_MACRO_AND_REPLAN``) when a
   rule shift invalidates the suffix.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

import numpy as np

from ..edd_cvt.ilf import InformationalLogicalField
from ..routing import GOAPAction, GOAPPlanner
from ..spiking.reasoning import RelationEdge, SymbolicGraphReasoner
from ..spiking_brain.truth_engine import ObservationDigest, TruthEngine
from .skill_library import ReconsolidationWindow, SkillLibrary

RepairDecisionKind = Literal[
    "NO_REPAIR_NEEDED",
    "SELECTIVE_LOCAL_REPAIR",
    "ABANDON_MACRO_AND_REPLAN",
    "REPAIR_FAILED",
]


def parse_structured_atom(atom: str) -> tuple[str, tuple[str, ...]]:
    """Parse ``rel(a,b)`` into ``('rel', ('a', 'b'))`` or ``prop`` into ``('prop', ())``."""
    s = atom.strip()
    if not s:
        raise ValueError("atom must be non-empty")
    open_idx = s.find("(")
    if open_idx < 0:
        return s, ()
    if not s.endswith(")") or open_idx == 0:
        raise ValueError(f"malformed relational atom: {atom!r}")
    head = s[:open_idx].strip()
    inner = s[open_idx + 1 : -1].strip()
    if not inner:
        return head, ()
    args = tuple(part.strip() for part in inner.split(",") if part.strip())
    return head, args


def format_structured_atom(head: str, args: Sequence[str]) -> str:
    """Format ``('rel', ('a', 'b'))`` canonically as ``'rel(a,b)'``."""
    h = head.strip()
    if not h:
        raise ValueError("head must be non-empty")
    if not args:
        return h
    return f"{h}({','.join(a.strip() for a in args)})"


@dataclass(frozen=True)
class LiftedAtom:
    """Predicate or action atom whose arguments are role variables ``?r0, ?r1, ...``."""

    relation: str
    role_args: tuple[str, ...]

    def instantiate(
        self,
        role_binding: Mapping[str, str],
        relation_map: Mapping[str, str] | None = None,
    ) -> str:
        mapped_rel = (
            relation_map.get(self.relation, self.relation) if relation_map else self.relation
        )
        concrete_args = tuple(role_binding[r] for r in self.role_args)
        return format_structured_atom(mapped_rel, concrete_args)


@dataclass(frozen=True)
class ParameterizedStep:
    """Single role-lifted operator template inside a ``RoleParameterizedMacroSkill``."""

    op_schema: str
    role_args: tuple[str, ...]
    preconditions: frozenset[LiftedAtom]
    add_effects: frozenset[LiftedAtom]
    del_effects: frozenset[LiftedAtom]
    cost: float = 1.0


@dataclass(frozen=True)
class RoleTopologyProfile:
    """Label-independent 2-hop structural profile of a role variable in a relational graph."""

    role_var: str
    out_degree: int
    in_degree: int
    two_hop_out_count: int
    two_hop_in_count: int
    appears_in_goal: bool


@dataclass(frozen=True)
class RoleParameterizedMacroSkill:
    """Executable, role-parameterized procedural macro-skill extracted from a plan trace."""

    skill_id: str
    source_domain: str
    roles: tuple[str, ...]
    steps: tuple[ParameterizedStep, ...]
    goal_template: frozenset[LiftedAtom]
    role_profiles: dict[str, RoleTopologyProfile]

    def instantiate_ground_plan(
        self,
        *,
        role_binding: Mapping[str, str],
        target_actions: Sequence[GOAPAction],
        operator_map: Mapping[str, str] | None = None,
    ) -> list[GOAPAction] | None:
        """Instantiate this macro-skill onto concrete ``target_actions`` under ``role_binding``."""
        by_name = {a.name: a for a in target_actions}
        grounded: list[GOAPAction] = []
        for step in self.steps:
            op_name = (
                operator_map.get(step.op_schema, step.op_schema) if operator_map else step.op_schema
            )
            try:
                concrete_args = tuple(role_binding[r] for r in step.role_args)
            except KeyError:
                return None
            ground_name = format_structured_atom(op_name, concrete_args)
            act = by_name.get(ground_name)
            if act is None:
                return None
            grounded.append(act)
        return grounded


def _compute_node_topology_profile(
    node: str,
    edges: Sequence[RelationEdge],
    goal_entities: set[str],
    role_var: str = "",
) -> RoleTopologyProfile:
    out_neighbors = [e.target for e in edges if e.source == node]
    in_neighbors = [e.source for e in edges if e.target == node]
    two_out = sum(1 for mid in out_neighbors for e2 in edges if e2.source == mid)
    two_in = sum(1 for mid in in_neighbors for e2 in edges if e2.target == mid)
    return RoleTopologyProfile(
        role_var=role_var or node,
        out_degree=len(out_neighbors),
        in_degree=len(in_neighbors),
        two_hop_out_count=two_out,
        two_hop_in_count=two_in,
        appears_in_goal=(node in goal_entities),
    )


def _profile_similarity(p_src: RoleTopologyProfile, p_dst: RoleTopologyProfile) -> float:
    """Compute bounded structural neighborhood similarity in [0, 1] between two role profiles."""
    if p_src.appears_in_goal != p_dst.appears_in_goal:
        return 0.0
    feats_a = (p_src.out_degree, p_src.in_degree, p_src.two_hop_out_count, p_src.two_hop_in_count)
    feats_b = (p_dst.out_degree, p_dst.in_degree, p_dst.two_hop_out_count, p_dst.two_hop_in_count)
    inter = sum(min(a, b) for a, b in zip(feats_a, feats_b, strict=True))
    union = sum(max(a, b) for a, b in zip(feats_a, feats_b, strict=True))
    if union == 0:
        return 1.0
    return float(inter / union)


def extract_macro_skill(
    *,
    skill_id: str,
    source_domain: str,
    plan: Sequence[GOAPAction],
    goal_state: frozenset[str],
    domain_edges: Sequence[RelationEdge] = (),
) -> RoleParameterizedMacroSkill:
    """Lift a concrete solved ``GOAPAction`` sequence into a ``RoleParameterizedMacroSkill``."""
    if not skill_id:
        raise ValueError("skill_id must be non-empty")
    if not plan:
        raise ValueError("cannot extract macro-skill from an empty plan")

    obj_to_role: dict[str, str] = {}

    def _lift_args(args: tuple[str, ...]) -> tuple[str, ...]:
        out: list[str] = []
        for obj in args:
            role = obj_to_role.get(obj)
            if role is None:
                role = f"?r{len(obj_to_role)}"
                obj_to_role[obj] = role
            out.append(role)
        return tuple(out)

    def _lift_fluent_set(fluents: Iterable[str]) -> frozenset[LiftedAtom]:
        lifted: set[LiftedAtom] = set()
        for f in sorted(fluents):
            rel, args = parse_structured_atom(f)
            # Only lift constants already bound by actions or introduce canonical roles
            lifted.add(LiftedAtom(relation=rel, role_args=_lift_args(args)))
        return frozenset(lifted)

    # First pass over action arguments establishes canonical role ordering ?r0, ?r1, ...
    raw_step_headers: list[tuple[str, tuple[str, ...], GOAPAction]] = []
    for act in plan:
        op_head, act_args = parse_structured_atom(act.name)
        role_args = _lift_args(act_args)
        raw_step_headers.append((op_head, role_args, act))

    lifted_steps: list[ParameterizedStep] = []
    for op_head, role_args, act in raw_step_headers:
        lifted_steps.append(
            ParameterizedStep(
                op_schema=op_head,
                role_args=role_args,
                preconditions=_lift_fluent_set(act.preconditions),
                add_effects=_lift_fluent_set(act.add_effects),
                del_effects=_lift_fluent_set(act.del_effects),
                cost=act.cost,
            )
        )

    lifted_goal = _lift_fluent_set(goal_state)
    goal_entities: set[str] = set()
    for g_f in goal_state:
        _r, g_args = parse_structured_atom(g_f)
        goal_entities.update(g_args)

    role_to_obj = {r: o for o, r in obj_to_role.items()}
    profiles: dict[str, RoleTopologyProfile] = {}
    for r_var in sorted(role_to_obj.keys(), key=lambda x: int(x[2:])):
        orig_obj = role_to_obj[r_var]
        profiles[r_var] = _compute_node_topology_profile(
            orig_obj, domain_edges, goal_entities, role_var=r_var
        )

    ordered_roles = tuple(sorted(role_to_obj.keys(), key=lambda x: int(x[2:])))
    return RoleParameterizedMacroSkill(
        skill_id=skill_id,
        source_domain=source_domain,
        roles=ordered_roles,
        steps=tuple(lifted_steps),
        goal_template=lifted_goal,
        role_profiles=profiles,
    )


def compute_regressed_kernels(
    steps: Sequence[GOAPAction],
    goal_state: frozenset[str],
) -> list[frozenset[str]] | None:
    """Compute backward weakest preconditions ``[W_0, W_1, ..., W_m]`` for ``steps``.

    ``W_m = goal_state``, and for ``j = m .. 1``:
    ``W_{j-1} = (W_j \\ add_j) | pre_j``, failing closed (returning ``None``) if
    step ``j`` deletes any fluent still required downstream (``W_j & del_j != empty``).
    """
    m = len(steps)
    kernels: list[frozenset[str]] = [frozenset() for _ in range(m + 1)]
    kernels[m] = frozenset(goal_state)
    for j in range(m, 0, -1):
        act = steps[j - 1]
        w_next = kernels[j]
        if w_next & act.del_effects:
            return None
        kernels[j - 1] = (w_next - act.add_effects) | act.preconditions
    return kernels


@dataclass(frozen=True)
class AnalogyAuditTrace:
    """Verifiable record of cross-domain role & operator mapping (T252 Phase 2)."""

    skill_id: str
    candidates_considered: int
    selected_role_binding: dict[str, str]
    selected_operator_map: dict[str, str]
    structural_similarity: float
    distractors_rejected: tuple[str, ...]
    verification_passed: bool
    reason: str


class AnalogicalRoleMapper:
    """Label-independent structural mapper binding macro-skills onto new domains (T252)."""

    def __init__(self, *, tau_analogy: float = 0.50) -> None:
        if not math.isfinite(tau_analogy) or not (0.0 <= tau_analogy <= 1.0):
            raise ValueError("tau_analogy must be finite and in [0, 1]")
        self.tau_analogy = float(tau_analogy)

    def map_skill(
        self,
        skill: RoleParameterizedMacroSkill,
        *,
        initial_state: frozenset[str],
        goal_state: frozenset[str],
        target_actions: Sequence[GOAPAction],
        target_edges: Sequence[RelationEdge],
    ) -> tuple[list[GOAPAction] | None, AnalogyAuditTrace]:
        """Discover injective entity & operator homomorphism rejecting distractor subgraphs."""
        reasoner = SymbolicGraphReasoner(target_edges)
        all_entities = set(reasoner.nodes)
        for act in target_actions:
            _, a_args = parse_structured_atom(act.name)
            all_entities.update(a_args)
        for f in initial_state | goal_state:
            _, f_args = parse_structured_atom(f)
            all_entities.update(f_args)

        goal_entities: set[str] = set()
        for gf in goal_state:
            _, g_args = parse_structured_atom(gf)
            goal_entities.update(g_args)

        entity_profiles = {
            ent: _compute_node_topology_profile(ent, target_edges, goal_entities)
            for ent in sorted(all_entities)
        }

        # Group target actions by (op_head, args)
        op_families: dict[str, list[tuple[tuple[str, ...], GOAPAction]]] = {}
        by_op_and_args: dict[tuple[str, tuple[str, ...]], GOAPAction] = {}
        for act in target_actions:
            op_h, a_args = parse_structured_atom(act.name)
            op_families.setdefault(op_h, []).append((a_args, act))
            by_op_and_args[(op_h, a_args)] = act

        # Candidate entities per role filtered by positive structural profile similarity
        role_candidates: dict[str, list[tuple[float, str]]] = {}
        for r_var in skill.roles:
            src_prof = skill.role_profiles[r_var]
            scored_ents: list[tuple[float, str]] = []
            for ent, dst_prof in entity_profiles.items():
                sim = _profile_similarity(src_prof, dst_prof)
                if sim >= self.tau_analogy:
                    scored_ents.append((sim, ent))
            scored_ents.sort(key=lambda item: (-item[0], item[1]))
            role_candidates[r_var] = scored_ents

        if any(not role_candidates[r] for r in skill.roles):
            return None, AnalogyAuditTrace(
                skill_id=skill.skill_id,
                candidates_considered=0,
                selected_role_binding={},
                selected_operator_map={},
                structural_similarity=0.0,
                distractors_rejected=tuple(sorted(all_entities)),
                verification_passed=False,
                reason="no_entity_passed_topology_threshold",
            )

        # Enumerate injective entity bindings ranked by mean 2-hop topology score
        candidate_lists = [[ent for _s, ent in role_candidates[r]] for r in skill.roles]
        evaluated = 0
        best_match: tuple[float, dict[str, str], dict[str, str], list[GOAPAction]] | None = None

        for combo in itertools.product(*candidate_lists):
            if len(set(combo)) != len(combo):
                continue
            evaluated += 1
            binding = dict(zip(skill.roles, combo, strict=True))
            sim_mean = float(
                np.mean(
                    [
                        _profile_similarity(skill.role_profiles[r], entity_profiles[binding[r]])
                        for r in skill.roles
                    ]
                )
            )

            # Match each ParameterizedStep's operator schema by chaining & goal production
            op_map, matched_steps = self._match_operator_chain(
                skill,
                binding=binding,
                initial_state=initial_state,
                goal_state=goal_state,
                op_families=op_families,
                by_op_and_args=by_op_and_args,
            )
            if matched_steps is None or op_map is None:
                continue

            # Verify weakest-precondition kernel exists (no internal clobbering)
            kernels = compute_regressed_kernels(matched_steps, goal_state)
            if kernels is None:
                continue

            # Score penalizes large unsatisfied W_0 gap while allowing 1-2 local refinements
            unsatisfied_w0 = len(kernels[0] - initial_state)
            if unsatisfied_w0 > 2:
                continue
            rank_score = sim_mean - 0.05 * unsatisfied_w0
            if best_match is None or rank_score > best_match[0]:
                best_match = (sim_mean, binding, op_map, matched_steps)

        if best_match is None:
            return None, AnalogyAuditTrace(
                skill_id=skill.skill_id,
                candidates_considered=evaluated,
                selected_role_binding={},
                selected_operator_map={},
                structural_similarity=0.0,
                distractors_rejected=tuple(sorted(all_entities)),
                verification_passed=False,
                reason="no_chaining_consistent_homomorphism",
            )

        sim_score, best_binding, best_op_map, best_steps = best_match
        bound_entities = set(best_binding.values())
        distractors = tuple(sorted(all_entities - bound_entities))
        return best_steps, AnalogyAuditTrace(
            skill_id=skill.skill_id,
            candidates_considered=evaluated,
            selected_role_binding=best_binding,
            selected_operator_map=best_op_map,
            structural_similarity=round(sim_score, 4),
            distractors_rejected=distractors,
            verification_passed=True,
            reason="verified_structural_homomorphism",
        )

    @staticmethod
    def _match_operator_chain(
        skill: RoleParameterizedMacroSkill,
        *,
        binding: Mapping[str, str],
        initial_state: frozenset[str],
        goal_state: frozenset[str],
        op_families: Mapping[str, list[tuple[tuple[str, ...], GOAPAction]]],
        by_op_and_args: Mapping[tuple[str, tuple[str, ...]], GOAPAction],
    ) -> tuple[dict[str, str] | None, list[GOAPAction] | None]:
        """Find operator correspondence ``op_A -> op_B`` preserving step-to-step causal chaining."""
        step_candidates: list[list[tuple[str, GOAPAction]]] = []
        for idx, p_step in enumerate(skill.steps):
            concrete_args = tuple(binding[r] for r in p_step.role_args)
            cands: list[tuple[str, GOAPAction]] = []
            # Fast path: same operator name exists in target domain (e.g., Phase 1 re-binding in A)
            same_act = by_op_and_args.get((p_step.op_schema, concrete_args))
            if same_act is not None:
                cands.append((p_step.op_schema, same_act))
            else:
                for op_b in sorted(op_families.keys()):
                    cand_act = by_op_and_args.get((op_b, concrete_args))
                    if cand_act is None:
                        continue
                    # Final step must contribute directly to goal_state
                    if idx == len(skill.steps) - 1 and not (cand_act.add_effects & goal_state):
                        continue
                    cands.append((op_b, cand_act))
            if not cands:
                return None, None
            step_candidates.append(cands)

        # Backtracking search over short macro length (typically m = 3..5) enforcing step chaining
        m = len(step_candidates)

        def _search(
            pos: int,
            chosen_ops: dict[str, str],
            chosen_acts: list[GOAPAction],
        ) -> tuple[dict[str, str], list[GOAPAction]] | None:
            if pos == m:
                # Verify step i produces at least one precondition of step i+1
                for k in range(m - 1):
                    if not (chosen_acts[k].add_effects & chosen_acts[k + 1].preconditions):
                        return None
                if not (chosen_acts[-1].add_effects & goal_state):
                    return None
                return chosen_ops, chosen_acts

            src_op = skill.steps[pos].op_schema
            for op_b, act_b in step_candidates[pos]:
                if src_op in chosen_ops and chosen_ops[src_op] != op_b:
                    continue
                if op_b in chosen_ops.values() and chosen_ops.get(src_op) != op_b:
                    continue
                # Step 0 should connect to initial_state (allowing <=1 local micro-refinement gap)
                if pos == 0 and len(act_b.preconditions - initial_state) > 1:
                    continue
                if pos > 0 and not (chosen_acts[-1].add_effects & act_b.preconditions):
                    continue
                nxt_ops = dict(chosen_ops)
                nxt_ops[src_op] = op_b
                res = _search(pos + 1, nxt_ops, [*chosen_acts, act_b])
                if res is not None:
                    return res
            return None

        found = _search(0, {}, [])
        if found is None:
            return None, None
        return found


class EmpiricalOperatorModel:
    """Agent-side belief over operator preconditions/effects updated from observed transitions."""

    def __init__(
        self,
        prior_actions: Sequence[GOAPAction],
        *,
        terminal_blocker_prefixes: Sequence[str] = ("terminal_fault(", "hull_lockout(", "breach("),
    ) -> None:
        self._actions: dict[str, GOAPAction] = {a.name: a for a in prior_actions}
        self._mutated_names: set[str] = set()
        self.terminal_blocker_prefixes: tuple[str, ...] = tuple(terminal_blocker_prefixes)

    @property
    def actions(self) -> tuple[GOAPAction, ...]:
        return tuple(self._actions[k] for k in sorted(self._actions))

    @property
    def mutated_operators(self) -> frozenset[str]:
        return frozenset(self._mutated_names)

    def get(self, name: str) -> GOAPAction:
        return self._actions[name]

    def clone(self) -> EmpiricalOperatorModel:
        copy = EmpiricalOperatorModel(
            list(self._actions.values()),
            terminal_blocker_prefixes=self.terminal_blocker_prefixes,
        )
        copy._mutated_names = set(self._mutated_names)
        return copy

    def record_transition_discrepancy(
        self,
        action_name: str,
        pre_state: frozenset[str],
        obs_post_state: frozenset[str],
    ) -> tuple[frozenset[str], frozenset[str]]:
        """Update empirical ``add_effects``/``del_effects`` of ``action_name`` from observation.

        Returns ``(delta_minus_missing, delta_plus_unexpected)``.
        """
        prior = self._actions[action_name]
        predicted = (pre_state - prior.del_effects) | prior.add_effects
        delta_minus = frozenset(predicted - obs_post_state)
        delta_plus = frozenset(obs_post_state - predicted)

        if delta_minus or delta_plus:
            observed_adds = frozenset(obs_post_state - pre_state)
            observed_dels = frozenset(pre_state - obs_post_state)
            self._actions[action_name] = GOAPAction(
                name=prior.name,
                preconditions=prior.preconditions,
                add_effects=observed_adds,
                del_effects=observed_dels,
                cost=prior.cost,
            )
            self._mutated_names.add(action_name)
        return delta_minus, delta_plus

    def has_unrecoverable_blocker(self, unexpected_added: Iterable[str]) -> bool:
        """Check whether ``unexpected_added`` contains a fluent that no operator can delete."""
        all_deletable: set[str] = set()
        for act in self._actions.values():
            all_deletable |= set(act.del_effects)
        for fluent in unexpected_added:
            if any(fluent.startswith(pref) for pref in self.terminal_blocker_prefixes):
                return True
            if (
                "fault" in fluent
                or "offline" in fluent
                or "lockout" in fluent
                or "breach" in fluent
            ) and fluent not in all_deletable:
                return True
        return False


class StatefulPlanningEnvironment:
    """Sandbox transition environment whose ground-truth rules are hidden from the agent."""

    def __init__(
        self,
        initial_state: frozenset[str],
        true_actions: Sequence[GOAPAction],
    ) -> None:
        self._state: frozenset[str] = frozenset(initial_state)
        self._true_actions: dict[str, GOAPAction] = {a.name: a for a in true_actions}
        self._step_idx = 0

    @property
    def state(self) -> frozenset[str]:
        return self._state

    def clone(self) -> StatefulPlanningEnvironment:
        copied = StatefulPlanningEnvironment(self._state, list(self._true_actions.values()))
        copied._step_idx = self._step_idx
        return copied

    def mutate_rule(self, mutated_action: GOAPAction) -> None:
        """Alter ground-truth transition rule without notifying any agent."""
        self._true_actions[mutated_action.name] = mutated_action

    def execute(self, action_name: str) -> tuple[bool, frozenset[str], ObservationDigest]:
        """Apply ``action_name`` in ground-truth environment and emit verifiable digest."""
        self._step_idx += 1
        act = self._true_actions.get(action_name)
        if act is None or not act.preconditions.issubset(self._state):
            digest = TruthEngine.tool_observation(
                "sandbox_env",
                {"step": self._step_idx, "action": action_name},
                {"applied": False, "state": sorted(self._state)},
                verifiable=True,
            )
            return False, self._state, digest

        self._state = (self._state - act.del_effects) | act.add_effects
        digest = TruthEngine.tool_observation(
            "sandbox_env",
            {"step": self._step_idx, "action": action_name},
            {"applied": True, "state": sorted(self._state)},
            verifiable=True,
        )
        return True, self._state, digest


@dataclass(frozen=True)
class EpisodeExecutionReport:
    """Complete execution, expansion, and repair audit trace for one episode."""

    arm: str
    goal_reached: bool
    planner_expansions: int
    executed_actions: tuple[str, ...]
    repair_decision: RepairDecisionKind
    abandon_reason: str
    discrepancy_step: int | None
    delta_minus: tuple[str, ...]
    delta_plus: tuple[str, ...]
    free_energy_peak: float
    spliced_skill_id: str | None
    analogy_trace: AnalogyAuditTrace | None


class ExperientialCognitiveAgent:
    """SPEACE agent supporting macro-skill transfer, selective local repair & global replan."""

    def __init__(
        self,
        *,
        arm_name: str,
        operator_model: EmpiricalOperatorModel,
        skill_library: SkillLibrary | None = None,
        macro_store: dict[str, RoleParameterizedMacroSkill] | None = None,
        reconsolidation: ReconsolidationWindow | None = None,
        ilf: InformationalLogicalField | None = None,
        alpha_local: float = 0.30,
        tau_analogy: float = 0.50,
        tau_surprise: float = 0.15,
        max_global_expansions: int = 256,
        micro_bridge_budget: int = 8,
        repair_mode: Literal["selective", "global_replan", "stubborn_reuse"] = "selective",
    ) -> None:
        if not math.isfinite(alpha_local) or not (0.0 < alpha_local <= 0.50):
            raise ValueError("alpha_local must be in (0, 0.50]")
        if max_global_expansions < 8:
            raise ValueError("max_global_expansions must be >= 8")

        self.arm_name = arm_name
        self.operator_model = operator_model
        self.skill_library = skill_library if skill_library is not None else SkillLibrary()
        self.macro_store: dict[str, RoleParameterizedMacroSkill] = (
            dict(macro_store) if macro_store is not None else {}
        )
        self.reconsolidation = reconsolidation or ReconsolidationWindow(window_seconds=300.0)
        self.ilf = ilf or InformationalLogicalField(
            coherence_phi=1.0, q_star_ema=0.25, coherence_phi_ema=0.25
        )
        self.ilf.register_agent("transition_predictor", weight=1.0)
        self.ilf.set_belief("transition_predictor", np.array([0.94, 0.02, 0.02, 0.02]))
        self.ilf.compute_q_star()

        self.alpha_local = float(alpha_local)
        self.mapper = AnalogicalRoleMapper(tau_analogy=tau_analogy)
        self.tau_surprise = float(tau_surprise)
        self.max_global_expansions = int(max_global_expansions)
        self.micro_bridge_budget = int(micro_bridge_budget)
        self.repair_mode = repair_mode

    def clone_from_checkpoint(
        self,
        *,
        new_arm_name: str,
        repair_mode: Literal["selective", "global_replan", "stubborn_reuse"],
    ) -> ExperientialCognitiveAgent:
        """Create an identical experiential clone differing ONLY in post-shift repair policy."""
        cloned_lib = SkillLibrary(
            max_skills=self.skill_library.max_skills,
            min_fitness=self.skill_library.min_fitness,
            min_generality=self.skill_library.min_generality,
        )
        for sk in self.skill_library.top_skills(k=self.skill_library.max_skills):
            cloned_lib.record_outcome(
                sk.skill_id,
                regime="checkpoint",
                success=sk.success_rate >= 0.5,
                latency_ms=sk.mean_latency_ms,
                description=sk.description,
            )
        return ExperientialCognitiveAgent(
            arm_name=new_arm_name,
            operator_model=self.operator_model.clone(),
            skill_library=cloned_lib,
            macro_store=dict(self.macro_store),
            alpha_local=self.alpha_local,
            tau_analogy=self.mapper.tau_analogy,
            tau_surprise=self.tau_surprise,
            max_global_expansions=self.max_global_expansions,
            micro_bridge_budget=self.micro_bridge_budget,
            repair_mode=repair_mode,
        )

    def consolidate_trace(
        self,
        *,
        skill_id: str,
        domain: str,
        plan: Sequence[GOAPAction],
        goal_state: frozenset[str],
        domain_edges: Sequence[RelationEdge],
    ) -> RoleParameterizedMacroSkill:
        """Extract and store a role-parameterized macro-skill (TDM consolidation step)."""
        macro = extract_macro_skill(
            skill_id=skill_id,
            source_domain=domain,
            plan=plan,
            goal_state=goal_state,
            domain_edges=domain_edges,
        )
        self.macro_store[skill_id] = macro
        self.skill_library.record_outcome(
            skill_id,
            regime=domain,
            success=True,
            latency_ms=float(len(plan)),
            description=f"macro:{domain}:{len(plan)}_steps",
        )
        return macro

    def solve_episode(
        self,
        env: StatefulPlanningEnvironment,
        *,
        domain: str,
        goal_state: frozenset[str],
        domain_edges: Sequence[RelationEdge],
        consolidate_on_success: bool = True,
        consolidate_skill_id: str | None = None,
    ) -> EpisodeExecutionReport:
        """Attempt to reach ``goal_state`` in ``env`` using macro transfer or A* search."""
        total_expansions = 0
        executed: list[str] = []
        analogy_trace: AnalogyAuditTrace | None = None
        candidate_plan: list[GOAPAction] | None = None
        used_skill_id: str | None = None

        # 1. Attempt analogical retrieval from learned macro_store, preferring zero-gap matches
        ranked_ids = [s.skill_id for s in self.skill_library.top_skills(k=16)]
        ordered_ids = [*ranked_ids, *(k for k in self.macro_store if k not in ranked_ids)]
        best_candidate: tuple[int, float, str, list[GOAPAction], AnalogyAuditTrace] | None = None

        for sid in ordered_ids:
            macro = self.macro_store.get(sid)
            if macro is None:
                continue
            mapped_steps, trace = self.mapper.map_skill(
                macro,
                initial_state=env.state,
                goal_state=goal_state,
                target_actions=self.operator_model.actions,
                target_edges=domain_edges,
            )
            if analogy_trace is None:
                analogy_trace = trace
            if mapped_steps is not None and trace.verification_passed:
                kernels = compute_regressed_kernels(mapped_steps, goal_state)
                w0_gap = len(kernels[0] - env.state) if kernels is not None else 99
                cand_tuple = (w0_gap, -trace.structural_similarity, sid, mapped_steps, trace)
                if best_candidate is None or cand_tuple[:2] < best_candidate[:2]:
                    best_candidate = cand_tuple
                    if w0_gap == 0:
                        break

        if best_candidate is not None:
            _gap, _neg_sim, used_skill_id, candidate_plan, analogy_trace = best_candidate
            self.reconsolidation.open_on_recall(used_skill_id, now=0.0)

        # 2. If no macro-skill matched, plan globally from scratch via GOAPPlanner
        if candidate_plan is None:
            planner = GOAPPlanner(
                self.operator_model.actions,
                simulate_only=True,
                max_expansions=self.max_global_expansions,
            )
            fresh_plan, exp = planner.plan_with_stats(env.state, goal_state)
            total_expansions += exp
            if fresh_plan is None:
                return EpisodeExecutionReport(
                    arm=self.arm_name,
                    goal_reached=False,
                    planner_expansions=total_expansions,
                    executed_actions=(),
                    repair_decision="REPAIR_FAILED",
                    abandon_reason="initial_global_plan_unreachable",
                    discrepancy_step=None,
                    delta_minus=(),
                    delta_plus=(),
                    free_energy_peak=0.0,
                    spliced_skill_id=None,
                    analogy_trace=analogy_trace,
                )
            candidate_plan = fresh_plan

        # 3. Execute candidate_plan step-by-step, handling micro-refinements & rule shifts
        fe_peak = 0.0
        repair_decision: RepairDecisionKind = "NO_REPAIR_NEEDED"
        abandon_reason = ""
        disc_step: int | None = None
        rec_delta_minus: tuple[str, ...] = ()
        rec_delta_plus: tuple[str, ...] = ()
        spliced_id: str | None = None
        executed_action_objs: list[GOAPAction] = []

        idx = 0
        while idx < len(candidate_plan):
            act = self.operator_model.get(candidate_plan[idx].name)

            # Non-isomorphic local refinement micro-bridge if pre(act) has a small gap
            if not act.preconditions.issubset(env.state):
                micro_planner = GOAPPlanner(
                    self.operator_model.actions,
                    simulate_only=True,
                    max_expansions=self.micro_bridge_budget,
                )
                micro_bridge, m_exp = micro_planner.plan_with_stats(
                    env.state,
                    act.preconditions,
                    max_expansions=self.micro_bridge_budget,
                )
                total_expansions += m_exp
                if micro_bridge is None:
                    # Escalate to post-discrepancy handler
                    disc_step = idx
                    repair_decision, abandon_reason, add_exp, tail_objs, spliced_id = (
                        self._handle_discrepancy(
                            env=env,
                            broken_plan=candidate_plan,
                            failed_index=idx,
                            delta_plus=frozenset(),
                            goal_state=goal_state,
                            domain=domain,
                            domain_edges=domain_edges,
                            prefix_objs=executed_action_objs,
                            used_skill_id=used_skill_id,
                        )
                    )
                    total_expansions += add_exp
                    executed.extend(a.name for a in tail_objs)
                    executed_action_objs.extend(tail_objs)
                    break

                for m_act in micro_bridge:
                    ok, _, _ = env.execute(m_act.name)
                    if ok:
                        executed.append(m_act.name)
                        executed_action_objs.append(self.operator_model.get(m_act.name))

            pre_s = env.state
            applied, post_s, _digest = env.execute(act.name)
            if applied:
                executed.append(act.name)

            d_minus, d_plus = self.operator_model.record_transition_discrepancy(
                act.name, pre_s, post_s
            )
            if not d_minus and not d_plus and applied:
                executed_action_objs.append(self.operator_model.get(act.name))
                idx += 1
                continue

            # Transition surprise! Trigger ILF variational free energy spike
            err_mag = float(len(d_minus) + len(d_plus) + (0 if applied else 1))
            self.ilf.observe_prediction_error("transition_predictor", err_mag)
            self.ilf.set_belief("transition_predictor", np.array([0.03, 0.91, 0.03, 0.03]))
            self.ilf.compute_q_star()
            fe_peak = max(fe_peak, float(self.ilf.variational_free_energy()))

            disc_step = idx
            rec_delta_minus = tuple(sorted(d_minus))
            rec_delta_plus = tuple(sorted(d_plus))
            prefix_with_applied = (
                [*executed_action_objs, self.operator_model.get(act.name)]
                if applied
                else list(executed_action_objs)
            )

            repair_decision, abandon_reason, add_exp, tail_objs, spliced_id = (
                self._handle_discrepancy(
                    env=env,
                    broken_plan=candidate_plan,
                    failed_index=idx,
                    delta_plus=d_plus,
                    goal_state=goal_state,
                    domain=domain,
                    domain_edges=domain_edges,
                    prefix_objs=prefix_with_applied,
                    used_skill_id=used_skill_id,
                )
            )
            total_expansions += add_exp
            executed.extend(a.name for a in tail_objs)
            executed_action_objs.extend(tail_objs)
            break

        reached = goal_state.issubset(env.state)
        if reached and consolidate_on_success and executed_action_objs and spliced_id is None:
            new_sid = consolidate_skill_id or f"macro_{domain}_{len(self.macro_store)}"
            refined_via_micro_bridge = len(executed_action_objs) != len(candidate_plan)
            if (
                used_skill_id is None
                or repair_decision != "NO_REPAIR_NEEDED"
                or refined_via_micro_bridge
            ):
                self.consolidate_trace(
                    skill_id=new_sid,
                    domain=domain,
                    plan=executed_action_objs,
                    goal_state=goal_state,
                    domain_edges=domain_edges,
                )
            elif used_skill_id is not None:
                self.skill_library.record_outcome(
                    used_skill_id, regime=domain, success=True, latency_ms=float(len(executed))
                )

        return EpisodeExecutionReport(
            arm=self.arm_name,
            goal_reached=reached,
            planner_expansions=total_expansions,
            executed_actions=tuple(executed),
            repair_decision=repair_decision,
            abandon_reason=abandon_reason,
            discrepancy_step=disc_step,
            delta_minus=rec_delta_minus,
            delta_plus=rec_delta_plus,
            free_energy_peak=round(fe_peak, 4),
            spliced_skill_id=spliced_id,
            analogy_trace=analogy_trace,
        )

    def _handle_discrepancy(
        self,
        *,
        env: StatefulPlanningEnvironment,
        broken_plan: Sequence[GOAPAction],
        failed_index: int,
        delta_plus: frozenset[str],
        goal_state: frozenset[str],
        domain: str,
        domain_edges: Sequence[RelationEdge],
        prefix_objs: Sequence[GOAPAction],
        used_skill_id: str | None,
    ) -> tuple[RepairDecisionKind, str, int, list[GOAPAction], str | None]:
        """Apply ``repair_mode`` policy ('selective', 'global_replan', or 'stubborn_reuse')."""
        expansions_spent = 0
        b_local = max(4, int(math.floor(self.alpha_local * self.max_global_expansions)))

        # Mode B: Global Replan Control (discards broken macro-skill immediately)
        if self.repair_mode == "global_replan":
            g_plan, exp = self._global_replan_and_execute(env, goal_state)
            return "ABANDON_MACRO_AND_REPLAN", "control_forced_global_replan", exp, g_plan, None

        suffix_raw = broken_plan[failed_index + 1 :]
        suffix_updated = [self.operator_model.get(a.name) for a in suffix_raw]

        # Mode C: Stubborn Reuse Diagnostic Control (forces old suffix without checking validity)
        if self.repair_mode == "stubborn_reuse":
            kernels = compute_regressed_kernels(suffix_updated, goal_state)
            target_w = kernels[0] if (kernels and suffix_updated) else goal_state
            planner = GOAPPlanner(
                self.operator_model.actions,
                simulate_only=True,
                max_expansions=self.max_global_expansions,
            )
            bridge, exp = planner.plan_with_stats(env.state, target_w)
            expansions_spent += exp
            tail_exec: list[GOAPAction] = []
            if bridge is not None:
                for b_act in [*bridge, *suffix_updated]:
                    ok, _, _ = env.execute(b_act.name)
                    if ok:
                        tail_exec.append(self.operator_model.get(b_act.name))
            return (
                "REPAIR_FAILED",
                "stubborn_reuse_forced_suffix",
                expansions_spent,
                tail_exec,
                None,
            )

        # Mode A: Credit-Localized Selective Repair with 3-Part Suffix Admissibility Gate
        # Check (C1): Non-empty suffix, unmutated suffix operators, and valid regressed kernel W_k
        if not suffix_updated:
            g_plan, exp = self._global_replan_and_execute(env, goal_state)
            self._penalize_skill(used_skill_id, domain)
            return (
                "ABANDON_MACRO_AND_REPLAN",
                "terminal_step_invalidated",
                exp,
                g_plan,
                None,
            )

        if any(a.name in self.operator_model.mutated_operators for a in suffix_updated):
            g_plan, exp = self._global_replan_and_execute(env, goal_state)
            self._penalize_skill(used_skill_id, domain)
            return (
                "ABANDON_MACRO_AND_REPLAN",
                "suffix_operator_mutated",
                exp,
                g_plan,
                None,
            )

        kernels = compute_regressed_kernels(suffix_updated, goal_state)
        if kernels is None:
            g_plan, exp = self._global_replan_and_execute(env, goal_state)
            self._penalize_skill(used_skill_id, domain)
            return (
                "ABANDON_MACRO_AND_REPLAN",
                "suffix_kernel_clobbered",
                exp,
                g_plan,
                None,
            )

        # Check (C2): No unrecoverable terminal blocker in unexpected side-effects delta_plus
        if self.operator_model.has_unrecoverable_blocker(delta_plus):
            g_plan, exp = self._global_replan_and_execute(env, goal_state)
            self._penalize_skill(used_skill_id, domain)
            return (
                "ABANDON_MACRO_AND_REPLAN",
                "unrecoverable_blocker_fluent",
                exp,
                g_plan,
                None,
            )

        # Forward simulation check of suffix from W_k
        w_k = kernels[0]
        sim_state = set(w_k)
        suffix_sim_valid = True
        for s_act in suffix_updated:
            if not s_act.preconditions.issubset(sim_state):
                suffix_sim_valid = False
                break
            sim_state = (sim_state - s_act.del_effects) | s_act.add_effects
        if not suffix_sim_valid or not goal_state.issubset(sim_state):
            g_plan, exp = self._global_replan_and_execute(env, goal_state)
            self._penalize_skill(used_skill_id, domain)
            return (
                "ABANDON_MACRO_AND_REPLAN",
                "suffix_simulation_failed_goal",
                exp,
                g_plan,
                None,
            )

        # Check (C3): Bounded local bridge search S_k^obs -> W_k within B_local
        local_planner = GOAPPlanner(
            self.operator_model.actions,
            simulate_only=True,
            max_expansions=b_local,
        )
        bridge, local_exp = local_planner.plan_with_stats(env.state, w_k, max_expansions=b_local)
        expansions_spent += local_exp

        if bridge is None:
            g_plan, g_exp = self._global_replan_and_execute(env, goal_state)
            self._penalize_skill(used_skill_id, domain)
            return (
                "ABANDON_MACRO_AND_REPLAN",
                "local_bridge_exceeded_budget",
                expansions_spent + g_exp,
                g_plan,
                None,
            )

        # Execute local bridge + preserved suffix!
        tail_executed: list[GOAPAction] = []
        for step_act in [*bridge, *suffix_updated]:
            ok, pre_next, _ = env.execute(step_act.name)
            if ok:
                tail_executed.append(self.operator_model.get(step_act.name))
            else:
                # Secondary unexpected mutation inside bridge/suffix -> fall back cleanly
                self.operator_model.record_transition_discrepancy(
                    step_act.name, env.state, pre_next
                )
                rem_plan, rem_exp = self._global_replan_and_execute(env, goal_state)
                expansions_spent += rem_exp
                tail_executed.extend(rem_plan)
                return (
                    "ABANDON_MACRO_AND_REPLAN",
                    "secondary_suffix_discrepancy",
                    expansions_spent,
                    tail_executed,
                    None,
                )

        # Reconsolidate the spliced macro-skill [prefix, *bridge, *suffix] for future variants!
        spliced_id: str | None = None
        if goal_state.issubset(env.state):
            full_repaired_seq = [*prefix_objs, *tail_executed]
            spliced_id = f"{used_skill_id or 'skill'}_spliced_{domain}"
            self.consolidate_trace(
                skill_id=spliced_id,
                domain=domain,
                plan=full_repaired_seq,
                goal_state=goal_state,
                domain_edges=domain_edges,
            )
            if used_skill_id is not None:
                orig_sk = self.skill_library.get(used_skill_id)
                if orig_sk is not None:
                    self.reconsolidation.record_context_update(used_skill_id, now=1.0)
                    self.reconsolidation.commit(orig_sk)
        return "SELECTIVE_LOCAL_REPAIR", "", expansions_spent, tail_executed, spliced_id

    def _global_replan_and_execute(
        self,
        env: StatefulPlanningEnvironment,
        goal_state: frozenset[str],
    ) -> tuple[list[GOAPAction], int]:
        planner = GOAPPlanner(
            self.operator_model.actions,
            simulate_only=True,
            max_expansions=self.max_global_expansions,
        )
        plan, exp = planner.plan_with_stats(env.state, goal_state)
        if plan is None:
            return [], exp
        ran: list[GOAPAction] = []
        for a in plan:
            ok, post_s, _ = env.execute(a.name)
            if ok:
                ran.append(self.operator_model.get(a.name))
            else:
                self.operator_model.record_transition_discrepancy(a.name, env.state, post_s)
                break
        return ran, exp

    def _penalize_skill(self, skill_id: str | None, domain: str) -> None:
        if skill_id is not None:
            self.skill_library.record_outcome(
                skill_id, regime=f"{domain}_mutated", success=False, latency_ms=50.0
            )


__all__ = [
    "AnalogicalRoleMapper",
    "AnalogyAuditTrace",
    "EmpiricalOperatorModel",
    "EpisodeExecutionReport",
    "ExperientialCognitiveAgent",
    "LiftedAtom",
    "ParameterizedStep",
    "RepairDecisionKind",
    "RoleParameterizedMacroSkill",
    "RoleTopologyProfile",
    "StatefulPlanningEnvironment",
    "compute_regressed_kernels",
    "extract_macro_skill",
    "format_structured_atom",
    "parse_structured_atom",
]
