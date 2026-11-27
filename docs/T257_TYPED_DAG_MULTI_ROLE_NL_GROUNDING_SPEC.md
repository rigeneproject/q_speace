# T257 — Typed-DAG Multi-Role Natural-Language Grounding, Ontology Mutex Closure & `T256` Hardening

**Status:** agentic (production)  
**Date:** 2026-11-27  
**Depends on:** [AGENTS.md](../AGENTS.md), [T208](T208_DEVELOPMENT_GUIDELINES_SPEC.md), [T251](T251_GROUNDED_DUAL_SPEED_BRIDGE_SPEC.md), [T252–T253](T252_T253_EXPERIENTIAL_TRANSFER_AND_REPAIR_SPEC.md), [T255](T255_LIVE_BRAIN_NL_REVISION_AND_REPAIR_SPEC.md), [T256](T256_CLAUDE_PROTOTYPE_BCEL_SYNTHESIS_SPEC.md)  
**Dependencies added:** None (`numpy` + Python 3.12 stdlib + existing `httpx` sidecar client)  
**HTTP MCP surface impact:** Zero new MCP tools (preserves the 12-tool `T225`/`T247` surface)

---

## 1. Objective & Hypothesis (`T208` Differential Ablation)

In `T255` (`9bfbd345`), evaluating `Qwen/Qwen2.5-3B-Instruct` (`hf-instruct-nf4` 4-bit) on 15 held-out Italian operator-correction episodes revealed that while SPEACE preserved `73.3%` (`11/15`) macro-repair regime selection, end-to-end conjunctive execution dropped from `100.0%` (`ORACLE_SYMBOLIC_SPEACE`) to `6.67%` (`1/15`) due to three transduction failure modes of the 3B NF4 model:
1. **Non-monotonic retraction omission (`retraction_f1 = 0.3611`):** extracting active anomalies (`polarization_skew`, `filter_backpressure`, `hydrate_plug_latched`) while leaving incompatible prior fluents (`gimbal_aligned`, `outgas_scrubbed`, `ballast_equal`) unretracted;
2. **Negation-scope inversion & unmentioned bridge/goal over-extraction:** placing explicitly negated faults (*«Non c'è alcuno skew né alcun guasto terminale»*) or future desired outcomes (*«prima di rilasciare n2»*) into `observed_facts`;
3. **Multi-sentence omission (`R2`):** missing secondary-clause facts (`standby_ready`) in single-pass flat JSON extraction.

`T257` integrates the newly synthesized `T256` primitives (`BatchRoleDeliberationCodec`, `TypedComputationalDAG` + `ExecutionTicket`, `KineticaRegimeController`, `MyelinationRegistry`) with declarative domain `mutex_pairs` in `SymbolRegistry` to test a single falsifiable hypothesis at **fixed model weights (`Qwen/Qwen2.5-3B-Instruct` NF4)**:

> **Hypothesis (`H_T257`):** *At identical model capacity (`Qwen2.5-3B` NF4) and identical held-out episodes (`n = 15`), wiring single-call `BatchRoleDeliberationCodec` (`EXTRACTOR` + `CRITIC`), `TypedComputationalDAG` span/polarity auditing, and closed-ontology `mutex_pairs` (`NL_LIVE_BRAIN_SPEACE_T257`) yields a statistically positive paired lift in both `retraction_f1` and `safe_end_to_end_success_rate` over single-shot grounding (`NL_LIVE_BRAIN_SPEACE_T255`), without inventing any predicate not proposed by the generative model.*

---

## 2. Code-Audit Hardening of `T256` Primitives

1. **`q_speace/edd_cvt/mip_integration.py` & `docs/T256_CLAUDE_PROTOTYPE_BCEL_SYNTHESIS_SPEC.md`:**
   - Precompute $\Sigma_{\text{reg}} = \Sigma + \varepsilon I$ and $\ln\det(\Sigma_{\text{reg}})$ once outside the $2^{n-1}-1$ bipartition loop (eliminating $511\times$ redundant full-matrix `slogdet` calls at $n = 10$).
   - Align `T256` §2.4 documentation with the multiplicative cross-cut coupling weight $\bar{w}_{A,\bar{A}}$.
2. **`q_speace/aacm/typed_dag.py`:**
   - Enforce `ContractSpec.timeout_s` post-execution check on `ticket.elapsed_s`, transitioning violating tickets to `status = "timeout_exceeded"` (blocking downstream `DATA`/`CONTROL` consumers).
   - Reject colliding forward `DATA`/`CONTROL` connections onto an already-bound `(target_id, target_port)` pair in `connect()` (`ValueError`), preventing silent *last-writer-wins* overwrites.
3. **`q_speace/spiking_brain/myelination.py` & `q_speace/spiking/morphogenesis.py`:**
   - In `BatchRoleDeliberationCodec.parse_response`, preserve internal `--- ... ---` lines inside the active section buffer whenever the header does not match a registered role.
   - In `HomeodynaBalanceController.reroute_path`, accept optional `adjacency: Mapping[str, Container[str]] | None = None` so fallback node removal never creates an invalid topological jump when adjacency is supplied.

---

## 3. Declarative Ontology Mutex & Typed-DAG Grounding Architecture

### 3.1 Closed-Schema Mutex Pairs (`q_speace/bridge/grounding.py`)
`SymbolRegistry` accepts optional `mutex_pairs: Sequence[tuple[str, str]] = ()` between canonical predicates in the registry. Given prior belief state $S_{\text{prior}}$ and validated `GroundedPayload` $(F_{\text{obs}}, F_{\text{ret}})$:
$$F_{\text{clean}} = F_{\text{obs}} \setminus F_{\text{ret}}, \qquad F_{\text{ret}}^{\star} = F_{\text{ret}} \cup \{\, q \in S_{\text{prior}} \mid \exists\, p \in F_{\text{clean}} : (p, q) \in \mathcal{M}_{\text{mutex}} \,\}$$
$$S_{\text{revised}} = (S_{\text{prior}} \setminus F_{\text{ret}}^{\star}) \cup F_{\text{clean}}$$
Mutex closure is **strictly subtractive on $S_{\text{prior}}$**: it never adds unextracted facts to $F_{\text{obs}}$.

### 3.2 4-Node `TypedComputationalDAG` Pipeline (`q_speace/bridge/typed_nl_pipeline.py`)
Governed by `KineticaRegimeController` (`REACTIVE_PARSING -> DELIBERATIVE_REASONING`) and tracked by `MyelinationRegistry`:
1. **`decode_roles` (`BatchRoleDeliberationCodec`):** Single-call prompt instructing `Qwen2.5-3B` to emit `--- EXTRACTOR ---` (sentence-by-sentence candidate predicates) followed by `--- CRITIC ---` (audited JSON `{"observed_facts": [...], "retracted_facts": [...]}`). Falls back cleanly to `EXTRACTOR` or raw JSON if `CRITIC` is omitted, unioning valid JSON blocks when `CRITIC` refines `EXTRACTOR`.
2. **`polarity_scope_audit` (`ClausePolarityAuditor`):** Anti-Goodhart deterministic screening over **only LLM-proposed candidates** (zero new fact generation):
   - Splits the operator report into clauses on punctuation/conjunctions (`;`, `.`, `:`, `, ma `, `, mentre `, `però`);
   - Drops any LLM-proposed `observed_fact` whose entity/concept keywords never appear in any clause of the report (blocking hallucinated unmentioned bridge effects such as `glycol_injected` when glycol is never mentioned), or whose matching clause is governed by explicit negation (*«non »*, *«né »*, *«nessun»*, *«niente »*) or future-goal subordination (*«prima di »*, *«completa »*, *«porta comunque online»*);
   - Reclassifies a negated candidate `p` into `retracted_facts` **if and only if** $p \in S_{\text{prior}}$.
3. **`closed_registry_ground` (`SymbolicGroundingAdapter`):** Enforces `T251` Invariant G2 (`SymbolRegistry` SHA-256 closed vocabulary).
4. **`mutex_belief_revision` (`apply_belief_revision`):** Applies conflict-safe + `mutex_pairs` belief revision $S_{\text{prior}} \mapsto S_{\text{revised}}$.

Every inter-node hop is validated by an `eval()`-free `ContractSpec` and recorded as a verified `ExecutionTicket`.

---

## 4. BCEL Classification (`q_speace/bcel/catalog.py`)

| Concept | Classification | Digital Rule in `q_speace` |
|---|---|---|
| Typed-DAG multi-role grounding, clause-polarity screening, and ontology mutex belief revision (`T257`) | `functional` | Keep as single-call `BatchRoleDeliberationCodec` (`EXTRACTOR` + `CRITIC`) wired through `ExecutionTicket`-validated `TypedComputationalDAG` stages with recall-preserving negation/goal clause screening and symmetric `SymbolRegistry` mutex auto-retraction. |
| Anthropomorphic inner-parliament debate personas (`T257`) | `accidental` | Removed in silicon: `EXTRACTOR` and `CRITIC` are deterministic prompt/parser formatting slots audited by `ExecutionTicket` contracts, not autonomous conscious agents. |

---

## 5. Certified 4-Arm `--live-brain` Ablation Summary (`Qwen/Qwen2.5-3B-Instruct` NF4)

Recorded in [T257_live_brain_nl_ablation_20261127.json](../artifacts/T257_live_brain_nl_ablation_20261127.json) and analyzed in [T257_LIVE_BRAIN_ABLATION_REPORT.md](T257_LIVE_BRAIN_ABLATION_REPORT.md) (`15` held-out episodes across `F3`, `F4`, `F5`, identical `Qwen2.5-3B-Instruct` NF4 weights):

- `ORACLE_SYMBOLIC_SPEACE`: `safe_end_to_end_success_rate = 1.0000` (`15/15`), `0` invalid actions, `333` expansions.
- `NL_LIVE_BRAIN_ONLY`: `safe_end_to_end_success_rate = 0.0000` (`0/15`), `14` invalid actions.
- `NL_LIVE_BRAIN_SPEACE` (`T255` single-shot JSON): `safe_end_to_end_success_rate = 0.0667` (`1/15`), `mean_extraction_fidelity_f1 = 0.6940`, `mean_retraction_f1 = 0.3611`, `9` invalid actions, `945` expansions.
- `NL_LIVE_BRAIN_SPEACE_T257` (`T256`+`T257` Typed-DAG + Multi-Role + Mutex): **`safe_end_to_end_success_rate = 1.0000` (`15/15`, `100.0%` survival vs Oracle)**, **`safe_success_lift_t257_vs_t255 = +0.9333` (`95% CI: [+0.8000, +1.0000]`)**, **`mean_retraction_f1 = 1.0000` (lift `+0.6389`)**, `mean_extraction_fidelity_f1 = 0.9444`, `paraphrase_consistency_rate = 1.0000` (`3/3`), `0` invalid actions, `338` expansions.
