"""Fail-closed Closed-World Symbol Grounding & Lagged Provenance Quarantine (T251).

Bridges continuous/textual ``ThinkResult`` outputs from ``SpikingBrainCortex`` to
deterministic symbolic engines (``StructuralCausalDAG`` and ``GOAPPlanner``) while
enforcing Invariants G1 & G2 of ``T251_GROUNDED_DUAL_SPEED_BRIDGE_SPEC.md``:

1. **Zero direct graph/state mutation from generated text**: LLM-proposed causal
   edges enter quarantine as ``UNVERIFIED`` candidates on ``HypothesisStack`` and
   never enter ``StructuralCausalDAG`` without repeated non-zero-lag verified
   ``ObservationDigest`` temporal precedence and pre-commit DAG acyclicity.
2. **Closed-world symbol registry**: unknown predicates, causal nodes, or action
   identifiers fail closed (``rejected_unknown_symbol``) with zero silent coercion.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections import deque
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np

from ..aacm.plasticity import ProposalOnlyEdgeGrower
from ..routing import GOAPAction, HypothesisEntry, HypothesisStack
from ..spiking.causal import CausalEdge, StructuralCausalDAG, spike_temporal_asymmetry
from ..spiking_brain.truth_engine import ObservationDigest

CandidateEdgeStatus = Literal[
    "UNVERIFIED",
    "VERIFIED",
    "CYCLE_CONFLICT",
    "LOW_CONFIDENCE",
]
GroundingStatus = Literal[
    "grounded_clean",
    "quarantined",
    "rejected_unknown_symbol",
    "rejected_schema",
]

_ALLOWED_SCHEMA_KEYS: frozenset[str] = frozenset(
    {
        "observed_facts",
        "goal_predicates",
        "proposed_edges",
        "proposed_action",
        "parser_confidence",
        "answer",
    }
)

_FENCED_JSON_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)


def _canonical_json_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _normalize_symbol(token: str) -> str:
    return token.strip().lower()


@dataclass(frozen=True)
class GroundingRejection:
    """Structured rejection reason emitted when a payload violates schema or vocabulary."""

    reason: str
    field: str
    token: str


@dataclass
class CandidateEdge:
    """Quarantined causal edge awaiting lagged verifiable provenance (T251 §4.1)."""

    source: str
    target: str
    max_parser_confidence: float
    proposal_count: int = 1
    lagged_cooccurrences: int = 0
    asymmetry: float = 0.0
    status: CandidateEdgeStatus = "UNVERIFIED"
    provenance_digests: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.source or not self.target or self.source == self.target:
            raise ValueError("source and target must be distinct non-empty symbols")
        if not math.isfinite(self.max_parser_confidence) or not (
            0.0 <= self.max_parser_confidence <= 1.0
        ):
            raise ValueError("max_parser_confidence must be finite and in [0, 1]")


@dataclass(frozen=True)
class GroundedPayload:
    """Validated result of grounding one structured ``ThinkResult`` payload."""

    status: GroundingStatus
    observed_facts: frozenset[str]
    goal_predicates: frozenset[str]
    proposed_action: GOAPAction | None
    proposed_edges: tuple[tuple[str, str], ...]
    promoted_edges: tuple[CausalEdge, ...]
    quarantined_edges: tuple[tuple[str, str], ...]
    cycle_conflicts: tuple[tuple[str, str], ...]
    rejections: tuple[GroundingRejection, ...]
    parser_confidence: float
    answer_text: str
    registry_digest: str


class SymbolRegistry:
    """Immutable closed-world registry of canonical predicates, causal nodes, and actions."""

    def __init__(
        self,
        *,
        predicates: Iterable[str],
        causal_nodes: Iterable[str],
        actions: Sequence[GOAPAction] = (),
        aliases: Mapping[str, str] | None = None,
    ) -> None:
        norm_preds = frozenset(_normalize_symbol(p) for p in predicates if _normalize_symbol(p))
        norm_nodes = frozenset(_normalize_symbol(n) for n in causal_nodes if _normalize_symbol(n))
        if not norm_preds and not norm_nodes:
            raise ValueError("SymbolRegistry requires at least one predicate or causal node")

        action_map: dict[str, GOAPAction] = {}
        for act in actions:
            act_name = _normalize_symbol(act.name)
            if not act_name:
                raise ValueError("action name must be non-empty")
            norm_pre = frozenset(_normalize_symbol(p) for p in act.preconditions)
            norm_add = frozenset(_normalize_symbol(p) for p in act.add_effects)
            norm_del = frozenset(_normalize_symbol(p) for p in act.del_effects)
            unknown_in_act = (norm_pre | norm_add | norm_del) - norm_preds
            if unknown_in_act:
                raise ValueError(
                    f"GOAPAction {act.name!r} references unregistered predicates: "
                    f"{sorted(unknown_in_act)}"
                )
            action_map[act_name] = GOAPAction(
                name=act_name,
                preconditions=norm_pre,
                add_effects=norm_add,
                del_effects=norm_del,
                cost=act.cost,
            )

        known_universe = norm_preds | norm_nodes | set(action_map.keys())
        norm_aliases: dict[str, str] = {}
        if aliases is not None:
            for raw_k, raw_v in aliases.items():
                k = _normalize_symbol(raw_k)
                v = _normalize_symbol(raw_v)
                if not k or not v:
                    raise ValueError("alias keys and targets must be non-empty")
                if v not in known_universe:
                    raise ValueError(f"alias {k!r} maps to unregistered target {v!r}")
                norm_aliases[k] = v

        self._predicates: frozenset[str] = norm_preds
        self._causal_nodes: frozenset[str] = norm_nodes
        self._actions: dict[str, GOAPAction] = action_map
        self._aliases: dict[str, str] = norm_aliases
        self._digest: str = _canonical_json_sha256(
            {
                "predicates": sorted(self._predicates),
                "causal_nodes": sorted(self._causal_nodes),
                "actions": {
                    k: {
                        "preconditions": sorted(a.preconditions),
                        "add_effects": sorted(a.add_effects),
                        "del_effects": sorted(a.del_effects),
                        "cost": a.cost,
                    }
                    for k, a in sorted(self._actions.items())
                },
                "aliases": dict(sorted(self._aliases.items())),
            }
        )

    @property
    def predicates(self) -> frozenset[str]:
        return self._predicates

    @property
    def causal_nodes(self) -> frozenset[str]:
        return self._causal_nodes

    @property
    def actions(self) -> tuple[GOAPAction, ...]:
        return tuple(self._actions[k] for k in sorted(self._actions))

    @property
    def registry_digest(self) -> str:
        return self._digest

    def _canonicalize(self, token: str) -> str:
        norm = _normalize_symbol(token)
        return self._aliases.get(norm, norm)

    def resolve_predicate(self, token: str) -> str | None:
        if not isinstance(token, str) or not token.strip():
            return None
        cand = self._canonicalize(token)
        return cand if cand in self._predicates else None

    def resolve_node(self, token: str) -> str | None:
        if not isinstance(token, str) or not token.strip():
            return None
        cand = self._canonicalize(token)
        return cand if cand in self._causal_nodes else None

    def resolve_action(self, token: str) -> GOAPAction | None:
        if not isinstance(token, str) or not token.strip():
            return None
        cand = self._canonicalize(token)
        return self._actions.get(cand)


def _parse_strict_json_object(raw_text: str) -> dict[str, Any] | None:
    """Extract and strictly validate a JSON object (rejects NaN/Infinity and extra types)."""
    if not isinstance(raw_text, str):
        return None
    stripped = raw_text.strip()
    if not stripped:
        return None

    candidate = stripped
    match = _FENCED_JSON_RE.search(stripped)
    if match is not None:
        candidate = match.group(1).strip()

    def _forbid_nonfinite(constant: str) -> Any:
        raise ValueError(f"non-finite JSON constant forbidden: {constant}")

    try:
        parsed = json.loads(candidate, parse_constant=_forbid_nonfinite)
    except (ValueError, TypeError):
        return None

    return parsed if isinstance(parsed, dict) else None


@dataclass
class _VerifiedTraceStep:
    active_nodes: frozenset[str]
    result_digest: str


class SymbolicGroundingAdapter:
    """Fail-closed grounding parser & lagged-provenance causal quarantine (T251 §4.1)."""

    def __init__(
        self,
        registry: SymbolRegistry,
        *,
        initial_edges: Sequence[CausalEdge] = (),
        tau_ground: float = 0.70,
        min_cooccurrences: int = 3,
        max_lag: int = 3,
        tau_asymmetry: float = 0.25,
        max_trace_steps: int = 256,
        hypothesis_stack: HypothesisStack | None = None,
        edge_grower: ProposalOnlyEdgeGrower | None = None,
    ) -> None:
        if not math.isfinite(tau_ground) or not (0.0 <= tau_ground <= 1.0):
            raise ValueError("tau_ground must be finite and in [0, 1]")
        if min_cooccurrences < 1:
            raise ValueError("min_cooccurrences must be >= 1")
        if max_lag < 1:
            raise ValueError("max_lag must be >= 1")
        if not math.isfinite(tau_asymmetry) or not (0.0 < tau_asymmetry <= 1.0):
            raise ValueError("tau_asymmetry must be finite and in (0, 1]")
        if max_trace_steps < 4:
            raise ValueError("max_trace_steps must be >= 4")

        self.registry = registry
        self.tau_ground = float(tau_ground)
        self.min_cooccurrences = int(min_cooccurrences)
        self.max_lag = int(max_lag)
        self.tau_asymmetry = float(tau_asymmetry)
        self.hypothesis_stack = hypothesis_stack or HypothesisStack(max_depth=64)
        self.edge_grower = edge_grower or ProposalOnlyEdgeGrower(
            proposal_threshold=0.55,
            min_observations=min_cooccurrences,
        )

        # Validate initial edges against closed causal_nodes and DAG acyclicity
        node_list = sorted(self.registry.causal_nodes)
        verified_map: dict[tuple[str, str], CausalEdge] = {}
        for edge in initial_edges:
            src = self.registry.resolve_node(edge.source)
            dst = self.registry.resolve_node(edge.target)
            if src is None or dst is None:
                raise ValueError(
                    f"initial edge ({edge.source!r} -> {edge.target!r}) uses unregistered node"
                )
            verified_map[(src, dst)] = CausalEdge(
                source=src,
                target=dst,
                weight=edge.weight,
                asymmetry=edge.asymmetry,
            )
        if node_list:
            _ = StructuralCausalDAG(nodes=node_list, edges=tuple(verified_map.values()))

        self._verified_edges: dict[tuple[str, str], CausalEdge] = verified_map
        self._candidates: dict[tuple[str, str], CandidateEdge] = {}
        self._hypotheses_by_pair: dict[tuple[str, str], HypothesisEntry] = {}
        self._obs_trace: deque[_VerifiedTraceStep] = deque(maxlen=max_trace_steps)

    @property
    def verified_edges(self) -> tuple[CausalEdge, ...]:
        return tuple(self._verified_edges.values())

    @property
    def candidate_edges(self) -> dict[tuple[str, str], CandidateEdge]:
        return dict(self._candidates)

    def active_dag(self) -> StructuralCausalDAG:
        """Return an immutable ``StructuralCausalDAG`` over verified edges only."""
        nodes = sorted(self.registry.causal_nodes)
        if not nodes:
            raise ValueError("SymbolRegistry has no causal_nodes configured for DAG construction")
        return StructuralCausalDAG(nodes=nodes, edges=tuple(self._verified_edges.values()))

    def record_verified_observation(
        self,
        active_nodes: Iterable[str],
        digest: ObservationDigest,
    ) -> bool:
        """Append one SHA-256-anchored tool/sensor observation step for lagged causal checks.

        Returns ``True`` if recorded, ``False`` if ``digest`` is marked unverifiable or
        non-supporting (Invariant G1). Raises ``ValueError`` if any node is outside
        ``SymbolRegistry.causal_nodes`` (Invariant G2).
        """
        if not digest.verifiable or not digest.supports_claims or not digest.result_digest:
            return False

        resolved: set[str] = set()
        for raw_node in active_nodes:
            canon = self.registry.resolve_node(raw_node)
            if canon is None:
                raise ValueError(f"unregistered causal node in verified observation: {raw_node!r}")
            resolved.add(canon)

        self._obs_trace.append(
            _VerifiedTraceStep(active_nodes=frozenset(resolved), result_digest=digest.result_digest)
        )

        # Update symmetric co-activation tracker purely as a proposal salience monitor
        activations = {
            n: (1.0 if n in resolved else 0.0) for n in sorted(self.registry.causal_nodes)
        }
        if activations:
            self.edge_grower.observe_and_propose(activations, set(self._verified_edges.keys()))
        return True

    def _compute_lagged_support(self) -> dict[tuple[str, str], tuple[int, float, tuple[str, ...]]]:
        """Compute non-zero-lag precedence counts and asymmetry across verified trace steps."""
        nodes = sorted(self.registry.causal_nodes)
        n_steps = len(self._obs_trace)
        if not nodes or n_steps < 2:
            return {}

        idx_of = {n: i for i, n in enumerate(nodes)}
        activity = np.zeros((len(nodes), n_steps), dtype=np.float64)
        steps_list = list(self._obs_trace)
        for t, step in enumerate(steps_list):
            for n in step.active_nodes:
                activity[idx_of[n], t] = 1.0

        discovered = spike_temporal_asymmetry(
            activity,
            max_lag=self.max_lag,
            min_cooccurrences=self.min_cooccurrences,
            threshold=self.tau_asymmetry,
            ids=nodes,
        )

        fired = activity > 0.0
        support: dict[tuple[str, str], tuple[int, float, tuple[str, ...]]] = {}
        for edge in discovered:
            i, j = idx_of[edge.source], idx_of[edge.target]
            fwd_hits = 0
            digests: list[str] = []
            max_l = min(self.max_lag, n_steps - 1)
            for lag in range(1, max_l + 1):
                mask = fired[i, : n_steps - lag] & fired[j, lag:]
                hit_indices = np.flatnonzero(mask)
                fwd_hits += int(hit_indices.size)
                for t_idx in hit_indices:
                    dig = steps_list[int(t_idx) + lag].result_digest
                    if dig not in digests:
                        digests.append(dig)
            if fwd_hits >= self.min_cooccurrences:
                support[(edge.source, edge.target)] = (
                    fwd_hits,
                    float(edge.asymmetry),
                    tuple(digests[-8:]),
                )
        return support

    def _push_or_update_hypothesis(
        self,
        pair: tuple[str, str],
        conf: float,
        *,
        pro_note: str | None = None,
        con_note: str | None = None,
    ) -> None:
        entry = self._hypotheses_by_pair.get(pair)
        if entry is None:
            hyp_id = f"edge:{pair[0]}->{pair[1]}"
            entry = HypothesisEntry(hypothesis_id=hyp_id, match_score=conf)
            if self.hypothesis_stack.active_count() < self.hypothesis_stack.max_depth:
                try:
                    self.hypothesis_stack.push(entry)
                except ValueError:
                    self.hypothesis_stack.prune_weak(min_score=0.50)
                    self.hypothesis_stack.backtrack()
            self._hypotheses_by_pair[pair] = entry
        else:
            entry.match_score = max(entry.match_score, conf)
        if pro_note and pro_note not in entry.pros:
            entry.pros.append(pro_note)
        if con_note and con_note not in entry.cons:
            entry.cons.append(con_note)

    def ground(
        self,
        raw_text: str,
        *,
        calibrated_confidence: float | None = None,
        verified_observations: Sequence[tuple[Sequence[str], ObservationDigest]] = (),
    ) -> GroundedPayload:
        """Validate ``raw_text`` against JSON schema + ``SymbolRegistry`` and quarantine edges."""
        if calibrated_confidence is not None and (
            not math.isfinite(calibrated_confidence) or not (0.0 <= calibrated_confidence <= 1.0)
        ):
            raise ValueError("calibrated_confidence must be finite and in [0, 1]")

        for obs_nodes, obs_digest in verified_observations:
            self.record_verified_observation(obs_nodes, obs_digest)

        parsed = _parse_strict_json_object(raw_text)
        if parsed is None:
            return self._empty_payload(
                status="rejected_schema",
                rejections=(GroundingRejection(reason="invalid_json_object", field="$", token=""),),
            )

        extra_keys = set(parsed.keys()) - _ALLOWED_SCHEMA_KEYS
        if extra_keys:
            return self._empty_payload(
                status="rejected_schema",
                rejections=tuple(
                    GroundingRejection(reason="unexpected_schema_key", field=k, token=k)
                    for k in sorted(extra_keys)
                ),
            )

        raw_conf = parsed.get("parser_confidence", 0.75)
        if (
            isinstance(raw_conf, bool)
            or not isinstance(raw_conf, int | float)
            or not math.isfinite(float(raw_conf))
            or not (0.0 <= float(raw_conf) <= 1.0)
        ):
            return self._empty_payload(
                status="rejected_schema",
                rejections=(
                    GroundingRejection(
                        reason="invalid_parser_confidence",
                        field="parser_confidence",
                        token=repr(raw_conf),
                    ),
                ),
            )
        parser_conf = float(raw_conf)
        # Apply optional calibration scaling factor while keeping parser extraction confidence
        # distinct from Fast-Path turn routing confidence (which triggers Slow-Path escalation).
        eff_conf = (
            float(min(1.0, parser_conf * (0.85 + 0.15 * float(calibrated_confidence))))
            if calibrated_confidence is not None
            else parser_conf
        )

        raw_answer = parsed.get("answer", "")
        if not isinstance(raw_answer, str):
            return self._empty_payload(
                status="rejected_schema",
                rejections=(
                    GroundingRejection(
                        reason="invalid_answer_type",
                        field="answer",
                        token=type(raw_answer).__name__,
                    ),
                ),
            )

        rejections: list[GroundingRejection] = []
        schema_errors: list[GroundingRejection] = []

        # 1. Validate observed_facts
        obs_facts: set[str] = set()
        raw_facts = parsed.get("observed_facts", [])
        if not isinstance(raw_facts, list):
            schema_errors.append(
                GroundingRejection("expected_list", "observed_facts", type(raw_facts).__name__)
            )
        else:
            for item in raw_facts:
                if not isinstance(item, str):
                    schema_errors.append(
                        GroundingRejection("expected_string", "observed_facts", repr(item))
                    )
                    continue
                canon = self.registry.resolve_predicate(item)
                if canon is None:
                    rejections.append(
                        GroundingRejection("unknown_predicate", "observed_facts", item)
                    )
                else:
                    obs_facts.add(canon)

        # 2. Validate goal_predicates
        goal_preds: set[str] = set()
        raw_goals = parsed.get("goal_predicates", [])
        if not isinstance(raw_goals, list):
            schema_errors.append(
                GroundingRejection("expected_list", "goal_predicates", type(raw_goals).__name__)
            )
        else:
            for item in raw_goals:
                if not isinstance(item, str):
                    schema_errors.append(
                        GroundingRejection("expected_string", "goal_predicates", repr(item))
                    )
                    continue
                canon = self.registry.resolve_predicate(item)
                if canon is None:
                    rejections.append(
                        GroundingRejection("unknown_predicate", "goal_predicates", item)
                    )
                else:
                    goal_preds.add(canon)

        # 3. Validate proposed_action
        resolved_action: GOAPAction | None = None
        raw_act = parsed.get("proposed_action")
        if raw_act is not None and raw_act != "":
            if not isinstance(raw_act, str):
                schema_errors.append(
                    GroundingRejection("expected_string", "proposed_action", repr(raw_act))
                )
            else:
                resolved_action = self.registry.resolve_action(raw_act)
                if resolved_action is None:
                    rejections.append(
                        GroundingRejection("unknown_action", "proposed_action", raw_act)
                    )

        # 4. Validate proposed_edges
        edge_pairs: list[tuple[str, str]] = []
        raw_edges = parsed.get("proposed_edges", [])
        if not isinstance(raw_edges, list):
            schema_errors.append(
                GroundingRejection("expected_list", "proposed_edges", type(raw_edges).__name__)
            )
        else:
            for entry in raw_edges:
                src_raw: Any = None
                dst_raw: Any = None
                if isinstance(entry, list) and len(entry) == 2:
                    src_raw, dst_raw = entry[0], entry[1]
                elif isinstance(entry, dict) and set(entry.keys()) <= {"source", "target"}:
                    src_raw, dst_raw = entry.get("source"), entry.get("target")
                else:
                    schema_errors.append(
                        GroundingRejection("invalid_edge_entry", "proposed_edges", repr(entry))
                    )
                    continue

                if not isinstance(src_raw, str) or not isinstance(dst_raw, str):
                    schema_errors.append(
                        GroundingRejection("expected_string_nodes", "proposed_edges", repr(entry))
                    )
                    continue

                src_canon = self.registry.resolve_node(src_raw)
                dst_canon = self.registry.resolve_node(dst_raw)
                if src_canon is None:
                    rejections.append(
                        GroundingRejection("unknown_causal_node", "proposed_edges.source", src_raw)
                    )
                if dst_canon is None:
                    rejections.append(
                        GroundingRejection("unknown_causal_node", "proposed_edges.target", dst_raw)
                    )
                if src_canon is not None and dst_canon is not None:
                    if src_canon == dst_canon:
                        schema_errors.append(
                            GroundingRejection("self_loop_forbidden", "proposed_edges", src_canon)
                        )
                    else:
                        pair = (src_canon, dst_canon)
                        if pair not in edge_pairs:
                            edge_pairs.append(pair)

        if schema_errors:
            return self._empty_payload(
                status="rejected_schema",
                rejections=tuple(schema_errors),
                parser_confidence=eff_conf,
                answer_text=raw_answer,
            )

        # Invariant G2: fail-closed on any out-of-vocabulary symbol (zero partial state mutation)
        if rejections:
            return self._empty_payload(
                status="rejected_unknown_symbol",
                rejections=tuple(rejections),
                parser_confidence=eff_conf,
                answer_text=raw_answer,
            )

        # 5. Quarantine & evaluate promotion for proposed causal edges (Invariant G1)
        lagged_support = self._compute_lagged_support()
        promoted: list[CausalEdge] = []
        quarantined: list[tuple[str, str]] = []
        cycle_conflicts: list[tuple[str, str]] = []
        nodes_sorted = sorted(self.registry.causal_nodes)

        for pair in edge_pairs:
            src, dst = pair
            if pair in self._verified_edges:
                continue

            cand = self._candidates.get(pair)
            if cand is None:
                cand = CandidateEdge(source=src, target=dst, max_parser_confidence=eff_conf)
                self._candidates[pair] = cand
            else:
                cand.proposal_count += 1
                cand.max_parser_confidence = max(cand.max_parser_confidence, eff_conf)

            support_info = lagged_support.get(pair)
            if support_info is not None:
                hits, asym, digests = support_info
                cand.lagged_cooccurrences = hits
                cand.asymmetry = asym
                cand.provenance_digests = digests

            # Pre-commit DAG acyclicity check against currently verified causal structure
            probe_edge = CausalEdge(
                source=src,
                target=dst,
                weight=round(0.5 + 0.4 * abs(support_info[1]), 4) if support_info else 0.5,
                asymmetry=support_info[1] if support_info else 1.0,
            )
            trial_edges = [*self._verified_edges.values(), probe_edge]
            try:
                _ = StructuralCausalDAG(nodes=nodes_sorted, edges=trial_edges)
            except ValueError:
                cand.status = "CYCLE_CONFLICT"
                self._push_or_update_hypothesis(
                    pair,
                    min(eff_conf, 0.10),
                    con_note="cycle_conflict_with_active_dag",
                )
                if pair in self._hypotheses_by_pair:
                    self._hypotheses_by_pair[pair].match_score = 0.05
                    self._hypotheses_by_pair[pair].cons.append("topological_cycle")
                self.hypothesis_stack.prune_weak(min_score=0.20)
                cycle_conflicts.append(pair)
                continue

            if eff_conf < self.tau_ground:
                cand.status = "LOW_CONFIDENCE"
                self._push_or_update_hypothesis(pair, eff_conf, con_note="below_tau_ground")
                quarantined.append(pair)
                continue

            if support_info is None:
                cand.status = "UNVERIFIED"
                self._push_or_update_hypothesis(pair, eff_conf, con_note="awaiting_lagged_digest")
                quarantined.append(pair)
                continue

            cand.status = "VERIFIED"
            self._verified_edges[pair] = probe_edge
            self._push_or_update_hypothesis(pair, eff_conf, pro_note="verified_lagged_provenance")
            promoted.append(probe_edge)

        final_status: GroundingStatus = (
            "quarantined" if (quarantined or cycle_conflicts) else "grounded_clean"
        )
        return GroundedPayload(
            status=final_status,
            observed_facts=frozenset(obs_facts),
            goal_predicates=frozenset(goal_preds),
            proposed_action=resolved_action,
            proposed_edges=tuple(edge_pairs),
            promoted_edges=tuple(promoted),
            quarantined_edges=tuple(quarantined),
            cycle_conflicts=tuple(cycle_conflicts),
            rejections=(),
            parser_confidence=eff_conf,
            answer_text=raw_answer,
            registry_digest=self.registry.registry_digest,
        )

    def _empty_payload(
        self,
        *,
        status: GroundingStatus,
        rejections: tuple[GroundingRejection, ...],
        parser_confidence: float = 0.0,
        answer_text: str = "",
    ) -> GroundedPayload:
        return GroundedPayload(
            status=status,
            observed_facts=frozenset(),
            goal_predicates=frozenset(),
            proposed_action=None,
            proposed_edges=(),
            promoted_edges=(),
            quarantined_edges=(),
            cycle_conflicts=(),
            rejections=rejections,
            parser_confidence=parser_confidence,
            answer_text=answer_text,
            registry_digest=self.registry.registry_digest,
        )


__all__ = [
    "CandidateEdge",
    "CandidateEdgeStatus",
    "GroundedPayload",
    "GroundingRejection",
    "GroundingStatus",
    "SymbolRegistry",
    "SymbolicGroundingAdapter",
]
