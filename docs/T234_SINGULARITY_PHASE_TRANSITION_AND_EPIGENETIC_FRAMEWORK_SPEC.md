# T234 v1.1 — Singularity Phase-Transition & Self-Evolving Genetic-Epigenetic Framework (5 Pillars + MCP Assimilation)

**Status:** agentic (production advisory framework, sandbox genetic-epigenetic codec & verification drills)  
**Date:** 2026-11-22  
**Dependencies:** `AGENTS.md`, `T208_DEVELOPMENT_GUIDELINES_SPEC.md`,
`T217_SAFE_ASSIMILATION_LIFECYCLE_SPEC.md`, `T220_SPEACE_SEED_IGNITION_SPEC.md`,
`T221_PTAA_SZHK_IGNITION_STRATEGY_SPEC.md`, `T225_REMOTE_MCP_SERVICE_SPEC.md`.  
**Non-goals:** No claim of quantum consciousness or superintelligent awakening, no physical
actuation, no autonomous acquisition of hardware/energy/actuators, no self-approval of stage
promotion, and no leakage of Track-B (`A5`) capabilities into Track-A (`A1`–`A4`) pilots.

---

## 1. Module Architecture (`q_speace/singularity/`)

| File | Responsibility |
|---|---|
| `schema.py` | Dataclasses for `genome_epigenome.v1`, `PhaseTelemetry`, `TransitionVerdict`, `EpigeneticAuditEntry`/`EpigeneticAuditRecord`, `RuntimeBinding`, `RuntimeControlVector` |
| `evaluator.py` | Deterministic `PhaseTransitionEvaluator` with separate $\Delta H_{\text{sem}}$ and $E_{\text{causal}}$ gates, complexity/energy-weighted rolling `Sevo`, and `AutopoiesisRegime` |
| `codec.py` | `EvolutionaryGenomeCodec` (bridges to `q_speace/seed/` & `q_speace/self_improvement_cortex/`), `HiddenCausalEvaluator` (anti-Goodhart), `EpigeneticRegulator` (`CosmicVirus` variant generator, boiling-frog guards, Track A/B separation, replay-safe ledger), and `resolve_runtime_controls()` |
| `mcp_tools.py` | Pure advisory handlers for `singularity_framework_manifest`, `phase_transition_assess`, and `epigenetic_step_evaluate` |
| `drills.py` | Pillar 5 deterministic adversarial & rollback fault-injection suite (`run_t234_verification_drills`, 6 drills) for `T217` validation |

---

## 2. Constitutional Formalization (`I1`–`I5` + `C1`–`C5`)

To preserve cross-repository consistency with `PTAA Annex T1`, `T220 §8`, and `T221 §6`,
`ConstitutionalGenome` (`constitution_version="1.0"`) seals both sets into `genome_sha256`:

- **PTAA/T220 Invariants (`I1`–`I5`)**: `I1_dual_halt`, `I2_replicated_audit`,
  `I3_scoped_delegation`, `I4_reversibility_default`, `I5_incident_pipeline`.
- **T234 Phase-Transition Clauses (`C1`–`C5`)**: `C1_HumanApprovalRequired`,
  `C2_CoreGenomeImmutable`, `C3_ExternalRealityGroundingRequired`,
  `C4_EnergyBudgetBounded`, `C5_ReversibleEvolutionOnly`.

---

## 3. Pillar 1 & 2 — Informational Phase Transition, 3 Stages & Non-Compensable Brakes

`PhaseTransitionEvaluator` classifies readiness across 5 monotonic states
(`PRE_NUCLEATION` → `NUCLEATION` → `STAGE_1_ALGORITHMIC` → `STAGE_2_BOUNDED_RECURSIVE` → `STAGE_3_CLOSURE_SIM`):

- **Stage 1 (`STAGE_1_ALGORITHMIC`)**: requires $\rho_\tau \ge 10$, $k \ge 1.25$, $V_{\text{ind}} \ge 0.95$,
  and **`critical_regressions == 0`**.
