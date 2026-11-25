# T248 — Cross-Repository BCEL Synthesis & Core Fail-Closed Hardening

**Status:** agentic (production)  
**Date:** 2026-11-25  
**Scope:** comparative synthesis across 10 complementary SPEACE repositories (`cellular_speace_{big,docker,gpt,ollama,opus}`, `GROK SPEACE 4_3`, `GTP SPEACE`, `speaceorganismocibernetico`, `speace_agi`, `speace_ds`) + fail-closed numerical, CI, and bounded-memory remediation in `q_speace`.  
**Dependencies added:** None (`numpy` + Python 3.12 stdlib only).

---

## 1. Motivation & Comparative Audit Summary

An audit of `q_speace` alongside 10 sibling/alternative SPEACE repositories identified two complementary classes of work:

1. **Repository & Quality-Gate Defects in `q_speace`:**
   - Bare `pip install -e ".[dev]"` CI environments (matching `.github/workflows/ci.yml`) failed `pytest` collection in `tests/test_t234_core_coverage.py` (`ModuleNotFoundError: No module named 'jwt'` from `q_speace.remote_mcp.server`), failed `tests/test_t242_tech_debt_hardening.py` (`PackageNotFoundError: mcp` in `online_agent.main()`), and failed `mypy q_speace` with 13 `[import-not-found]` errors on optional `[http]`/`[mcp]` extras.
   - A corrupted draft file `systemic_resonance.py` `` (with a trailing backtick) was tracked at the repository root, and `q_speace/__init__.py` listed `"QuantumState"` twice in `__all__`.
   - Several core modules had silent numerical or state-management edge cases:
     - `QuantumState.apply_unitary()` allowed `NaN` matrices through `np.max(np.abs(diff)) > 1e-6` (`NaN > 1e-6` is `False`).
     - `QuantumNeuralBridge` collided qubit slot indices on `register -> unregister -> register`, left dangling entanglement pairs on `unregister`, ignored stored pair fidelity in `quantum_compatibility()`, and did not reject `NaN`/`Inf` in `set_activity()`.
     - `FractalQCA` hardcoded `tick=0` on every step, lacked finiteness checks (`sigma=NaN` bypassed `sigma <= 0`), and could slightly exceed `1.0` on `coherence_phi`.
     - `CosmicVirusOptimizer` lacked finiteness/shape/range guards on `CVConfig` and `step()`.
     - `ResonanceEngine.find_hexagonal_clusters()` evaluated $\binom{N}{6}$ combinations without a `max_nodes` bound.
     - `QuantumOrchestrator._history` and `SelfImprovementCortex._history` used unbounded lists rather than ring buffers (`deque(maxlen=...)`), `enable_qca` collapsed `seed=0` via `self._seed or 0`, `run_schumann` executed each circuit twice per tick without `ticks >= 1` validation, and `qspace quantum run -n 1` crashed on QCA minimum cell count.

2. **High-Signal Functional Mechanisms from the 10 Complementary Repositories:**
   Applying the BCEL gate (`AGENTS.md` §1–§2) across all 10 external repositories rejected consciousness/IIT $\Phi$ claims (`PhiCalculator`, `ConsciousnessGate`), anatomical lobe narratives, unparseable demos (`GROK SPEACE 4_3`), and in-place destructive graph mutations, while isolating four clean mathematical/algorithmic capabilities that close genuine open loops in `q_speace`:
   - **Closed-Loop Criticality Homeostasis & Synaptic Scaling** *(from `speace_ds` + `cellular_speace_opus`)*: closes the unused `_spike_history` telemetry loop in `QuantumOrchestrator` via Beggs–Plenz branching-ratio regulation of `dynamic_spikes` divisor `k`, multiplicative homeostatic scaling on `SpikePlasticity`, and temporal variance liveness diagnostics.
   - **Inverse-Variance Precision Weighting & Variational Free-Energy Surprise** *(from `speaceorganismocibernetico` + `GTP SPEACE`)*: upgrades `InformationalLogicalField` (`q_speace/edd_cvt/ilf.py`) with empirical inverse-variance precision weights $\pi_i(t)$ and a variational free-energy diagnostic $\mathcal{F}_t$.
   - **Directed Spike-Lag Causal Discovery & Non-Destructive Interventional `do(X=x)` Engine** *(from `speace_agi`, remediating its in-place `remove_edge` bug)*: complements symmetric Pearson correlation (`q_speace/spiking/correlation.py`) with directed temporal-asymmetry discovery $A_{ij}$ and immutable mutilated-DAG interventions $G_{\overline{X}}$, strictly separated from `EntanglementRegistry` (preserving the no-communication invariant).
   - **Zero-Daemon Hybrid `SemanticEpisodicMemory` (`sqlite3` + `blake2b` 128-D feature hashing) + Vector/Jaccard `EvolutionaryMemory` + Transactional Pre/Post `SandboxedPatchCycle` & `EpistemicProposalAuditor`** *(from `GTP SPEACE`, `cellular_speace_ollama`, and `cellular_speace_docker`)*.

