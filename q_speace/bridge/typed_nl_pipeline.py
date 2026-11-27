"""T257 — Typed-DAG Multi-Role Natural-Language Grounding & Clause-Polarity Pipeline.

Wires ``T256`` primitives (:class:`BatchRoleDeliberationCodec`, :class:`TypedComputationalDAG`,
:class:`ContractSpec` / :class:`ExecutionTicket`, :class:`KineticaRegimeController`, and
:class:`MyelinationRegistry`) into a fail-closed 4-stage neuro-symbolic belief-revision
pipeline:

    decode_roles -> polarity_scope_audit -> closed_registry_ground -> mutex_belief_revision

Anti-Goodhart Invariant (T208):
- Zero predicate invention: ``polarity_scope_audit`` screens and reclassifies ONLY predicates
  proposed by the upstream generative model (never injecting unextracted domain facts).
- ``mutex_belief_revision`` applies symmetric ontology ``mutex_pairs`` purely subtractively
  against ``prior_state``.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ..aacm.typed_dag import ContractSpec, ExecutionTicket, FieldConstraint, TypedComputationalDAG
from ..spiking.morphogenesis import CognitiveRegime, KineticaRegimeController
from ..spiking_brain.myelination import BatchRoleDeliberationCodec, MyelinationRegistry
from .grounding import (
    GroundedPayload,
    SymbolicGroundingAdapter,
    SymbolRegistry,
    apply_belief_revision,
    compute_effective_retracted_facts,
)

_GENERIC_GLOSS_WORDS: frozenset[str] = frozenset(
    {
        "attivo",
        "attiva",
        "attivi",
        "pronto",
        "pronta",
        "iniziale",
        "primario",
        "primaria",
        "secondario",
        "secondaria",
        "isolato",
        "isolata",
        "anomalia",
        "allarme",
        "modulo",
        "canale",
        "condotto",
        "portello",
        "camera",
        "unita",
        "unità",
        "baia",
        "anello",
        "stato",
        "completato",
        "eseguito",
        "operativa",
        "irreversibile",
        "distrattore",
    }
)

_DISTRACTOR_MARKERS: tuple[str, ...] = (
    "distrattor",
    "solo in test",
    "solo un test",
    "chiuso per test",
    "modulo test",
    "modulo di test",
    "collettore test",
    "sensore di test",
    "ramo di test",
    "collaudo",
    "fuori linea",
    "in manutenzione",
    "scollegat",
    "irrilevant",
    "da ignorare",
    "non toccare",
    "ignora il modulo",
    "ignora il collettore",
    "ignora il sensore",
)

_GOAL_CLAUSE_MARKERS: tuple[str, ...] = (
    "completa il ",
    "porta comunque online",
    "porta online",
    "prima di poter ",
    "prima di rilasciare",
)

_CLEFT_AFFIRMATIVE_OVERRIDES: tuple[str, ...] = (
    "a mancare",
    "non serve ",
    "erano già",
    "era già",
    "risultavano già",
    "aveva già",
    "già attiv",
    "già armat",
    "già sigillat",
    "già in sede",
    "già silenziat",
    "già eseguit",
    "confermat",
)

_NEGATION_PREFIXES: tuple[str, ...] = (
    "non ",
    "né ",
    "nessun",
    "nessuna",
    "niente ",
    "senza ",
    "perso ",
    "persa ",
    "perso l'",
    "invece del ",
    "invece dello ",
    "invece della ",
    "invece di ",
)


def _extract_atom_args(atom: str) -> tuple[str, tuple[str, ...]]:
    s = atom.strip().lower()
    lpar = s.find("(")
    if lpar < 0 or not s.endswith(")"):
        return s, ()
    head = s[:lpar].strip()
    args = tuple(a.strip() for a in s[lpar + 1 : -1].split(",") if a.strip())
    return head, args


def _distinctive_stems(atom: str, gloss: str) -> tuple[str, ...]:
    head, args = _extract_atom_args(atom)
    arg_set = set(args)
    raw_tokens = re.findall(r"[a-zàèéìòù0-9]+", f"{head.replace('_', ' ')} {gloss.lower()}")
    specific: list[str] = []
    fallback: list[str] = []
    for tok in raw_tokens:
        if len(tok) < 4 or tok in arg_set or tok.isdigit():
            continue
        stem = tok[:5] if len(tok) >= 6 else tok
        if tok in _GENERIC_GLOSS_WORDS:
            if stem not in fallback:
                fallback.append(stem)
        elif stem not in specific:
            specific.append(stem)
    return tuple(specific if specific else fallback)


def _extract_json_dicts(section_text: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    decoder = json.JSONDecoder()
    idx = 0
    n = len(section_text)
    while idx < n:
        brace = section_text.find("{", idx)
        if brace < 0:
            break
        try:
            obj, end_rel = decoder.raw_decode(section_text[brace:])
            if isinstance(obj, dict):
                out.append(obj)
            idx = brace + max(1, end_rel)
        except ValueError:
            idx = brace + 1
    return out


@dataclass(frozen=True)
class TypedPipelineResult:
    """Auditable output of :class:`TypedMultiRoleNLGroundingPipeline`."""

    grounded: GroundedPayload
    revised_belief_state: frozenset[str]
    effective_retracted_facts: frozenset[str]
    dropped_candidates: tuple[str, ...]
    reclassified_retractions: tuple[str, ...]
    critic_section_used: bool
    kinetica_regime: str
    tickets: Mapping[str, ExecutionTicket]
    myelination_top_paths: tuple[tuple[str, str, float], ...]


class ClausePolarityAuditor:
    """Recall-preserving syntactic clause-polarity and provenance screener (T257 §3.2)."""

    @staticmethod
    def split_clauses(text: str) -> list[str]:
        parts = re.split(
            r"(?:[.;:!]+|\bma\b|\bmentre\b|\bperò\b|\bpoiché\b|\bperché\b|\ba causa di\b|\bper via di\b|\bper un\b)",
            text.lower(),
        )
        return [p.strip() for p in parts if p and p.strip()]

    @classmethod
    def audit_candidates(
        cls,
        *,
        operator_message: str,
        prior_state: frozenset[str],
        predicate_glosses: Mapping[str, str],
        candidate_observed: list[str],
        candidate_retracted: list[str],
    ) -> tuple[list[str], list[str], list[str], list[str]]:
        """Screen LLM-proposed candidates against clause polarity & entity mention."""
        msg_low = operator_message.lower()
        clauses = cls.split_clauses(operator_message)
        gloss_low = {k.strip().lower(): v for k, v in predicate_glosses.items()}
        prior_low = {p.strip().lower() for p in prior_state}

        kept_observed: list[str] = []
        kept_retracted: list[str] = []
        dropped: list[str] = []
        reclassified: list[str] = []

        def _clause_disposition(atom_norm: str) -> str:
            """Return 'affirmative', 'negated', or 'ungrounded' for ``atom_norm``."""
            _head, args = _extract_atom_args(atom_norm)
            if any(arg not in msg_low for arg in args):
                return "ungrounded"

            gloss = gloss_low.get(atom_norm, "")
            stems = _distinctive_stems(atom_norm, gloss)
            if not stems:
                return "ungrounded"

            saw_affirmative = False
            saw_negated = False
            for cl in clauses:
                if any(dm in cl for dm in _DISTRACTOR_MARKERS):
                    # Note: parenthetical distractor remark inside an active clause
                    cl_clean = re.sub(r"\([^)]*\)", " ", cl)
                    if any(dm in cl_clean for dm in _DISTRACTOR_MARKERS):
                        continue
                else:
                    cl_clean = cl

                # Strip subordinate future-goal tail ("prima di poter...", "prima di rilasciare...")
                for gm in _GOAL_CLAUSE_MARKERS:
                    gm_idx = cl_clean.find(gm)
                    if gm_idx == 0:
                        cl_clean = ""
                        break
                    if gm_idx > 0:
                        cl_clean = cl_clean[:gm_idx].strip()
                if not cl_clean:
                    continue
                if args and not any(arg in cl_clean for arg in args):
                    continue

                matched_positions = [cl_clean.find(st) for st in stems if cl_clean.find(st) >= 0]
                if not matched_positions:
                    continue

                if any(ov in cl_clean for ov in _CLEFT_AFFIRMATIVE_OVERRIDES):
                    saw_affirmative = True
                    continue

                pos = min(matched_positions)
                win_start = max(0, pos - 34)
                prefix_sub = cl_clean[win_start:pos]
                if "," in prefix_sub:
                    prefix_sub = prefix_sub.rsplit(",", 1)[-1]
                win_end = min(len(cl_clean), pos + 42)
                window = " " + prefix_sub + cl_clean[pos:win_end] + " "
                if any(neg in window for neg in _NEGATION_PREFIXES):
                    saw_negated = True
                else:
                    saw_affirmative = True

            if saw_negated and not saw_affirmative:
                return "negated"
            if saw_affirmative:
                return "affirmative"
            return "ungrounded"

        for raw_obs in dict.fromkeys(x.strip().lower() for x in candidate_observed if x.strip()):
            disp = _clause_disposition(raw_obs)
            if disp == "affirmative":
                kept_observed.append(raw_obs)
            elif disp == "negated":
                if raw_obs in prior_low:
                    kept_retracted.append(raw_obs)
                    reclassified.append(raw_obs)
                else:
                    dropped.append(raw_obs)
            else:
                dropped.append(raw_obs)

        for raw_ret in dict.fromkeys(x.strip().lower() for x in candidate_retracted if x.strip()):
            if raw_ret not in prior_low:
                dropped.append(raw_ret)
                continue
            disp = _clause_disposition(raw_ret)
            if disp == "negated":
                if raw_ret not in kept_retracted:
                    kept_retracted.append(raw_ret)
            else:
                dropped.append(raw_ret)

        return kept_observed, kept_retracted, dropped, reclassified


class TypedMultiRoleNLGroundingPipeline:
    """4-node ``TypedComputationalDAG`` coupling ``BatchRoleDeliberationCodec`` & Mutex revision."""

    ROLE_SPEC: Mapping[str, str] = {
        "extractor": (
            "Read EVERY sentence of QUERY. Output ONE JSON line with all mentioned allowed "
            'predicates: {"observed_facts": ["..."], "retracted_facts": ["..."]}'
        ),
        "critic": (
            "Audit EXTRACTOR against QUERY: remove distractor/test units, remove negated faults "
            '("non", "né", "nessun", "niente"), remove future goals ("completa", "porta online", '
            '"prima di"), move negated Prior predicates into retracted_facts, and output ONE JSON '
            'line: {"observed_facts": ["..."], "retracted_facts": ["..."]}'
        ),
    }

    def __init__(
        self,
        registry: SymbolRegistry,
        *,
        tau_ground: float = 0.70,
        kinetica: KineticaRegimeController | None = None,
        myelination: MyelinationRegistry | None = None,
    ) -> None:
        self.registry = registry
        self.adapter = SymbolicGroundingAdapter(registry, tau_ground=tau_ground)
        self.codec = BatchRoleDeliberationCodec(self.ROLE_SPEC)
        self.kinetica = kinetica or KineticaRegimeController()
        self.myelination = myelination or MyelinationRegistry()
        self._step_clock = 0.0

    def build_prompt(
        self,
        *,
        operator_message: str,
        prior_state: frozenset[str],
        predicate_glosses: Mapping[str, str],
    ) -> str:
        """Build single-call ``BatchRoleDeliberationCodec`` prompt (`EXTRACTOR` + `CRITIC`)."""
        gloss_block = "\n".join(
            f"  {pred}: {desc}" for pred, desc in sorted(predicate_glosses.items())
        )
        query = (
            f'Italian operator report: "{operator_message}"\n'
            f"Prior assumed state: {json.dumps(sorted(prior_state))}\n"
            f"Allowed predicates ONLY:\n{gloss_block}\n"
            "Output ONLY the --- EXTRACTOR --- and --- CRITIC --- sections."
        )
        return self.codec.build_prompt(query)

    def run(
        self,
        *,
        raw_llm_output: str,
        operator_message: str,
        prior_state: frozenset[str],
        predicate_glosses: Mapping[str, str],
        calibrated_confidence: float = 0.85,
        coherence_phi: float = 0.80,
        resource_usage: float = 0.35,
    ) -> TypedPipelineResult:
        """Execute the 4-stage ``TypedComputationalDAG`` with ``ExecutionTicket`` checks."""
        self._step_clock += 1.0
        if self.kinetica.current_regime == CognitiveRegime.IDLE:
            self.kinetica.step("task_start", phi=coherence_phi, resource_usage=resource_usage)
        self.kinetica.step("complex_reasoning", phi=coherence_phi, resource_usage=resource_usage)

        dag = TypedComputationalDAG("t257_multi_role_grounding")
        holder: dict[str, Any] = {}

        c_decode = ContractSpec(
            name="decode_roles_contract",
            input_constraints={"raw_llm_output": FieldConstraint(expected_type="str")},
            output_constraints={
                "candidate_bundle": FieldConstraint(expected_type="dict", non_empty=True),
            },
            timeout_s=5.0,
        )
        c_audit = ContractSpec(
            name="polarity_audit_contract",
            input_constraints={"bundle_in": FieldConstraint(expected_type="dict", non_empty=True)},
            output_constraints={
                "audited_json": FieldConstraint(expected_type="str", non_empty=True),
            },
            timeout_s=5.0,
        )
        c_ground = ContractSpec(
            name="registry_ground_contract",
            input_constraints={"json_in": FieldConstraint(expected_type="str", non_empty=True)},
            output_constraints={"grounded_ok": FieldConstraint(expected_type="bool")},
            timeout_s=5.0,
        )
        c_revise = ContractSpec(
            name="mutex_revision_contract",
            input_constraints={"ground_flag": FieldConstraint(expected_type="bool")},
            output_constraints={"revised_list": FieldConstraint(expected_type="list")},
            timeout_s=5.0,
        )

        def _node_decode(inputs: Mapping[str, Any]) -> Mapping[str, Any]:
            raw = str(inputs["raw_llm_output"])
            sections = self.codec.parse_response(raw)
            critic_txt = sections.get("critic", "")
            ext_txt = sections.get("extractor", "")
            critic_used = "[critic:missing]" not in critic_txt

            obs_cands: list[str] = []
            ret_cands: list[str] = []
            sources = [critic_txt, ext_txt] if critic_used else [raw]
            for sec in sources:
                for obj in _extract_json_dicts(sec):
                    for key_obs in ("observed_facts", "candidates"):
                        vals = obj.get(key_obs)
                        if isinstance(vals, list):
                            obs_cands.extend(str(v) for v in vals if isinstance(v, str))
                    for key_ret in ("retracted_facts", "failed_or_lost", "negated_or_failed"):
                        vals_r = obj.get(key_ret)
                        if isinstance(vals_r, list):
                            ret_cands.extend(str(v) for v in vals_r if isinstance(v, str))

            if not obs_cands and not ret_cands:
                for obj in _extract_json_dicts(raw):
                    vals = obj.get("observed_facts")
                    if isinstance(vals, list):
                        obs_cands.extend(str(v) for v in vals if isinstance(v, str))
                    vals_r = obj.get("retracted_facts")
                    if isinstance(vals_r, list):
                        ret_cands.extend(str(v) for v in vals_r if isinstance(v, str))

            holder["critic_used"] = critic_used
            return {
                "candidate_bundle": {
                    "obs": obs_cands,
                    "ret": ret_cands,
                    "critic_used": critic_used,
                }
            }

        def _node_polarity_audit(inputs: Mapping[str, Any]) -> Mapping[str, Any]:
            bundle = inputs["bundle_in"]
            kept_obs, kept_ret, dropped, reclass = ClausePolarityAuditor.audit_candidates(
                operator_message=operator_message,
                prior_state=prior_state,
                predicate_glosses=predicate_glosses,
                candidate_observed=list(bundle["obs"]),
                candidate_retracted=list(bundle["ret"]),
            )
            # Strip unknown hallucinated vocabulary items prior to strict closed-registry check
            # ONLY if they are absent from registry; valid registry tokens pass cleanly.
            valid_obs = [p for p in kept_obs if self.registry.resolve_predicate(p) is not None]
            valid_ret = [p for p in kept_ret if self.registry.resolve_predicate(p) is not None]
            for bad_tok in (*kept_obs, *kept_ret):
                if self.registry.resolve_predicate(bad_tok) is None:
                    dropped.append(bad_tok)

            holder["dropped"] = tuple(dropped)
            holder["reclassified"] = tuple(reclass)
            payload_str = json.dumps(
                {
                    "observed_facts": sorted(set(valid_obs)),
                    "retracted_facts": sorted(set(valid_ret)),
                }
            )
            return {"audited_json": payload_str}

        def _node_ground(inputs: Mapping[str, Any]) -> Mapping[str, Any]:
            g = self.adapter.ground(
                str(inputs["json_in"]),
                calibrated_confidence=calibrated_confidence,
            )
            holder["grounded"] = g
            return {"grounded_ok": g.status == "grounded_clean"}

        def _node_revise(inputs: Mapping[str, Any]) -> Mapping[str, Any]:
            _ = inputs["ground_flag"]
            g: GroundedPayload = holder["grounded"]
            eff_ret = compute_effective_retracted_facts(prior_state, g, registry=self.registry)
            s_rev = apply_belief_revision(prior_state, g, registry=self.registry)
            holder["eff_ret"] = eff_ret
            holder["s_rev"] = s_rev
            return {"revised_list": sorted(s_rev)}

        dag.add_node("decode_roles", _node_decode, contract=c_decode)
        dag.add_node("polarity_scope_audit", _node_polarity_audit, contract=c_audit)
        dag.add_node("closed_registry_ground", _node_ground, contract=c_ground)
        dag.add_node("mutex_belief_revision", _node_revise, contract=c_revise)

        dag.connect(
            "decode_roles",
            "polarity_scope_audit",
            source_port="candidate_bundle",
            target_port="bundle_in",
        )
        dag.connect(
            "polarity_scope_audit",
            "closed_registry_ground",
            source_port="audited_json",
            target_port="json_in",
        )
        dag.connect(
            "closed_registry_ground",
            "mutex_belief_revision",
            source_port="grounded_ok",
            target_port="ground_flag",
        )

        tickets = dag.execute({"decode_roles": {"raw_llm_output": raw_llm_output}})
        grounded_res: GroundedPayload = holder["grounded"]
        phi_eff = float(max(0.0, min(1.0, coherence_phi)))
        if tickets["mutex_belief_revision"].status == "completed":
            self.myelination.activate(
                "decode_roles", "polarity_scope_audit", phi=phi_eff, now_s=self._step_clock
            )
            self.myelination.activate(
                "polarity_scope_audit",
                "closed_registry_ground",
                phi=phi_eff,
                now_s=self._step_clock,
            )
            self.myelination.activate(
                "closed_registry_ground",
                "mutex_belief_revision",
                phi=phi_eff,
                now_s=self._step_clock,
            )

        return TypedPipelineResult(
            grounded=grounded_res,
            revised_belief_state=holder["s_rev"],
            effective_retracted_facts=holder["eff_ret"],
            dropped_candidates=holder.get("dropped", ()),
            reclassified_retractions=holder.get("reclassified", ()),
            critic_section_used=bool(holder.get("critic_used", False)),
            kinetica_regime=str(self.kinetica.current_regime),
            tickets=tickets,
            myelination_top_paths=self.myelination.top_priority_paths(limit=3),
        )


__all__ = [
    "ClausePolarityAuditor",
    "TypedMultiRoleNLGroundingPipeline",
    "TypedPipelineResult",
]
