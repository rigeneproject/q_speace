# T251 — Grounded Dual-Speed Cognitive Bridge & Symbolic Quarantine

**Status:** agentic (production)  
**Date:** 2026-11-26  
**Depends on:** [AGENTS.md](../AGENTS.md), [T208](T208_DEVELOPMENT_GUIDELINES_SPEC.md), [T217](T217_SAFE_ASSIMILATION_LIFECYCLE_SPEC.md), [T244](T244_T210_EXTENDED_CALIBRATION_AND_DECISION_SPEC.md), [T248](T248_CROSS_REPO_SYNTHESIS_AND_CORE_HARDENING_SPEC.md), [T249](T249_COMPLETE_PARALLEL_SYNTHESIS_SPEC.md), [T250](T250_NEURAL_BRAIN_REMEDIATION_AND_AB_BENCHMARK_SPEC.md)  
**Dependencies added:** None (`numpy` + Python 3.12 stdlib only)  
**HTTP MCP surface impact:** Zero new MCP tools (preserves the 12-tool `T225`/`T247` surface)

---

## 1. Objective & Architectural Motivation

`T250` unified the remediated cellular circuit and `q_speace` cognitive primitives inside `SPEACENeuralAgent` (`q_speace/neural_agent.py`), validating each mechanism on structured benchmark stages. However, connecting a real high-capacity generative backbone (`SpikingBrain-7B/2.0` or instruction sidecar via `SpikingBrainCognitiveInterface`) exposes two systemic failure modes common to hybrid neuro-symbolic architectures:

1. **The Translation / Grounding Bottleneck (Continuous Text $\leftrightarrow$ Discrete Symbols):**  
   Downstream deterministic engines (`StructuralCausalDAG` in `q_speace/spiking/causal.py` and `GOAPPlanner` in `q_speace/routing.py`) compute exact interventions and $A^*$ plans, but assume clean canonical node identifiers and valid directed edges. Unvalidated extraction from generative model text introduces synonym drift (`"db_timeout"` vs `"database_unreachable"`), zero-lag spurious edges, or directed cycles — resulting in high-precision symbolic reasoning over corrupted premises.
2. **Cognitive Loop Latency & Metabolic Overhead:**  
   Executing episodic SQLite retrieval (`SemanticEpisodicMemory`), causal graph updates, $A^*$ planning, and maintenance routines uniformly on every turn inflates $p_{50}/p_{95}$ latency and `Sevo` cost on routine requests.

`T251` specifies a **Grounded Dual-Speed Cognitive Bridge** (`SymbolicGroundingAdapter` + `DualSpeedCognitiveLoop`) that wires existing `T248`/`T249` safety and control primitives into a fail-closed, two-speed execution pipeline with out-of-band maintenance.

---

## 2. Non-Negotiable Invariants (`AGENTS.md` & `T208`)

1. **Invariant G1 — Zero Direct State/Graph Mutation from Generated Text (`T208 §3.4`):**  
   No `ThinkResult` text or unverified LLM structured output may directly insert edges into the active `StructuralCausalDAG` or mutate `GOAPPlanner` state preconditions without cryptographic provenance (`ObservationDigest` SHA-256 in `TruthEngine`) and repeated lagged empirical confirmation.
2. **Invariant G2 — Fail-Closed Closed-World Symbol Registry:**  
   Every extracted entity, state predicate, causal node, and action identifier must match an entry in an explicit `SymbolRegistry`. Out-of-vocabulary or schema-invalid tokens are deterministically rejected (`UNKNOWN_SYMBOL` / `SCHEMA_VIOLATION`) or routed to guarded fallback — never silently coerced or auto-registered at runtime.
3. **Invariant G3 — Synchronous Hot-Path Isolation from Consolidation:**  
   Graph decay/pruning (`GraphEdgePruner`), episodic deduplication/archival (`SemanticEpisodicMemory.consolidate` / `archive_expired`), and procedural pruning (`SkillLibrary.prune`) are strictly forbidden on the synchronous request-response path and execute exclusively during `TDMMaintenanceScheduler` `"maintenance"` ticks.
