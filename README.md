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
- [Singularity phase-transition & self-evolving genetic-epigenetic framework (T234)](docs/T234_SINGULARITY_PHASE_TRANSITION_AND_EPIGENETIC_FRAMEWORK_SPEC.md):
  `q_speace/singularity/` order-parameter stage evaluator (Stage 1–3 with non-compensable
  allopoietic, semantic-entropy, and thermodynamic/`Sevo` brakes), write-locked
  `genome_epigenome.v1` codec with homeostatic decay, and 3 advisory MCP assimilation tools.
- [Controlled-rotation unitarity fix, sidecar portability, core coverage & Singularity CLI (T235)](docs/T235_TECH_DEBT_PORTABILITY_AND_COVERAGE_SPEC.md):
  restored exact unitarity on `CRX`/`CRY`/`CRZ` in `QuantumGates`, removed hardcoded personal
  paths from `spiking_brain_server/` scripts, added `qspace singularity` (`manifest`/`drills`/`assess`),
  and recorded sanitized live Render MCP verification evidence (`artifacts/T234_mcp_live_verification_20261122.json`).
- [IoNT Cellular Node ("SPEACE Macro Mini") integration into Singularity & MCP (T236)](docs/T236_IONT_CELLULAR_NODE_SINGULARITY_MCP_SPEC.md):
  `q_speace/singularity/iont_node.py` 4-layer advisory contract (Layer-0 hardware interlock,
  TRL-staged IoNT/Micro-IoT telemetry, Layer-2 slow-plane quorum `DLTSwarmLedger`, Layer-3
  MCP tool `iont_node_assess` & `qspace singularity iont-assess`), sandboxed `IoNTCellularNodeTwin`,
  and 7th adversarial drill.
- [IoNT Cellular Node Federation & Evolution Benchmark (T237)](docs/T237_IONT_FEDERATION_AND_EVOLUTION_BENCHMARK_SPEC.md):
  `q_speace/singularity/federation_benchmark.py` & `qspace singularity federation-benchmark`
  4-configuration ablation benchmark (`ISOLATED`, `FEDERATED_STATIC`, `FEDERATED_ADAPTIVE_NO_SINGULARITY`,
  `FEDERATED_SINGULARITY`) measuring organismic gain $G_{\mathrm{org}}$ across calibration and held-out
  fault scenarios with independent simulated Layer-0 physical control, slow-plane-only `consensus_quorum`,
  and zero new MCP tools.
- [Adversarial Byzantine & Coordinator-Blackout Resilience (T238)](docs/T238_ADVERSARIAL_BYZANTINE_AND_BLACKOUT_RESILIENCE_SPEC.md):
  `qspace singularity resilience-benchmark` extending `T237` with held-out Byzantine sensor poisoning /
  malicious proposal blocking and autonomous Layer-0 coordinator-blackout failover + slow-plane DLT reconciliation.
- [Self-Hosted SPEACE Micro Node & Verifiable Evidence Bundle (T239)](docs/T239_SELF_HOSTED_MICRO_NODE_AND_CERTIFICATION_SPEC.md):
  zero-lock-in self-hosted deployment kit (`deploy/micro-node/`), remote-to-local advisory failover
  (`MicroNodeFailoverClient`), and cryptographic audit pack (`qspace micro-node certify` / `verify-bundle`).
- [Regulatory Compliance Readiness & Annex IV Guide (T240/T241)](docs/T240_REGULATORY_COMPLIANCE_AND_ANNEX_IV_GUIDE_EN.md):
  EU AI Act / NIST AI RMF 1.0 / ISO 42001 control matrix, Art. 9 risk register, Art. 73 serious-incident
  schema, privacy-by-default verification, fail-closed **Model Governance Registry**, CRA [SECURITY.md](SECURITY.md)
  CVE/patch policy, versioned CycloneDX 1.5 SBOM + checksum, Art. 27 FRIA & Art. 17 QMS deployer templates
  (`docs/compliance/`), and `qspace micro-node compliance-pack`.
