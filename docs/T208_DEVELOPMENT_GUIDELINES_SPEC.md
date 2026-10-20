# T208 — Development Guidelines: Evidence-First Q-SPEACE

**Status:** agentic (production guidance)  
**Date:** 2026-09-08  
**Scope:** development priorities, architecture boundaries, validation and release
criteria for Q-SPEACE.  
**Non-goal:** introduce a new cognitive, quantum, economic, or radio feature.

---

## 1. Decision

Q-SPEACE is developed as an **evidence-first research engineering platform**.
Its near-term objective is not to add architectural layers or to make claims
about intelligence, consciousness, or quantum advantage. It is to deliver one
small, reproducible, useful vertical slice and to measure its trade-offs
against a simple baseline.

The initial reference vertical slice is:

```
text request
    -> EventRouter
    -> SpikingBrainCortex / instruction sidecar
    -> confidence + ILF + Sevo + energy gate
    -> answer, refusal, or fallback
    -> structured telemetry and offline evaluation
```

This choice reuses working components already present in the repository while
keeping the quantum, radio, economy, AACM, and self-improvement layers
optional. It does **not** assert that the language sidecar is a brain, that
spikes are biological spikes, or that the gate is consciousness or agency.

## 2. Product hypothesis

The first claim that Q-SPEACE should attempt to falsify is deliberately
narrow:

> For a bounded instruction-dialogue workload, a policy that routes and gates
> requests using explicitly measured confidence, latency, and energy can offer
> a documented quality/cost/safety trade-off relative to an always-answer
> baseline.

This is a systems claim, not a claim of general intelligence. It is accepted
only when the result is reproducible from versioned inputs, code, configuration,
and measurements.

### 2.1 Baselines are mandatory

Every experiment or feature that influences a routing or execution decision
must name at least one baseline. The initial baseline is:

```text
same model + same prompt set + same generation limits + no Q-SPEACE gate
```

Candidate policies can then be compared with the baseline:

| Policy | Decision rule | Expected use |
|---|---|---|
| `always_answer` | invoke sidecar for every valid text request | baseline |
| `energy_gate` | refuse/fallback when predicted budget is exceeded | cost control |
| `confidence_gate` | refuse/fallback below calibrated threshold | reliability control |
| `combined_gate` | apply both gates, with an auditable reason | target policy |

No policy is described as better merely because it exposes more internal
metrics or resembles a biological metaphor.

## 3. Non-negotiable invariants

The existing repository invariants remain hard requirements.

1. **No consciousness claim.** Q-SPEACE is a computational system. Terms such
   as *thought*, *brain*, *metacognition*, and *organism* are interface labels
   or analogies and must not be presented as evidence of subjective experience.
2. **No communication through entanglement.** Entanglement can only be modeled
   as a computational correlation or binding resource. Any inter-component
   communication must use an explicit classical channel.
3. **No physical claim from a proxy.** `coherence_phi`, Sevo, spike counts,
   fidelity proxies, and energy estimates are software metrics unless a
   protocol explicitly validates them against physical observations.
4. **No autonomous state mutation from generated text.** Model output is
   untrusted input. Any state-changing action requires a separate, explicit,
   deterministic policy check and an audit record.
5. **No real quantum backend without gates.** A real backend requires
   `QuantumGeneSet.noise_model`, an energy budget, a Sevo gate, a shot budget,
   and a reproducible execution record.
6. **No actuation from simulation defaults.** Radio, economic, and external
   control modules remain simulation-only unless their hardware, regulatory,
   authorization, and human-oversight requirements are separately specified
   and tested.

The BCEL catalog is the source of truth for whether a bio/quantum metaphor is
retained as a mathematical rule or removed as accidental. A new concept must
be classified before it is wired into an execution path.

## 4. Architecture boundaries

### 4.1 Core, experimental, and deferred layers

| Layer | Current role | Rule for development |
|---|---|---|
| Routing, sidecar client, cortex, gates, telemetry | **core vertical slice** | stabilize APIs; test end-to-end |
| Cost model and evaluation | **measurement infrastructure** | calibrate against observed data; version parameters |
| Pseudo-spiking primitives | **optional computation feature** | retain only if an experiment shows a benefit |
| Numpy quantum simulator | **research module** | use for controlled simulations; do not imply hardware advantage |
| Real quantum backends | **deferred experimental module** | enable only after gate and noise-model requirements are satisfied |
| Radio/RF, economy, AACM, self-improvement | **isolated experiments** | no dependency from the initial vertical slice; each needs its own measurable hypothesis |

