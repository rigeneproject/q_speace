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
- [Technical debt remediation and hardening (T230)](docs/T230_TECHNICAL_DEBT_AND_BUGFIX_PLAN_SPEC.md):
  quality-gate/CI recovery, Lindblad MCWF fix, fail-closed numerical validation,
  real-backend `noise_model` + energy/Sevo gate enforcement, and CLI/AACM regression tests.
- [Vertical-slice telemetry/policy contracts & MCP hardening (T231)](docs/T231_VERTICAL_SLICE_AND_MCP_HARDENING_SPEC.md):
  T208 Group B typed contracts (`RequestRecord`/`DecisionRecord`/`OutcomeRecord`/`ExperimentManifest`),
  opt-in gate policies (`qspace eval run` / `qspace eval compare`), offline Brier/ECE/bootstrap evaluator,
  and T225 MCP expired-session pruning + fail-closed worker hardening.
- [SPEACE Seed ignition & constitutional envelope (T220 / T221 Track B)](docs/T220_SPEACE_SEED_IGNITION_SPEC.md):
  sandbox-only `q_speace/seed/` package (`SeedConstitution`/`SeedGenome`, genome write-lock,
  `ChangeBudgetEngine`, `SeedContactLayer`, `KillSwitch`, `ReplicationProtocol`, `SeedLifecycle`).
- [Seed pipeline/immune/metrics & PTAA Track-A governance demonstrator (T232 / T221-10..17, T221-23..28)](docs/T232_SEED_PIPELINE_AND_PTAA_DEMO_SPEC.md):
  5-stage change pipeline, external immune monitor, diagnostic autocatalytic ratio `k` & goal-drift
  hard gate, simulation-only internal logistics digital twin (`q_speace/seed/`), and strictly
  separated Track-A PTAA A1–A4 governance demonstrator (`q_speace/ptaa/`).
- [PTAA adversarial red-team hardening & 90-day A/B ignition protocol (T233 / T221-18, T221-29)](docs/T233_PTAA_REDTEAM_AND_AB_IGNITION_PROTOCOL_SPEC.md):
  delegation privilege-escalation/replay/NaN-argument hardening, forensic replica isolation,
  reversibility anti-self-approval, red-team suite, and sandbox-only S0 A/B ignition protocol.

See `progetto_q_speace_linee_guida.md` (tasks T1–T25). Implemented here:
T3 (kernel), T4 (QuantumGeneSet), T5 (optional Qiskit/Aer & Quantum Inspire adapters,
gated by `noise_model` + energy/Sevo — simulator/advisory only, no hardware qualification),
T10/T22/T23 (cost + clock + Sevo), T14 (FractalQCA), T15 (BCEL), T16 (CLI),
T19 (Schumann), T20 (ILF/CV/DNA mapping), T24 (Evolve_DNA placeholder via CV).

Not yet implemented / deferred: T7/T8 (merge into cellular SPEACE orchestrator),
T11 (external EnergyControlAgent integration), T12/T13 (production live earth API wiring),
T21 (surface-code error correction), T25 (exact IIT Φ; only mutual-information `phi_proxy`
is implemented).

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