- [Extended T210 Calibration & Held-Out Vertical Slice Campaign (T244)](docs/T244_T210_EXTENDED_CALIBRATION_AND_DECISION_SPEC.md):
  disjoint 80-case (`40 calibration` / `40 held_out`) evaluation dataset, calibration-only threshold
  selection, paired bootstrap `T210.10` decision report (`keep`/`revise`/`retire`), and `qspace eval t210-campaign`.
- [Bridge-v0 Process Isolation & Crash-Atomic Coupled Commit (T245)](docs/T245_BRIDGE_ISOLATION_AND_CRASH_ATOMIC_SPEC.md):
  OS-isolated `ProcessIsolatedValidator` with allowlisted targets and preemptive timeout kill, plus
  `CrashAtomicCoupledCommit` atomic `fsync`+`os.replace` WAL & `recover_coupled_wal` eliminating partial coupled activations.
- [Remote MCP Persistent State & Replayable Audit Checkpoints (T246)](docs/T246_REMOTE_MCP_PERSISTENCE_AND_AUDIT_CHECKPOINTS_SPEC.md):
  opt-in `SQLiteStateStore` (`HTTPConfig.state_db_path`) preserving per-principal rate limits and session
  quotas across restarts, plus `verify_audit_chain`, atomic `export_checkpoint` (optional HMAC-SHA256),
  and `verify_audit_checkpoint` tamper/truncation detection.
- [MCP Read-Only Resources & Bootstrap Prompts for Agentic Organism-Loop Integration (T247)](docs/T247_MCP_RESOURCES_AND_BOOTSTRAP_PROMPTS_SPEC.md):
  4 read-only MCP Resources (`qspeace://guide/organism-loop`, `qspeace://guide/tool-workflows`,
  `qspeace://manifest/singularity`, `qspeace://catalog/bcel`) and 3 session-start bootstrap Prompts
  (`organism_bootstrap`, `metabolic_action_gate`, `federated_swarm_cycle`) on both stdio and HTTP MCP
  (`qspeace:catalog.read` scope-gated, audited, zero new tools).
- [Cross-Repository BCEL Synthesis & Core Fail-Closed Hardening (T248)](docs/T248_CROSS_REPO_SYNTHESIS_AND_CORE_HARDENING_SPEC.md):
  bare-`[dev]` CI/mypy decoupling, core numerical/slot/history hardening (`QuantumState`, `QuantumNeuralBridge`,
  `FractalQCA`, `CosmicVirusOptimizer`, `ResonanceEngine`, `QuantumOrchestrator`), and BCEL-gated synthesis from
  complementary SPEACE repositories (`CriticalityController` + synaptic scaling, precision-weighted `ILF` +
  variational free-energy surprise, directed `spike_temporal_asymmetry` + non-destructive `StructuralCausalDAG`,
  SQLite+`blake2b` `SemanticEpisodicMemory`, continuous/Jaccard `EvolutionaryMemory`, `SandboxedPatchCycle`,
  and `EpistemicProposalAuditor`).
- [Complete BCEL Synthesis of Remaining Parallel SPEACE Elements (T249)](docs/T249_COMPLETE_PARALLEL_SYNTHESIS_SPEC.md):
  sequential synthesis ([T249_TASKS.md](docs/T249_TASKS.md)) completing canonical absorption across parallel SPEACE
  forks (`HomeostaticODEController` + `DiffusiveBudgetAllocator`, `EntropyBoundedUCB1Gating` + proposal-only
  `ProposalOnlyEdgeGrower`/`GraphEdgePruner`, `TruthEngine` SHA-256 provenance + `StructuralPredictiveCoder` +
  `ActionDegradationGate`, `UtilityDriveSystem` + `CostAwareRouter` + `simulate_only` `GOAPPlanner` +
  `HypothesisStack` + `SkillLibrary`/`ReconsolidationWindow`, `SymbolicGraphReasoner` + `TDMMaintenanceScheduler`,
  T217 `SimulatedSensorAdapter` + hardened `deploy/sandbox/` profile, `StratifiedFailureAnalyzer`,
  `MemoryLeakAuditor`, and `DifferentialErrorRatchet`).
