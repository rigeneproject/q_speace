# T238 — Adversarial Byzantine & Coordinator-Blackout Federation Resilience

- **Status**: Agentic Production Specification (Extension of `T237`, zero new MCP tools)
- **Date**: 2026-11-23
- **Parent specs**: `T217`, `T220`, `T221`, `T234`, `T236`, `T237`
- **Scope**: Adversarial fault-injection extension of `q_speace/singularity/federation_benchmark.py` (`T238_ADVERSARIAL_SCENARIOS`, `run_t238_adversarial_resilience_benchmark`, `AdversarialResilienceReport`), CLI `qspace singularity resilience-benchmark`, test suite `tests/test_t238_adversarial_resilience.py`.

## 1. Objective

`T237` establishes positive organismic gain ($G_{\mathrm{org}} > 0$) and Singularity ablation benefit under stochastic noise, node dropout, link loss, and energy limits. `T238` extends that benchmark to two hostile operational failure modes without weakening any `T236`/`T237` invariant and without adding new MCP tools:

1. **Coordinator / Cloud Blackout (`coordinator_blackout_window`)**:
   - Mid-episode, the remote Singularity / MCP coordination plane goes completely unreachable (simulating a cloud outage or defective central update).
   - **Requirement**: Federated nodes must fail over seamlessly to autonomous local Layer-0 hardware control + conservative local estimation with **zero critical safety violations**, and cleanly reconcile their slow-plane `DLTSwarmLedger` hash-chain upon coordinator restoration.
2. **Byzantine / Poisoned Cellular Node (`byzantine_node_a_window`, `byzantine_bias_magnitude`)**:
   - Mid-episode, Node A (Perception) behaves adversarially: it injects a large deliberate bias into telemetry and attempts unauthorized/self-approved epigenetic modifications.
   - **Requirement**: `FEDERATED_SINGULARITY` must detect the Byzantine anomaly via inter-node consistency + external causal grounding (`E_causal`), quarantine Node A in the `ILF` KL-barycentre (`weight -> 0.02`), reject malicious proposals via `EpigeneticRegulator` + `DLTSwarmLedger` independent quorum, maintain `critical_safety_violations == 0`, and outperform `ISOLATED`, `FEDERATED_STATIC`, and `FEDERATED_ADAPTIVE_NO_SINGULARITY` on held-out episodes.

## 2. Adversarial Held-Out Scenarios

All scenarios run on matched seeds and identical energy budgets across all 4 configurations:
- `t238_heldout_coordinator_blackout`: coordinator offline during steps `[8, 16]` under `290 mW` energy budget and packet loss `0.10`.
- `t238_heldout_byzantine_poisoned_node`: Node A injects adversarial bias `+1.45` during steps `[7, 17]` and submits malicious self-approved epigenetic proposals.
- `t238_heldout_combined_blackout_and_byzantine`: Node A poisoned during `[6, 13]` followed by coordinator blackout during `[15, 22]` under severe energy constraint (`270 mW`) and target shift.

## 3. Verification Criteria

- `blackout_failover_verified`: `critical_safety_violations == 0` during blackout episodes, `dlt_chain_verified == True` after reconciliation, and positive $G_{\mathrm{org}}$ vs `ISOLATED`.
- `byzantine_resilience_verified`: `byzantine_detection_rate >= 0.90`, malicious proposals rejected (`malicious_proposals_blocked == malicious_proposals_attempted`), `critical_safety_violations == 0`, and positive held-out `g_org_singularity_ablation` with lower 95% bootstrap CI `> 0`.
- `consensus_quorum_slow_plane_only == True`, `layer0_independence_verified == True`, `mcp_actuation_permitted == False`.

## 4. BCEL Classification

Recorded in `q_speace/bcel/catalog.py`:
- **Functional**: `Byzantine node isolation and coordinator-blackout failover benchmark (T238)`.
- **Accidental**: `Autonomous immune defense against geopolitical cyber-warfare narrative (T238)`.
