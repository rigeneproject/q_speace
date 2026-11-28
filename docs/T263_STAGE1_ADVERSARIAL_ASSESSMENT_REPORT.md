# T263 — Stage-1 Adversarial Assessment: Generalization, Attribution & Two Kernel Fixes

**Status:** agentic (evaluation + 2 targeted fixes) · **Date:** 2026-11-28
**Scope:** the T261–T262 Stage-1 CPU prototype (`q_speace/bridge/stage1_workspace.py`,
`q_speace/bridge/latent_discovery.py`). CPU-only, single process, sandboxed twins (T217).
**Battery:** `q_speace/vertical_slice/t263_stage1_adversarial_battery.py`
(`python -m q_speace.vertical_slice.t263_stage1_adversarial_battery`).
**Tests:** `tests/test_t263_stage1_adversarial.py`.

## 1. Why this battery

The T261–T262 gates pass (37/37 tests incl. BCEL catalog). They do not measure: whether
the sigma gate can fail, whether spikes/criticality change any decision, whether learned
rules survive repeated use after reboot, or whether anything transfers beyond the exact
surface on which it was learned. T263 measures these, and nothing else.

## 2. Kernel fixes (behavioural, covered by tests)

| ID | Defect | Fix | Evidence |
|---|---|---|---|
| T263-1 | `load_consolidated_into` restored rules but not `EpigeneticEngine` counters. First post-boot validation recreated a fresh state (1 promotion) and **de-consolidated the rule after one use**. T262 did not see it: one held-out unit per mechanism. | Restore `promotion_count`, `suppression_count`, `consolidated` into the engine on load. | 3 held-out inverted bus units after cold boot: failed actuations `0,1,1` → `0,0,0`; ticks 17 → 9. |
| T263-2 | A spurious rule on the distractor probe (`probe_ambient_hum`, chance correlation) could be minted first; `_try_induce_rule` then returned it forever, so the true rule could never be induced (3/10 random streams). | Retract a non-consolidated candidate with ≥2 suppressions and stability < 0.70; bar its signature from re-minting. | Spurious lock-ins 3/10 → 0/10; streams with both rules consolidated 4/10 → 5/10. |

Original T261–T262 tests remain green after both fixes.

### Independent review notes (accepted)
- T263-1 is wider than first reported: cryo units fail the same way ([0,1,1] before fix).
- T263-2 was extended to consolidated rules after review; over 200 random streams, spurious
  distractor rules at stream end fell 73 → 14 (consolidated 21 → 11), with 0 correct rules
  retracted. Residual: a spurious rule consolidated early with stability ≈ 0.5 can persist.
  `retracted_signatures` is not persisted across cold boot.
- E3b comparison arm was rebuilt without the extra fact (bug, fixed); rerun gives identical
  numbers. E5/E6 now count only *correct* consolidated rules.
- E3b/E4 negative results follow directly from exact-surface lookup; they document the design,
  not a general impossibility. σ in-band growth case is 1.12×/tick; 1.3×/tick is rejected.

## 3. Findings (post-fix)

| Exp | Question | Result | Reading |
|---|---|---|---|
| E1 | Does `0.85 ≤ σ ≤ 1.15` discriminate dynamics? | constant 1.000, decay-to-silence 0.963, explosive ×1.12/tick 1.107, Poisson noise 1.142 — **all in band**; uniform 0–12 noise 1.472 out | Gate 1 is not evidence of criticality. |
| E2 | Do spikes / closed-loop k affect decisions? | k frozen (kp=0) and spikes zeroed both give **identical** action/probe sequences, ticks (57) and failures (2) | Decisions come from hand-set salience constants + refractory damping; the spiking/criticality layer is telemetry. |
| E3a | Memory on a known surface after reboot | 9 ticks / 0 failures vs amnesic 21 / 3 | Real, attributable consolidation benefit. |
| E3b | Same unit + one irrelevant surface fact | 21 / 3 = amnesic | Recall keyed on exact surface set; no abstraction. |
| E4 | New device class, same hidden mechanism, same probe | 21 / 3 = amnesic | Zero transfer across devices. |
| E5 | 20 % probe-token flips, curated curriculum | 0/5 runs consolidate both rules | Validation too short for noisy evidence. |
| E6 | Curated curriculum randomly permuted | 0/10 consolidate both | Original result depends on presentation order. |
| E6b/c | 31-episode random stream (clean / 10 % noise) | both rules in 5/10 / 2/10 seeds | Learner works without curation, but needs more evidence. |
| E7 | Latent with no informative probe | latent never learned; 3 failures on held-out | Closed sensor vocabulary: cannot invent a new observation. |

Peak RSS across the battery: ≈ 58–60 MiB (budget 250 MiB). No GPU.

## 4. Assessment

The prototype does show a complete, small loop: action failure → non-destructive probing →
contrastive hypothesis → empirical validation → consolidation → retention across a real
process restart, with fail-closed RAM and genome guards. After T263-1/2 it also withdraws
falsified hypotheses.

It does not yet show: (a) emergent decision-making (E2), (b) a criticality signal that
carries information (E1), (c) abstraction beyond exact surfaces (E3b, E4), (d) robustness to
noise and order (E5, E6), (e) invention of new observables or concepts (E7). Classification:
**experimental neuro-symbolic cognitive architecture, Stage-1 sandbox, narrow-domain
adaptive learning**; it is not an AGI and not a proto-AGI on any external benchmark.

## 5. Next steps (by measured bottleneck)

1. **Abstraction (E3b/E4):** match rules by causal role (`blocked_action` precondition set +
   probe signature) instead of exact surface equality; preregister the pump transfer as gate.
2. **Make the workspace causal (E2):** derive salience from measured quantities (prediction
   error, expected information gain, plan cost), then require that ablating spikes or k
   changes outcomes.
3. **Replace σ gate (E1):** use avalanche-size distribution or a perturbation-response test.
4. **Evidence accumulation (E5/E6):** Bayesian rule confidence instead of fixed counts.
5. **New observables (E7):** allow composite probes (sequences/thresholds) as hypotheses.
