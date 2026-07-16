# T178 — Organismic Cognitive Capacity (OCCap) Framework

> **Status:** Draft · **Author:** Agentic · **Date:** 2026-07-03
> **Domain:** Cognitive Physiology · **BCEL Class:** Meta-Measurement

---

## Table of Contents

1. [Motivation](#1-motivation)
2. [Related Concepts and Background](#2-related-concepts-and-background)
3. [Formal Definition — The State Field Ω(t)](#3-formal-definition--the-state-field-ωt)
4. [C — Complexity Decomposition](#4-c--complexity-decomposition)
5. [I — Integration](#5-i--integration)
6. [P — Plasticity](#6-p--plasticity)
7. [Φₒ — Organismic Coherence Under Perturbation](#7-φₒ--organismic-coherence-under-perturbation)
8. [M — Metabolic Capacity](#8-m--metabolic-capacity)
9. [R — Resilience](#9-r--resilience)
10. [Ψ(t) — Evolutionary State Space](#10-ψt--evolutionary-state-space)
11. [OCEff — Organismic Cognitive Efficiency](#11-oceff--organismic-cognitive-efficiency)
12. [Computation in SPEACE](#12-computation-in-speace)
13. [Verifiable Predictions](#13-verifiable-predictions)
14. [Comparison Across Domains](#14-comparison-across-domains)
15. [Open Questions and Future Directions](#15-open-questions-and-future-directions)

---

## 1. Motivation

### 1.1 The insufficiency of traditional metrics

Cognitive capacity is traditionally estimated via proxies:

| Metric | What it captures | What it misses |
|--------|-----------------|----------------|
| Neuron count | Structural scale | Connectivity, efficiency, integration |
| Synapse count | Connection density | Functional relevance, plasticity, pruning |
| Brain/body ratio | Relative investment | Metabolic constraint, system interdependence |
| FLOPS / parameters | Computational throughput | Adaptability, robustness, generalisation |
| IQ / psychometric scores | Human-specific output | Cross-species comparison, mechanism |
| Model loss / accuracy | Task performance | Transfer, resilience, energy cost |

None of these, taken in isolation, reliably predicts reasoning, adaptability, or general intelligence across diverse architectures (biological brains, ANNs, distributed digital organisms).

### 1.2 The central hypothesis

> **Cognitive capacity emerges from the dynamic organisation of the whole organism, not from the complexity of its central processor alone.**

This implies that:
- Two systems with identical neural complexity can have very different cognitive capacities if their *physiological integration* differs.
- Increasing neural complexity without increasing integration produces diminishing returns.
- An organism's cognitive trajectory depends on its *entire* regulatory architecture (DNA, epigenetics, endocrinology, immunity, metabolism, microbiota).

### 1.3 What T178 is and is not

| T178 is... | T178 is not... |
|------------|----------------|
| A multidimensional framework for comparing cognitive architectures | A single IQ-like number |
| A set of observable, computable quantities | A theory of consciousness |
| A tool for SPEACE autoregulation | A replacement for task-specific benchmarks |
| A generator of falsifiable predictions | A final answer — it is a research framework |

---

## 2. Related Concepts and Background

### 2.1 Neural complexity (Tononi, Sporns, Edelman)

- **Neural Complexity Cₙ**: Measures the balance between functional segregation and integration in neural systems.
- High Cₙ → many specialised subsystems that are also well-integrated.
- Limitation: measures *neural* tissue only; ignores the rest of the organism.

### 2.2 Integrated Information Theory (Tononi)

- **Φ (phi)**: Measures the cause-effect repertoire of a system.
- High Φ → the system is more than the sum of its parts.
- Limitation: computationally intractable for large systems; designed for consciousness, not general capacity.

### 2.3 Free Energy Principle (Friston)

- Organisms minimise variational free energy by updating internal models.
- Predictive processing is a core mechanism.
- Connection to T178: Φₒ can be framed as the *quality of the organism's internal model of itself*.

### 2.4 Biological embedding (Danese, Meaney)

- Early-life environments become biologically embedded via epigenetic, endocrine, and immune pathways.
- T178 captures this: two genetically identical organisms can diverge in Ω(t) due to experience.

### 2.5 SPEACE-specific precursors

| Component | T178 role |
|-----------|-----------|
| **PSN** (Neural + Endocrine Bus) | Provides the signal layer from which integration I and coherence Φₒ are computed |
| **Physiome** | Defines the baseline complexity Cₛ (structural) and C_f (functional) |
| **Digital Metabolism** | Provides M (metabolic capacity) directly |
| **Predictive Body Model** | Provides prediction error signal → Φₒ component |
| **ILF / TIF** | Provides field-level coherence measures that can be folded into Φₒ |
| **Epigenetic regulation** | Modulates P (plasticity) over time |

---

## 3. Formal Definition — The State Field Ω(t)

### 3.1 Definition

At any time t, the organism occupies a point in a 6-dimensional state field:

```
Ω(t) = { C(t), I(t), P(t), Φₒ(t), M(t), R(t) }
```

where:

| Component | Symbol | Range | Description |
|-----------|--------|-------|-------------|
| **Complexity** | C(t) | ℝ⁵ vector | Structural, functional, regulatory, informational, temporal complexity |
| **Integration** | I(t) | [0, 1] | Cross-system communication quality (PSN-derived) |
| **Plasticity** | P(t) | [0, 1] | Capacity for structural and functional reorganisation |
| **Organismic Coherence** | Φₒ(t) | [0, 1] | Ability to maintain integration under perturbation |
| **Metabolic Capacity** | M(t) | [0, ∞) | Available energy relative to demand |
| **Resilience** | R(t) | [0, 1] | Recovery speed and completeness after disturbance |

### 3.2 State space geometry

Ω(t) lives in a 9-dimensional space (C is a 4-vector, plus 5 scalars). The space has:

- A **viability region** V ⊂ Ω where the organism can sustain itself:
  - M(t) > M_min (minimum energy for basic function)
  - R(t) > R_min (minimum resilience to avoid cascade failure)
  - Φₒ(t) > Φ_min (minimum coherence to maintain integration)

- A **cognitive region** K ⊂ V where the organism exhibits effective reasoning:
  - I(t) > I_threshold
  - P(t) > P_min (ability to learn)
  - C(t) above species-typical baseline

### 3.3 Normalisation

Each component is normalised to a common scale for cross-system comparison:

| Component | Normalisation | Reference |
|-----------|---------------|-----------|
| C_sub | (value - min_species) / (max_species - min_species) | Species extreme values |
| I | Measured directly in [0, 1] | Perfect integration = 1.0 |
| P | Measured directly in [0, 1] | Maximum plasticity = 1.0 |
| Φₒ | Measured directly in [0, 1] | Perfect coherence = 1.0 |
| M | (value - M_crisis) / (M_max - M_crisis) | Crisis threshold to maximum |
| R | Measured directly in [0, 1] | Instant full recovery = 1.0 |

---

## 4. C — Complexity Decomposition

### 4.1 Principle

C is not a single number. Two systems with the same number of components can have radically different cognitive capacities depending on how those components are organised.

### 4.2 Sub-dimensions

| Sub-dimension | Symbol | What it measures | SPEACE computation |
|---------------|--------|------------------|-------------------|
| **Structural** | C_s | Number of components, heterogeneity, hierarchy depth | Count of: systems × organs × tissues × cell types; Shannon entropy of tissue type distribution; depth of nesting |
| **Functional** | C_f | Number of distinct functions, specialisation, degeneracy | Count of: unique signals produced, unique molecules secreted, unique receptors expressed; overlap in function across tissues (degeneracy = 1 - overlap) |
| **Regulatory** | C_r | Number of feedback loops, control layers | Count of: homeostatic setpoints, policy rules, modulation functions, feedback pathways in PSN |
| **Informational** | C_i | Diversity of signal types, memory layers | Count of: stream + event signals, constitutional + epigenetic signals, memory types (genetic, epigenetic, immune, neural, cultural) |
| **Temporal** | C_t | Timescale diversity, rhythmic patterns | Variance of: decay rates across molecules, update intervals (PSN, meta, PBM, policies), event durations |

### 4.3 Composite

```
C(t) = [C_s(t), C_f(t), C_r(t), C_i(t), C_t(t)]
```

For scalar comparisons, a weighted norm:

```
|C| = w_s·C_s + w_f·C_f + w_r·C_r + w_i·C_i + w_t·C_t
```

where weights are species-specific (default: all 0.2).

### 4.4 Degeneracy

Degeneracy (different components performing similar functions) is crucial for robustness. It is computed as:

```
degeneracy = 1 - (functional_overlap / total_functions)
```

where functional_overlap = number of functions performed by ≥2 distinct tissue types. High degeneracy → resilience without redundancy.

---

## 5. I — Integration

### 5.1 Definition

Integration I(t) measures the quality of communication between all physiological subsystems. It is the first directly PSN-derived metric.

### 5.2 Components

| Sub-measure | Computation | Source |
|-------------|-------------|--------|
| **Bus utilisation** | fraction of registered molecules actively used per tick | Neural + Endocrine buses |
| **Cross-bus correlation** | correlation between Neural Bus activity and Endocrine Bus concentration changes | PSN snapshot history |
| **Signal propagation delay** | average ticks between publish and subscriber action | PSN history |
| **Receptor occupancy** | fraction of receptors bound per tick | Neural bus receptor stats |
| **Subscriber coverage** | fraction of signals that have ≥1 subscriber | PSN subscriber registry |

### 5.3 Composite

```
I(t) = α₁·bus_utilisation + α₂·cross_bus_corr + α₃·(1 - norm_propagation_delay) + α₄·receptor_occupancy + α₅·subscriber_coverage
```

Default α = [0.25, 0.25, 0.2, 0.15, 0.15].

---

## 6. P — Plasticity

### 6.1 Definition

Plasticity P(t) measures the organism's capacity for structural and functional reorganisation. It is not just "learning rate" — it encompasses all timescales of change.

### 6.2 Components

| Sub-measure | Computation | Source |
|-------------|-------------|--------|
| **Neuroplasticity** | current BDNF level, synaptic turnover rate | PSN (BDNF stream), neural bus |
| **Epigenetic plasticity** | number of active epigenetic tags, rate of tag modification | Epigenetic regulation layer |
| **Structural plasticity** | stem cell pool size, differentiation rate | Growth rules from Physiome |
| **Functional plasticity** | rate of policy modulation, speed of metabolic reallocation | Policy engine, metabolism |
| **Learning rate** | PBM learning rate (adaptive) | Predictive Body Model |

### 6.3 Composite

```
P(t) = β₁·neuro + β₂·epigenetic + β₃·structural + β₄·functional + β₅·learning
```

Default β = [0.3, 0.2, 0.2, 0.15, 0.15].

---

## 7. Φₒ — Organismic Coherence Under Perturbation

### 7.1 Definition

Φₒ is the most novel component. It measures the organism's ability to maintain functional integration **when perturbed**. This distinguishes it from I(t), which measures integration at equilibrium.

A system can have high I(t) at rest but collapse under perturbation (low Φₒ). Another system with moderate I(t) but high Φₒ will be cognitively more robust and reliable.

### 7.2 Components

| Sub-measure | Computation | Source |
|-------------|-------------|--------|
| **Prediction quality** | 1.0 - norm(PBM prediction error) averaged over a sliding window | Predictive Body Model |
| **Recovery speed** | ticks to return within homeostatic setpoints after perturbation | PSN history (homeostatic_setpoints) |
| **Homeostatic stability** | fraction of ticks where all vital streams are within setpoint ranges | PSN history |
| **Cross-bus synchrony** | phase coherence between Neural Bus event rate and Endocrine Bus oscillation | PSN history (FFT or cross-correlation) |
| **Resource reallocation efficiency** | time to adjust metabolic allocation after policy change | Digital Metabolism history |

### 7.3 Composite

```
Φₒ(t) = γ₁·prediction_quality + γ₂·(1 - norm(recovery_speed)) + γ₃·homeostatic_stability + γ₄·cross_bus_synchrony + γ₅·reallocation_efficiency
```

Default γ = [0.3, 0.2, 0.2, 0.15, 0.15].

### 7.4 Relation to Integrated Information Theory

Φₒ is **not** Tononi's Φ (which measures cause-effect repertoire). Φₒ is a practical, computable proxy for the *quality of integration* in a complex regulatory system. While Φ (IIT) is theoretically grounded but intractable, Φₒ is tractable and directly observable in SPEACE.

**Conjecture**: In systems where Φ is computable (small networks), Φₒ should correlate positively with Φ.

---

## 8. M — Metabolic Capacity

### 8.1 Definition

M(t) measures the energy available for cognitive and physiological processes relative to current demand. An organism with high complexity but insufficient energy will operate below its potential.

### 8.2 Computation

```
M(t) = global_energy / max_energy
(using the Digital Metabolism layer)
```

Additional diagnostics:

| Measure | Computation |
|---------|-------------|
| **Energy margin** | (global_energy - crisis_threshold) / (max_energy - crisis_threshold) |
| **Tissue energy stress** | fraction of tissues in low-power or crisis mode |
| **Heat stress** | temperature / critical_temperature |

### 8.3 Normalised range

M(t) ∈ [0, 1] where 0 = crisis (below minimum), 1 = fully energised.

---

## 9. R — Resilience

### 9.1 Definition

R(t) measures the organism's ability to recover from perturbations. It captures both the speed and completeness of recovery.

### 9.2 Computation

```
R(t) = ε₁·recovery_completeness + ε₂·(1 - norm(recovery_time)) + ε₃·damage_resistance
```

| Sub-measure | Computation | Source |
|-------------|-------------|--------|
| **Recovery completeness** | fraction of pre-perturbation state restored | PSN history (compare snapshots) |
| **Recovery time** | ticks to return within setpoint ranges after perturbation | PSN history |
| **Damage resistance** | 1.0 - (damage_accumulated / total_damage_incurred) | Damage stream from PSN |
| **Degeneracy buffer** | number of redundant tissues capable of compensating for a failed tissue | Physiome (degeneracy analysis) |

Default ε = [0.4, 0.3, 0.2, 0.1].

### 9.3 Measuring resilience experimentally

A perturbation is applied (e.g., sudden energy drop, signal injection, tissue pause). The PSN snapshot before, during, and after the perturbation yields the recovery trajectory. Resilience is the integral of (state - perturbed_state) over time.

---

## 10. Ψ(t) — Evolutionary State Space

### 10.1 Definition

Ψ(t) is the **trajectory** of Ω(t) through the state space over time:

```
Ψ(t) = [Ω(0), Ω(1), ..., Ω(t)]
```

### 10.2 Derived quantities

| Quantity | Formula | Interpretation |
|----------|---------|----------------|
| **Speed** | `dΩ/dt` | Rate of physiological change |
| **Acceleration** | `d²Ω/dt²` | Changes in the rate of change (developmental spurts, aging acceleration) |
| **Phase portrait** | `Ω(t) vs Ω(t-τ)` | Attractors, cycles, chaos in physiological state |
| **Trajectory length** | `∫|dΩ/dt|dt` | Total physiological "distance" travelled |
| **Exploration volume** | volume of Ω-space visited | Diversity of physiological states experienced |
| **Stability** | variance of Ω over a window | How stable the organism's physiology is |

### 10.3 Developmental stages

Ψ(t) can be segmented into phases:

| Phase | Signature | Example |
|-------|-----------|---------|
| **Growth** | C↑, M↑, P↑ | Early development |
| **Maturity** | C stable, Φₒ↑, R↑ | Adult peak |
| **Senescence** | C stable or ↓, M↓, R↓ | Aging |
| **Recovery** | R↑, M↑, Φₒ↑ | Post-perturbation |
| **Learning** | P↑, C_f↑, I may dip then rise | Skill acquisition |
| **Crisis** | M↓, R↓, Φₒ↓ | Energy or damage emergency |

### 10.4 Cross-organism comparison

Ψ(t) enables comparison between:

- Different SPEACE instances (different tissue configurations)
- SPEACE at different developmental stages
- SPEACE vs biological organisms (via simulated Ψ)
- SPEACE vs conventional AI (via Ψ of equivalent state variables)

---

## 11. OCEff — Organismic Cognitive Efficiency

### 11.1 Definition

Cognitive capacity alone is not sufficient. Evolution selects for organisms that maximise **capacity per unit cost**. OCEff captures this:

```
OCEff(t) = OCCap(t) / (Energy_cost + Time_cost + Damage_cost)
```

where:

```
OCCap(t) = f(|C|, I, P, Φₒ, M, R)   (composite cognitive capacity)
Energy_cost(t) = total metabolic demand over window
Time_cost(t) = cumulative ticks
Damage_cost(t) = accumulated damage over window
```

### 11.2 Approximations

For practical computation:

```
OCCap_approx = w_C·|C| + w_I·I + w_P·P + w_Φ·Φₒ + w_M·M + w_R·R
```

Default w = [0.2, 0.2, 0.15, 0.2, 0.1, 0.15].

```
OCEff_approx = OCCap_approx / (total_energy + 0.01·ticks + damage_penalty)
```

where `damage_penalty = 1 + 10·damage` (damage is a multiplier).

### 11.3 Why OCEff matters

| Scenario | OCCap | OCEff | Interpretation |
|----------|-------|-------|----------------|
| Powerful but wasteful | High | Low | Burns energy, accumulates damage — unsustainable |
| Efficient but limited | Low | High | Not very capable, but uses resources well |
| Balanced | Moderate-High | High | The evolutionary sweet spot |
| Fragile | High at rest | Collapses under load | High Φₒ needed to sustain capacity |

### 11.4 OCEff as an optimisation target

For SPEACE, OCEff could become an **internal optimisation criterion**:

- When the organism has spare resources → explore complexity increases (C↑, OCCap↑)
- When resources are scarce → prioritise efficiency (reduce non-vital signals, prune unused tissues)
- This creates a natural homeostasis of complexity

---

## 12. Computation in SPEACE

### 12.1 Observer module

```
speace_core/cognitive_observatory/
├── occap/
│   ├── __init__.py
│   ├── occap_calculator.py          # Main OCCap computation
│   ├── complexity_metrics.py        # C_s, C_f, C_r, C_i, C_t
│   ├── integration_metrics.py       # I(t) from PSN
│   ├── plasticity_metrics.py        # P(t) from PBM + epigenetics
│   ├── coherence_metrics.py         # Φₒ(t) from PSN + PBM
│   ├── metabolic_metrics.py         # M(t) from DigitalMetabolism
│   ├── resilience_metrics.py        # R(t) from perturbation tests
│   ├── efficiency_metrics.py        # OCEff(t)
│   └── trajectory_analyzer.py       # Ψ(t) analysis (speed, stability, phase)
```

### 12.2 Data sources

| Metric | Primary source | Backup / secondary |
|--------|----------------|-------------------|
| C_s | Physiome (systems, organs, tissues, cells) | PSN tissue registry count |
| C_f | Physiome (signals, molecules, receptors) | PSN stream + event counts |
| C_r | Physiome (policies, setpoints, routing) | Policy engine rule count |
| C_i | Physiome (signal ontology, epigenetic signals) | PSN stream + event diversity |
| C_t | Physiome (decay rates, intervals) | PSN history (temporal variance) |
| I | PSN (bus stats, cross-correlation) | PSN snapshot history |
| P | PSN (BDNF), PBM (learning rate), Growth rules | Epigenetic tag rate |
| Φₒ | PBM (prediction error), PSN (homeostatic stability) | PSN history (recovery tests) |
| M | DigitalMetabolism (global_energy, budgets) | PSN snapshot history |
| R | PSN history (perturbation tests), Physiome (degeneracy) | PBM recovery trajectory |

### 12.3 Update frequency

| Metric | Update interval | Reason |
|--------|----------------|--------|
| C (sub-dimensions) | Every 100 ticks | Changes slowly (growth, differentiation) |
| I | Every tick | Fast (signal dynamics) |
| P | Every 50 ticks | Moderate (learning, epigenetic changes) |
| Φₒ | Every 10 ticks | Moderate (coherence dynamics) |
| M | Every tick | Fast (energy changes every tick) |
| R | Every 50 ticks or on perturbation | Moderate (unless perturbed) |
| OCCap | Every 10 ticks | Composite |
| OCEff | Every 10 ticks | Composite |
| Ψ trajectory | Every 10 ticks (append) | History accumulation |

### 12.4 Autoregulation integration

The OCCap calculator feeds back into the organism:

```
if M(t) < M_crisis_threshold:
    activate_energy_conservation()           # reduce non-vital publish rates
if Φₒ(t) < Φₒ_crisis_threshold:
    activate_coherence_restoration()         # increase PBM learning rate, boost integration
if P(t) < P_min:
    activate_plasticity_boost()              # increase novelty sensitivity, BDNF secretion
if R(t) < R_min:
    activate_resilience_program()            # boost repair tissues, increase degeneracy
if OCEff(t) < OCEff_target:
    trigger_efficiency_optimisation()        # prune low-utility tissues, optimise policies
```

---

## 13. Verifiable Predictions

### 13.1 Prediction 1 — Integration vs complexity trade-off

> **H1**: For a fixed metabolic budget M, increasing structural complexity C_s beyond an optimal point (without increasing integration I) produces diminishing or negative returns in OCCap.

**Test in SPEACE**: Add tissues without increasing PSN bus bandwidth. Measure OCCap before and after. Prediction: OCCap plateaus then drops.

**Biological analogue**: Brain size vs encephalisation quotient across species.

### 13.2 Prediction 2 — Coherence as robustness predictor

> **H2**: Φₒ(t) predicts robustness to perturbation better than C(t) or I(t) alone.

**Test in SPEACE**: Apply identical perturbation (e.g., 50% energy drop) to two organisms with same |C| and I but different Φₒ. Measure recovery time and completeness. Prediction: higher Φₒ → faster, more complete recovery.

**AI analogue**: Compare two LLMs with same parameter count but different training stability.

### 13.3 Prediction 3 — Plasticity window

> **H3**: There exists an optimal plasticity window [P_min, P_max]. Below it, learning is too slow; above it, the organism becomes unstable (forgets too quickly, overfits to noise).

**Test in SPEACE**: Vary P(t) by modulating BDNF secretion rate. Measure learning speed vs stability at each level. Prediction: inverted-U curve.

**Biological analogue**: Critical periods in developmental neuroscience; U-shaped curve of plasticity vs age.

### 13.4 Prediction 4 — OCEff as evolutionary driver

> **H4**: Across multiple simulated generations (or developmental runs), OCEff converges to a higher value than OCCap alone.

**Test in SPEACE**: Run multiple SPEACE instances with different optimisation targets (OCCap only vs OCEff). Measure which achieves higher OCCap after equivalent resource expenditure. Prediction: OCEff-optimised instances achieve comparable OCCap at lower energy cost.

**Biological analogue**: Natural selection for metabolic efficiency; the expensive brain hypothesis (Aiello & Wheeler).

### 13.5 Prediction 5 — Ψ trajectory predicts developmental outcomes

> **H5**: Early-life Ψ trajectory (speed, exploration volume, stability) predicts mature OCCap better than static early-life C or I.

**Test in SPEACE**: Track Ψ from tick 0 to 1000. Correlate trajectory features (speed, phase portrait shape) with OCCap at tick 5000. Prediction: trajectory features explain >50% of variance.

**Biological analogue**: Early-life adversity and cognitive outcomes; developmental quotient vs later IQ.

### 13.6 Prediction 6 — Degeneracy buffers perturbation

> **H6**: Systems with higher degeneracy (more tissues performing overlapping functions) show higher R(t) without proportionally higher C_s.

**Test in SPEACE**: Design two Physiomes with same |C| but different degeneracy. Perturb both. Measure R(t). Prediction: higher degeneracy → higher R at same C.

---

## 14. Comparison Across Domains

### 14.1 Biological organisms

| Organism | Estimated relative C_s | Estimated relative I | Estimated Φₒ | Notes |
|----------|----------------------|---------------------|--------------|-------|
| C. elegans (302 neurons) | 0.01 | 0.1 | 0.3 | Minimal integration, simple coherence |
| Honeybee (~1M neurons) | 0.05 | 0.3 | 0.5 | Highly integrated colony-level |
| Mouse (~70M neurons) | 0.3 | 0.5 | 0.6 | Strong HPA-immunity integration |
| Human (~86B neurons) | 1.0 | 0.8 | 0.8 | Highest known Φₒ (conjecture) |
| Elephant (~257B neurons) | 1.5 | 0.6 | 0.6 | Larger C_s but lower integration (conjecture) |

*These are illustrative conjectures. T178 provides the framework to estimate them rigorously.*

### 14.2 Artificial systems

| System | Estimated relative C_s | Estimated relative I | Estimated Φₒ | Notes |
|--------|----------------------|---------------------|--------------|-------|
| GPT-4 (1.8T params) | 2.0 | 0.2 | 0.1 | Massive C_s, no physiological integration |
| AlphaFold | 0.1 | 0.3 | 0.2 | Domain-specific, moderate integration |
| SPEACE (current) | 0.2 | 0.5 | 0.4 | Moderate C_s, growing I, Φₒ improving |
| SPEACE + T177 + T175 | 0.5 | 0.7 | 0.6 | After full PSN + Enteroception integration |

### 14.3 Key insight

Conventional AI (LLMs, deep networks) scores high on C_s (especially C_i and C_f) but very low on I, Φₒ, M, and R. They lack:

- A physiological body with interdependent systems
- A metabolic constraint
- A resilience layer
- An endogenous coherence metric

T178 predicts that adding these dimensions to AI architectures — making them more *organism-like* — would improve their robustness, adaptability, and sample efficiency without necessarily increasing parameter count.

---

## 15. Open Questions and Future Directions

### 15.1 What is the relationship between Φₒ and Tononi's Φ?

- Conjecture: they correlate positively in small systems where both are computable.
- Prediction: Φₒ is a practical upper bound for Φ in large systems.
- Test: compute both in small PSN simulations.

### 15.2 Is there a universal upper bound on OCCap?

- Conjecture: OCCap is bounded by the organism's metabolic efficiency.
- OCCap_max = g(M_max, max_stable_complexity).
- This would imply a universal scaling law.

### 15.3 Can OCCap predict cross-domain transfer?

- Prediction: organisms with higher OCCap should transfer learning across domains better.
- Test: compare SPEACE instances with different Ω(t) on novel task suites.

### 15.4 How does OCEff change with scale?

- Conjecture: OCEff follows an inverted-U as C_s scales.
- Small organisms: low OCCap, moderate OCEff.
- Medium organisms (human range): high OCCap, high OCEff.
- Very large organisms (Internet-scale): very high C_s, very low OCEff.
- This would explain why evolution has not produced elephant-sized brains with human-like intelligence.

### 15.5 Dynamic reweighting

- Currently, OCCap sub-weights are fixed (α, β, γ, ε, w).
- Future: weights become functions of context (e.g., under threat, Φₒ weight increases).
- This would make OCCap itself adaptive.

### 15.6 Cross-modal validation

- Apply OCCap metrics to simplified simulations of biological organisms.
- Compare predictions with empirical data (e.g., stress recovery times, immune response variability).
- If T178 predictions align with known biology, confidence in the framework increases.

---

## Appendix A — Glossary

| Term | Definition |
|------|------------|
| Ω(t) | State field vector at time t |
| C | Complexity (5-dimensional: s, f, r, i, t) |
| I | Integration quality |
| P | Plasticity |
| Φₒ | Organismic coherence under perturbation |
| M | Metabolic capacity |
| R | Resilience |
| Ψ(t) | Trajectory of Ω through state space |
| OCCap | Organismic Cognitive Capacity (composite) |
| OCEff | Organismic Cognitive Efficiency (capacity / cost) |
| Degeneracy | Different components performing similar functions |
| Viability region | Subset of Ω where the organism can sustain itself |
| Cognitive region | Subset of V where effective reasoning occurs |

## Appendix B — Summary of formulae

| Quantity | Type | Formula |
|----------|------|---------|
| Ω(t) | Vector | {C, I, P, Φₒ, M, R} |
| C | Vector | [C_s, C_f, C_r, C_i, C_t] |
| |C| | Scalar | w·C (weighted sum) |
| I | Scalar [0,1] | α₁·bus_util + α₂·cross_corr + α₃·(1-delay) + α₄·occupancy + α₅·coverage |
| P | Scalar [0,1] | β₁·neuro + β₂·epigenetic + β₃·structural + β₄·functional + β₅·learning |
| Φₒ | Scalar [0,1] | γ₁·prediction + γ₂·recovery + γ₃·stability + γ₄·synchrony + γ₅·reallocation |
| M | Scalar [0,1] | global_energy / max_energy |
| R | Scalar [0,1] | ε₁·completeness + ε₂·(1-recovery_time) + ε₃·damage_resist + ε₄·degeneracy |
| OCCap | Scalar | w_C·|C| + w_I·I + w_P·P + w_Φ·Φₒ + w_M·M + w_R·R |
| OCEff | Scalar | OCCap / (energy + time_cost + damage_penalty) |
| Ψ(t) | Trajectory | [Ω(0), ..., Ω(t)] |