### 4.2 Dependency direction

The production path must be acyclic and should depend only on stable contracts:

```
CLI/Web API -> EventRouter -> Cortex -> Client Protocol -> Sidecar
                               |             |
                               v             v
                         Gate Policy     Telemetry Record
                               \             /
                                -> Offline Evaluator
```

Experimental modules may consume telemetry through a documented adapter, but
they must not silently alter a core decision. In particular, no module may
change thresholds, route selection, model configuration, or persisted state as
a side effect of importing it.

### 4.3 Data contracts

Use typed, serializable records at every boundary. Minimum fields for one
request are:

```python
RequestRecord(
    run_id: str,
    request_id: str,
    model_id: str,
    model_revision: str | None,
    policy_id: str,
    prompt_hash: str,
    started_at: str,
)

DecisionRecord(
    route: str,
    gate_open: bool,
    decision_reason: str,
    predicted_energy_j: float | None,
    confidence: float | None,
    thresholds: dict[str, float],
)

OutcomeRecord(
    status: str,  # answered | refused | fallback | failed
    latency_s: float,
    tokens_in: int | None,
    tokens_out: int | None,
    measured_energy_j: float | None,
    response_hash: str | None,
)
```

Do not put raw sensitive prompts or generated text into default telemetry.
Store hashes and aggregate metrics by default; make raw capture an explicit,
documented opt-in with retention rules.

## 5. Evidence and measurement protocol

### 5.1 Separate the quantities

The following are different measurements and must never be conflated:

| Quantity | Example metric | Valid conclusion |
|---|---|---|
| Response quality | task accuracy, rubric score, human preference | quality on this benchmark |
| Confidence calibration | Brier score, ECE, reliability plot | confidence quality on labelled data |
| Efficiency | joules/request, joules/token, latency, VRAM | resource trade-off on this hardware |
| Gate behavior | accept/refuse/fallback rate, false-refusal rate | policy behavior on this workload |
| Quantum behavior | circuit outcome against simulator/backend | behavior of that circuit/backend only |

For example, a low Brier score on a dataset containing only correct answers is
not evidence of calibrated confidence. A calibration set must contain both
correct and incorrect outcomes, difficult and adversarial prompts, and an
outcome labelling protocol independent from the model's own confidence.

### 5.2 Experiment manifest

Every reported experiment must commit a JSON or YAML manifest containing:

- Git commit and dirty-tree status;
- operating system, Python, package, GPU-driver, CUDA, and model versions;
- model revision and quantization;
- prompt-set identifier, licence, sample size, and label source;
- policy and threshold configuration;
- random seeds and generation parameters;
- energy sampling method, idle-baseline method, and sampling frequency;
- summary metrics plus raw, privacy-safe result rows.

The measurement script must generate the manifest rather than rely on a prose
description written after the run.

### 5.3 Acceptance criteria for the first vertical slice

The exact numeric thresholds are set in the experiment spec before collecting
results. A release candidate needs all of the following:

1. Identical prompt set and model settings for baseline and candidate.
2. A labelled held-out evaluation set that includes negative and abstention
   cases; no all-correct or all-incorrect calibration set.
3. Bootstrap confidence intervals or an equivalent uncertainty estimate for
   quality, energy, latency, and calibration metrics.
4. No unacceptable degradation against baseline according to the predeclared
   quality threshold.
5. A measurable benefit in at least one target dimension (for example,
   reduced measured energy or fewer unsafe answers), with the trade-off stated
   explicitly.
6. A decision trace for every refusal or fallback.
7. Independent rerun from the manifest on the same target hardware.

If a criterion is missed, the result is recorded as inconclusive. It is not
retroactively reframed as validation.

## 6. Calibration and cost-model policy

`QuantumCostModel` contains both a functional shape and empirical scale
parameters. Treat them differently.

- The form of the model is a hypothesis and must be tested with residual
  analysis, not merely a correlation coefficient.
- A global calibration multiplier is a versioned parameter with a data source,
  interval of validity, units, hardware/model scope, and effective date.
- Tests that assert energy deltas must include all active multipliers, or set
  the multiplier explicitly to the desired controlled value.
- A calibration based on a Qwen NF4 workload must not be generalized to
  SpikingBrain, a QPU, or RF hardware without a new measurement campaign.
- Gating should use a conservative upper confidence bound whenever the cost
  estimate has known uncertainty; a point estimate alone is insufficient for a
  safety-relevant decision.

The current mismatch between the global recalibration factor and a spike-energy
unit test is a concrete example of the failure this policy prevents: whenever
a physical calibration changes, update the parameter metadata, contract tests,
documentation, and affected gates together in one ticket.

