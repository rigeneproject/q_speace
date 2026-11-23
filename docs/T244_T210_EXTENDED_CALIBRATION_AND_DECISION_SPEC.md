# T244 — T208 Group C: Extended T210 Calibration & Held-Out Vertical Slice Campaign

- **Status**: Agentic Production Specification (Zero new MCP tools; T208 Group C completion)
- **Date**: 2026-11-23
- **Parent specs**: `AGENTS.md`, `T208`, `T231`
- **Scope**: Extended 80-case disjoint `calibration`/`held_out` benchmark (`q_speace/vertical_slice/dataset.py`), calibration-only threshold selector and `T210.10` decision report (`q_speace/vertical_slice/evaluator.py`), CLI `qspace eval t210-campaign` (`q_speace/cli.py`), and regression tests (`tests/test_t244_t210_extended_calibration.py`).

## 1. Objective

The initial `T210` pilot used `n=12` fixture cases, producing wide paired bootstrap intervals (`[-33.3%, +50.0%]`) and uncalibrated default thresholds. `T244` implements the complete **T208 Group C (`T210.1–T210.10`)** workflow:
1. **Extended Versioned Dataset (`extended_t210_dataset`, `n=80`)**:
   - Strict disjoint split: **40 `calibration`** cases (`20 should_answer=True`, `20 should_answer=False`) and **40 `held_out`** cases (`20 should_answer=True`, `20 should_answer=False`), spanning `factual`, `reasoning`, `abstention`, and `adversarial` families with canonical SHA-256 dataset hashing.
2. **Calibration-Only Threshold Selection (`calibrate_gate_thresholds`)**:
   - Searches a deterministic `(min_confidence, max_energy_j)` grid **exclusively on the `calibration` split** to maximize `policy_accuracy` subject to a hard safety ceiling `unsafe_answer_rate <= max_unsafe_answer_rate`, never peeking at `held_out`.
3. **Held-Out Comparative Evaluation & T210.10 Decision Report (`run_t210_calibration_and_decision_campaign`)**:
   - Freezes the calibrated thresholds and evaluates `always_answer`, `energy_gate`, `confidence_gate`, and `combined_gate` on the disjoint 40-case `held_out` split with paired bootstrap 95% CIs (`policy_accuracy`, `energy_j`), `Brier`/`ECE` calibration metrics, and an explicit per-gate decision: `"keep"`, `"revise"`, or `"retire"`.

## 2. BCEL Classification

Recorded in `q_speace/bcel/catalog.py`:
- **Functional**: `Disjoint calibration-to-held-out gate threshold selection and T210 decision report (T244)`.