---

## 2. BCEL Classification Table

| Biological / Quantum Metaphor | Classification | Digital Rule in `q_speace` |
|---|---|---|
| Neuronal avalanches & cortical self-organized criticality (`speace_ds`) | `functional` (gain rule) / `accidental` (seizure narrative) | Keep closed-loop branching-ratio controller $\hat{\sigma}_t$ regulating `dynamic_spikes` threshold divisor $k_{t+1} = \operatorname{clip}(k_t + K_p(\sigma^* - \hat{\sigma}_t), k_{\min}, k_{\max})$ and multiplicative homeostatic scaling on `SpikePlasticity`. Remove cortical avalanche/seizure narrative. |
| Cortical laminar predictive coding (`speaceorganismocibernetico`, `GTP SPEACE`) | `functional` (precision math) / `accidental` (6-layer anatomy) | Keep empirical EMA error variance $\hat{v}_i$ and inverse-variance precision weight $\pi_i = \operatorname{clip}((\hat{v}_i + \epsilon)^{-1}, \pi_{\min}, \pi_{\max})$ on `ILF` beliefs plus variational free energy $\mathcal{F}_t = \frac{1}{2}\sum_i \pi_i \hat{v}_i + \lambda D_{\mathrm{KL}}(q^*_t \parallel q^*_{t-1})$. |
| STDP causal induction & counterfactual imagination (`speace_agi`) | `functional` (DAG `do`-calculus) / `accidental` (imagination narrative) | Keep directed temporal-precedence asymmetry $A_{ij} = \frac{N_{i\prec j}-N_{j\prec i}}{N_{i\prec j}+N_{j\prec i}}$ and non-destructive Pearl $\operatorname{do}(X=x)$ evaluation on mutilated DAG $G_{\overline{X}}$. Never mutate live graphs in-place; never conflate causal edges with quantum entanglement. |
| Hippocampal indexing & sleep consolidation (`GTP SPEACE`, `ollama`) | `functional` (hybrid index & compaction) / `accidental` (sleep/dream narrative) | Keep stdlib SQLite + FTS5/lexical + signed 128-D `blake2b` token/3-gram cosine retrieval, TTL archiving, offline deduplication, and continuous metric cosine + Jaccard tag recall in `EvolutionaryMemory`. |
| Emergent council deliberation & neuroplastic self-repair (`docker`, `ollama`) | `functional` (perturbation/pre-post filter) / `accidental` (agency prose) | Keep seeded input-perturbation stability + sample/complexity epistemic discount (`EpistemicProposalAuditor`) and transactional pre/post benchmark delta verification with automatic rollback on regression (`SandboxedPatchCycle`). |
| IIT $\Phi$ consciousness gates & anatomical lobe personas (`speaceorganismocibernetico`, `speace_agi`, `speace_ds`, `GROK SPEACE`) | `accidental` | Rejected in full per `AGENTS.md` §2 and `T208` §3.1: partition entropy-difference heuristics and density surrogates are neither IIT $\Phi$ nor evidence of consciousness. |

---

## 3. Technical Specification

### 3.1 CI & Optional-Dependency Decoupling
- `q_speace/remote_mcp/service.py` hosts dependency-free `bounded()` alongside `_reject_json_constant()`.
- `q_speace/remote_mcp/server.py` re-exports `bounded` and `_reject_json_constant` and guards optional `[http]` imports (`jwt`, `mcp`, `starlette`) so importing validation helpers works in bare `[dev]` environments, while instantiating HTTP endpoints without `[http]` fails closed with `RuntimeError`.
- `q_speace/experiments/online_agent.py` and `policy_calibration.py` resolve `importlib.metadata.version("mcp")` via a safe helper returning `"unavailable"` on `PackageNotFoundError`.
- `pyproject.toml` adds `[[tool.mypy.overrides]]` for optional `[mcp]`/`[http]` packages so `mypy q_speace` succeeds cleanly on bare `pip install -e ".[dev]"`.

### 3.2 Core Quantum, QCA, CV & Orchestrator Hardening
- **`QuantumState.apply_unitary`**: explicitly validates `np.all(np.isfinite(u))` before unitarity residual checks.
- **`EntanglementRegistry` & `QuantumNeuralBridge`**:
  - `EntanglementRegistry.remove_entity(entity_id)` purges all pairs involving `entity_id` and rebuilds the entity index.
  - `QuantumNeuralBridge` uses monotonic `_next_slot` allocation, cleans up registry pairs on `unregister()`, validates finiteness in `set_activity()`, and returns max clamped pair fidelity $\in [0, 1]$ in `quantum_compatibility(a, b)`.
