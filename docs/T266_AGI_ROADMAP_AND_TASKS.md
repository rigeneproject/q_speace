# T266 — Development Plan Toward General Capability: Roadmap, Gates and Tasks

**Status:** approved by the maintainer on 2026-11-28; revision 2 (same day) · **Date:** 2026-11-28
**Depends on:** T208, T217, T263, T264, T265 · **Hardware envelope:** notebook, RTX 3060 6 GB, 16 GB RAM

## Revision 2 — changes after the external critique of the first assessment

1. **Measure before building.** One external, preregistered, four-arm experiment (T267) now
   precedes the unified kernel. Former P2 becomes P1; the kernel (now P2) is built only around
   what the experiment shows to matter.
2. **ARC-AGI removed from the near-term plan.** On a 3B model it measures the base weights, not
   grounding or cross-session memory. Target environments are sequential, partially observable
   and non-stationary: TextWorld, PlanBench, ALFWorld (text), MiniGrid/BabyAI with perturbations.
3. **Four arms at equal model and equal token budget:** schema-constrained LLM; LLM + standard
   verifier/retry; core without memory; full core. The third arm attributes any gain.
4. **Repository strategy.** Publish history and tag the current state on `main`; low-risk
   clean-up through small pull requests; physical split of frozen modules only on a short
   `core-refactor` branch *after* T267 (the remote MCP service imports `economy/`,
   `singularity/` and IoNT code, so "frozen" cannot mean "moved" yet).
5. **Vocabulary.** Every bio-inspired term is paired with its engineering name; "proto-AGI"
   is withdrawn from reports by errata (T266-05).

## 0. Principles (binding for every task below)

1. **One brain.** A single entry point (`q_speace/brain/`) owns perception → belief → memory →
   decision → learning. Other loops become adapters or are frozen.
2. **External yardstick first.** No capability claim without a public benchmark and a
   non-SPEACE baseline at equal model and budget.
3. **Ablation or removal.** A mechanism that changes no outcome when ablated is removed from
   the decision path within one milestone (kept only as telemetry).
4. **Author ≠ examiner.** Specs/gates are written and frozen (hash in `prereg_lock.py`) before
   code; results are reviewed by a separate session or person.
5. **Kill criteria.** Each phase has a stop/pivot rule; a failed gate is published, not tuned.
6. **Vocabulary.** "AGI", "proto-AGI", "brain", "consciousness" are not used as result labels
   (T208); reports state benchmark, baseline, delta, interval.

## 1. Phases, gates, kill criteria

| Phase | Goal | Exit gate (preregistered) | Kill / pivot |
|---|---|---|---|
| P0 Consolidate | green CI, published history, frozen scope, honest labels | CI green on 3.12 Linux+Windows; T257–T266 published; frozen-module list merged | — |
| P1 One external experiment (T267) | find out whether the core adds anything | four-arm result on ≥1 external suite, ≥5 seeds, real variance, preregistered failure criteria | see decision rule below |
| P2 Unified brain kernel | one loop, one memory, one learning signal — only for components that mattered in P1 | T261–T265 batteries and the T267 arm run through the `brain` API with identical numbers | if unification changes numbers, fix before P3 |
| P3 Vocabulary-free abstraction | fix T265 | trained ≤ 0.8× amnesic failures on new-vocabulary devices, decoy cost ≤ 2; sample efficiency ≥ baseline on the T267 suite | after 2 failed design iterations → verification-layer track only |
| P4 LLM proposes, kernel verifies | open ontology | T257 result without hand-declared `mutex_pairs`; on held-out families LLM+kernel > LLM+verifier at equal tokens | no gain at equal tokens → stop P4 |
| P5 Cross-session learning | cumulative skill | A→B→reboot→C: retention of A ≥ 95 %, C learned with ≥ 30 % fewer samples; triple ablation attributes the gain | no attributable gain → memory stays external, no weight work |
| P6 Weight plasticity (optional) | consolidate into weights | LoRA sleep-replay on 3B: gain on the P5 metric with ≤ 2 % forgetting | only if P5 shows transduction as the bottleneck |
| P7 Positioning and replication | honest external standing | independent rerun of T267 from the replication package; wider suites only then | — |

**Decision rule after P1.** (a) full core > verifier/retry → extract the core, continue to P2–P3.
(b) only core-without-memory > verifier/retry → the product is the verification layer; memory
returns to research status. (c) neither → publish the negative result and revise the hypothesis
before any further construction.

## 2. Task registry

### P0 — Consolidate
| ID | Task | Done when |
|---|---|---|
| T266-01 | Publish T257–T266; tag the pre-refactor state `v0.1-monolith`; CI matrix (ubuntu, windows; py3.12) | CI badge green |
| T266-02 | Move personal notes/transcripts from `docs/` to `docs/notes/`; remove stray `cellular_speace/C:cellular…server.log`; list in `.gitignore` | `git status` clean |
| T266-03 | Declare frozen modules (`quantum/`, `radio/`, `economy/`, `ptaa/`, IoNT, compliance, `cellular_speace/`): bug-fix only, no physical move before T267 | `docs/FROZEN_MODULES.md` |
| T266-04 | Diagnose `test_mcp_connection_agent::test_local_demo_cli…` | passes or documented skip |
| T266-05 | Rename result labels in T251/T259 reports per principle 6 (errata, not rewrite) | errata file merged |
| T266-06 | Persist Stage-1 `retracted_signatures`; `MemoryBudgetGuard` current-RSS on POSIX | tests added |

