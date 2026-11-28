# T267 — External four-arm experiment: preregistration (DRAFT — not yet hash-locked)

**Status:** draft awaiting maintainer approval (T266-20). No harness code may be written
against the held-out split before this file is approved and its hash recorded.
**Date:** 2026-11-28 · **Depends on:** T208, T265, T266 rev. 2

## 1. Question

At equal language model and equal token budget, does the q_speace core make an agent
(i) more reliable within an episode and (ii) more sample-efficient across sessions when
rules or vocabulary change, compared with standard verification baselines?

## 2. Environment

- **Suite:** TextWorld (generated games; text-only, partially observable, sequential).
  PlanBench is the second suite, run only after this one is reported.
- **Families:** 6 game families by generator seed and skill set (navigation, containers,
  locked doors, cooking-style recipes, ...). 2 calibration families, 4 held-out.
- **Sessions:** each run is 3 sessions in separate OS processes (A → B → C), 8 games each.
  Between A and B one rule changes (a required step is added or an action stops working);
  between B and C object and verb names are remapped by a fixed random bijection
  (new vocabulary, same structure). Perturbations are applied by a wrapper, not by the agent.
- **Hardware:** RTX 3060 6 GB; one model instance (Qwen2.5-3B-Instruct NF4) behind a semaphore.

## 3. Arms (same model, same prompts where applicable, same per-game token cap)

| Arm | Description |
|---|---|
| A | LLM with schema-constrained action output |
| B | A + standard verifier/retry (admissible-action check, up to k retries) |
| C | q_speace core without cross-session memory (grounding, belief revision, planner) |
| D | C + cross-session memory and consolidation |

Token cap per game: fixed from arm B's median on calibration families, applied to all arms.
An arm that exhausts the cap fails that game.

## 4. Metrics

Primary: games solved within the cap (per session). Secondary: invalid actions, tokens per
solved game, wall-clock, session-C minus session-A success (cross-session gain).
Statistics: 5 seeds × 4 held-out families × 3 sessions × 8 games; paired bootstrap (2,000
resamples) over games; report means with 95 % intervals. Zero-width intervals must be
reported as "deterministic".

## 5. Preregistered outcomes

| Outcome | Condition (held-out, primary metric, interval excludes 0) |
|---|---|
| H-core | D > B |
| H-verify-only | C > B and not D > C |
| H-memory | D > C on session C |
| H-null | neither C nor D > B |
| Harm | D < C on session C (negative transfer, as in T265) |

All outcomes are reported. Thresholds, prompts and k are chosen on calibration families only
and frozen; the held-out split is run once.

## 6. Threats to validity (to be addressed in the report)

Small model ceiling (all arms near zero → uninformative; then raise the cap once on
calibration and document it); generator-specific structure; prompt sensitivity; author of the
harness is also author of the core (mitigation: T266-24 independent review, replication
package T266-70).

## 7. Open choices for the maintainer

1. TextWorld first (proposed) or PlanBench first.
2. k for arm B (proposed 3).
3. Whether ALFWorld (text) is added as a third suite later.