## 7. Delivery workflow

### 7.1 Ticket template

Every production ticket must include:

1. a problem statement and a falsifiable hypothesis;
2. a BCEL entry or an explicit statement that BCEL is unaffected;
3. an API/data-contract change, if any;
4. baseline, dataset, and metrics;
5. safety and failure-mode analysis;
6. tests and acceptance criteria;
7. a rollback or feature-flag plan;
8. documentation and experiment-manifest outputs.

The implementation order is: specification -> BCEL classification -> tests ->
implementation -> quality gates -> measured report. A passing unit test is not
a substitute for a measured report when the ticket makes an empirical claim.

### 7.2 Definition of done

A production change is complete only when:

- `pytest` passes, including regression tests;
- `python -m py_compile` passes for touched Python files;
- `ruff check` and `black --check` pass for the touched scope;
- `mypy` passes for the touched scope, or a narrowly documented pre-existing
  exception is tracked separately;
- public APIs have typed tests for success, refusal, timeout, and malformed
  dependency responses;
- a changed gate has both allow and block tests;
- the relevant spec, BCEL catalog, and changelog/status document agree.

Do not lower coverage thresholds or delete tests to pass a gate. Repair a
failing pre-existing test before building new behavior on the affected contract
unless the ticket explicitly isolates it and a maintainer approves the risk.

### 7.3 Reproducibility and repository hygiene

- Commit one coherent ticket at a time; avoid mixing documentation, generated
  measurements, model assets, and unrelated refactors in the same change.
- Keep generated, large, or potentially sensitive runtime data out of source
  control by default. Commit small, privacy-safe fixtures and manifests.
- Treat a dirty tree as part of the experiment state and record it.
- Pin or record external model revisions; model names alone are not sufficient.
- Keep experimental claims labelled *experimental* until independently
  reproduced.

## 8. Work-breakdown structure and expansion gates

This is the authoritative work ordering for the evidence-first path. Task IDs
with the `T209` prefix are **proposed** by this specification; they do not
replace or reinterpret completed historical tickets. Existing tickets are
referenced only where their deliverable must be reconciled with the new path.

### Group A — Foundation and repository recovery

**Objective:** make the current repository trustworthy as an experimental
instrument before adding behavior.  
**Depends on:** none.  
**Exit gate A:** all Group A tasks complete and the scoped quality gates are
green.

#### A.1 — Contract and calibration alignment

- **A.1.1 — Reconcile T207-bis cost contracts.** Update the spike-energy
  expectation so that it intentionally includes the active
  `RICALIBRATION_FACTOR`, or controls that factor explicitly in the test.
  Record the exact model/hardware/data scope in the calibration metadata.
- **A.1.2 — Audit affected cost gates.** Verify that energy budgets, Sevo
  behavior, CLI output, and reports use the same calibrated unit convention.
- **A.1.3 — Add calibration-regression fixtures.** Test factor `1.0`, the
  active calibrated factor, invalid/negative spike counts, and the numerical
  monotonicity of every energy term.

#### A.2 — Quality-gate recovery

- **A.2.1 — Restore the test suite.** Resolve the known failing test and any
  subsequently exposed regression; do not mark a failure as harmless without a
  tracking ticket and an isolated scope.
- **A.2.2 — Restore style checks.** Apply Black and Ruff fixes in focused,
  reviewable commits, then retain only deliberately justified lint exceptions.
- **A.2.3 — Reduce static-type errors.** Start from the vertical-slice modules
  (`routing`, `spiking_brain`, `metabolism`, `orchestrator`, CLI) and eliminate
  untyped or unsafe boundary values before touching optional modules.
- **A.2.4 — Compile smoke scope.** Add the touched modules to a repeatable
  `py_compile` command in CI or a documented local check.

#### A.3 — Status and source-control hygiene

- **A.3.1 — Reconcile status documents.** Align README, T205/T206/T207,
  T-SPB reports, and code with what has been measured versus what is only
  implemented or pending.
- **A.3.2 — Split the dirty tree.** Separate unrelated work into coherent
  tickets/commits; keep temporary scripts, raw chat histories, model assets,
  and generated data out of product commits unless explicitly required.
- **A.3.3 — Terminology audit.** Mark speculative economy/philosophy material
  as such and remove wording that could contradict the no-consciousness and
  no-communication invariants.

### Group B — T209: reference vertical-slice contracts

