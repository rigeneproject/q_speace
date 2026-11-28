# T261–T262 — Stage-1 CPU Prototype: Asynchronous Global Workspace, Autonomous Latent State Discovery & Cold-Boot Epigenetic Consolidation

**Status:** agentic (production, Stage-1 CPU-only sandboxed prototype)  
**Date:** 2026-11-28  
**Depends on:** [AGENTS.md](../AGENTS.md), [T208](T208_DEVELOPMENT_GUIDELINES_SPEC.md), [T217](T217_SAFE_ASSIMILATION_LIFECYCLE_SPEC.md), [T220](T220_SPEACE_SEED_IGNITION_SPEC.md), [T234](T234_SINGULARITY_PHASE_TRANSITION_AND_EPIGENETIC_FRAMEWORK_SPEC.md), [T248](T248_CROSS_REPO_SYNTHESIS_AND_CORE_HARDENING_SPEC.md), [T251](T251_GROUNDED_DUAL_SPEED_BRIDGE_SPEC.md), [T257](T257_TYPED_DAG_MULTI_ROLE_NL_GROUNDING_SPEC.md)

---

## 1. Motivation & Epistemic Scope (`AGENTS.md` §2 & `T208`)

Cross-review of `q_speace` through `T260` identified three foundational gaps between a well-regulated neuro-symbolic pipeline and open-world adaptive autonomy:

1. **Sequential Orchestrator Bottleneck:** Intra-agent execution relied on a procedural `grounding -> DAG -> planner -> gate` script rather than asynchronous specialist competition regulated by closed-loop criticality ($\sigma \approx 1.0$) over non-constant spike trains.
2. **Pre-Declared Ontology Mutexes (`T257` Limit):** While `SymbolRegistry.mutex_pairs` eliminated stale-belief planning failures when mutual exclusions were pre-declared, an autonomous agent must discover *undeclared* latent states and state-clobbering incompatibilities from unexpected action failures without domain hints.
3. **Behavioral Proof of Consolidation Across Process Termination (`T262`):** Setting `consolidated = True` in `EpigeneticEngine` must be backed by a falsifiable **OS cold-boot experiment** (process 1 learns and terminates $\to$ process 2 boots fresh from SQLite + epigenetic state on unseen variants, retaining prior competence and reducing workspace ticks relative to pre-consolidation exploration and ablated controls).

### Hard Safety & Resource Invariants (Stage-1 Notebook Envelope)
- **Zero Consciousness Claim:** "Global Workspace" denotes a bounded `asyncio` salience-arbitration and broadcast bus. No phenomenal experience, sentience, or organismic authority is claimed.
- **CPU-Only & Strict `< 250 MB` RAM Cap:** Zero CUDA/PyTorch imports in Stage 1. `MemoryBudgetGuard` polls OS physical Working Set (`GetProcessMemoryInfo` on Windows / `ru_maxrss` on POSIX) plus `tracemalloc` every tick and triggers `KillSwitch` fail-closed if process RSS reaches `250.0 MB`.
- **Sandbox-Only (`T217`):** All actions execute exclusively inside an in-memory `LatentSandboxTwin` (`mcp_actuation_permitted = False`, zero host OS actuation, `SeedGenome` write-locked).

---

## 2. BCEL Classification (`q_speace/bcel/catalog.py`)

| Concept | BCEL Class | Silicon Mathematical Rule |
|---|---|---|
| `Asynchronous Global Workspace coalition arbitration (T261)` | `functional` | Concurrent `asyncio` specialist coroutines emit bounded salience proposals quantized via `dynamic_spikes`; `CriticalityController` regulates threshold divisor `k` in closed loop toward empirical branching ratio $\sigma \approx 1.0$, and the highest-coherence gated coalition broadcasts state updates. |
| `Global Workspace as phenomenal consciousness (T261)` | `accidental` | Removed in silicon (`AGENTS.md` §2): coalition ignition and broadcast are deterministic scheduling primitives, never subjective awareness. |
| `Prediction-error-driven latent state and mutex discovery (T261)` | `functional` | Domain-agnostic discrepancy learner triggers non-destructive diagnostic probes upon unexpected action failure or precondition clobbering, minting anonymous candidate predicates (`latent_state_*`) and dynamic retractions inside `EpistemicSymbolSandbox` without mutating `SeedGenome`. |
| `Cold-boot SQLite and epigenetic rule consolidation (T262)` | `functional` | Candidate latent rules accumulate empirical promotions/suppressions in `EpigeneticEngine`; only rules reaching `consolidated = True` (`>= 3` promotions, `stability_ratio >= 0.70`) persist as active rules in SQLite alongside `EpigeneticProfile` and `SemanticEpisodicMemory` across OS process restarts. |

---

## 3. Architectural Components