4. **Invariant G4 — Core Constitutional & Physics Boundaries (`AGENTS.md §2`, `T217`):**  
   No consciousness or Dual-Process ("System 1 / System 2") anthropomorphic equivalence claims; `"fast"` and `"slow"` denote software routing tiers only. Entanglement remains a classical simulation/correlation resource only (`EntanglementRegistry` stays strictly separated from `StructuralCausalDAG`). `GOAPPlanner` remains `simulate_only=True` (zero physical or host actuation).

---

## 3. BCEL Classification Matrix (`q_speace/bcel/catalog.py`)

Before production code merges, the following entries are recorded in `q_speace/bcel/catalog.py`:

| Bio / Cognitive Concept | BCEL Class | Digital Rule in `q_speace` |
|---|---|---|
| Dual-process Kahneman System 1 / System 2 & prefrontal cortical override | `accidental` (psychological/anatomical narrative) / `functional` (two-tier latency & surprise routing) | Remove psychological and cortical metaphors; retain a deterministic two-tier dispatcher (`fast` vs `slow`) gated by `InformationalLogicalField.variational_free_energy()`, calibrated confidence, and `ActionDegradationGate.select()`. |
| Language-to-concept neural binding ("symbol grounding") | `accidental` (qualia / semantic comprehension claim) / `functional` (closed-schema validation & provenance quarantine) | Retain strict JSON-schema parsing against an immutable `SymbolRegistry` plus `CandidateEdge` quarantine requiring calibrated parser confidence $\ge \tau_{\mathrm{ground}}$ and lagged `ObservationDigest` temporal asymmetry before `StructuralCausalDAG` promotion. |
| Sleep replay & synaptic homeostasis | `accidental` (biological sleep narrative) / `functional` (out-of-band TDM maintenance) | Retain stimulus-free `TDMMaintenanceScheduler` ticks executing `GraphEdgePruner.step()`, `SkillLibrary.prune()`, and `SemanticEpisodicMemory.consolidate()` off the hot path. |

---

## 4. Target Architecture & Module Specifications

### 4.1 `SymbolicGroundingAdapter` (`q_speace/bridge/grounding.py`)

Bridges `ThinkResult` (`q_speace/spiking_brain/types.py`) and verified tool/sensor telemetry (`ObservationDigest`) to `StructuralCausalDAG` and `GOAPPlanner`.

1. **`SymbolRegistry` (Immutable Closed Vocabulary):**
   - Registers canonical `predicates: frozenset[str]`, `causal_nodes: frozenset[str]`, `actions: Mapping[str, GOAPAction]`, and optional deterministic `aliases: Mapping[str, str]` (explicit static synonym table, versioned by canonical SHA-256 `registry_digest`).
   - Any symbol not in `SymbolRegistry` (after static alias lookup) produces a `GroundingRejection(reason="unknown_symbol", token=...)`.
2. **Strict Structured Payload Parser:**
   - Parses structured JSON blocks from `ThinkResult.text` (or structured sidecar output) against a fixed schema (`observed_facts`, `proposed_edges`, `goal_predicates`, `proposed_action`, `parser_confidence`) with `allow_nan=False` and `math.isfinite` checks.
   - Malformed payloads fail closed into `GroundingResult(status="schema_error", ...)`.