**Objective:** turn the current instruction-sidecar path into a small,
observable system whose output can be evaluated.  
**Depends on:** Group A.  
**Exit gate B:** a single command can execute a policy and emit a
privacy-safe, schema-valid request/decision/outcome record plus manifest.

#### B.1 — Input, outcome, and dataset contract

- **T209.1 — Benchmark specification.** Define task families, prompt-set
  licensing, held-out partition, expected-answer or rubric format, abstention
  cases, adversarial cases, and independent labelling procedure.
- **T209.2 — Dataset implementation.** Add a small deterministic test fixture
  and a versioned evaluation dataset reference. Ensure it contains both correct
  and incorrect outcomes so calibration is identifiable.
- **T209.3 — Privacy policy for requests.** Decide which fields are hashed,
  redacted, retained, or opt-in raw capture; add tests that default telemetry
  cannot contain prompt or response text.

#### B.2 — Runtime contracts and telemetry

- **T209.4 — Typed telemetry schema.** Implement `RequestRecord`,
  `DecisionRecord`, `OutcomeRecord`, and an experiment manifest with JSON
  serialization and schema/round-trip tests.
- **T209.5 — Policy configuration contract.** Define stable configuration for
  `always_answer`, `confidence_gate`, `energy_gate`, and `combined_gate`,
  including thresholds, model revision, fallback behavior, and a policy ID.
- **T209.6 — Decision-trace integration.** Wire the router/cortex/client path
  to emit an allow, refusal, fallback, timeout, and malformed-sidecar trace.
  Generated text must remain incapable of directly mutating Q-SPEACE state.

#### B.3 — Operable entry point

- **T209.7 — Reproducible evaluation CLI.** Provide a command that accepts an
  explicit policy and manifest location, records seed and generation settings,
  and returns a non-zero exit code for invalid configuration or failed runs.
- **T209.8 — Feature flags and rollback.** Keep the combined gate opt-in until
  Group E approval; define the no-sidecar and no-telemetry fallback behavior.

### Group C — T210: baseline, calibration, and policy evaluation

**Objective:** collect evidence for the narrow product hypothesis rather than
for the project’s broad architecture.  
**Depends on:** Group B and a working target sidecar/hardware configuration.  
**Exit gate C:** a report can compare all policies under identical conditions
and declares the result validated, inconclusive, or rejected.

#### C.1 — Baseline characterization

- **T210.1 — Always-answer run.** Run the versioned dataset with the chosen
  model, fixed generation configuration, idle-power procedure, and manifest.
- **T210.2 — Measurement integrity checks.** Verify token counts, latency
  clock, energy sampling interval, idle-baseline subtraction, missing samples,
  and hardware metadata before interpreting results.
- **T210.3 — Baseline report.** Report quality, abstention behavior, latency,
  joules/request, joules/token, memory, and uncertainty intervals.

#### C.2 — Gate-policy experiments

- **T210.4 — Confidence-gate run.** Predeclare threshold selection on a
  development partition, then evaluate once on the held-out partition.
- **T210.5 — Energy-gate run.** Predeclare budget selection and measure both
  cost reduction and false refusals against the baseline.
- **T210.6 — Combined-gate run.** Evaluate ordering and reason precedence when
  both gates block; no opaque single “confidence” field may hide the cause.
- **T210.7 — Failure-path run.** Exercise sidecar timeout, malformed payload,
  unavailable endpoint, budget exhaustion, and zero/unknown confidence.

#### C.3 — Calibration and statistical analysis

- **T210.8 — Calibration evaluation.** Compute Brier score, ECE, reliability
  diagram, coverage by confidence bin, and confidence intervals on data with
  positive and negative outcomes. Reject degenerate labels as calibration data.
- **T210.9 — Comparative analysis.** Use the same prompt IDs for every policy;
  publish paired deltas and bootstrap intervals rather than only averages.
- **T210.10 — Decision report.** Publish inputs, limitations, raw privacy-safe
  rows, manifest, plots, and a decision to keep, revise, or retire each gate.

### Group D — Optional subsystem proof tracks

**Objective:** test one experimental layer at a time after the reference slice
has a trustworthy baseline.  
**Depends on:** Group C. A proof track cannot modify default behavior until
Group E.  
**Exit gate D (per track):** a predeclared experiment finds a reproducible
benefit over the simplest comparator, or records a negative/inconclusive result.

#### D.1 — Pseudo-spiking track

- **T211.1 — Comparator and ablation.** Compare plain tensor path, dynamic
  spikes, and spike/plasticity variants on the same workload.
- **T211.2 — Cost/quality study.** Measure actual latency and energy alongside
  sparsity; do not infer a saving from spike count alone.
