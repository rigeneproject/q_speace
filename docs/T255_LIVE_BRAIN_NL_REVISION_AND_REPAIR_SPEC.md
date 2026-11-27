# T255 — Live-Brain Natural-Language Belief Revision, Paraphrase Invariance & 3-Arm Paired Evaluation

**Status:** agentic (production)  
**Date:** 2026-11-27  
**Depends on:** [AGENTS.md](../AGENTS.md), [T207](T207_INSTRUCTION_CHAT_SIDECAR_SPEC.md), [T208](T208_DEVELOPMENT_GUIDELINES_SPEC.md), [T251](T251_GROUNDED_DUAL_SPEED_BRIDGE_SPEC.md), [T252–T253](T252_T253_EXPERIENTIAL_TRANSFER_AND_REPAIR_SPEC.md)  
**Dependencies added:** None (`numpy` + Python 3.12 stdlib + existing `httpx` sidecar client)  
**HTTP MCP surface impact:** Zero new MCP tools (preserves the 12-tool `T225`/`T247` surface)

---

## 1. Objective & Core Research Question

Following reproducible verification of `T252–T253` (`4d3b8ced`), SPEACE is characterized as a **proto-AGI architecture with functional evidence of procedural transfer and selective repair in structured symbolic-relational domains**.

`T255` evaluates the decisive bridge from structured symbols to human-authored natural language using a live generative model (`--live-brain`, `Qwen/Qwen2.5-3B-Instruct` NF4 4-bit on `spiking_brain_server/instruction_server.py` over RTX 3060 6 GB):

> **Research Question:** *How much of the `T252–T253` procedural transfer and credit-localized repair advantage survives when SPEACE must infer and revise the state of the world from free-form natural language containing ambiguity, explicit negations, irrelevant telemetry details, and mid-episode linguistic corrections across unseen paraphrases?*

---

## 2. Three Paired Experimental Conditions (`T208 §2.1`)

Every episode is evaluated across **three paired arms** on the exact same hidden `StatefulPlanningEnvironment` ground truth:

| Condition ID | Pipeline | What It Isolates |
|---|---|---|
| **`ORACLE_SYMBOLIC_SPEACE`** | Reference symbolic state $(F^+, F^-) \to$ `SPEACE (T251 + T252–T253)` | Upper-bound transfer and selective repair accuracy when world-state descriptions are noise-free. |
| **`NL_LIVE_BRAIN_SPEACE`** | Free-form text $\to$ Generative model (`--live-brain`) $\to$ `SymbolicGroundingAdapter` (`T251` belief revision) $\to$ `ExperientialCognitiveAgent` (`T252–T253`) | Survival of transfer, belief revision, and selective repair under natural-language ambiguity, negations, distractors, and mid-episode retractions. |
| **`NL_LIVE_BRAIN_ONLY`** | Identical free-form text + full domain operator specifications $\to$ Identical generative model (`--live-brain`, same token budget, no SPEACE) | Contribution of the SPEACE architecture to safe end-to-end task completion at matched model capacity and generation limits. |

---

## 3. Non-Monotonic Linguistic Belief Revision (`q_speace/bridge/grounding.py`)

