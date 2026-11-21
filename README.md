# Q-SPEACE — Quantum Super Planetary Entità Autonoma Cibernetica

![CI](https://github.com/rigeneproject/q_speace/actions/workflows/ci.yml/badge.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

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

### Engineering specifications

- [Evidence-first development guidelines (T208)](docs/T208_DEVELOPMENT_GUIDELINES_SPEC.md).
- [Safe assimilation lifecycle (T217)](docs/T217_SAFE_ASSIMILATION_LIFECYCLE_SPEC.md):
  proposed correction, validated simulation, isolated host replica, confined
  prototype tests, independent review, and selective integration. This is a
  documentation-only specification; no VR engine, host clone, hardware access,
  or release gate is implemented by it.
- [NCM coarse-to-fine codec, Phase 0 (T222)](docs/T222_NCM_CODEC_SPEC.md):
  codec-only experiment with preregistration and deterministic section locking.
  Includes calibration-only scaffolding; no NCM generator, no held-out run,
  no DoD claim, and no AACM integration yet. Task registry:
  [T222_TASKS.md](docs/T222_TASKS.md).

See `progetto_q_speace_linee_guida.md` (tasks T1–T25). Implemented here:
T3 (kernel), T4 (QuantumGeneSet), T10/T22/T23 (cost + clock + Sevo),
T14 (FractalQCA), T15 (BCEL), T16 (CLI), T19 (Schumann), T20 (ILF/CV/DNA
mapping), T24 (Evolve_DNA placeholder via CV).

Not yet implemented: T5 (real Qiskit backend), T7/T8 (merge into SPEACE
orchestrator), T11 (gate quantum via EnergyControlAgent), T12/T13 (live
earth API wiring), T21 (surface-code error correction), T25 (IIT Φ proxy).

## SpikingBrain integration status

- **T-SPB-0A / 0B** ✅ — verification + sliding-window cache diagnosis
- **T-SPB-4** ✅ — formal `SpikingBrainCognitiveInterface` Protocol
- **T-SPB-2 (real SpB-7B NF4)** — pending RTX 3060 cache-less run
- **T-SPB-7 (real SpB 2.0)** — pending HuggingFace public release

Monthly HF monitor: see `docs/spb2_monitor.md` (run `curl ... | jq` on
the first of every month against `https://huggingface.co/api/models?author=BICLab`).


## Remote MCP experimental service and Paradigm 6.0

- [English agent connection guide and domain use cases (Wiki)](https://github.com/rigeneproject/q_speace/wiki).
- [Manifesto v2.0 Technical Edition](docs/Paradigm_6.0_Manifesto_v2.0_Technical_Edition.pdf), preserved original; read with the [technical errata](docs/PARADIGM_6_0_V2_0_ERRATA.md).
- [T225 HTTP specification and T218 reuse matrix](docs/T225_REMOTE_MCP_SERVICE_SPEC.md).
- [English technical connection/deployment guide](docs/T225_AGENT_CONNECTION_GUIDE_EN.md).
- [T226 bounded LLM agent connection experiment and evidence](docs/T226_AGENT_MCP_CONNECTION_EXPERIMENT_SPEC.md).

Endpoint: `https://q-speace-mcp.onrender.com/mcp` (authorized OAuth access required).
Eight advisory/numerical tools are exposed; no physical actuation or DAT mutation
is available over HTTP. Free-tier hosting and local ephemeral state make this a
research prototype. The recorded LLM/MCP test demonstrates interoperability, not
a diagnostic, energy-efficiency or quantum advantage. Updating this repository
does not automatically deploy a new server build; auto-deployment is disabled.
