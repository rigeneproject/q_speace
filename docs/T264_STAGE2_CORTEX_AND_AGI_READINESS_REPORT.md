# T264 — Stage-2 Cortex Prototype & AGI-Readiness Battery (spec + report)

**Status:** agentic, experimental · **Date:** 2026-11-28 · **Depends on:** T261–T263, T208, T217
**Code:** `q_speace/bridge/stage2_cortex.py`, `q_speace/spiking/criticality_mr.py`,
`q_speace/vertical_slice/t264_agi_readiness_battery.py` · **Tests:** `tests/test_t264_stage2_cortex.py`
**Run:** `python -m q_speace.vertical_slice.t264_agi_readiness_battery` (≈25 s, CPU-only, ≈57 MiB RSS)

## 1. What was built (one change per T263 bottleneck)

| T263 gap | T264 mechanism |
|---|---|
| E2 workspace not causal | Candidates carry computed values (expected utility of an actuation from a learned failure probability; value of information of a probe); spike-gated ignition against an idle-cost reference |
| E1 σ gate uninformative | Multistep-regression (MR) branching estimator, nonlinear fit `r_k = b·m^k`, significance threshold on lag 1 |
| E3b/E4 no abstraction | Schemas over **causal roles** of the action graph (`block`: cheapest of interchangeable actions fails; `clobber`: goal action destroys its restorable precondition); subset matching; per-action **scope learning** for transfer |
| E5/E6 noise & order | Laplace-smoothed balanced accuracy, majority of repeated readings, blame assignment, two-sided validation ("fails iff F"), hypothesis competition, retraction |
| E7 no new observables | Constructed conjunctive observables (2-literal features) when no single reading discriminates |

## 2. Preregistered gates and results (final run)

| Axis | Gate | Result | Verdict |
|---|---|---|---|
| A1 workspace | beats shuffled & constant values; frozen k more idle | beats shuffled (45 vs 60 failures); loses to probe-everything constant (45 vs 39 failures, −35 % ticks); frozen k identical | **FAIL** |
| A2 informative σ | MR within ±0.12 for m=0.5/0.9, >1.1 for 1.3, <0.2 noise | 0.385 / 0.906 / 1.235 / 0.0 (ratio estimator: 1.18 / 1.04 / 1.42 / 1.24) | PASS (post-hoc, see §4) |
| A3 abstraction | new-device memory < amnesic; no-abstraction ablation no gain | pump 4 vs 15, iceline 5 vs 15, ablation 15/15; bus_fan 0 vs 15 but ablation also 0 | **FAIL** (bus_fan sub-gate misspecified) |
| A4 robustness | both correct schemas ≥8/10 (flip 0, 0.1), ≥6/10 (0.2), 0 spurious | 5/10, 1/10, 0/10; spurious 1, 1, 2 | **FAIL** |
| A5 new observables | conjunction learned ≥8/10; ablation 0 | 5/10; ablation 0 | **FAIL** |
| A6 cold boot | separate process, memory < amnesic, Task A kept | 2 vs 8 failures; Task A kept | PASS |
| A7 negative controls | 0 consolidated on unobservable / shuffled probes | 0 / 1 | **FAIL** |
| A8 resources | < 250 MiB, no GPU | 57 MiB, no GPU | PASS |

## 3. Independent red-team findings (accepted)

- **Workspace = heuristic.** Replacing spike-gated arbitration with `argmax(value) if value > −0.15`
  leaves every A1 arm identical; idle is 0 everywhere, so the threshold never binds, and the
  T248 controller output was never used to set k (now marked in code). The workspace is a
  hand-weighted expected-value planner with a learned failure probability.
- **Transfer is real but shallow.** Schemas carry all of the A3 benefit (prior-only ablation: no
  gain), and it survives balanced 50 % latent tests (5 vs 18). But the cue is a shared token
  with the same meaning on every device: this is role-indexed lookup, not transfer to a new cue.
- **A6 overstates novelty.** Of the 2 vs 8 gap, novel devices account for 2 vs 4.
- **Fixed after review:** order-dependent veto in `_p_fail` (one spurious schema could disable a
  correct one); scope exclusion now weighs failures against verified transfers and is reversible.
- **Open:** exclusion is per action name, not per device; credit is episode-level.

## 4. Deviations from preregistration (disclosed)

1. MR fit changed (log-linear → nonlinear, lag significance) after the first run failed A2.
2. Idle-cost reference, stall fix ("schemas are advisory"), homeostatic band, two-sided validation
   and hypothesis competition were added after the first run exposed stalls and spurious schemas.
3. An induction threshold of 0.75 was tried and reverted (more spurious schemas).
4. The bus_fan ablation sub-gate was wrong by design (subset matching is on in both arms); left
   failing rather than rewritten.

## 5. Assessment

Gates passed: 3/8 (A2 post-hoc, A6, A8). The system is an **experimental neuro-symbolic sandbox
agent** with: hypothesis induction from failures, validation, retraction, role-indexed transfer
over a shared sensor vocabulary, and retention across process restarts. Against any reasonable
operational definition of AGI (efficient acquisition of skills in open, unseen domains, e.g.
ARC-AGI-style tasks, perception from raw data, language, long-horizon autonomy), it is not
close; none of those capabilities is exercised by this battery.

## 6. Next experiment (red-team recommendation, adopted as T265)

Transfer under a **new vocabulary**: test devices with a renamed probe/token whose role must be
inferred (e.g. `probe_torque`/`torque_inverted`), mixed decoy and genuine devices sharing action
names, compared against amnesic and "always try the alternative" baselines. Also: replace the
hand constants in value computation with a single learned cost model, and require that removing
the spike gate changes behaviour before claiming a workspace effect.