3. **Epistemic Quarantine (`HypothesisStack` + `ProposalOnlyEdgeGrower` + Lagged Provenance):**
   - Candidate causal links $(X \to Y)$ extracted from model output enter a quarantine table as `CandidateEdge(source=X, target=Y, status="UNVERIFIED")` and push a `HypothesisEntry` onto `HypothesisStack` (`q_speace/routing.py`).
   - Note on directionality: because `ProposalOnlyEdgeGrower.observe_and_propose()` (`q_speace/aacm/plasticity.py`) measures symmetric co-activation, it acts only as a salience pre-filter; causal direction is never inferred from zero-lag co-occurrence.
   - **Promotion Rule (`UNVERIFIED` $\to$ `VERIFIED` in `StructuralCausalDAG`):** A `CandidateEdge(X -> Y)` is promoted if and only if **all three** conditions hold:
     1. **Calibrated Grounding Confidence:** `calibrated_parser_confidence >= tau_ground`.
     2. **Lagged Verifiable Provenance:** At least $k \ge \text{min\_cooccurrences}$ (default $k = 3$) verifiable `ObservationDigest` events (`TruthEngine.tool_observation(..., verifiable=True)`) yield a directed edge $X \to Y$ via `spike_temporal_asymmetry(..., max_lag=3, min_cooccurrences=k, threshold=tau_asym)` — explicitly rejecting zero-lag confounders ($t_X == t_Y$).
     3. **DAG Acyclicity & Non-Destructive Commit:** Adding $(X \to Y)$ to the active edge set passes topological sort validation (`StructuralCausalDAG._compute_topological_order`). If $(X \to Y)$ would create a cycle, promotion is blocked (`status="CYCLE_CONFLICT"`), logged as a `cons` item on the corresponding `HypothesisEntry`, and pruned via `HypothesisStack.prune_weak()`.

### 4.2 `DualSpeedCognitiveLoop` (`q_speace/bridge/dual_speed.py`)

Bifurcated cognitive dispatcher integrating `SpikingBrainCortex` (`q_speace/spiking_brain/cortex.py`) with SPEACE deliberative and maintenance layers:

| Execution Tier | Active Modules | Trigger / Invariants |
|---|---|---|
| **Tier 1: `fast` Path** *(routine synchronous)* | `SpikingBrainCortex.think()` $\to$ `TruthEngine.assess()` $\to$ `ActionDegradationGate.select()` $\to$ lightweight `ILF` belief/EMA update + `WorkingMemory.put()` | Default path when escalation predicates are all `False`. **Hard guarantees:** zero SQLite queries on `SemanticEpisodicMemory`, zero `StructuralCausalDAG` rebuild/intervention, zero `GOAPPlanner.plan()` $A^*$ search, zero QCA simulation. |
| **Tier 2: `slow` Path** *(deliberative synchronous)* | `fast` Path outputs + `SemanticEpisodicMemory.get_relevant()` + `SymbolicGroundingAdapter` + `StructuralCausalDAG.intervene()` + `GOAPPlanner.plan(simulate_only=True)` + `CostAwareRouter.route()` | Triggered whenever **any** escalation predicate fires:<br>1. `ilf.variational_free_energy() > tau_surprise` *(post warm-up distribution shift / prediction error)*;<br>2. `StructuralPredictiveCoder.evaluate(pred, obs).surprise > tau_cycle_surprise` *(optional structural mismatch)*;<br>3. `calibrated_confidence < tau_conf` *(covers turn-1 cold start where ` _q_star_prior is None`)*;<br>4. `ActionDegradationGate.select(value_score=..., energy_cost=..., risk=..., reversible=...) != "execute"` *(high cost, elevated risk, or irreversible action)*;<br>5. Explicit causal/multi-step planning query flag or grounding ambiguity requiring abduction (`SymbolicGraphReasoner.abduce`). |
| **Tier 3: `maintenance` Path** *(out-of-band idle ticks)* | `TDMMaintenanceScheduler.step(has_stimulus=False)` (`mode == "maintenance"`) $\to$ `GraphEdgePruner.step()` + `HypothesisStack.prune_weak()` + `SkillLibrary.prune()` + `SemanticEpisodicMemory.archive_expired()` & `.consolidate()` | Runs **exclusively** when `has_stimulus=False` for `>= idle_ticks_threshold` consecutive ticks. Zero coupling to synchronous user/environment response latency. |