### P2 — Unified brain kernel (after T267)
| ID | Task | Done when |
|---|---|---|
| T266-10 | Spec `docs/T267_UNIFIED_BRAIN_KERNEL_SPEC.md`: interfaces `Percept`, `BeliefState`, `Memory`, `Policy`, `Learner`, tick contract, BCEL entries | reviewed spec, hash-locked |
| T266-11 | `q_speace/brain/kernel.py`: single async loop; adapters for sandbox twins and for `DualSpeedCognitiveLoop` | T261–T265 batteries via kernel, same numbers |
| T266-12 | One persistent store (schemas, episodes, epigenetic state, retractions) with schema version + migration | cold-boot tests on unified store |
| T266-13 | Replace hand constants in value computation by one learned cost model (failure cost, probe cost fitted from episodes) | "probe-everything" no longer beats it on failures at equal ticks (T264 A1) |
| T266-14 | Remove spike gate from the decision path or give it a measured role (bounded-compute anytime arbitration); MR estimator on real activity | ablation changes outcome, else removed |
| T266-15 | Decide the fate of the cellular 80-neuron circuit: required role with ablation, or frozen | decision record |

### P1 — One external experiment (before the kernel)
| ID | Task | Done when |
|---|---|---|
| T266-20 | Preregistration `docs/T267_EXTERNAL_BENCHMARK_PREREG_SPEC.md`: suite, perturbation protocol, four arms, token budget, seeds, metrics, failure criteria; hash-locked before code | approved by the maintainer, hash in `prereg_lock.py` |
| T266-21 | Harness `q_speace/evals/` with one adapter (TextWorld first; PlanBench second) and a shared LLM client with a single-instance semaphore | runs CPU-only with a stub model and on GPU with Qwen2.5-3B NF4 |
| T266-22 | Baselines A (schema-constrained) and B (verifier/retry) reproduced and sanity-checked | baseline table committed before the core arms run |
| T266-23 | Core arms C (no memory) and D (full), run once on the held-out split | result artifact + report, including negative outcomes |
| T266-24 | Independent review of T266-23 by a separate session/person | review appended to the report |

### P3 — Vocabulary-free abstraction
| ID | Task | Done when |
|---|---|---|
| T266-30 | Second-order schema: "block-role failure is predicted by some reading" → probe-first prior and fast induction on new tokens | T265 rotor gate |
| T266-31 | Remove the silent-schema veto across devices; per-device (not per-action-name) scope; reinstatement | T265 decoy gate; T264 red-team item closed |
| T266-32 | Bayesian evidence (Beta posterior per schema, sequential test) replacing fixed counts | T264 A4 gates at flip 0/0.1/0.2 |
| T266-33 | Constructed observables: conjunction, threshold on numeric readings, short temporal patterns; MDL preference | T264 A5 ≥ 8/10; numeric-probe variant |
| T266-34 | Active experiment selection by expected information gain (replaces probe heuristics) | fewer probes at equal failures vs T264 |

### P4 — LLM proposes, kernel verifies
| ID | Task | Done when |
|---|---|---|
| T266-40 | LLM as hypothesis generator: proposes predicates, mutex pairs, schemas, probes from raw text observations; kernel tests and consolidates only verified ones | T257 result reproduced **without** hand-declared `mutex_pairs` |
| T266-41 | Semaphore-guarded single 3B instance, token budget per episode, cached proposals | RAM/VRAM envelope respected |
| T266-42 | Evaluation on TextWorld/PlanBench held-out families vs P2 baselines at equal tokens | P4 gate |

### P5–P7
| ID | Task | Done when |
|---|---|---|
| T266-50 | A→B→reboot→C protocol with triple ablation (shuffled memory, frozen epigenome, no schemas) on external suites | P5 gate |
| T266-51 | Skill library growth without interference (regression suite after every consolidation) | retention ≥ 95 % |
| T266-60 | (optional) LoRA sleep-replay on consolidated episodes, EWC/replay guard, 6 GB budget | P6 gate |
| T266-70 | Replication package for T267 (seeds, container, prereg hashes); wider suites only after an external rerun | external rerun reproduces the table |

## 3. Honest expectation

This plan can produce a verifiable agent kernel that makes a small LLM measurably more
reliable and more sample-efficient across sessions, and a clean answer on whether the
bio-inspired mechanisms contribute. It does not make reaching AGI on this hardware likely;
P3 and P4 are research questions with real chances of a negative result, which the plan is
built to detect early.

## 4. Status log

| Date | Task | State |
|---|---|---|
| 2026-11-28 | T266-01 | local: branch `t261-t266-stage-prototypes`, tag `v0.1-monolith`, CI matrix; **publication pending** (GitHub account not linked to the agent session) |
| 2026-11-28 | T266-02 | done locally (notes moved to `docs/notes/`, local transcripts ignored) |
| 2026-11-28 | T266-03 | done (`docs/FROZEN_MODULES.md`) |
| 2026-11-28 | T266-04 | done: local demo exceeded the default token bucket (`burst=10`) since the 12-tool walkthrough; timing-dependent 429 |
| 2026-11-28 | T266-05 | done (`docs/T251_T259_TERMINOLOGY_ERRATA.md`) |
| 2026-11-28 | T266-06 | done (retractions persisted; current RSS on Linux) |
| 2026-11-28 | T266-20 | draft written, **awaiting maintainer approval** before hash-lock |
