# T265 — New-Vocabulary Transfer Experiment & Kernel Debug Report

**Status:** agentic (evaluation + targeted fixes) · **Date:** 2026-11-28 · **Depends on:** T263, T264, T208
**Code:** `q_speace/vertical_slice/t265_new_vocabulary_transfer.py` · **Tests:** `tests/test_t265_kernel_fixes.py`
**Artifact:** `artifacts/T265_new_vocabulary_transfer_20261128.json`

## 1. Experiment (preregistered reading in the module docstring)

Stage-2 agent trained on bus/cryo/relay, then tested on `rotor` (block role; hidden state
revealed only by a new probe token `probe_torque = torque_inverted`) and on `decoy` (old cue
token `phase_180deg` always present, primary action always works). 10 seeds, 24 rotor units,
10 decoy units, 50 % latent.

| Measure | Trained | Amnesic |
|---|---:|---:|
| Rotor failed actuations (total) | **77** | **49** |
| Rotor failed actuations, first 6 units | 31 | 31 |
| Seeds in which the torque schema was learned | 6/10 | 10/10 |
| Median units until the schema exists | 8 | 8 |
| Decoy failed actuations | **12** | **0** |

**Verdict: `H1_token_lookup`, with negative transfer.** Prior schemas do not help on a new
vocabulary and actively interfere: the old schema's "measured but silent" veto marks the
primary action as safe, so the agent stops probing and learns the new cue less often. On
decoys the old token costs 12 avoidable failures. Stage-2 "abstraction" is role-indexed
token lookup. This closes the T264 A3 question negatively.

## 2. Debug of the brain path (whole-repo pass)

Method: `ruff` + `mypy` on 186 source files, full test suite on Python 3.12 in an isolated
copy (≈880 tests), invariant probes on the criticality / epigenetic / spiking primitives.

| ID | Defect | Effect on the "brain" | Fix |
|---|---|---|---|
| T265-B1 | `CriticalityController.empirical_branching_ratio` used the mean of ratios, biased >1 for any stationary noisy activity (σ≈1.19 for Poisson(4)) | under stationary input `k` was driven to `k_min` (0.5): the regulator saturated instead of regulating | ratio of sums; stationary Poisson now gives σ=1.00 and `k` stays in range |
| T265-B2 | `EpigeneticEngine(min_promotions, stability_threshold)` arguments were ignored (hard-coded 3 / 0.7) | consolidation policy could not be configured or tested | engine thresholds honoured |
| T265-B3 | a consolidated mutation stayed consolidated forever, even with `should_rollback == True` | falsified knowledge could not be forgotten | de-consolidation when the rollback criterion is met |
| T265-B4 | `EpigeneticEngine.register` silently wiped accumulated evidence | re-registration reset learning | idempotent |
| T265-B5 | `tests/test_sia.py` hard-coded `C:\Users\rober\...` | 3 tests fail on any other machine/CI | repository-relative path |
| T265-B6 | `stage1_workspace.py` type error (`Counter[Literal]`) and 2 lint findings | quality gates red | fixed |

After the fixes: `ruff` clean except one style note (`myelination.py:220`, behaviour-neutral),
`mypy` clean, all suites green in the isolated copy except
`test_mcp_connection_agent::test_local_demo_cli…` (fails before and after; not diagnosed,
probably environment).

## 3. Structural limits found (not patchable; inputs to T266)

1. **No single brain.** There are four unconnected loops: `QuantumOrchestrator` (its spike
   activity is `rng.uniform` noise used only for cost accounting), `SPEACENeuralAgent`
   (cellular circuit, benchmark-only), `DualSpeedCognitiveLoop` (LLM grounding + planner),
   Stage-1/Stage-2 agents. None feeds another; no shared state, memory or learning signal.
2. **Spikes and criticality are never causal** for a decision in any loop (T263 E2, T264 A1).
3. **Knowledge is token-bound** (this report) and the ontology is hand-declared.
4. **Benchmarks are authored with the mechanisms**; none is external.
5. `MemoryBudgetGuard` on POSIX reads *peak* RSS (`ru_maxrss`), not current (conservative).
6. Stage-1 `retracted_signatures` are not persisted across cold boot.