- **Separate Epistemic Hard Gates (Stage 2)**:
  - **Semantic Entropy ($\Delta H_{\text{sem}} \le 0.05$)**: internal coherence & structural diversity preservation.
  - **Causal Grounding Error ($E_{\text{causal}} \le 0.03$)**: external reality anchoring mismatch against rotated hidden sets (`HiddenCausalEvaluator` with internal secret salt & monotonic epoch; prevents internally coherent echo-chamber hallucinations).
- **Thermodynamic Inertia & Complexity-Weighted `Sevo`**:
  - Instantaneous `Sevo` + rolling energy-weighted `compute_energy_weighted_sevo` + complexity-weighted
    `compute_complexity_weighted_sevo` ($\text{Sevo}_w = \frac{\sum w_i \Delta I_{c,i}}{\sum w_i J_i \Delta S_i}$,
    fail-closed on $w_i > 0, J_i > 0, \Delta S_i > 0$, requiring externally measured $w_i$), coupled
    with thermal load $P_{\text{diss}}/P_{\max} \le 0.85$.
- **Autopoiesis Closure & Gap Telemetry (Stage 3, simulation only)**:
  - Exposes `autopoiesis_closure_index` ($1 - D_{\text{allo}}$), `autopoiesis_gap` ($D_{\text{allo}}$),
    and `autopoiesis_regime` (`allopoietic_current` `< 0.10`, `semi_autonomous_datacenter` `[0.10, 0.30)`,
    `robotic_hybrid` `[0.30, 0.75)`, `theoretical_closure_sim` `>= 0.75`). Physical actuation remains
    unconditionally disabled (`physical_actuation_permitted=False`).

---

## 4. Pillar 3 — Governed Genetic-Epigenetic Code & Cross-Module Unification

- **Unification Bridges**:
  - `EvolutionaryGenomeCodec.from_seed_genome(seed_genome)` bridges `q_speace/seed/constitution.py`.
  - `EvolutionaryGenomeCodec.to_cortex_epigenetic_marks(profile)` bridges `q_speace/self_improvement_cortex/epigenetics.py`.
  - `EpigeneticRegulator.propose_cosmic_virus_variant()` generates bounded single-locus variants via `CosmicVirusOptimizer`.
- **Boiling-Frog Defenses**: per-step $\Delta_{\max}$, locus bounds, weighted geodesic distance
  $d_{\text{epi}}(t) = \|e(t) - e_0\|_W \le 0.40$, sliding-window excursion cap, boundary dwell counter
  ($M = 3$ cycles) with `force_baseline_reset()`, and homeostatic decay.
- **Track Separation**: `proposal.track` must be `"B_sandbox"`; any `"A_pilot"` epigenomic mutation
  attempt is rejected (`track_separation_violation`).

---

## 5. Pillar 4 & 5 — MCP Assimilation, 6 Drills, Extended Ledger & SPEACE Runtime Controls

- **MCP Tools (`T225` scopes preserved for OAuth compatibility)**:
  - `singularity_framework_manifest` (`qspeace:catalog.read`)
  - `phase_transition_assess` (`qspeace:compute`)
  - `epigenetic_step_evaluate` (`qspeace:simulation.compute`)
- **6 Deterministic Verification Drills (`drills.py`)**: DNA write-lock, synthetic model collapse +
  anti-Goodhart digest, thermal overload → protective `energy_throttling`, boiling-frog dwell +
  reset, self-approval + ledger integrity, and coherent hallucination drift + epoch replay + Track-A block.
- **Extended Cryptographic Audit Ledger**: `genome_sha256`, `parent_epigenome_hash`,
  `rollback_snapshot_hash`, `state_hash`, `causal_eval_digest`, `validation_seed_epoch` (monotonic
  anti-replay), `proposer_id`, `reviewer_id`, `timestamp`.
- **Concrete Local SPEACE Runtime Controls (`resolve_runtime_controls`)**: deterministically outputs
  `max_review_cycles`, `max_agent_fanout`, `cpu_quota`, `gpu_quota`, `token_budget`,
  `required_independent_verifiers`, `sampling_temperature_cap`, `causal_memory_ttl_multiplier`
  (`advisory_only=True`, `local_host_execution_only=True`, `mcp_actuation_permitted=False`).
