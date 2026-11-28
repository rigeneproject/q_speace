# Terminology errata for T251 and T259–T260 reports (T266-05)

**Date:** 2026-11-28 · The original reports are kept unchanged as historical records; this
errata governs how their results may be cited.

| Report | Original wording | Corrected reading |
|---|---|---|
| T251 report §2 | "proto-AGI funzionale su base sperimentale" | planner with reusable plan fragments and selective repair, evaluated on generated symbolic families |
| T251 report §2 | placement on "Levels of AGI" (Competent / Expert) | not applicable: no external benchmark was run |
| T259–T260 report §3 | "architettura proto-AGI neuro-simbolica e sistemica" | experimental neuro-symbolic control and verification layer around a 3B language model |
| T260 | `PASS_ALL_7_ORGANISM_AXES` | internal regression profile; it does not measure capability outside the project's own suites |
| T251/T260 tables | bootstrap intervals of zero width (e.g. `[+0.8120, +0.8120]`) | deterministic outcome on generated cases, not a statistical estimate |
| T257 | 1/15 → 15/15 | holds with hand-declared `mutex_pairs`; discovery of incompatibilities is not shown |

Reason: T208 §3 and AGENTS.md forbid capability labels not backed by a named external
benchmark and baseline. Findings T263–T265 (non-causal spike layer, order dependence,
token-bound transfer, negative transfer under a new vocabulary) confirm that the earlier
labels were not supported.