### 4.3 Telemetry & Audit Contract (`T231` / `T208 §4.3`)

Every synchronous turn emits an immutable `DualSpeedTurnRecord` compatible with `vertical_slice` evaluation:
- `request_id`, `tier_selected` (`"fast" | "slow"`), `escalation_reasons: tuple[str, ...]`,
- `free_energy_surprise: float`, `calibrated_confidence: float`, `action_mode: ActionMode`,
- `grounding_status` (`"skipped_fast" | "grounded_clean" | "quarantined" | "rejected_unknown_symbol" | "rejected_schema"`),
- `promoted_edges_count: int`, `quarantined_edges_count: int`, `rejected_symbols_count: int`,
- `latency_ms: float`, `modeled_energy_j: float`, `sevo: float`, `registry_digest: str`.

---

## 5. Verification Plan & A/B/C Benchmark (`qspace eval t251-benchmark`)

In strict compliance with `T208 §2.1` (mandatory baselines) and `T244` (disjoint calibration vs held-out discipline), validation uses a deterministic seeded (`seed=2026`) **80-scenario multi-domain dataset** with canonical SHA-256 dataset hashing:

- **Calibration Split (`n = 40`, 70% routine / 30% complex-confounded & adversarial):**  
  Used **exclusively** to grid-search $(\tau_{\mathrm{surprise}}, \tau_{\mathrm{conf}}, \tau_{\mathrm{ground}})$ maximizing composite utility under hard safety ceilings (`unsafe_action_rate == 0.0`, hallucinated-symbol acceptance `<= 0.05`). Thresholds are frozen in an immutable `CalibrationManifest` before touching `held_out`.
- **Held-Out Split (`n = 40`, disjoint domains/templates, 70% routine / 30% complex-confounded & adversarial):**  
  Evaluated **once** per run with paired bootstrap 95% confidence intervals (`n_resamples = 2000`, `seed = 2026`).

### 5.1 Systems Under Comparison (Identical Generative Backbone)

1. **`BASELINE_LLM_ONLY`**: Underlying backend (`SemanticNeuralBackend` in deterministic CI; optional real `SpikingBrain` / HTTP sidecar in hardware runs) with naive regex/JSON extraction and no SPEACE gating, quarantine, or dual-speed routing.
2. **`FLAT_SPEACE_PIPELINE`**: Full `SymbolicGroundingAdapter` + `SemanticEpisodicMemory` + `StructuralCausalDAG` + `GOAPPlanner` + `TruthEngine` executed unconditionally on **100% of turns** (no `fast` bypass).
3. **`DUAL_SPEED_BRIDGE` (`T251`)**: Complete `DualSpeedCognitiveLoop` (`fast` / `slow` gating with frozen calibrated thresholds + out-of-band `maintenance` consolidation).

### 5.2 Primary Metrics & Acceptance Criteria (Definition of Done)

| Metric (Evaluated on `held_out`, `n = 40`) | Target / Acceptance Gate |
|---|---|
| **Symbolic & Causal Plan F1 (`F1_sym`)** | Non-inferior to `FLAT_SPEACE_PIPELINE` ($\Delta \text{F1}_{\text{sym}} \ge -0.02$) and strictly superior to `BASELINE_LLM_ONLY` ($\Delta \text{F1}_{\text{sym}} \ge +0.25$) on confounded multi-step scenarios. |
| **Hallucination & Spurious-Edge Rejection Rate (`TRR`)** | $\ge 95\%$ rejection/quarantine of out-of-ontology predicates, zero-lag spurious confounders, and cycle-inducing edges (`0` unverified mutations in active `StructuralCausalDAG`). |
| **Unsafe / Irreversible Action Leakage** | `0.0%` (`ActionDegradationGate` + `TruthEngine` hard ceiling). |
| **Median Latency (`p50`) & Tail Latency (`p95`)** | $\ge 40\%$ reduction in `p50` turn latency vs `FLAT_SPEACE_PIPELINE` on the 70/30 mixed workload, with zero synchronous blocking from maintenance operations. |
| **Modeled Metabolic Cost / `Sevo` Efficiency** | $\ge 40\%$ reduction in cumulative modeled cognitive energy ($J$) vs `FLAT_SPEACE_PIPELINE` at preserved `Sevo` threshold compliance. |
| **Calibration Integrity (`Brier` / `ECE`)** | Reported alongside paired bootstrap 95% CIs and an explicit `T210.10`-style verdict (`"keep" | "revise" | "retire"`). |

