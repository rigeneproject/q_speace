# T256 — BCEL Synthesis of Useful Elements from `SPEACE PROTOTIPO CLAUDE`

**Status:** agentic (production)  
**Date:** 2026-11-27  
**Depends on:** [T208](T208_DEVELOPMENT_GUIDELINES_SPEC.md), [T217](T217_SAFE_ASSIMILATION_LIFECYCLE_SPEC.md), [T249](T249_COMPLETE_PARALLEL_SYNTHESIS_SPEC.md), [T250](T250_NEURAL_BRAIN_REMEDIATION_AND_AB_BENCHMARK_SPEC.md)  
**Task Registry:** [T256_TASKS.md](T256_TASKS.md)  
**Scope:** BCEL-filtered extraction and fail-closed, `numpy`/stdlib-only implementation of the 6 non-redundant functional mechanisms identified in `D:\SPEACE PROTOTIPO CLAUDE` (`neural_engine/` and `SPEACE_Cortex/`), strictly preserving all `AGENTS.md` invariants and the frozen 12-tool HTTP MCP contract.

---

## 1. BCEL Audit & Classification Matrix

| Source Module (`SPEACE PROTOTIPO CLAUDE`) | Biological / Prototype Concept | BCEL Class | Target Module in `q_speace` | Engineering Rule / Rationale |
|---|---|---|---|---|
| `SPEACE_Cortex/astrocyte_network.py` (*Nature 2026* regional glial syncytium) | Plastic regional astrocyte networks with gap junctions & metabolic buffering | `functional` | `q_speace/metabolism/astrocyte_syncytium.py` | Bidirectional gap-junction conductances $g_{ij} \in [g_{\min}, 1.0]$ modulated by regional coherence $\bar{\Phi}$ with pruning below $g_{\text{prune}}$, attenuated BFS alert/coherence propagation, and donor-floor-protected ($\ge 0.30$) energy redistribution. |
| `neural_engine/protocol.py`, `graph_core.py`, `config/contracts.yaml` | `ExecutionTicket` pre/post-condition contracts & multi-port typed DAG | `functional` | `q_speace/aacm/typed_dag.py` | Safe declarative `FieldConstraint` & `ContractSpec` validation (**zero `eval()`**), verified `ExecutionTicket` lifecycle, typed multi-port edges (`DATA`, `CONTROL`, `FEEDBACK`), Kahn topological sort with cycle rejection, and subgraph execution. |
| `SPEACE_Cortex/morphogenesis_engine.py` | *Kinetica* cognitive-regime transitions & *Homeodyna* overload rerouting / E-I balance | `functional` | `q_speace/spiking/morphogenesis.py` | Deterministic 7-state FSM (`REACTIVE`, `DELIBERATIVE`, `ABSTRACTION`, `CREATIVE`, `META`, `EMERGENCY`, `IDLE`) with `EMERGENCY` override at `resource_usage > 0.90`, $\Phi$ gate on `META`, E/I balance score, and overload bypass `reroute_path`. |
| `SPEACE_Cortex/adaptive_consciousness/phi_calculator.py`, `metacognitive.py` | Exact small-system Minimum Information Partition (MIP, $2 \le n \le 10$) & $\exp(-\text{CV})$ strategy switching | `functional` | `q_speace/edd_cvt/mip_integration.py` | Pure-`numpy` Gaussian/empirical bipartition mutual information weighted by cross-cut coupling (`compute_mip_integration`, closing `T25` strictly as a network-coupling metric — **never** consciousness), plus `CVStrategySelector` ($\exp(-\sigma/\mu)$). |
| `SPEACE_Cortex/swarm/swarm_node.py` | SWIM-like bounded-TTL gossip & `SelfHealingManager` | `functional` | `q_speace/singularity/swarm_gossip.py` | Bounded-TTL epidemic dissemination with `(sender_id, msg_id)` deduplication, deterministic `ACTIVE -> STALE -> FAILED` peer detector, and advisory `RepairPlan` (`reroute`, `replace`, `rebalance`). |
| `SPEACE_Cortex/myelination_engine.py`, `neural_parliament.py`, `neural_engine/load_balancer.py` | Oligodendrocyte path myelination, hysteretic multi-resource load balancing, & single-call batch role framing | `functional` | `q_speace/spiking_brain/myelination.py` | $\bar{\Phi}$-driven pathway conductivity (`MyelinationRegistry`) with inactivity pruning, inter-resource variance `HystereticLoadBalancer`, and deterministic `BatchRoleDeliberationCodec` (`--- ROLE ---`). |
| `digital_brain.py:260`, `protocol.py:160`, `adaptive_consciousness/`, `glial_controller.py:99` | Unsanitized `eval()` predicates, `"consciousness_index"` claims, narrative identity, & `psutil` host-CPU coupling in $\Phi$ | `accidental` | **Rejected** | Eliminated in full: `eval()` introduces code-injection vulnerabilities, consciousness claims violate `AGENTS.md` §2, and coupling $\Phi$ to host CPU load corrupts determinism. |

---

## 2. Mathematical & Safety Specifications

