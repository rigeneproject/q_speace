# T172 — Information Value Module (H → V → π)

**Document ID:** SPEACE-T172-SPEC
**Version:** 1.0
**Status:** Draft
**Date:** 2026-06-26
**Owner:** cellular_brain / omni_rag
**Layer:** L5 (Cognitive Agents) — wraps L1-L4 with observer + proposer role

---

## 1. Purpose and Scope

Close the gap identified in the context-engineering diagnosis:
**SPEACE has drive values but lacks a value function that operationalizes
the trade-off between order and exploration.** This document specifies
three cooperating modules that together instantiate the relationship
`state → perceived_entropy → informational_value → action proposal`.

The design does NOT modify any constitutional DNA, ILF field, BCEL catalog
entry, or safety-critical path. All modifications are confined to:

- a new package `speace_core/cellular_brain/information_value/`
- a new Omni-RAG collector `speace_core/omni_rag/collectors/information_value_collector.py`
- a new audit helper `motivation_audit`
- a new test suite under `tests/`

---

## 2. Problem Statement

SPEACE already has:

| Component | Location | What it does |
|---|---|---|
| Autonomous drives | `drives/autonomous_drive_engine.py` | 7 homeostatic drives with setpoints |
| Drive conflict resolver | `drives/drive_conflict_resolver.py` | winner-take-all with conflict matrix |
| Curiosity layer | `experience/infant_curiosity_layer.py` | observational curiosity score |
| Endogenous exploration bonus | `experience/endogenous_exploration_bonus.py` | pseudo-count + RND novelty bonus |
| Active inference | `dynamics/active_inference_engine.py` | action selection by EFE minimisation |
| State transition policy | `cognition/state_transition_policy.py` | guard logic for FSM transitions |
| Entropy monitor | `evolutionary_kernel/entropy_dynamics_monitor.py` | informational + thermodynamic entropy |
| Information density | `analysis/information_density_engine.py` | activation/weight/connectivity entropy |

What is missing:

1. **A unified perceived-entropy scalar `H_local(t)`** that aggregates the
   existing signals into a single quantity the rest of the system can
   condition on.
2. **An inverted-U value function `V(novelty, predictability, compressibility)`**
   that operationalizes the relationship between
   `destructive_entropy_reduction` (S_ent) and
   `generative_variability_preservation` (V_gen) without modifying the
   principles themselves.
3. **A deterministic exploration policy `π(a|s,V)`** that proposes (does
   NOT execute) actions through the existing actuator governance.
4. **A motivational audit** that lets the Omni-RAG answer "how much
   internal motivation does SPEACE have right now, and is it traceable
   from the genome down to a decision?".

---

## 3. Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    INFORMATION VALUE TRIAD                        │
│                                                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐    │
│  │ PerceivedEntropy│─▶│ Informational  │─▶│ Exploration    │    │
│  │ Module          │  │ ValueFunction  │  │ Policy π(a|s,V)│    │
│  │                 │  │ (inverted-U)   │  │                │    │
│  │ H_local(t) ∈[0,1]│ │ V ∈ [-1,+1]    │  │ ActionProposal │    │
│  └────────────────┘  └────────────────┘  └────────┬───────┘    │
│         ▲                                            │           │
│         │                                            ▼           │
│  ┌──────┴───────┐                       ┌────────────────┐     │
│  │ existing     │                       │ EmbodiedAction │     │
│  │ engines      │                       │ Actuator       │     │
│  │ (read-only)  │                       │ (governance)   │     │
│  └──────────────┘                       └────────────────┘     │
└──────────────────────────────────────────────────────────────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │ Omni-RAG cognitive    │
                    │ graph + audit         │
                    └───────────────────────┘
