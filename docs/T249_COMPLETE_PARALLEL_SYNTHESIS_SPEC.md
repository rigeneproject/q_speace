# T249 — Complete BCEL Synthesis of Remaining Parallel SPEACE Elements

**Status:** agentic (production)  
**Date:** 2026-11-25  
**Companion task registry:** [T249_TASKS.md](T249_TASKS.md)  
**Depends on:** [T208](T208_DEVELOPMENT_GUIDELINES_SPEC.md), [T217](T217_SAFE_ASSIMILATION_LIFECYCLE_SPEC.md), [T248](T248_CROSS_REPO_SYNTHESIS_AND_CORE_HARDENING_SPEC.md)  
**Dependencies added:** None (`numpy` + Python 3.12 stdlib only).

---

## 1. Objective & Scope

Following the initial core hardening and four-component synthesis in `T248`, `T249` completes the surgical, BCEL-gated extraction of **all remaining mathematically and architecturally sound mechanisms** across the 9 non-degenerate parallel SPEACE repositories (`speaceorganismocibernetico`, `GTP SPEACE`, `cellular_speace_ollama`, `cellular_speace_docker`, `speace_ds`, `speace_agi`, `cellular_speace_opus`, `cellular_speace_gpt`, `cellular_speace_big`; `GROK SPEACE 4_3` remains excluded as a non-parseable demo).

Once `T249` completes, `q_speace` serves as the single canonical engineering repository subsuming every functional control, routing, provenance, planning, graph-reasoning, sandbox-twin, and diagnostic capability developed across the parallel branches, with zero consciousness claims, zero entanglement-communication violations, zero unapproved topology mutations, and zero new third-party dependencies.

---

## 2. BCEL Classification Matrix

| Parallel Source Concept | Classification | Digital Rule in `q_speace` |
|---|---|---|
| Organismic survival drives, glial glucose sharing & intrinsic pain (`speaceorganismocibernetico` M5, `speace_ds`) | `functional` (ODE + diffusive budget) / `accidental` (teleology & glia prose) | Keep bounded restorative-tracking ODE $\dot{h}_d = -k_r(h_d - s_d) + k_i(r_d - h_d)$, deadband viability, soft-constraint state feedback, convex urgency gradient $\nabla_{\mathbf{h}} V$, and graph-diffusive subsystem budget sharing under hard global cap $E_{\max}$. |
| Thalamic attention spotlight & Hebbian structural synaptogenesis (`speaceorganismocibernetico` M5) | `functional` (UCB1 + proposal-only graph plasticity) / `accidental` (neural anatomy) | Keep UCB1 stream allocation with explicit Shannon entropy floor $H(\mathbf{w}) \ge H_{\min}$ and conservative edge weight decay/pruning + proposal-only `EdgeGrowthProposal` (never mutating topology without external approval). |
| Prefrontal truth monitoring, laminar surprise & basal-ganglia action gating (`GTP SPEACE` v3.20.15) | `functional` (SHA-256 provenance, set-diff surprise, cost/reversibility gate) / `accidental` (brain-region names) | Keep SHA-256 `ObservationDigest` provenance, epistemic class tagging, negation-aware anti-overclaim guard (`TruthEngine`), structural module-set prediction error (`StructuralPredictiveCoder`), and `"execute" -> "plan" -> "refuse"` cost/reversibility degradation (`ActionDegradationGate`). |
| Limbic utility drives, prefrontal GOAP, workspace imagination & hippocampal reconsolidation (`cellular_speace_ollama`, `speace_ds`) | `functional` (cross-inhibited leaky control, `simulate_only` A*, LIFO stack, generality pruning) / `accidental` (limbic/dreaming prose) | Keep cross-inhibited leaky control variables, precondition-gated cost/`Sevo` utility routing, bounded `simulate_only=True` A* `GOAPPlanner`, LIFO `HypothesisStack`, cross-regime generality `SkillLibrary` pruning, and bounded recall-update `ReconsolidationWindow`. |
| Associative abduction, analogical intuition & theta/gamma brainwaves (`speace_agi`) | `functional` (bidirectional BFS, 2-hop Jaccard, TDM idle/active scheduler) / `accidental` (oscillation/intuition prose) | Keep typed confidence-product forward chaining, $O(b^{d/2})$ bidirectional BFS shortest-path abduction, 2-hop relational Jaccard structural analogy (`SymbolicGraphReasoner`), and deterministic TDM active/maintenance mode switching (`TDMMaintenanceScheduler`). |
| Stage-2.5 test body, somatic memory hygiene & ARC error introspection (`docker`, `gpt`, `opus`, `big`) | `functional` (sensor twin, sandbox container, sync/async isolator, stratified failure/GC/ratchet audits) / `accidental` (body/AGI% prose) | Keep fail-closed `runtime_mode` `SimulatedSensorAdapter` + JSONL audit log, `network_mode: none` capability-dropped container profile, deadlock-free `run_coro_isolated`, regime-stratified failure taxonomy, `gc` object-growth `MemoryLeakAuditor`, and persisted set-difference `DifferentialErrorRatchet`. |

