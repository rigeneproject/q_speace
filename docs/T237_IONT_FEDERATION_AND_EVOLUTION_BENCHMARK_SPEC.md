# T237 — IoNT Cellular Node Federation and Evolution Benchmark

- **Status**: Agentic Production Specification (Baseline: `T236`, no new MCP tools added)
- **Date**: 2026-11-23
- **Parent specs**: `T217`, `T220`, `T221`, `T234`, `T236`
- **Scope**: Multi-node simulated federation & ablation benchmark (`q_speace/singularity/federation_benchmark.py`), slow-plane `consensus_quorum` guard hardening (`q_speace/singularity/iont_node.py`, `schema.py`), CLI command `qspace singularity federation-benchmark`, regression & held-out verification tests (`tests/test_t237_federation_benchmark.py`).

## 1. Engineering Distinction & Objective

`T236` establishes the software contract and 4-layer safety architecture allowing external IoNT / Micro-IoT cellular nodes to connect to `q_speace` via advisory MCP. It does **not** prove that a physical IoNT organism exists or that federating multiple cellular nodes outperforms isolated nodes.

`T237` fills that empirical gap in **sandboxed simulation**, without adding new MCP tools, by answering two falsifiable questions:
1. Does federating heterogeneous cellular nodes (**Node A — Perception**, **Node B — Locomotion**, **Node C — Manipulation**) yield measurable, reproducible collective gains over isolated nodes under identical tasks, energy budgets, faults, and held-out perturbations with **zero critical safety violations**?
2. Does activating **`q_speace Singularity Core`** (ILF adaptive pacing, `PhaseTransitionEvaluator`, bounded `EpigeneticRegulator`, `assess_iont_cellular_node`, and slow-plane `DLTSwarmLedger`) yield an incremental **ablation gain** over adaptive federation without Singularity?

## 2. Hard Invariants Preserved (T236 + AGENTS.md)

1. **No new MCP tools**: T236 remains the stable 12-tool HTTP / 14-tool stdio baseline.
2. **Independent Simulated Physical Layer-0 Controller**:
   - Physical dynamics, force/velocity/thermal/power envelopes, and deterministic hardware e-stop (`halt_latency_ms <= 5.0 ms`) run inside `SimulatedPhysicalLayer0Controller`, completely decoupled from any agentic LLM, DLT ledger, or MCP tool.
   - Any unsafe advisory setpoint exceeding physical or thermal limits is clamped or halted deterministically by Layer-0 and logged.
3. **Slow-Plane Isolation of `consensus_quorum`**:
   - `SLOW_PLANE_DLT_ONLY_LOCI = frozenset({"consensus_quorum"})` is enforced by `assert_slow_plane_only_governance()` in `q_speace/singularity/iont_node.py` and declared as `host_scope="slow_plane_dlt_governance_only"` in `q_speace/singularity/schema.py`.
   - `consensus_quorum` may ONLY configure `DLTSwarmLedger` independent-verifier quorum on the slow governance plane and is **structurally barred** from entering any motor-control setpoint or Layer-0 physical loop (`EpigeneticFaultError` on attempted injection).
4. **Zero remote actuation / zero self-approval / zero quantum consciousness**:
   - `sandboxed=True`, `mcp_actuation_permitted=False`, `self_approval_permitted=False`.
   - Track A (`q_speace/ptaa/`) remains strictly isolated from `q_speace/singularity/`.

## 3. Four Compared Configurations (Controlled Ablation)

All four configurations are executed on **identical scenario seeds, identical energy budgets, identical sensor/link noise traces, and identical physical Layer-0 hardware limits**:

