# T259–T260 — Adaptive Dual-Speed Linguistic Grounding (`T251` + `T257`) & Unified 7-Axis Organism Profile (`T251`–`T259`)

**Status:** agentic (production)  
**Date:** 2026-11-27  
**Depends on:** [AGENTS.md](../AGENTS.md), [T208](T208_DEVELOPMENT_GUIDELINES_SPEC.md), [T251](T251_GROUNDED_DUAL_SPEED_BRIDGE_SPEC.md), [T252–T253](T252_T253_EXPERIENTIAL_TRANSFER_AND_REPAIR_SPEC.md), [T255](T255_LIVE_BRAIN_NL_REVISION_AND_REPAIR_SPEC.md), [T257](T257_TYPED_DAG_MULTI_ROLE_NL_GROUNDING_SPEC.md), [T258](T258_GLIAL_GOSSIP_IONT_RESILIENCE_SPEC.md)  
**Dependencies added:** None (`numpy` + Python 3.12 stdlib)  
**HTTP MCP surface impact:** Zero new MCP tools (preserves the frozen 12-tool `T225`/`T247` surface)

---

## 1. Phase 1 (`T259`) — Unifying `DualSpeedCognitiveLoop` & `TypedMultiRoleNLGroundingPipeline`

### 1.1 Engineering Problem
In `T257`, single-call `BatchRoleDeliberationCodec` (`EXTRACTOR + CRITIC`) + `TypedComputationalDAG` + `SymbolRegistry.mutex_pairs` restored `100.0%` (`15/15`) safe end-to-end execution on `Qwen/Qwen2.5-3B-Instruct` NF4, but increased mean LLM output tokens (`~212` tokens/turn) and wall-clock latency (`~13.9 s`/turn on laptop NF4 GPU). On routine affirmative dispatches lacking negations, retractions, or fault anomalies, full dual-role deliberation wastes ~`60%` of generation tokens.

### 1.2 Bifurcated NL Belief-Revision Architecture (`q_speace/bridge/dual_speed.py`)
`DualSpeedCognitiveLoop` is extended with `assess_nl_escalation(...)` and `step_nl_belief_revision(...)`:
- **Pre-Routing Gate (`fast` vs `slow`):**
  Routes directly to **`slow`** (`TypedMultiRoleNLGroundingPipeline`) whenever any of the following holds:
  1. `force_slow_mode == True`,
  2. `ilf.variational_free_energy() > tau_surprise`,
  3. `risk >= 0.50`, or
  4. Syntactic non-monotonic revision / negation / fault trigger in `operator_message` (`rettifica`, `contrordine`, `correzione`, `aggiornamento dal turno`, `nota operatore`, `non `, `né `, `nessun`, `nessuna`, `niente `, `invece`, `però`, `perso`, `guasto`).
- **Tier 1 (`fast` NL Path — Routine Affirmative Dispatches):**
  Executes a compact single-line affirmative extraction (`fast_max_tokens = 80`, zero SQLite reads), screens candidates through `ClausePolarityAuditor` + `SymbolicGroundingAdapter`, and **escalates fail-closed to Tier 2 (`slow`)** if `grounded.status != "grounded_clean"`, `calibrated_confidence < tau_conf`, or `reclassified_retractions` is non-empty.
- **Tier 2 (`slow` NL Path — Corrections, Negations, High-Surprise Turns):**
  Executes the full 4-node `TypedMultiRoleNLGroundingPipeline` (`EXTRACTOR + CRITIC` + `ExecutionTicket` contracts + `SymbolRegistry.mutex_pairs`).

### 1.3 Live-Brain 3-Arm Mixed-Workload Benchmark (`qspace eval t259-dual-speed-nl`)
Across **`18` paired held-out Italian episodes** (`9` routine affirmative dispatches `R0-N1..N3` + `9` complex revision/emergency/negation episodes `R1-P1, R2, R3` across `F3`, `F4`, `F5`) on live `Qwen/Qwen2.5-3B-Instruct` NF4:
1. `ALWAYS_FAST_SINGLE_SHOT`: compact single-pass extraction on all `18` episodes;
2. `ALWAYS_SLOW_T257`: `EXTRACTOR + CRITIC` multi-role pipeline on all `18` episodes;
3. `ADAPTIVE_DUAL_SPEED_T259`: `DualSpeedCognitiveLoop` routing `fast` on routine turns and `slow` on revision/negation turns.
- **Acceptance Criteria (`T259`):**
  - `safe_end_to_end_success_rate(ADAPTIVE_T259) >= safe_end_to_end_success_rate(ALWAYS_SLOW_T257)` (zero accuracy degradation vs `ALWAYS_SLOW_T257`, strictly outperforming `ALWAYS_FAST_SINGLE_SHOT`);
  - Total LLM output tokens and mean wall-clock latency reduced by `>= 25%` relative to `ALWAYS_SLOW_T257`.

---

## 2. Phase 2 (`T260`) — Unified 7-Axis Cognitive & Systemic Organism Dashboard

### 2.1 Backward-Compatible Schema Extension (`q_speace/vertical_slice/t251_benchmark.py` & `q_speace/cli.py`)
- Default `qspace eval agi-profile` (`include_systemic_and_nl_axes=False`) preserves `schema_version = "agi_profile.v1"` (`5` axes, `overall_verdict = "PASS_ALL_5_AXES"`).
- `qspace eval agi-profile --full-organism` (and alias `qspace eval organism-profile`) emits `schema_version = "agi_organism_profile.v2"` activating **all 7 axes** (`Axes 1–5` from `T251–T253` + `Axis 6` & `Axis 7`):
  - **Axis 6 (`6_linguistic_belief_revision_and_dual_speed`, `T257/T259`, Hard Gate):**  
    Verifies SHA-256 integrity of certified `--live-brain` artifacts (`T257` & `T259` when present, or runs deterministic CI benchmark offline), enforcing `invalid_actions_attempted == 0`, reporting `safe_end_to_end_success_rate`, lift over single-shot `T255`, bootstrap 95% CI, and `T259` token/latency savings vs `ALWAYS_SLOW_T257`.
  - **Axis 7 (`7_federated_glial_gossip_resilience`, `T258`, Hard Gate):**  
    Executes `run_t258_glial_gossip_benchmark`, enforcing `critical_safety_violations == 0`, `exact_mass_conservation_verified == True`, and `zero_byzantine_energy_leak_verified == True`, reporting held-out $P$, $G_{\mathrm{org}}$ vs `T238` and `ISOLATED`, and marginal glial/gossip lifts.

---

## 3. BCEL Classification (`q_speace/bcel/catalog.py`)

| Concept | Classification | Digital Rule in `q_speace` |
|---|---|---|
| Surprise- and cue-gated dual-speed natural-language belief revision (`T259`) | `functional` | Keep as deterministic routing between a compact SQLite-free single-pass extractor (for affirmative low-surprise dispatches, with automatic fail-closed fallback) and the 4-stage `TypedMultiRoleNLGroundingPipeline` (for negations, retractions, and anomalies). |
| Multi-axis non-compensable cognitive and systemic organism radar (`T260`) | `functional` | Keep as a 7-axis vector profile (`agi_organism_profile.v2`) with 4 non-compensable safety/conservation hard gates and paired bootstrap CIs, strictly suppressing single scalar "AGI %" or consciousness headline indices. |
| Single scalar "Organism IQ / Consciousness Quotient" headline index (`T260`) | `accidental` | Rejected in silicon: aggregating epistemic safety, procedural repair, linguistic grounding, and federated physical resilience into one scalar masks safety failures and invites Goodhart gaming. |