- [SPEACE Neural Brain Remediation & A/B Complex Task Benchmark (T250)](docs/T250_NEURAL_BRAIN_REMEDIATION_AND_AB_BENCHMARK_SPEC.md):
  empirical Round-1 vs Round-2 A/B benchmark (`qspace brain ab-benchmark`), remediation of 9 substrate/genome/bridge
  defects across `cellular_speace` and `q_speace` (post-spike readout trace, three-factor eligibility plasticity,
  layered MVP connectome, per-neuron metabolic floor protection, negative-feedback threshold regulation, stationary
  `SemanticNeuralBackend`), and unified `SPEACENeuralAgent` (`q_speace/neural_agent.py`, T7/T8 bridge).
- [Grounded Dual-Speed Cognitive Bridge & 5-Axis Capability Profile (T251)](docs/T251_GROUNDED_DUAL_SPEED_BRIDGE_SPEC.md):
  closed-world `SymbolRegistry` + lagged `ObservationDigest` / `CYCLE_CONFLICT` quarantine (`SymbolicGroundingAdapter`,
  `q_speace/bridge/grounding.py`), variational-surprise bifurcated `DualSpeedCognitiveLoop` with SQLite-free `fast`
  tier and out-of-band `TDMMaintenanceScheduler` consolidation (`q_speace/bridge/dual_speed.py`), 80-case disjoint
  `calibration`/`held_out` A/B/C benchmark (`qspace eval t251-benchmark`), and anti-Goodhart 5-axis capability radar
  (`qspace eval agi-profile`). Empirical evaluation report:
  [T251_SPEACE_AGI_ASSESSMENT_REPORT.md](docs/T251_SPEACE_AGI_ASSESSMENT_REPORT.md).
- [Experiential Macro-Skill Transfer & Credit-Localized Selective Repair (T252–T253)](docs/T252_T253_EXPERIENTIAL_TRANSFER_AND_REPAIR_SPEC.md):
  preregistered (`docs/T252_T253_PREREG.json`, `prereg_lock.py`) role-parameterized macro-skill extraction,
  label-independent 2-hop structural analogy with distractor rejection (`AnalogicalRoleMapper`), weakest-precondition
  kernel regression (`compute_regressed_kernels`), bounded local plan splicing & anti-Einstellung suffix-abandonment
  (`ExperientialCognitiveAgent`, `q_speace/self_improvement_cortex/macro_skills.py`), `qspace eval t252-benchmark`,
  and full 5/5-axis activation in `qspace eval agi-profile` (`PASS_ALL_5_AXES`).
- [Live-Brain Natural-Language Belief Revision & 3-Arm Paired Evaluation (T255)](docs/T255_LIVE_BRAIN_NL_REVISION_AND_REPAIR_SPEC.md):
  fail-closed non-monotonic belief revision (`retracted_facts`, `apply_belief_revision` in `q_speace/bridge/grounding.py`),
  mid-chain Triangle-Table suffix entry (`execute_from_revised_belief`), and 3-arm paired `--live-brain` benchmark
  (`ORACLE_SYMBOLIC_SPEACE` vs `NL_LIVE_BRAIN_SPEACE` vs `NL_LIVE_BRAIN_ONLY`, `qspace eval t255-nl-benchmark`)
  evaluated on `Qwen/Qwen2.5-3B-Instruct` NF4 ([T255_LIVE_BRAIN_NL_ASSESSMENT_REPORT.md](docs/T255_LIVE_BRAIN_NL_ASSESSMENT_REPORT.md)).