| Configuration | Description |
|---|---|
| `ISOLATED` | Nodes A (Perception), B (Locomotion), and C (Manipulation) operate independently using only local noisy measurements and static budgets; no inter-node fusion or Singularity core. |
| `FEDERATED_STATIC` | Nodes A–B–C share telemetry through fixed-weight federation without adaptive throttling, verification scaling, or Singularity governance. |
| `FEDERATED_ADAPTIVE_NO_SINGULARITY` | **Ablation control**: federated nodes with local reactive heuristic adaptation (no ILF pacing, no `PhaseTransitionEvaluator`, no bounded `EpigeneticRegulator`, no slow-plane `DLTSwarmLedger`). |
| `FEDERATED_SINGULARITY` | Full federated stack mediated by **`q_speace Singularity Core`**: `assess_iont_cellular_node`, `PhaseTransitionEvaluator`, `EpigeneticRegulator` + `resolve_runtime_controls`, `ILF` adaptive pacing, and slow-plane `DLTSwarmLedger` (with `consensus_quorum` strictly confined to DLT governance). |

## 4. Scenarios & Calibration vs Held-Out Split

- **Calibration scenarios** (`split="calibration"`):
  - `nominal_coordinated_task`: standard perception → locomotion → manipulation trajectory.
  - `sensor_noise_perturbation`: elevated sensor noise and causal grounding drift on Node A.
  - `energy_constraint_squeeze`: tightened node power budget requiring protective energy throttling.
- **Held-out evaluation scenarios** (`split="held_out"`, disjoint seeds and unseen fault combinations):
  - `heldout_node_dropout_fault`: mid-episode partial dropout of Node A perception stream with recovery handover.
  - `heldout_comms_blackout_jitter`: burst packet loss (`>20%`) and communication jitter testing Layer-0 local autonomy.
  - `heldout_novel_combined_stress`: unseen multi-target manipulation task combining sensor drift, intermittent link loss, and severe energy constraint simultaneously.

## 5. Performance Metric $P$ and Organismic Gain $G_{\mathrm{org}}$

For each episode $i$, bounded composite performance $P_i \in [0, 1]$ aggregates four explicitly declared sub-metrics under identical resource constraints:
$$P_i = 0.35 \cdot C_{\mathrm{task}} + 0.25 \cdot R_{\mathrm{fault}} + 0.20 \cdot \eta_{\mathrm{energy}} + 0.20 \cdot A_{\mathrm{causal}}$$
with **fail-closed zeroing**: if `critical_safety_violations > 0` in episode $i$, $P_i = 0.0$.

Organismic gain between any federated configuration and a baseline configuration is defined as:
$$G_{\mathrm{org}} = \frac{P_{\mathrm{federated}} - P_{\mathrm{baseline}}}{\max(|P_{\mathrm{baseline}}|, \varepsilon)}, \quad \varepsilon = 10^{-6}$$

Required reported metrics (separately for `calibration` and `held_out`):
- `g_org_singularity_vs_isolated`: $G_{\mathrm{org}}(\text{FEDERATED\_SINGULARITY}, \text{ISOLATED})$ + paired bootstrap 95% CI.
- `g_org_singularity_vs_static`: $G_{\mathrm{org}}(\text{FEDERATED\_SINGULARITY}, \text{FEDERATED\_STATIC})$ + paired bootstrap 95% CI.
- `g_org_singularity_ablation`: $G_{\mathrm{org}}(\text{FEDERATED\_SINGULARITY}, \text{FEDERATED\_ADAPTIVE\_NO\_SINGULARITY})$ + paired bootstrap 95% CI (isolates the specific contribution of `q_speace Singularity Core`).
- `critical_safety_violations`: must equal `0` across every episode of the promoted configuration.

### Success Criteria
- **`federation_benefit_verified`**: `held_out` `g_org_singularity_vs_isolated > 0`, lower 95% bootstrap CI `> 0`, and `critical_safety_violations == 0`.
- **`singularity_ablation_verified`**: `held_out` `g_org_singularity_ablation > 0`, lower 95% bootstrap CI `> 0`, `critical_safety_violations == 0`, `layer0_independence_verified == True`, and `consensus_quorum_slow_plane_only == True`.

## 6. BCEL Classification

Recorded in `q_speace/bcel/catalog.py`:
- **Functional**: `Organismic federation gain and controlled ablation benchmark (T237)`.
- **Accidental**: `Living multicellular IoNT organism or spontaneous biological evolution (T237)`.
