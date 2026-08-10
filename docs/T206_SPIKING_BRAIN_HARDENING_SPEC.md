# T206 — SpikingBrain hardening, gated chat, and calibration

**Status:** agentic (production)

## Purpose

Make the existing SpikingBrain satellite internally consistent and safe to
evaluate as a *consultative computational component*.  It does not assert or
implement consciousness.  Language output is untrusted until it passes the
existing coherence/Sevo gate, and confidence is treated as a forecast to be
measured, not as metacognition by declaration.

## Scope

1. Restore the T202 contracts: spike count enters `QuantumOperation`; a
   correlation binding preserves its label in `QuantumNeuralBridge`.
2. Make `brain chat` use `SpikingBrainCortex.tick()` and its gate, without
   duplicating the rolling history.
3. Provide deterministic calibration metrics (Brier score and ECE) for
   labelled evaluation runs.  Metrics do not train, alter weights, or grant
   the model agency.
4. Document an optional small instruction-tuned sidecar profile.  Downloading
   a model or changing model weights is explicitly outside this ticket.

## BCEL gate

| Concept | Class | Digital rule |
|---|---|---|
| Biological confidence / introspection | accidental | Removed; no claim of subjective uncertainty. |
| Calibrated predictive confidence | functional | Compare numeric confidence with labelled outcomes using Brier/ECE. |
| Conversation | functional | Untrusted text channel; only gated belief updates affect ILF/SIA. |

## Acceptance criteria

- Existing spike-energy and correlation tests pass.
- A chat turn is processed once, with `tick()` as the only cognitive update
  path; rejected output cannot update ILF.
- Calibration metrics have unit tests for perfect and miscalibrated forecasts.
- `pytest`, `py_compile`, Ruff, Black, and mypy pass on touched files.

## Hardware profile

The 7B SpikingBrain sidecar remains experimental on an RTX 3060 6 GB.  A
small instruction-tuned model may be exposed through the same HTTP contract
on a separate endpoint; it is a language interface, not a replacement for
the spike/ILF control layer.

> **Forward-ref (2026-08-10)**: il piano operativo per abilitare il
> modello reale (verifica pesi WSL2 + fix SDPA mask shape) è ora
> definito in `docs/T-SPB-0A_PLAN.md`. T206 resta limitato a
> hardening del consultivo (gating, calibrazione, BCEL); il
> fix di runtime è demandato a T-SPB-0A.