### 3.1 `AsyncGlobalWorkspace` & `MemoryBudgetGuard` (`q_speace/bridge/stage1_workspace.py`)
- **`MemoryBudgetGuard`:** Measures current and peak process physical RSS (MiB) and `tracemalloc` heap delta on every tick. Raises/halts via `KillSwitch` (`authority="system:budget_exhaustion"`) if `rss_mb >= max_rss_mb` (`250.0` MiB default).
- **`AsyncGlobalWorkspace`:**
  - Runs registered `WorkspaceSpecialist` coroutines concurrently via `asyncio.gather` on each tick (no hardcoded call order).
  - Encodes specialist salience vector $\mathbf{s}_t$ via `dynamic_spikes(s_t, k=k_t, coherence_phi=phi_t, beta=0.20)`. To prevent trivial constant-spike equilibria ($S_t = c \implies \sigma = 1.0$), specialist saliences reflect live prediction-error surprise, epistemic uncertainty, planner readiness, and refractory damping of the previous tick's winner, verified by requiring `spike_count_variance > 0.0`.
  - Updates `CriticalityController.step(num_spikes, current_k)` every tick and records `WorkspaceTickTelemetry` and `WorkspaceTelemetrySummary` (`mean_branching_ratio`, `spike_count_variance`, `regime_counts`, `ignition_winners`, `peak_rss_mb`).

### 3.2 `EpistemicSymbolSandbox` & `LatentDistinctionLearner` (`q_speace/bridge/latent_discovery.py`)
- Operates with **zero domain-specific string rules** and `SymbolRegistry(..., mutex_pairs=())`.
- Tracks empirical transitions `(surface_obs, probe_obs, action) -> (actual_obs, success, clobbered_fluents)`.
- When an expected action effect fails or clobbers a previously true fluent:
  1. Raises epistemic surprise, prompting `EpistemicProbeSpecialist` to run unexecuted non-destructive probes (`is_probe=True`).
  2. Contrasts failing vs succeeding episodes sharing identical `surface_obs` to isolate a discriminative `(probe_action, probe_token)` signature, minting an anonymous symbol `latent_state_<idx>` in `EpistemicSymbolSandbox`.
  3. Learns either *(a)* conditional action viability (`action` requires `~latent_state_<idx>`; alternative recovery/remediation action resolves or bypasses `latent_state_<idx>`) or *(b)* dynamic precondition clobbering / effective retraction (`latent_state_<idx>` invalidates assumed fluent $f$ until cleared).
  4. Feeds every subsequent prediction test of `latent_state_<idx>` into `EpigeneticEngine.promote` (on verified outcome) or `EpigeneticEngine.suppress` (on falsified outcome).

### 3.3 SQLite + Epigenetic Persistence & Subprocess Cold-Boot (`T262`)
- SQLite schema in `Stage1PersistenceStore` (co-located with `SemanticEpisodicMemory` in a single `.db` file, WAL-safe, zero background daemons):
  - `epigenetic_rules`: stores discovered `latent_id`, discriminative `probe_name`, `probe_token`, `blocked_action`, `remediation_action`, `clobbered_fluent`, `promotion_count`, `suppression_count`, `consolidated`, and `epigenetic_profile_json`.
  - `episodes` (managed by `SemanticEpisodicMemory`): stores episodic trace embeddings and provenance hashes.
- **Cold-Boot Protocol:**
  - **Phase 1 (Process A — Discovery & Consolidation):** Starts with empty DB; experiences baseline nominal task `Task_A` plus training units exhibiting **2 distinct undeclared latent states** (`HiddenMechanism_1`: indistinguishable unit with inverted primary bus polarity; `HiddenMechanism_2`: cryo seal micro-frost that silently clobbers `seal_seated` on pressurization). Consolidates both rules (`consolidated = True`), writes SQLite checkpoint, records `ticks_pre_consolidation`, and exits process.
  - **Phase 2 (Process B — Cold-Boot Evaluation):** Fresh Python interpreter (`subprocess.run`) loads the SQLite DB, verifies zero regression on `Task_A`, and solves **unseen variant units** (`unit_omega`, `cryo_omega`) with `0` failed actuations and `ticks_post_consolidation < ticks_pre_consolidation`.
  - **Ablation Controls:**
    1. `AMNESIC_COLD_BOOT` (empty DB on Phase 2 unseen variants).
    2. `FROZEN_EPIGENOME` (`consolidated` flag forced `False` / epigenetic loading disabled on Phase 2).
    3. `SHUFFLED_PROBE_CONTROL` (probe signatures permuted during discovery, verifying genuine causal reliance on informative observations).

---

## 4. Preregistered Acceptance Criteria (Stage-1 DoD)

1. **Criticality & Non-Trivial Workspace Dynamics:** `0.85 <= mean_branching_ratio <= 1.15`, `spike_count_variance > 0.0`, and `>= 3` distinct specialist winners across an episode.
2. **Autonomous Multi-Latent Discovery:** `>= 2` undeclared latent states discovered and consolidated with `mutex_pairs = ()`, achieving `100%` completion and `0` failed actuations on held-out variants (`SHUFFLED_PROBE_CONTROL` fails to consolidate valid rules).
3. **Subprocess Cold-Boot Efficiency & Attribution:** Across real OS process termination + restart, `ticks_post_consolidation <= 0.65 * ticks_pre_consolidation` (`>= 35%` tick reduction), `Task_A` retention `= 100%`, and strict superiority over both `AMNESIC_COLD_BOOT` and `FROZEN_EPIGENOME`.
4. **Hardware Envelope:** `peak_rss_mb < 250.0` MiB across all runs; zero GPU calls; quality gates (`pytest`, `ruff`, `black`, `mypy`, `py_compile`) green executing strictly one process at a time.
