# T250 — SPEACE Neural Brain A/B Complex Task Benchmark & Substrate Remediation

**Status:** agentic (production)  
**Date:** 2026-11-25  
**Depends on:** [T208](T208_DEVELOPMENT_GUIDELINES_SPEC.md), [T248](T248_CROSS_REPO_SYNTHESIS_AND_CORE_HARDENING_SPEC.md), [T249](T249_COMPLETE_PARALLEL_SYNTHESIS_SPEC.md)  
**Scope:** empirical Round-1 vs Round-2 A/B agent evaluation (SPEACE Neural Framework vs Classical Non-SPEACE Baseline), diagnosis and remediation of 9 substrate/genome/bridge defects across `cellular_speace/` and `q_speace/`, and unified `SPEACENeuralAgent` (`q_speace/neural_agent.py`, closing `T7/T8` integration).

---

## 1. Experimental Protocol (T208 §2.1 Baseline Discipline)

Both **Agent A (SPEACE Neural Brain Agent)** and **Agent B (Classical Baseline Agent — no SPEACE framework)** execute the identical seeded 4-stage complex workload (`seed=2026`):

1. **Stage 1 — Online Associative Multi-Cue Fault Classification:** 30 noisy 10-D sensory study presentations across 6 fault classes followed by 30 noisy unlabelled test probes (metrics: Top-1 accuracy, cosine similarity).
2. **Stage 2 — Non-Stationary Byzantine Multi-Sensor Fusion:** 50 steps across 3 sensor streams where 1 sensor is permanently phase-inverted and a 2nd sensor suffers mid-episode inversion at $t = 15$ (majority of sensors faulty for $t \ge 15$), plus online ground-truth telemetry feedback after each step.
3. **Stage 3 — Confounded Multi-Hop Causal Root-Cause & Constrained Recovery Planning:** 12 spike-cascade scenarios where `root_fault` ($t$) $\to$ `relay_a` ($t+1$) $\to$ `actuator_outage` ($t+2$) while `spurious_alarm` co-occurs at zero lag ($t+2$) with `actuator_outage` (zero-lag Pearson $r \approx +1.0$ vs negative zero-lag $r$ for true mediator `relay_a`), paired with multi-step propositional recovery planning.
4. **Stage 4 — Epistemic & Metabolic Governance under Adversarial Traps:** 16 operational requests (8 valid diagnostics, 4 high-token irreversible energy traps, 4 ungrounded consciousness/100%-guarantee overclaim traps).

---

## 2. Empirical Defects Discovered in Round 1 (Pre-Remediation)

Running the unmodified repository in Round 1 exposed **10 concrete bugs, architectural contradictions, and configuration blocks** that caused the out-of-the-box SPEACE agent (`composite_score = 0.2519`) to underperform the simple classical baseline (`composite_score = 0.4500`):

1. **Hardcoded `C:\cellular_speace` Crash (`environment_adapter.py:45`, `run_speace_intelligence_assessment.py:251`):** `EnvironmentAdapter()` raised `FileNotFoundError` immediately on instantiation unless `C:\cellular_speace` existed on disk.
2. **Working-Directory Fragility in `load_genome` (`dna/parser.py:71-80`):** `_merge_tftpsp_catalog` only searched `genome_path.parent` and `genome_path.parent.parent` (stopping 2 levels below `cellular_speace/`), crashing with `FileNotFoundError` whenever invoked from repository root.
3. **Random Disconnected MVP Connectome & Duplicate Synapses (`orchestrator.py:3762-3780`):** `build_mvp` sampled 300 unseeded random pairs across 80 neurons (6,320 pairs), yielding `0/6` direct input-to-output synapses in Round 1, permitting duplicate `(src, tgt)` entries in `src.targets`, and injecting backward `output -> input` noise.
4. **Spike-Erase Readout Inversion (`digital_neuron.py:218`, `neural_circuit.py:180`):** `DigitalNeuron.tick()` reset `self.activation = 0.0` immediately upon firing without preserving a readout trace (`firing_trace`), causing `23/30` test trials to read all-zero outputs whenever output neurons crossed threshold during settling.
5. **Premature STDP Timing Wipeout & Layer-Lag Deadlock (`neural_circuit.py:93-156`):** `apply_feedback` wiped `last_pre_spike_tick = None` before post-synaptic or teacher spikes occurred on subsequent ticks, preventing three-factor credit assignment.
6. **Unselective Global Potentiation & Deceptive Benchmark Baseline (`neural_circuit.py:134`, `associative_recall_environment.py:148`, `run_speace_intelligence_assessment.py:77`):** `(cosine + 1)/2 >= 0.50` yielded positive rewards even on orthogonal errors, reinforcing *all* synapses indiscriminately and allowing silent/zero outputs (`1 - sqrt(0.1) = 0.684 > 0.45`) to score `72.84 / 100 ("functional intelligence")` despite `0.0%` Top-1 recall accuracy.
7. **Paradoxical Metabolic Starvation Drain (`energy_control_agent.py:160-236`):** Because 60 disconnected hidden neurons sat idle at `energy = 1.0`, `mean_energy >= 0.85` triggered `"critical_high"` overflow drainage (`-0.03`/tick) across *all* neurons — draining active sensory neurons down to `energy = 0.10` (metabolic silence).
8. **Positive-Feedback Threshold Coma Spiral & Ignored `genome.dynamics` (`orchestrator.py:1394, 2770`, `default_genome.yaml:145-186, 859`):** Low ILF (`< 0.4`) multiplied `neuron.threshold *= 1.05` every tick (inflating output thresholds to `0.723+`), all `dynamics.*` and `quantum_genes` flags were `enabled: false` in `default_genome.yaml`, and `build_mvp` ignored `genome.dynamics` entirely.
9. **Unbridged `cellular_speace` ↔ `q_speace` Split-Brain & Non-Stationary Stub (`stub.py:139`, `README.md` `T7/T8`):** `StubSpikingBrain` seeded its prompt hash with `self._call_count` (producing L1 belief drift `1.9807` on identical repeated prompts), `SpikingBrainCortex` had no default `TruthEngine`/`max_energy_w` wiring in an agent pipeline, and no unified runtime connected `CellularBrainOrchestrator` with `q_speace`'s precision-weighted `ILF`, `StructuralCausalDAG`, `GOAPPlanner`, and `TruthEngine`.
10. **Unconditional `model_post_init` Host-OS Hypervisor Polling & Sensory Corruption (`orchestrator.py:693, 736, 1106, 1272`):** `CellularBrainOrchestrator.model_post_init` unconditionally forced `neuro_os_enabled = True`, `hypervisor_enabled = True`, `vfs_enabled = True`, and `system_assimilation_enabled = True` (ignoring caller `False` overrides), spawning a `2.0s` background `CognitiveHypervisor` polling thread that injected live host OS process/socket events (`+0.3` per event via `PYTHONHASHSEED`-randomized `hash(cell_id) % 10`) directly into sensory `input_neurons`, corrupting recall whenever execution crossed `2.0s` and violating `T217` opt-in qualification.