- **T211.3 — Retention decision.** Keep a spiking feature only if its measured
  trade-off meets the predeclared limit on quality loss.

#### D.2 — Quantum simulation/backend track

- **T212.1 — Task-specific hypothesis.** State the circuit, classical
  comparator, input scale, expected observable, and no-communication argument.
- **T212.2 — Noisy-simulator validation.** Evaluate against declared noise,
  shot, energy, and Sevo budgets; preserve all execution metadata.
- **T212.3 — Real-backend readiness.** Before any hardware run, require a
  configured `noise_model`, spending caps, explicit authorization, and a
  reproducible replay plan.

#### D.3 — Resilience/AACM track

- **T213.1 — Fault model.** Define faults, attacker capabilities, recovery
  objective, and classical comparator without strategic or real-world claims.
- **T213.2 — Controlled resilience trial.** Measure recovery rate, time,
  false redirects, and preservation of the resilience constraint under the
  simulated fault model.

#### D.4 — Radio/RF track

- **T214.1 — Simulation-only benchmark.** Use the digital twin and compliance
  filter to compare a control policy under documented channel conditions.
- **T214.2 — Actuation readiness review.** Hardware/RF work requires a
  separate spec covering authorization, spectrum compliance, human oversight,
  kill switch, and physical test boundaries.

#### D.5 — Economy/governance track

- **T215.1 — Formal mechanism scope.** Express one allocation or admission
  rule as typed inputs, deterministic outputs, invariants, and counterexamples.
- **T215.2 — Simulation evaluation.** Test distributional outcomes, failure
  modes, appeals/override, and explicit legal-social assumptions. This is not a
  claim about a future system’s values or preferences.

### Group E — Replication, integration, and release

**Objective:** prevent a promising one-off experiment from becoming a default
architectural dependency.  
**Depends on:** Group C and, for an optional layer, its corresponding Group D
exit gate.  
**Exit gate E:** integration is reversible, documented, and reproducible.

#### E.1 — Replication

- **T216.1 — Same-environment replay.** Re-run from the stored manifest with
  a fresh output directory and verify metric agreement within predeclared
  tolerance.
- **T216.2 — Independent variation.** Re-run on a different seed, held-out
  partition, or independently operated environment.
- **T216.3 — Drift check.** Compare model revision, drivers, dependencies, and
  calibration parameters; label any non-comparable run as such.

#### E.2 — Controlled integration

- **T216.4 — BCEL and safety review.** Recheck every new concept, decision
  path, fallback, and external interface against the invariants in §3.
- **T216.5 — Default-off integration.** Add the proven component behind a
  feature flag with an observable rollback path and integration tests.
- **T216.6 — Release review.** Update README, specifications, status tables,
  and user-facing claims; promote a component to default only with explicit
  maintainer approval and a green quality suite.

### Cross-group task dependencies

```text
Group A: repository recovery
    -> Group B: T209 contracts and CLI
        -> Group C: T210 evidence for the reference slice
            -> Group D: one optional proof track (T211–T215)
            -> Group E: T216 replication and default-off integration
```

Groups D.1–D.5 are parallel alternatives after Group C, not a mandatory
sequence. Select one track at a time according to the strongest falsifiable
hypothesis and available measurement capability; do not start all tracks merely
because their modules already exist.

## 9. Communication rules

External and internal documents must distinguish among:

- **implemented:** code and tests exist;
- **measured:** a versioned empirical run exists;
- **validated:** the result satisfies predeclared criteria and is reproduced;
- **proposed:** an idea or architecture without sufficient evidence.

Avoid phrases such as “planetary brain”, “consciousness”, “autonomous
organism”, or “quantum cognition” in technical claims. If such terms appear in
historical, philosophical, or exploratory material, label that material
explicitly as speculative and link back to the invariants in this document and
in the BCEL catalog.

## 10. First executable follow-up ticket

The recommended next ticket is **T209 — Energy-Aware Instruction Vertical
Slice**. Its deliverables are:

1. a fixed, versioned prompt set with independent labels and abstention cases;
2. a request/decision/outcome telemetry schema and manifest writer;
3. baseline and three gate-policy runs under identical settings;
4. an offline evaluator for quality, Brier/ECE, energy, latency, and refusal
   errors, including bootstrap intervals;
5. a report that decides whether the combined gate is retained;
6. a green `pytest`, `py_compile`, Ruff, Black, and mypy scope.

T209 must not add a new quantum, radio, economy, or self-improvement feature.
Its purpose is to establish the engineering loop that every later subsystem
must satisfy.