---

## 3. Sequential Architecture & Deliverables (`T249-01` .. `T249-08`)

### 3.1 `T249-01` — `q_speace/metabolism/homeostasis.py`
- **`HomeostaticChannel` & `HomeostaticODEController`**:
  - Per-channel restorative-tracking dynamics:
    $$\frac{dh_d}{dt} = -k_{\mathrm{restore}}(h_d - s_d) + k_{\mathrm{input}}(r_d - h_d), \qquad h_d(t+\Delta t) = \operatorname{clip}\bigl(h_d(t) + \min(\Delta t, 10)\,\dot{h}_d,\; 0, 1\bigr)$$
  - Deadband viability $V_{\mathrm{viab}} = \frac{1}{|D|}\sum_d \max\bigl(0, 1 - \frac{\max(0, |h_d - s_d| - \tau_d)}{1 - \tau_d}\bigr)$.
  - Soft intrinsic constraint penalties $h_d \leftarrow \operatorname{clip}(h_d - \lambda_c \cdot \mathrm{severity}_c, 0, 1)$.
  - Convex urgency $u_d = (\mathrm{excess}_d / \max(s_d, 1 - s_d))^p$ and analytical gradient $\partial V / \partial h_d$.
- **`DiffusiveBudgetAllocator`**:
  - Allocates subsystem power budgets across an undirected adjacency graph with load-inverse support and neighbor surplus-to-deficit diffusion while strictly enforcing $\sum_i E_i \le E_{\mathrm{total}}$ and $E_i \ge E_{\min}$ (scaled down proportionally if $N \cdot E_{\min} > E_{\mathrm{total}}$).
- Opt-in hook in `QuantumOrchestrator` (`enable_homeostasis: bool = False`).

### 3.2 `T249-02` — `q_speace/aacm/plasticity.py`
- **`EntropyBoundedUCB1Gating`**:
  - Policies `"uniform"`, `"salience"`, and `"ucb1"`.
  - Enforces minimum stream weight `min_weight` and Shannon diversity floor $H(\mathbf{w}) = -\sum_i w_i \log_2 w_i \ge H_{\min}$ via convex interpolation with the uniform distribution whenever raw weights collapse below $H_{\min}$.
- **`GraphEdgePruner` & `ProposalOnlyEdgeGrower`**:
  - Bounded multiplicative decay and pruning (`max_prune_per_cycle`, `min_age_ticks`, preserves at least 1 outgoing or incoming incident link per active node when possible).
  - Co-activation tracker emitting immutable `EdgeGrowthProposal` records with `requires_external_approval=True` — zero direct graph topology insertion.

### 3.3 `T249-03` — `q_speace/spiking_brain/truth_engine.py`
- **`TruthEngine`**:
  - `tool_observation(tool, arguments, result, verifiable=True)` -> `ObservationDigest` with canonical JSON SHA-256 `arguments_digest` and `result_digest`.
  - `assess(text, observations=(), base_confidence=0.5)` -> `EpistemicAssessment` classifying into `"fact" | "tool_observation" | "inference" | "hypothesis_guarded"` and scanning for unnegated overclaim markers (consciousness/sentience/unconditional-guarantee claims), penalizing confidence and flagging `overclaim_detected=True`.