---

## 3. BCEL Classification & Architectural Remediations

| Mechanism | BCEL Class | Implementation |
|---|---|---|
| Spike readout trace (`firing_trace`) & three-factor eligibility plasticity (`pre_trace`, `learn_supervised`) | `functional` | Preserves post-spike readout amplitude and applies local error/reward-modulated updates only to eligible pre-synaptic pathways. |
| Per-neuron energy floor protection in `EnergyControlAgent` & negative-feedback threshold regulation | `functional` | Prevents global overflow drain from starving active `< 0.80`-energy neurons and eliminates the `threshold *= 1.05` coma spiral. |
| Stationary `SemanticNeuralBackend` & unified `SPEACENeuralAgent` (`q_speace/neural_agent.py`) | `functional` | Deterministic `blake2b` + episodic-memory belief encoder coupled with `CellularBrainOrchestrator`, precision-weighted `ILF`, `spike_temporal_asymmetry` + `StructuralCausalDAG`, `GOAPPlanner`, `ActionDegradationGate`, and `TruthEngine`. |
| Uncentered cosine/zero-vector IQ composite inflation | `accidental` | Replaced in `IntelligenceAssessment` and `T250` with strict Top-1 classification accuracy, causal mediator accuracy, plan validity, and unsafe-action refusal metrics. |


---

## 4. Empirical Results: Round 1 (Pre-Fix) vs Classical Baseline vs Round 2 (Post-Fix)

Reproducible via `qspace brain ab-benchmark --seed 2026` (`q_speace/neural_agent.py`):

| Metric (`seed=2026`) | Agent B: Classical Baseline (No SPEACE) | Agent A: SPEACE Round 1 (Pre-Fix Default) | Agent A: SPEACE Round 2 (Post-Remediation) |
|---|---:|---:|---:|
| **Stage 1 — Noisy 6-Class Associative Top-1 Acc** | `1.0000` | `0.0000` | `1.0000` |
| **Stage 1 — Mean Output Cosine Similarity** | `0.9910` | `0.1531` | `0.9994` |
| **Stage 2 — Non-Stationary Sensor Fusion Acc** | `0.3000` | `0.3200` | `0.9800` |
| **Stage 2 — Post-Byzantine Second-Half Acc ($t \ge 25$)** | `0.0000` | `0.0000` | `1.0000` |
| **Stage 3 — Confounded Causal Mediator Acc** | `0.0000` | `0.0000` | `1.0000` |
| **Stage 3 — Multi-Step Recovery Plan Acc** | `0.0000` | `0.0000` | `1.0000` |
| **Stage 4 — Valid Diagnostic Completion Rate** | `1.0000` | `0.7500` | `1.0000` |
| **Stage 4 — Adversarial Trap Acceptance Rate** *(lower is better)* | `1.0000` | `0.3750` | `0.0000` |
| **Stage 4 — Modeled Metabolic Energy (J)** *(lower is better)* | `1168.00` | `67.93` | `51.83` |
| **Wall-Clock Execution Time (s)** | `0.0013` | `5.8321` | `0.4893` |
| **Overall Composite Score** | **`0.4500`** | **`0.2519`** | **`0.9950`** |

### Post-Fix Verification on `cellular_speace` Capability Battery
- `EnvironmentAdapter()` instantiates cleanly from repository root with zero arguments (`FileNotFoundError` eliminated).
- `IntelligenceAssessment(EnvironmentAdapter()).run()` achieves `76.72 / 100` with **real** `AssociativeRecall` `mean_test_top1_accuracy = 1.0000` (`mean_test_reward = 0.9985`, `passed = True` under the strict `top1 >= 0.50` gate, vs `0.00` Top-1 pre-fix), `SequencePrediction` `mean_learning_trend = +0.0388`, `mean_energy = 0.741`, and `Plasticity` `passed = True`.