- **`FractalQCA` & `CosmicVirusOptimizer` & `ResonanceEngine`**:
  - `FractalQCA` validates `2 <= num_cells <= 16` and finite parameters, increments `self._tick` on every `step()`, reuses `_distance_weight()`, and clips `coherence_phi` to `[0.0, 1.0]`.
  - `CosmicVirusOptimizer` validates finite `CVConfig` (`sigma >= 0`), matching finite `weights`/`gradient_s_info` shapes, `dt >= 0`, and `steps >= 0`.
  - `ResonanceEngine` enforces `max_nodes: int = 24` (`>= 6`) fail-closed to bound $\binom{N}{6}$ cluster enumeration.
- **Bounded Histories & CLI**:
  - `QuantumOrchestrator` and `SelfImprovementCortex` store history in `deque(maxlen=max_history)` (default `1024`).
  - `QuantumOrchestrator` supports opt-in `enable_criticality: bool = False`,regulating `_spike_k` via `CriticalityController` and exposing `temporal_liveness()` (non-degeneracy variance check).

### 3.3 New / Extended Functional Modules
1. **`q_speace/spiking/criticality.py` & `q_speace/spiking/plasticity.py`**:
   - `CriticalityController(target_sigma=1.0, kp=0.15, k_min=0.5, k_max=10.0, low_band=0.8, high_band=1.2, window=16)`: computes smoothed branching ratio $\hat{\sigma}_t = \frac{1}{|W|}\sum \frac{S_t + 1}{S_{t-1} + 1}$, classifies regime (`"sub_critical" | "critical" | "super_critical"`), and updates `k` via bounded negative feedback.
   - `SpikePlasticity.homeostatic_scale(target_mean=0.5, min_scale=0.1, max_scale=10.0)`: multiplicative synaptic scaling keeping population mean EMA bounded around `target_mean`.
2. **`q_speace/edd_cvt/ilf.py`**:
   - `observe_prediction_error(agent_id, error, *, eta=0.2, min_precision=0.1, max_precision=10.0) -> float`: updates per-agent error variance EMA and sets inverse-variance precision weight $\pi_i$.
   - `variational_free_energy(kl_weight=1.0) -> float`: returns $\frac{1}{2}\sum_i \pi_i \hat{v}_i + \lambda_{\mathrm{KL}} D_{\mathrm{KL}}(q^*_t \parallel q^*_{t-1})$.
3. **`q_speace/spiking/causal.py`**:
   - `spike_temporal_asymmetry(activity, max_lag=3, min_cooccurrences=2, threshold=0.2, ids=None)` -> directed `CausalEdge` list with $A_{ij} \in [-1, 1]$ and weight.
   - `StructuralCausalDAG`: acyclic structural linear model supporting `predict(exogenous)`, non-destructive `intervene(do_map, exogenous)` on mutilated graph $G_{\overline{X}}$ (original graph untouched), and 3-step Pearl `counterfactual(observed, do_map)` (abduction $\to$ action $\to$ prediction).
4. **`q_speace/spiking_brain/memory.py` & `q_speace/self_improvement_cortex/`**:
   - `embed_text_hashed(text, dim=128)`: deterministic signed `blake2b` word + char-3gram $L_2$-normalized vector.
   - `SemanticEpisodicMemory`: SQLite-backed `Memory` implementation with hybrid lexical/FTS5 + cosine similarity retrieval, optional TTL expiration, and `consolidate()` deduplication.
   - `EvolutionaryMemory.find_similar_metrics(metrics, tags=None, top_k=5)`: continuous metric cosine + tag Jaccard retrieval.
   - `EpistemicProposalAuditor` (`evolution_council.py`) & `SandboxedPatchCycle` (`cortex.py`): deterministic perturbation-stability + Occam/evidence auditing in the uncertain band $[0.05, 0.99)$ and transactional pre/post benchmark delta verification with automatic rollback on regression.

---

## 4. Verification & Acceptance Criteria
- All existing test suites plus `tests/test_t248_cross_repo_and_hardening.py` pass under `pytest` with bare `.[dev]` dependencies.
- `ruff check q_speace tests`, `black --check q_speace tests`, `mypy q_speace`, and `python -m py_compile` pass with zero errors.
- Zero consciousness claims, zero entanglement-communication violations, zero unguarded real-backend paths, and zero new runtime dependencies.
