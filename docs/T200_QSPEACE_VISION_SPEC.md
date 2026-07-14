# T200 — Q-SPEACE Vision & Engineering Spec

**Status**: baseline (derived from `progetto_q_speace_linee_guida.md`)
**Scope**: quantum layer for the SPEACE organism
**Author**: Rigene Project (rework of R. De Biase guidelines)

## 1. Purpose

Q-SPEACE is a hybrid classical-quantum computational model that encodes the
informational invariants shared across scales (atom → cell → brain →
organism → Earth → solar system) as testable digital rules. It is **not**
a living or conscious entity.

## 2. Scientific corrections (must hold)

- Entanglement is a *computational binding resource*, never a communication
  channel (no-communication theorem).
- Living systems do not minimize global entropy; they export it. Q-SPEACE
  optimizes entropic efficiency `Sevo = ΔU/ΔS_info > 1.5`.
- "Fractality" kept as a *functional* scaling rule; biological fractal shape
  is accidental and removed.
- No claim of quantum consciousness (mirrors SPEACE COR constraint).

## 3. Architecture

```
EarthFeed ──► Orchestrator (quantum_enabled)
                 ├─ QuantumNeuralBridge + EntanglementRegistry
                 ├─ FractalQCA (recursive weights)
                 ├─ ILF (coherence_phi, adaptive clock)
                 ├─ CosmicVirusOptimizer (self-optimization)
                 ├─ QuantumCostModel (energy + Sevo gate)
                 └─ BCEL catalog (accidental/functional filter)
```

Real backend (Qiskit/Aer) is a future optional extension behind the same
`QuantumGeneSet` interface used by the numpy emulator.

## 4. Modules (this repo)

See `README.md` table. All modules are numpy-only by default; Qiskit is an
optional extra.

## 5. Validation

- `pytest` must pass on `tests/`.
- Schumann benchmark reports `mean_coherence` in [0,1] and a stable (non-
  collapsing) trace over ticks.
- Orchestrator `report()` returns finite `mean_coherence_phi` and
  `mean_energy_w`.

## 6. Open tasks (see guidelines)

T1–T26. Implemented: T1,T2,T3,T4,T5,T6,T7,T8,T10,T11,T14,T15,T16,T19,T20,T22,T23,T24,T25,T26.
Remaining (out of scope / external): T9 (resonance layer), T17 (cellular_speace path), T18 (external assessment), T21 (surface-code, requires Qiskit).