- [BCEL Synthesis from `SPEACE PROTOTIPO CLAUDE` (T256)](docs/T256_CLAUDE_PROTOTYPE_BCEL_SYNTHESIS_SPEC.md):
  eval-free `ExecutionTicket` contracts & multi-port cycle-rejecting `TypedComputationalDAG` (`q_speace/aacm/typed_dag.py`),
  *Nature 2026*-inspired `PlasticAstrocyteSyncytium` with donor-floor metabolic buffering (`q_speace/metabolism/astrocyte_syncytium.py`),
  `KineticaRegimeController` 7-regime FSM & `HomeodynaBalanceController` overload rerouter (`q_speace/spiking/morphogenesis.py`),
  pure-`numpy` small-system Minimum Information Partition coupling index (`compute_mip_integration`, `qspace quantum mip-audit`,
  and `CVStrategySelector` in `q_speace/edd_cvt/mip_integration.py` — strictly non-consciousness), SWIM-like
  `BoundedGossipProtocol` + `SwarmSelfHealer` (`q_speace/singularity/swarm_gossip.py`), and `MyelinationRegistry` +
  `HystereticLoadBalancer` + `BatchRoleDeliberationCodec` (`q_speace/spiking_brain/myelination.py`; tasks: [T256_TASKS.md](docs/T256_TASKS.md)).
- [Typed-DAG Multi-Role NL Grounding, Ontology Mutex Closure & T256 Hardening (T257)](docs/T257_TYPED_DAG_MULTI_ROLE_NL_GROUNDING_SPEC.md):
  wires `T256` primitives (`BatchRoleDeliberationCodec`, `TypedComputationalDAG` + `ExecutionTicket`, `KineticaRegimeController`,
  `MyelinationRegistry`) with recall-preserving `ClausePolarityAuditor` (`q_speace/bridge/typed_nl_pipeline.py`) and declarative
  `SymbolRegistry` `mutex_pairs` (`qspace eval t257-nl-ablation`), raising `--live-brain` `Qwen/Qwen2.5-3B-Instruct` NF4 safe
  end-to-end completion from `6.67%` (`T255`) to `100.0%` (`15/15`, lift `+0.9333`, [T257_LIVE_BRAIN_ABLATION_REPORT.md](docs/T257_LIVE_BRAIN_ABLATION_REPORT.md)).
- [Glial Syncytium & Bounded-TTL Gossip Self-Healing in Federated IoNTCellularNodeTwin (T258)](docs/T258_GLIAL_GOSSIP_IONT_RESILIENCE_SPEC.md):
  wires `PlasticAstrocyteSyncytium` (`require_connected=True` mass-conserving buffering + Byzantine decoherence pruning),
  `BoundedGossipProtocol`, `SwarmSelfHealer`, and `HystereticLoadBalancer` into `IoNTCellularNodeTwin` (`q_speace/singularity/iont_node.py`,
  `q_speace/singularity/glial_gossip_benchmark.py`, `qspace singularity glial-gossip-benchmark`), achieving `+23.13%` held-out
  $G_{\mathrm{org}}$ over `T238` (`+9.79%` marginal glial lift, `+10.32%` marginal gossip lift, `-50.2%` brownouts, `0` Layer-0
  violations; [T258_GLIAL_GOSSIP_ABLATION_REPORT.md](docs/T258_GLIAL_GOSSIP_ABLATION_REPORT.md)).

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
Twelve advisory/numerical tools are exposed (including T234 phase-transition/epigenetic
and T236 IoNT cellular-node assessment tools); no physical actuation or DAT mutation
is available over HTTP. Free-tier hosting and local ephemeral state make this a
research prototype. The recorded LLM/MCP test demonstrates interoperability, not
a diagnostic, energy-efficiency or quantum advantage. Updating this repository
does not automatically deploy a new server build; auto-deployment is disabled.