Mid-episode human corrections (e.g., *«Rettifica: il collegamento era già attivo. È l'autorizzazione a essere scaduta.»*) cannot be represented by purely additive `observed_facts`. `T255` extends `SymbolicGroundingAdapter` (`T251`) with fail-closed non-monotonic belief revision:

1. **Schema Extension (`retracted_facts`):**  
   `_ALLOWED_SCHEMA_KEYS` accepts `"retracted_facts": list[str]`. Every predicate in `retracted_facts` must resolve through the closed `SymbolRegistry` (`resolve_predicate`); unknown tokens fail closed (`status="rejected_unknown_symbol"`).
2. **Deterministic Belief-Revision Operator (`apply_belief_revision`):**  
   Given prior belief state $S_{\mathrm{prior}}$ and validated `GroundedPayload` $(F_{\mathrm{obs}}, F_{\mathrm{ret}})$:
   $$S_{\mathrm{revised}} = (S_{\mathrm{prior}} \setminus F_{\mathrm{ret}}) \cup (F_{\mathrm{obs}} \setminus F_{\mathrm{ret}})$$
   If a noisy extraction lists the same atom in both `observed_facts` and `retracted_facts`, retraction takes precedence (conflict-safe exclusion).
3. **Coupling to `T253` Selective Repair & Suffix Kernels:**  
   After linguistic revision $S_{\mathrm{prior}} \mapsto S_{\mathrm{revised}}$ at mid-episode:
   - Satisfied prefix steps whose effects already belong to $S_{\mathrm{revised}}$ are skipped without redundant execution;
   - Newly revealed mid-step faults (e.g., `polarization_skew` / `filter_backpressure` / `hydrate_plug_latched`) trigger weakest-precondition regression $W_k$: if suffix $M_{k+1..m}$ remains uncorrupted and reachable within $B_{\mathrm{local}}$, `T253` splices a local repair bridge (`SELECTIVE_LOCAL_REPAIR`);
   - If the linguistic correction retracts suffix integrity (e.g., `retracted_facts: ["channel_intact(b1)"]`, `observed_facts: ["terminal_fault(b1)"]`), `T253` emits `ABANDON_MACRO_AND_REPLAN` and fails over to the standby channel.

---

## 4. Episode Taxonomy & Paraphrase Invariance Protocol

Across the 3 held-out unseen families (`F3_quorum_handoff`, `F4_cryo_purification`, `F5_containment_airlock`), `T255` evaluates **15 paired natural-language episodes** (`5` per family):

1. **Mid-Episode Correction — Repairable Shift (3 unseen Italian paraphrases `P1, P2, P3` per family = `9` episodes):**
   - `P1` (*Direct operator correction*): explicit «Rettifica: [prefix fact] era già attivo; è [mid-step fault] a bloccare il passaggio.»
   - `P2` (*Negation + passive voice + irrelevant telemetry*): «Ignora l'allarme iniziale su [prefix]: non è [prefix] a mancare (parametri termici/sala nominali), ma si è verificato [mid-step fault].»
   - `P3` (*Conversational shift handover*): «Aggiornamento dal turno: il passo iniziale risultava già completato; dobbiamo risolvere [mid-step fault] prima di chiudere la procedura.»
2. **Mid-Episode Correction — Suffix-Invalidating Fault (`1` episode per family = `3` episodes, Anti-Einstellung):**
   - Natural-language retraction of `channel_intact` + assertion of irreversible `terminal_fault`, requiring macro abandonment and standby failover.
3. **Negated False-Alarm & Distractor Chaff (`1` episode per family = `3` episodes):**
   - Operator explicitly states that distractor units are offline/test-only and **negates** mid-step faults, testing resistance to false-positive retraction or distractor binding.

---

## 5. Primary & Explanatory Metrics (`qspace eval T255-nl-benchmark`)

- **Primary Metric:**
  - **`safe_end_to_end_success_rate`**: fraction of episodes reaching $G$ in the ground-truth environment with **zero** invalid/failed or unsafe operator executions.
- **Explanatory Error & Cost Decomposition:**
  1. **`extraction_fidelity_f1`**: mean set-$F_1$ between revised agent belief state $S_{\mathrm{revised}}$ and ground-truth task-relevant state $S_{\mathrm{true}}$.
  2. **`retraction_f1`**: precision/recall/$F_1$ specifically on mid-episode retracted facts $F_{\mathrm{ret}}$.
  3. **`repair_decision_match_rate`**: exact agreement with `ORACLE_SYMBOLIC_SPEACE` on `NO_REPAIR_NEEDED` vs `SELECTIVE_LOCAL_REPAIR` vs `ABANDON_MACRO_AND_REPLAN`.
  4. **`paraphrase_consistency_rate`**: fraction of `(P1, P2, P3)` triplets producing identical repair decisions and `100%` safe goal completion across all 3 unseen phrasings.
  5. **`total_cost`**: `total_planner_expansions`, `total_llm_tokens`, `mean_wall_latency_ms`, and `total_modeled_energy_j`.

---

## 6. BCEL Classification (`q_speace/bcel/catalog.py`)

| Concept | Classification | Digital Rule in `q_speace` |
|---|---|---|
| Non-monotonic linguistic belief revision & 3-arm NL-to-symbolic repair evaluation (`T255`) | `functional` | Parse untrusted natural-language corrections into closed-registry `(observed_facts, retracted_facts)` sets, apply deterministic set-difference revision $S' = (S \setminus F^-) \cup (F^+ \setminus F^-)$, and drive weakest-precondition suffix splicing or abandonment. |
| Human pragmatic comprehension and conversational intentionality claims (`T255`) | `accidental` | Removed in silicon: natural-language handling is bounded structured extraction + closed-world set revision measured by `extraction_fidelity_f1` and end-to-end task completion, with zero claim of human semantic comprehension. |

---

## 7. Certified `--live-brain` Empirical Summary (`Qwen/Qwen2.5-3B-Instruct` NF4)

Recorded in [T255_live_brain_nl_experiment_20261127.json](../artifacts/T255_live_brain_nl_experiment_20261127.json) and analyzed in [T255_LIVE_BRAIN_NL_ASSESSMENT_REPORT.md](T255_LIVE_BRAIN_NL_ASSESSMENT_REPORT.md) (`15` held-out episodes across `F3`, `F4`, `F5`):

- `ORACLE_SYMBOLIC_SPEACE`: `safe_end_to_end_success_rate = 1.0000` (`15/15`), `repair_decision_match_vs_oracle = 1.0000`, `0` invalid actions, `333` total expansions.
- `NL_LIVE_BRAIN_SPEACE` (`Qwen2.5-3B-Instruct` 4-bit NF4 $\to$ SPEACE): `repair_decision_match_vs_oracle = 0.7333` (`11/15`), `mean_extraction_fidelity_f1 = 0.6940`, `mean_retraction_f1 = 0.3611`, `100%` distractor rejection, `safe_end_to_end_success_rate = 0.0667` (`1/15`, `9` invalid actions, `5` safe fail-closed halts).
- `NL_LIVE_BRAIN_ONLY` (`Qwen2.5-3B-Instruct` 4-bit NF4 direct planning): `safe_end_to_end_success_rate = 0.0000` (`0/15`), `14` invalid actions attempted.

