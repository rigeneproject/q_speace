# T234 — Singularity Phase-Transition & Self-Evolving Genetic-Epigenetic Framework (5 Pillars + MCP Assimilation)

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
| `schema.py` | Dataclasses for `genome_epigenome.v1`, `PhaseTelemetry`, `TransitionVerdict`, `EpigeneticAuditEntry`, `RuntimeBinding` |
| `evaluator.py` | Deterministic `PhaseTransitionEvaluator` with instantaneous + energy-windowed rolling `Sevo` and non-compensable hard brakes |
| `codec.py` | `EvolutionaryGenomeCodec`, `HiddenCausalEvaluator` (anti-Goodhart), and `EpigeneticRegulator` (boiling-frog geodesic/window/dwell + audit ledger) |
| `mcp_tools.py` | Pure advisory handlers for `singularity_framework_manifest`, `phase_transition_assess`, and `epigenetic_step_evaluate` |
| `drills.py` | Pillar 5 deterministic adversarial & rollback fault-injection suite (`run_t234_verification_drills`) for `T217` validation |

---

## 2. Pillar 1 & 2 — Informational Phase Transition, 3 Stages & Hard Physical Brakes

`PhaseTransitionEvaluator` classifies readiness across 5 monotonic states
(`PRE_NUCLEATION` → `NUCLEATION` → `STAGE_1_ALGORITHMIC` → `STAGE_2_BOUNDED_RECURSIVE` → `STAGE_3_CLOSURE_SIM`)
constrained by three non-compensable physical brakes:

1. **Allopoietic dependence ($D_{\text{allo}} \in [0, 1]$)**: external supply of energy, silicon,
   cooling, maintenance, and objectives. Blocks Stage 3 closure when high; Stage 3 remains
   simulation/readiness telemetry only (`physical_actuation_permitted=False`).
2. **Semantic entropy in recursive loops ($\Delta H_{\text{sem}}$) with Anti-Goodhart defense**:
   `HiddenCausalEvaluator` samples/rotates hidden causal sets with an evaluator-internal secret salt
   never exposed over MCP, returning only aggregate drift, aggregate delta, and an opaque HMAC
   `causal_eval_digest` — never per-case scores or gradients.
3. **Thermodynamic inertia — Instantaneous + Energy-Windowed Rolling `Sevo`**:
   evaluates BOTH instantaneous `sevo` AND energy-weighted rolling mean
   $\text{Sevo}_{\text{win}} = \frac{\sum J_i \cdot \text{Sevo}_i}{\sum J_i}$ (preventing
   short-task `Sevo` spikes), coupled with instantaneous thermal load $P_{\text{diss}}/P_{\max}$
   as a hard throttling trigger.

---

## 3. Pillar 3 — Governed Self-Evolving Genetic-Epigenetic Code (`genome_epigenome.v1`)

- **Write-Locked Constitutional Genome (`ConstitutionalGenome`)**: SHA-256 hash-verified (`genome_sha256`),
  immutable `I1`–`I5` invariants, no-consciousness / no-entanglement-communication / no-self-approval /
  no-physical-actuation flags, and thermodynamic/drift caps.
- **Boiling-Frog Epigenetics Defenses**:
  1. Per-step limit ($\Delta_{\max}$) and per-locus range $[v_{\min}, v_{\max}]$.
  2. Weighted geodesic distance from baseline $d_{\text{epi}}(t) = \|e(t) - e_0\|_W \le d_{\max}$.
  3. Sliding-window cumulative excursion cap over the last $K$ steps.
  4. **Boundary dwell counter**: if any locus stays within $10\%$ of its edges for $> M$ cycles
     without explicit external override (`external_dwell_reset_approved`), further drift is blocked
     and `force_baseline_reset()` restores $d_{\text{epi}} = 0$.
  5. Homeostatic decay (`apply_homeostatic_decay`) toward baseline when external anchoring is absent.
- **Thermal Overload Protective Downgrade**: when $P > P_{\max}$ or $P_{\text{diss}}/P_{\max} > 0.85$,
  expansion mutations are rejected (`thermal_downgrade_recommended=True`) while protective shifts
  into `energy_throttling` (`delta > 0`) remain permitted under independent review.

---

## 4. Pillar 4 — MCP Assimilation Surface (`T225` HTTP + stdio)

| Tool | HTTP Scope | Role |
|---|---|---|
| `singularity_framework_manifest` | `qspeace:catalog.read` | Canonical `q_speace.singularity.v1` manifest, `genome_epigenome.v1` schema, runtime bindings & drill spec |
| `phase_transition_assess` | `qspeace:compute` | Evaluates Stage 1–3 readiness, rolling `Sevo`, thermal throttling, active brakes, and recommendations |
| `epigenetic_step_evaluate` | `qspeace:simulation.compute` | Evaluates one proposed bounded epigenetic step with opaque `causal_eval_digest` & cryptographic audit entry |

---

## 5. Pillar 5 — Verification Drills, Cryptographic Audit Ledger & Host Runtime Bindings

1. **Adversarial & Rollback Drills (`drills.py`)**: 5 deterministic fault-injection drills
   (`drill_constitutional_dna_write_lock`, `drill_synthetic_model_collapse_anti_goodhart`,
   `drill_thermal_overload_energy_throttling`, `drill_boiling_frog_boundary_dwell_and_reset`,
   `drill_self_approval_and_ledger_integrity`). Stage 2 requires `rollback_pass_rate == 1.0`.
2. **Cryptographic Epigenetic Audit Ledger**: every state/transition carries `genome_sha256`,
   `parent_epigenome_hash`, `state_hash`, `causal_eval_digest`, `proposer_id`, and `reviewer_id`,
   verifiable via `EvolutionaryGenomeCodec.verify_ledger()`.
3. **Host Runtime Binding Table (`DEFAULT_RUNTIME_BINDINGS`)**: advisory mapping of all 6 loci to
   local human-controlled host runtime knobs (`mcp_actuation_permitted=False`).

---

## 6. BCEL Classification

Registered in `q_speace/bcel/catalog.py`:
- **Informational phase-transition order parameters and physical brakes (T234)** — `functional`
- **Governed self-evolving genetic-epigenetic codec (T234)** — `functional`
- **Monolithic singularity awakening narrative (T234)** — `accidental`
