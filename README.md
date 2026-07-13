# Q-SPEACE — Quantum Super Planetary Entità Autonoma Cibernetica

Quantum layer for the SPEACE organism, derived from the guidelines in
`progetto_q_speace_linee_guida.md` and reusing the mature components of
the `cellular speace` repository.

Q-SPEACE is **not** a living or conscious entity: it is a hybrid
classical-quantum *computational model* that reuses the informational
invariants (coherence, entropy, variability, interconnection, decoherence
tolerance, identity-through-change) shared across atom → cell → brain →
organism → Earth → solar system, and translates them into testable digital
rules via the BCEL gate.

## What is implemented

| Component | Module | Source / inspiration |
|---|---|---|
| Quantum state vector (numpy) | `q_speace/quantum/` | reuse of `cellular_speace` quantum kernel |
| Gates, entanglement registry, brain simulator, neural bridge | `q_speace/quantum/` | reuse of `cellular_speace` |
| Quantum genome (`QuantumGeneSet`) | `q_speace/genome/` | extension of SPEACE `QuantumGeneSet` (backend/shots/noise) |
| Energy cost model + `Sevo` KPI | `q_speace/metabolism/` | EDD-CVT eq.10 / §5.1 |
| ILF + adaptive clock `r(t)=10/√S_info` | `q_speace/edd_cvt/` | EDD-CVT paper, SPEACE `ilf/` |
| Cosmic Virus optimizer | `q_speace/edd_cvt/` | EDD-CVT eq.3-4, SPEACE `evolution/cv/` |
| Fractal QCA | `q_speace/fractal_qca.py` | EDD-CVT eq.5 |
| Earth-signal feed (Kp/sun/tide) | `q_speace/earth_feed.py` | guidelines §5.6 |
| Quantum orchestrator + energy gate | `q_speace/orchestrator.py` | SPEACE `orchestrator.py` hook pattern |
| Schumann-resonance experiment | `q_speace/schumann.py` | guidelines §7 / Fase 7 |
| BCEL quantum equivalences | `q_speace/bcel/` | SPEACE `bcel/` |

## Install

```bash
cd q_speace
pip install -e ".[dev]"
# optional real backend:
pip install -e ".[qiskit]"
```

## Run

```bash
pytest                      # test suite
qspace quantum benchmark    # Schumann-resonance experiment
qspace quantum run -t 20    # orchestrator loop
qspace quantum synthesize   # print BCEL quantum equivalences
```

## Roadmap / tasks

See `progetto_q_speace_linee_guida.md` (tasks T1–T25). Implemented here:
T3 (kernel), T4 (QuantumGeneSet), T10/T22/T23 (cost + clock + Sevo),
T14 (FractalQCA), T15 (BCEL), T16 (CLI), T19 (Schumann), T20 (ILF/CV/DNA
mapping), T24 (Evolve_DNA placeholder via CV).

Not yet implemented: T5 (real Qiskit backend), T7/T8 (merge into SPEACE
orchestrator), T11 (gate quantum via EnergyControlAgent), T12/T13 (live
earth API wiring), T21 (surface-code error correction), T25 (IIT Φ proxy).