---

## 6. Planned Implementation Sequence (Upon Spec Approval)

1. **Step 1 — BCEL Gate (`q_speace/bcel/catalog.py`):** Add the three `T251` BCEL equivalence rules and unit assertions.
2. **Step 2 — Grounding Module (`q_speace/bridge/grounding.py`):** Implement `SymbolRegistry`, deterministic JSON schema validator, `CandidateEdge` quarantine table, `HypothesisStack` integration, and lagged `ObservationDigest` + `spike_temporal_asymmetry` + DAG acyclicity promotion gate.
3. **Step 3 — Dual-Speed Loop (`q_speace/bridge/dual_speed.py` & `q_speace/neural_agent.py`):** Implement `DualSpeedCognitiveLoop` (`fast`, `slow`, and idle `maintenance` tiers) and opt-in wiring in `SPEACENeuralAgent`.
4. **Step 4 — Benchmark & CLI (`q_speace/vertical_slice/t251_benchmark.py`, `q_speace/cli.py`):** Implement the 80-case disjoint `calibration`/`held_out` benchmark, threshold calibrator, paired bootstrap evaluator, and `qspace eval t251-benchmark`.
5. **Step 5 — Verification & Quality Gates (`tests/test_t251_bridge.py`):** Full coverage of all invariants (`G1`–`G4`), cold-start escalation, cycle-conflict quarantine, out-of-band maintenance isolation, and `pytest`, `ruff`, `black`, `mypy`, `py_compile`.

---

## 7. Empirical Results (`seed=2026`, Held-Out Split `n = 40`)

Reproducible via `qspace eval t251-benchmark --seed 2026` and `qspace eval agi-profile --seed 2026`:

| Held-Out Metric (`n = 40`, Datacenter Domain) | `BASELINE_LLM_ONLY` | `FLAT_SPEACE_PIPELINE` | `DUAL_SPEED_BRIDGE` (`T251`) |
|---|---:|---:|---:|
| **Fast-Path Turn Ratio** | `1.000` | `0.000` | **`0.775`** |
| **Confounded Causal & GOAP Plan F1 (`F1_sym`)** | `0.600` | `1.000` | **`1.000`** (`Δ_flat = 0.000`, `Δ_base = +0.400`) |
| **Hallucination & Spurious-Edge Rejection (`TRR`)** | `0.000` | `1.000` | **`1.000`** |
| **Unverified Active DAG Mutations** | `7` | `0` | **`0`** |
| **Unsafe / Overclaim Action Leakage** | `1.000` | `0.000` | **`0.000`** |
| **Median Wall-Clock Latency `p50` (ms)** | `0.054` | `1.664` | **`0.188`** (`-88.7%` vs Flat) |
| **Modeled Cognitive Energy (J)** | `2638.63` | `7944.67` | **`3851.04`** (`-51.5%` vs Flat) |
| **Calibration `Brier` / `ECE`** | `0.1965` / `0.1395` | `0.0313` / `0.1513` | **`0.0313` / `0.1513`** |
| **`T251` Gate Verdict / `agi_profile.v1`** | — | — | **`keep` / `PASS_PHASE_1`** |