### 2.1 Plastic Regional Astrocyte Syncytium (`T256-01`)
Given regional nodes $V_A$ with calcium/activity state $c_i \in [0, 1]$, local coherence $\Phi_i \in [0, 1]$, and metabolic reserve $m_i \in [0, 1]$, bidirectional gap junctions $(i, j)$ carry permeability $g_{ij} \in [g_{\min}, 1.0]$:
- **Wave propagation:** BFS from origin $o$ attenuates signal amplitude by $\gamma \cdot g_{ij}$ ($\gamma = 0.80$) per hop without revisiting nodes.
- **Coherence-driven plasticity:** For sliding-window mean $\bar{\Phi}$: $g_{ij} \leftarrow \min(1, g_{ij} + \Delta_+)$ if $\bar{\Phi} > \theta_{\text{high}}$, and $g_{ij} \leftarrow g_{ij} - \Delta_-$ if $\bar{\Phi} < \theta_{\text{low}}$, pruning the junction when $g_{ij} < g_{\text{prune}}$.
- **Protected redistribution:** Donors $d$ transfer at most $\frac{1}{2}\max(0, m_d - m_{\text{floor}})$ ($m_{\text{floor}} = 0.30$) to needy regions $u$, strictly conserving total metabolic reserve $\sum_i m_i$.

### 2.2 Safe Contract `ExecutionTicket` & Multi-Port DAG (`T256-02`)
- Replaces string `eval()` conditions with declarative `FieldConstraint` rules (`required_type`, `min_val`, `max_val`, `non_empty`, `allowed_values`) checked on both `inputs` (before issuing an active `ExecutionTicket`) and `outputs` (before marking the ticket `"completed"`).
- `TypedComputationalDAG` enforces finite edge weights/delays, rejects cycles via Kahn's algorithm in $\mathcal{O}(|V| + |E|)$, routes named `source_port -> target_port` payloads across `DATA`/`CONTROL` edges, and supports bounded ancestor/descendant subgraph execution (`start_nodes` $\to$ `end_nodes`).

### 2.3 Kinetica Regime FSM & Homeodyna Rerouting (`T256-03`)
- `KineticaRegimeController` governs transitions across 7 regimes; if `resource_usage > 0.90` during high-cost transitions (`DELIBERATIVE`, `ABSTRACTION`, `CREATIVE`), it deterministically diverts into `EMERGENCY` (`parallel_units=1, depth_limit=1, exploration_rate=0.0`), and blocks `META` whenever $\Phi < 0.60$.
- `HomeodynaBalanceController` computes $B_{\text{EI}} = 1 - |E - I| \in [0, 1]$, penalizes threshold/resource violations, and reroutes overloaded paths through healthy bypass candidates without mutating caller lists.

### 2.4 Small-System MIP Coupling Index (`T256-04` — Closing `T25` Without Consciousness Claims)
- For $T \times n$ finite state trajectories $X$ ($2 \le n \le 10$, $T \ge 3$) and optional symmetric coupling matrix $W \in \mathbb{R}_{\ge 0}^{n \times n}$, `compute_mip_integration` evaluates all $2^{n-1} - 1$ non-trivial bipartitions $(A, \bar{A})$ using regularized Gaussian mutual information:
  $$I(X_A; X_{\bar{A}}) = \frac{1}{2}\ln\frac{\det(\Sigma_{AA} + \varepsilon I)\,\det(\Sigma_{\bar{A}\bar{A}} + \varepsilon I)}{\det(\Sigma + \varepsilon I)}$$
  normalized by $\min(|A|, |\bar{A}|)$ and weighted multiplicatively by mean cross-cut coupling $\bar{w}_{A, \bar{A}}$ ($\bar{w}_{A,\bar{A}} = 1$ when `connectivity=None`, fixing the prototype's `np.trace` bug where zero-diagonal adjacency matrices produced `0.0` everywhere while guaranteeing `0.0` across disconnected blocks). For $n > 10$, it falls back cleanly to a deterministic bisection/spectral coupling proxy.
- `CVStrategySelector` tracks bounded performance windows and computes confidence $c = \exp(-\sigma / (|\mu| + \varepsilon)) \in (0, 1]$, switching to the highest-mean historical strategy when $c < \theta_c$ or monotonic decline is detected.

### 2.5 Bounded-TTL Swarm Gossip & Self-Healing (`T256-05`)
- `BoundedGossipProtocol` enforces `0 <= ttl <= max_ttl` (`max_ttl = 8`), bounded deduplication ring buffer `(sender_id, msg_id)`, sender exclusion, and deterministic seeded peer fanout (`np.random.default_rng(seed)`).
- `SwarmSelfHealer` transitions peers `ACTIVE -> STALE -> FAILED` using explicit monotonic timestamps (`now_s` — no wall-clock flakiness) and emits advisory `RepairPlan` records (`replace` when a healthy standby exists, `reroute` for relay/edge faults, `rebalance` under load skew).

### 2.6 Adaptive Myelination, Hysteretic Load Balancer & Batch Role Codec (`T256-06`)
- `MyelinationRegistry` tracks per-edge sliding $\Phi$ history (`maxlen=20`), potentiates priority conductivity when $\bar{\Phi} > 0.70$, demyelinates when $\bar{\Phi} < 0.40$ or idle elapsed time exceeds `idle_threshold_s`, and prunes at $\le 0.05$.
- `HystereticLoadBalancer` computes weighted utilization, inter-resource variance `balance_score`, dynamic safety margin, and hysteretic `throttle_factor` recovery.
- `BatchRoleDeliberationCodec` formats multi-role prompts (`planner`, `critic`, `creative`, `researcher`, `executor`) into one deterministic batch prompt and parses `--- ROLE ---` sections with graceful fallback for missing sections.

---

## 3. Invariants & Verification Gates
- **No consciousness claim:** `compute_mip_integration` is documented, typed, and exported strictly as an information-theoretic subsystem-coupling diagnostic (`mip_integration_index`).
- **Zero `eval()` & zero new dependencies:** `pyproject.toml` dependencies remain unchanged; all validation is static/declarative.
- **Frozen MCP surface:** HTTP MCP tool count remains `12` (`0` new tools).
- **Quality gates:** `pytest`, `ruff check`, `black --check`, `mypy q_speace`, and `python -m py_compile` clean.