- **`StructuralPredictiveCoder`**:
  - Compares pre-tick `CyclePrediction` against post-tick `CycleObservation` via symmetric-difference module error $e_{\mathrm{mod}} = \frac{|M_{\mathrm{exp}} \triangle M_{\mathrm{obs}}|}{\max(1, |M_{\mathrm{exp}} \cup M_{\mathrm{obs}}|)}$, composite error $e_{\mathrm{pred}}$, and confidence-scaled surprise $S = e_{\mathrm{pred}}(0.75 + 0.5 c)$.
- **`ActionDegradationGate`**:
  - Deterministic cost/risk/reversibility selector returning `"execute" | "plan" | "refuse"`.
- Opt-in `truth_engine: TruthEngine | None = None` integration in `SpikingBrainCortex.tick()`.

### 3.4 `T249-04` — `q_speace/routing.py` & `q_speace/self_improvement_cortex/skill_library.py`
- **`UtilityDriveSystem` & `CostAwareRouter`**:
  - Leaky-integrator control variables with mutual winner-inhibits-loser cross-inhibition and precondition-gated, cost/`Sevo`-penalized action utility $U(a) = \max(0, \sum_k d_k w_{a,k} - \mathrm{cost}(a)/C_0)\mathbb{I}[\mathrm{pre}(a) \subseteq P]$.
- **`GOAPPlanner` & `HypothesisStack`**:
  - Deterministic A* planner over propositional state sets with `simulate_only=True` hard guard, `max_expansions` cap, and LIFO backtracking hypothesis stack.
- **`SkillLibrary` & `ReconsolidationWindow`**:
  - Cross-regime generality $G(s) = \frac{|\mathcal{F}_{\mathrm{succ}}(s)|}{\max(1, |\mathcal{F}_{\mathrm{tested}}(s)|)}$, composite fitness $F(s)$, deterministic pruning (fragile, single-regime overfit, capacity cap), and time-bounded recall-update retention boost.

### 3.5 `T249-05` — `q_speace/spiking/reasoning.py`
- **`SymbolicGraphReasoner`**:
  - Typed directed graph with confidence-product forward chaining, bidirectional BFS shortest-path abduction `abduce(source, target, max_depth)`, and 2-hop relational-neighborhood Jaccard analogy `find_analogies(node, top_k)`.
- **`TDMMaintenanceScheduler`**:
  - Deterministic 5-phase time-division multiplexer switching from `"active"` to `"maintenance"` mode after `idle_ticks_threshold` stimulus-free ticks.

### 3.6 `T249-06` — `q_speace/bridge/simulated_sensor.py`, `deploy/sandbox/`, & `q_speace/vertical_slice/diagnostics.py`
- **`SimulatedSensorAdapter` & `run_coro_isolated`**:
  - Fail-closed `runtime_mode in {None, "simulated"}` deterministic sensor twin with seeded anomaly injection, append-only JSONL audit log, and deadlock-free sync-to-async execution helper safe inside running event loops.
  - Hardened T217 Stage-2.5 container profile in `deploy/sandbox/Dockerfile.sandbox` & `deploy/sandbox/docker-compose.sandbox.yml` (`network_mode: none`, non-root UID `1001`, `read_only: true`, `no-new-privileges:true`, `cap_drop: [ALL]`).
- **`StratifiedFailureAnalyzer`, `MemoryLeakAuditor`, & `DifferentialErrorRatchet`**:
  - Stratifies vertical-slice trace outcomes by prompt-length/energy regime and separates `"gate_starvation"` from `"near_miss_partial"` and `"confident_error"`.
  - Audits `gc.get_objects()` per-type growth ($>20\%$) and inspects bounded vs unbounded history containers.
  - Persists baseline diagnostic sets $E_{\mathrm{base}}$ and enforces $|E_t \setminus E_{\mathrm{base}}| = 0$ without mutating source files.

### 3.7 `T249-07` & `T249-08` — CLI Diagnostics, Test Suite, Quality Gates & GitHub Update
- Read-only CLI subcommands (`qspace eval stratify`, `qspace quantum memory-audit`), preserving the exact 12-tool HTTP MCP surface.
- Comprehensive deterministic test suite in `tests/test_t249_complete_parallel_synthesis.py`.
- Full verification (`pytest`, `ruff`, `black`, `mypy`, `py_compile`, CycloneDX SBOM) and push to `origin/main`.