```

### 3.1 Module A — PerceivedEntropyModule

**File:** `speace_core/cellular_brain/information_value/perceived_entropy.py`

Aggregates the following inputs (all optional, clipped to `[0, 1]`):

| Signal | Source | Default weight |
|---|---|---|
| `prediction_error` | `PredictiveCodingEngine.get_prediction_error` | 0.30 |
| `novelty` | `InfantCuriosityLayer.get_average_curiosity` | 0.25 |
| `informational_entropy` | `EntropyDynamicsMonitor.summarize()` | 0.20 |
| `signal_diversity` | `InformationDensityEngine.compute_all()` | 0.15 |
| `surprise` | `ActiveInferenceEngine.expected_free_energy` | 0.10 |

Output: `H_local(t) ∈ [0, 1]` snapshot, persisted in a bounded ring buffer
(1024 entries, half-evicted).

**DNA mapping:** S_ent (when H is high) and V_gen (when H is low).
**Does NOT modify** any principle.

### 3.2 Module B — InformationalValueFunction

**File:** `speace_core/cellular_brain/information_value/value_function.py`

Implements the inverted-U value function:

```
V_raw       = exp(-((n - 0.5)² + (p - 0.5)² + (c - 0.5)²) / (2σ²))
V_normalised = 2 · V_raw - 1       ∈ [-1, +1]
```

with `σ = 0.30` and sweet spot at `(0.5, 0.5, 0.5)`.

Regimes:

| Regime | Condition | Meaning |
|---|---|---|
| `sweet_spot` | V_normalised ≥ 0.55 | Information-rich equilibrium |
| `ordered` | n < 0.1, p > 0.8, c > 0.8 | Rigid / uninformative |
| `chaotic` | n > 0.7, p < 0.3, c < 0.3 | Noise / un-compressible |
| `saturated` | n > 0.95, p < 0.2 | Over-stimulation |
| `suboptimal` | −0.5 ≤ V_norm ≤ 0.55 | Off sweet spot but recoverable |
| `anti_preferred` | V_norm < −0.5 | Actively avoid |

The function exposes `as_functional_law()` which returns a dict compatible
with `FunctionalConstraintLaw` registration in the BCEL catalog.

### 3.3 Module C — ExplorationPolicy

**File:** `speace_core/cellular_brain/information_value/exploration_policy.py`

Deterministic policy `π(a | s, V)` that returns an `ActionProposal`.
The proposal is intentionally a value object: it never executes the
action. The caller (e.g. the orchestrator or the ANS) is expected to
forward it through `EmbodiedActionActuator.propose_action()`.

Mapping:

| Regime | Proposal kind | Rationale |
|---|---|---|
| `energy_crisis` | `request_sleep` | Energy below 0.25 — sleep to recover |
| `coherence_crisis` | `checkpoint` | Coherence below 0.25 — snapshot state |
| `starvation` | `actuate` | V < −0.30 — inject variation |
| `satiation` | `garbage_collect` | V > 0.40 — consolidate memories |
| `sweet_spot` / `suboptimal` | `observe` | Low-pressure probe |

Each proposal includes: `kind`, `params`, `score`, `rationale`, `regime`,
`V`, `timestamp`.

---

## 4. DNA / BCEL / Periodic Table Mapping

### 4.1 DNA

The module does NOT modify `species_orientation.yaml`. It operationalizes
the implicit trade-off between:

- `destructive_entropy_reduction` (S_ent) — kept low → low H_local
- `generative_variability_preservation` (V_gen) — kept above threshold → high H_local

A proposed addendum to add a 7th principle `informational_value_optimization`
(symbol `S[I]`) is left for human gate per AGENTS.md §3 and §7.

### 4.2 BCEL

The collector registers 4 new equivalences as `BCEL_MAPPING` nodes:

| Name | Biological form | Digital implementation |
|---|---|---|
| `motivational_dopaminergic_loop` | RPE / dopamine | `ExplorationPolicy` |
| `curiosity_rnd_signal` | Random Network Distillation novelty | `EndogenousExplorationBonus` |
| `free_energy_active_inference` | Friston FEP | `ActiveInferenceEngine + EmbodiedLoop` |
| `inverted_u_value_function` | Yerkes-Dodson inverted-U | `InformationalValueFunction` |

These can be materialised into `bcel/catalog.py` via a human-approved
edit. In T172 we only register them in the Omni-RAG collector; the
catalog itself is not modified.

### 4.3 Periodic Table

The value function exposes `as_functional_law()` to be registered via
`FunctionalConstraintRegistry.register()`. No edit to
`functional_constraint_law.py` is required — the registry is data-driven.

---

## 5. Omni-RAG Integration

### 5.1 Collector

`InformationValueCollector` is exposed in `speace_core/omni_rag/collectors/`.

Calling `collector.collect_snapshot(signals, state)` returns:

- 1 `METRIC` node for `H_local`
- 1 `METRIC` node for `V` (informational_value)
- 1 `DECISION` node for the proposal
- 4 `BCEL_MAPPING` nodes for the new equivalences
- 6 edges: H→V (TRIGGERS), V→proposal (REGULATES), 4× BCEL→proposal (IMPLEMENTS)

### 5.2 Audit

`motivation_audit(graph)` returns a structured report:

```python
{
    "pass": bool,
    "perceived_entropy_present": bool,
    "informational_value_present": bool,
    "proposal_present": bool,
    "bcel_coverage": {...},
    "v_to_decision_edge_present": bool,
    "missing_bcel": [...],
}
```

The audit is invoked via `speace omni-audit --type motivation` (to be wired
into `cli.py` in a follow-up task T173, gated by AGENTS.md §3 review).

---

## 6. Safety Boundaries

1. **No mutation of constitutional files.** DNA, BCEL catalog, ILF,
   orchestrator, immune, action governance are untouched.
2. **No direct action execution.** `ExplorationPolicy` returns a proposal;
   the caller must forward it through the existing actuator governance.
3. **No external dependencies.** All modules use stdlib + existing deps.
4. **Bounded memory.** Each module keeps at most 1024 history entries.
5. **Reversible.** Removing the package leaves no persistent state.

---

## 7. Test Plan

Two test files:

- `tests/cellular_brain/information_value/test_information_value.py` — 20 tests
  covering each module + end-to-end loop.
- `tests/omni_rag/collectors/test_information_value_collector.py` — 8 tests
  covering graph materialisation + motivation audit.

All 28 tests pass. The full `tests/omni_rag/` suite (86 tests including
pre-existing ones) still passes — no regressions.

---

## 8. Acceptance Criteria

- [x] H_local aggregates 5 signals into `[0, 1]`
- [x] V is maximum at the sweet spot, minimum at pure order / pure chaos
- [x] π proposes, never executes
- [x] Safety floor: energy < 0.25 → sleep, coherence < 0.25 → checkpoint
- [x] motivation_audit can detect a missing value node
- [x] 28 new tests pass, 0 regressions
- [x] `python -m py_compile` passes on all touched files
- [x] No new dependencies introduced
- [x] No modification to DNA / BCEL / ILF / orchestrator

---

## 9. Future Work (out of scope for T172)

- T173: wire `motivation_audit` into `cli.py` and into the
  Omni-RAG CLI commands (`speace omni-audit --type motivation`).
- T174: register the 4 new BCEL equivalences into `bcel/catalog.py`
  via human-approved PR (AGENTS.md §3).
- T175: propose DNA addendum for `informational_value_optimization`
  principle (human gate required, AGENTS.md §7.1).
- T176: integrate `ExplorationPolicy` into `AutonomicNervousSystem.pulse`
  to drive `generate_internal_thought` from V (in addition to the
  existing `tendency` parameter).
- T177: drive `StateTransitionPolicy.CURIOSITY_HIGH` threshold from V
  rather than from a fixed constant.

---

## 10. References

- `AGENTS.md` — production mode rules and human gates
- `docs/SPEACE_BCEL_DESIGN.md` — BCEL pipeline
- `docs/SPEACE_OMNI_RAG_ARCHITECTURE.md` — Omni-RAG layer specs
- `speace_core/dna/genome/core/species_orientation.yaml` — informational principles
- `speace_core/cellular_brain/drives/autonomous_drive_engine.py` — existing drive system
- `speace_core/cellular_brain/experience/infant_curiosity_layer.py` — existing curiosity layer
- `speace_core/cellular_brain/dynamics/active_inference_engine.py` — existing active inference
- `speace_core/cellular_brain/neuroperiodic/functional_constraint_law.py` — periodic table

---

*End of specification — T172 Information Value Module*