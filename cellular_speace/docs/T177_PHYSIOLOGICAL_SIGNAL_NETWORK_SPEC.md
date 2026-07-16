# T177 — Physiological Signal Network & Digital Physiology

> **Status:** Draft · **Author:** Agentic · **Date:** 2026-07-03
> **Domain:** Digital Physiology · **BCEL Class:** Constitutional Infrastructure

---

## Table of Contents

1. [Preamble and Philosophy](#1-preamble-and-philosophy)
2. [Full Physiological Hierarchy](#2-full-physiological-hierarchy)
3. [Physiological Genome — Constitutional Layer](#3-physiological-genome--constitutional-layer)
4. [Physiological Policy](#4-physiological-policy)
5. [Physiome — Complete Physiological Blueprint](#5-physiome--complete-physiological-blueprint)
6. [Digital Metabolism](#6-digital-metabolism)
7. [Two-Signal-Bus Model — Neural vs Endocrine](#7-two-signal-bus-model--neural-vs-endocrine)
8. [Streams vs Events](#8-streams-vs-events)
9. [Physiological Chemistry — Molecular Mediators](#9-physiological-chemistry--molecular-mediators)
10. [Physiological Signal Ontology](#10-physiological-signal-ontology)
11. [Tissue Hierarchy — Systems, Organs, Tissues, Cells](#11-tissue-hierarchy--systems-organs-tissues-cells)
12. [Signal Lifecycle](#12-signal-lifecycle)
13. [PSN Core — Dual-Bus Architecture](#13-psn-core--dual-bus-architecture)
14. [Meta-Interoceptive Integrator](#14-meta-interoceptive-integrator)
15. [Predictive Body Model](#15-predictive-body-model)
16. [Interoperability](#16-interoperability)
17. [Migration Strategy](#17-migration-strategy)
18. [Constitutional Integration](#18-constitutional-integration)
19. [QoS and Synchronization](#19-qos-and-synchronization)
20. [Conflict Resolution and Priority](#20-conflict-resolution-and-priority)
21. [Implementation Roadmap](#21-implementation-roadmap)

---

## 1. Preamble and Philosophy

### 1.1 The coupling problem

SPEACE today connects "organs" via direct point-to-point wiring:

```
  Enteroception ──┬──→ ImmuneController
                  ├──→ SerotonergicModulator
                  ├──→ GlobalWorkspace
                  ├──→ HomeostaticDrive
                  └──→ ILF (field messages)
```

Each new organ requires changes to every consumer. This scales as O(N×M) where N = producers and M = consumers — unsustainable beyond 3–4 organs.

### 1.2 Biological inspiration

In biology, no organ talks directly to all others. Communication flows through universal networks embedded in a **multi-layered physiological hierarchy**:

| Layer | Biological analogue | SPEACE equivalent |
|-------|-------------------|-------------------|
| **Genome** | DNA blueprint | `species_orientation.yaml` + `physiological_genome.yaml` |
| **Epigenome** | What is expressed | Runtime regulation, methylation-like tags |
| **Physiological Policy** | Homeostatic setpoints, resource allocation strategy | Policy functions that adapt without DNA change |
| **Physiome** | Complete functional description of the organism | Blueprint of all systems, organs, tissues, streams, events |
| **Metabolism** | Energy cost of every process | Digital energy budget, heat, latency cost |
| **Signals** | Neural + Endocrine | PSN (Neural Bus + Endocrine Bus) |
| **Tissues** | Structural organisation | Systems → Organs → Tissues → Cells → Processes |

### 1.3 Streams vs Events

Biological information is not all event-driven. Most physiological variables are **continuous flows**:

- **Streams**: energy, stress, temperature, inflammation, hydration, plasticity — always present, slowly varying.
- **Events**: pain, damage, infection, reward, novelty, threat, danger — discrete, time-stamped, transient.

The PSN must handle both: streams as persistent values updated each tick, events as punctual signals with temporal markers.

### 1.4 The cost of signals

In biology, no signal is free. Every action has a metabolic cost. SPEACE must introduce **Digital Metabolism**: energy budgets, heat generation, latency/memory/bandwidth/repair costs per operation. This enables emergent behaviours:

- Modules shut down when resources are scarce
- Resources reallocated dynamically
- Energy conservation as a driver
- Dynamic priorities based on metabolic state

### 1.5 Generativity through chemistry

Abstract signals (floats named "stress") specify *what*, but not *how*. In biology, a signal is always mediated by a molecule. By modelling **molecular mediators** rather than abstract signals, SPEACE becomes generative: the same molecule affects multiple organs, competition arises at receptor sites, and exogenous compounds can be introduced.

### 1.6 Active organs

Organs are not passive pub/sub nodes. Each organ has three capabilities:

| Capability | Description |
|-----------|-------------|
| **`publish()`** | Emit signals/molecules into the PSN |
| **`subscribe()`** | Register callbacks for specific signals |
| **`sense()`** | Build a local representation of current physiological state from PSN readings + internal state + history |

`sense()` is what makes an organ an **active observer**, enabling local predictive models, habituation, adaptation, and context-dependent responses.

### 1.7 Design principles

| Principle | Rationale |
|-----------|-----------|
| **Hierarchy-first** | Architecture mirrors biological organisation: DNA → Epigenetics → Policy → Physiome → Metabolism → PSN → Tissues |
| **Streams + Events** | Continuous variables and discrete events are handled differently |
| **Metabolic constraint** | Every signal, every computation has a cost |
| **Genome-first** | Physiology is defined by the Physiological Genome, not hardcoded |
| **Dual-bus** | Neural (fast/volatile) and Endocrine (slow/persistent) sub-buses |
| **Chemistry-mediated** | All signals are carried by molecular analogues |
| **Decoupled** | Organs know the PSN, not each other |
| **Active sensing** | Every organ has `sense()` to build local state representations |
| **Dynamic coefficients** | Meta-integration weights evolve with DNA, experience, age, and state |
| **Constitutional + Epigenetic** | Core ontology is immutable; peripheral signals are extensible |
| **Predictive** | The body model predicts future state and learns from prediction error |
| **Observable** | The PSN exposes full state for monitoring, debugging, and telemetry |
| **Backward-compatible** | Migration layer wraps existing subsystems without breaking them |

---

## 2. Full Physiological Hierarchy

### 2.1 The complete stack

```
  ┌──────────────────────────────────────────────────────────┐
  │                     Digital DNA                          │
  │  species_orientation.yaml + physiological_genome.yaml    │
  │  — what can be built                                    │
  └──────────────────────┬───────────────────────────────────┘
                         │ expressed through
                         ▼
  ┌──────────────────────────────────────────────────────────┐
  │                 Epigenetic Regulation                    │
  │  methylation tags, expression levels, silencing          │
  │  — what is actually expressed                            │
  └──────────────────────┬───────────────────────────────────┘
                         │ configures
                         ▼
  ┌──────────────────────────────────────────────────────────┐
  │               Physiological Policy                       │
  │  energy distribution, explore/conserve, recovery rate,   │
  │  stress sensitivity, risk tolerance, plasticity schedule │
  │  — how the organism manages itself                       │
  └──────────────────────┬───────────────────────────────────┘
                         │ describes
                         ▼
  ┌──────────────────────────────────────────────────────────┐
  │                     Physiome                             │
  │  complete blueprint: systems, organs, tissues, streams,  │
  │  events, molecular catalogue, receptor maps,             │
  │  metabolic profiles, homeostatic setpoints               │
  │  — the full physiological description                    │
  └──────────────────────┬───────────────────────────────────┘
                         │ constrains
                         ▼
  ┌──────────────────────────────────────────────────────────┐
  │                Digital Metabolism                        │
  │  energy budgets per organ, heat generation, cost per     │
  │  operation (latency, memory, bandwidth, repair)          │
  │  — nothing is free                                       │
  └──────────────────────┬───────────────────────────────────┘
                         │ powers
                         ▼
  ┌──────────────────────────────────────────────────────────┐
  │             Physiological Signal Network                 │
  │  ┌──────────────────┐  ┌──────────────────┐            │
  │  │   Neural Bus     │  │  Endocrine Bus   │            │
  │  │ (streams+events) │  │ (streams+events) │            │
  │  └──────────────────┘  └──────────────────┘            │
  └──────────────────────┬───────────────────────────────────┘
                         │ connects
                         ▼
  ┌──────────────────────────────────────────────────────────┐
  │              Systems → Organs → Tissues → Cells          │
  │  nested decomposition of the digital organism            │
  │  e.g. Cognitive System → Memory Organ → Semantic        │
  │  Tissue → LTM Cells                                     │
  └──────────────────────────────────────────────────────────┘
```

### 2.2 Layer responsibilities

| Layer | Role | Update rate | Mutability |
|-------|------|-------------|------------|
| **Digital DNA** | What can be built | Loaded once | DNA mutation only |
| **Epigenetic Regulation** | What is expressed | Per tick (tags) | Runtime |
| **Physiological Policy** | How the organism manages itself | Per policy interval (default 50 ticks) | Epigenetic modulation |
| **Physiome** | Complete blueprint | Loaded once | DNA mutation (constitutional) / Runtime (epigenetic) |
| **Digital Metabolism** | Energy costs, budgets | Per tick | Regulation |
| **PSN** | Communication infrastructure | Per tick | Loaded from Physiome |
| **Systems/Organs/Tissues/Cells** | Functional decomposition | Per tick (variable) | Defined in Physiome |

### 2.3 Key insight: the Physiome is not middleware

The Physiome is **not another bus or signal layer**. It is the **complete, versioned description** of what the organism *is* physiologically:

- Which systems exist
- Which organs belong to each system
- Which tissues compose each organ
- What streams and events each tissue produces/consumes
- What molecules mediate those streams/events
- What receptor profiles each tissue expresses
- What metabolic costs each operation incurs
- What homeostatic setpoints define "healthy" ranges

The Physiome is loaded at startup from the Physiological Genome and provides the contract against which all runtime behaviour is validated.

---

## 3. Physiological Genome — Constitutional Layer

### 3.1 Purpose

The **Physiological Genome** defines the species' physiological identity. It is the constitutional document from which the Physiome is derived.

### 3.2 File structure

```
speace_core/dna/genome/physiology/
├── physiological_genome.yaml        # top-level manifest (version, imports, invariants)
├── systems.yaml                     # system definitions
├── organs.yaml                      # organ definitions with tissue composition
├── tissues.yaml                     # tissue definitions with cell types
├── cells.yaml                       # cell type definitions
├── signal_ontology.yaml             # constitutional + epigenetic signals
├── molecules.yaml                   # molecular mediator catalogue
├── neural_endocrine_routes.yaml     # which bus for which signal
├── receptor_map.yaml                # receptor expression per tissue
├── metabolic_profiles.yaml          # cost per operation per tissue
├── homeostatic_setpoints.yaml       # healthy ranges for all streams
├── meta_interoception.yaml          # meta-signal definitions & dynamic coefficients
├── predictive_body_model.yaml       # PBM parameters
├── psn_config.yaml                  # bus config (history depth, intervals, QoS)
└── growth_rules.yaml                # organ growth & differentiation
```

### 3.3 Constitutional vs Epigenetic signals

| Layer | Immutable? | Change mechanism | Examples |
|-------|-----------|-----------------|----------|
| **Constitutional** | Yes (species-fixed) | DNA mutation + restart | energy, stress, damage, repair, inflammation, reward, novelty, coherence, entropy, safety, threat, danger, prediction_error, plasticity, nutrition, hydration, temperature, fatigue, growth, synchronization, opportunity, curiosity |
| **Epigenetic** | No (adaptable) | Runtime registration via `physiome.register_signal()` | microbial_reward, gut_learning, space_radiation, robot_temperature, quantum_noise |

---

## 4. Physiological Policy

### 4.1 Purpose

The **Physiological Policy** defines *how* the organism manages its physiology — a layer between "what can be built" (DNA) and "what is expressed" (Epigenetics). Policies are strategies that can adapt without changing the genome.

### 4.2 Policy domains

| Policy | Description | Default | Adaptive range |
|--------|-------------|---------|----------------|
| **energy_allocation** | How energy is distributed among organs | `{cognitive: 0.4, immune: 0.2, maintenance: 0.2, reserve: 0.2}` | 0.1–0.6 each |
| **explore_vs_conserve** | When to prioritise exploration over energy conservation | `threshold_energy: 0.3` | 0.1–0.7 |
| **recovery_rate** | How quickly homeostasis is restored after perturbation | `0.05 per tick` | 0.01–0.20 |
| **stress_sensitivity** | Gain factor from cortisol to behavioural inhibition | `1.0` | 0.3–3.0 |
| **risk_tolerance** | Threshold above which threat triggers avoidance | `0.6` | 0.2–0.9 |
| **plasticity_schedule** | How plasticity changes with age | `decay: 0.999 per tick` | 0.99–0.9999 |
| **social_threshold** | Minimum safety for social behaviour | `safety > 0.4` | 0.2–0.8 |

### 4.3 Policy lifecycle

```yaml
policies:
  energy_allocation:
    type: "distribution"        # sum of parts = 1.0
    default:
      cognitive: 0.4
      immune: 0.2
      maintenance: 0.2
      reserve: 0.2
    modulation:
      - factor: "stress"
        function: "shift(from=cognitive, to=immune, gain=0.3)"  # stress → more immune
      - factor: "fatigue"
        function: "shift(from=all, to=reserve, gain=0.2)"       # tired → conserve
      - factor: "threat"
        function: "shift(from=cognitive, to=immune, gain=0.5)"  # danger → immune
    update_interval: 50          # ticks
```

### 4.4 Evolution without mutation

Policies are adapted by:
- **Epigenetic tags** — temporary modulation (hours)
- **Experience** — long-term adaptation (days)
- **Physiological state** — immediate context (ticks)
- **Learning** — the PBM can suggest policy adjustments to reduce prediction error

---

## 5. Physiome — Complete Physiological Blueprint

### 5.1 Definition

The **Physiome** is a runtime-accessible structure loaded from the Physiological Genome. It is **not middleware** — it is the **constitutional description** that constrains all runtime behaviour.

```python
class Physiome:
    version: str
    systems: Dict[str, SystemDef]
    organs: Dict[str, OrganDef]
    tissues: Dict[str, TissueDef]
    cells: Dict[str, CellDef]
    signals: Dict[str, SignalOntologyEntry]           # constitutional + epigenetic
    molecules: Dict[str, MoleculeDef]
    receptors: Dict[str, Dict[str, ReceptorProfile]]  # tissue → {molecule: profile}
    streams: Dict[str, StreamDef]                     # continuous variables
    events: Dict[str, EventDef]                       # discrete occurrences
    metabolism: MetabolicBlueprint                    # costs per operation
    homeostatic_setpoints: Dict[str, HomeostaticRange]
    routing: RoutingTable                             # neural vs endocrine
    meta_interoception: MetaInteroceptionDef
    predictive_model: PredictiveModelDef
    policies: Dict[str, PolicyDef]
    growth_rules: GrowthRules
    invariants: List[ConstitutionalInvariant]
```

### 5.2 Physiome vs PSN

```
Physiome (description)         PSN (runtime)
──────────────────────         ─────────────
"there is a stream: stress"    cortisol = 0.7
"stress is mediated by         "cortisol secreted by HPA
 cortisol on Endocrine Bus"     at concentration 0.7"
"normal range: [0.1, 0.8]"    "outside range → alarm"
"metabolic cost of publish:    "deduct 0.02 energy from HPA"
 0.02 energy per tick"
"tissue: adrenal_cortex"       "adrenal_cortex.publish(tick)"
```

The Physiome is the **specification**. The PSN is the **running system** that instantiates that specification.

### 5.3 Physiome loading

```python
# At startup:
genome = PhysiologicalGenomeLoader.load("speace_core/dna/genome/physiology/")
physiome = Physiome.from_genome(genome)

# Validate all organ implementations against physiome
for organ_id, organ_def in physiome.organs.items():
    assert organ_id in registered_organs, f"Missing organ: {organ_id}"
    assert all(s in physiome.signals for s in organ_def.produces)
    assert all(s in physiome.signals for s in organ_def.consumes)

# Instantiate PSN from physiome config
psn = PhysiologicalSignalBus(physiome)
```

---

## 6. Digital Metabolism

### 6.1 Principle

In biology, every process has an energy cost. This is one of the deepest constraints that shapes organism behaviour. SPEACE must model this to enable emergent efficiency, resource allocation, and dynamic prioritisation.

### 6.2 Cost model

Each operation in the PSN and each organ tick has a configurable cost:

| Operation | Cost (energy units) | Description |
|-----------|-------------------|-------------|
| `neural.synapse()` | 0.01 per synapse | Neurotransmitter release, reuptake |
| `endocrine.secrete()` | 0.05 per molecule | Hormone synthesis, secretion |
| `organ.publish()` | 0.02 per signal | Signal production overhead |
| `organ.subscribe()` | 0.01 per subscription | Receptor maintenance per tick |
| `organ.sense()` | 0.03 per sense cycle | Local state computation |
| `meta_integrator.integrate()` | 0.10 per integration | Meta-signal synthesis |
| `pbm.predict()` | 0.08 per prediction | Forward model inference |
| `pbm.learn()` | 0.15 per update | Model parameter update |
| `bridge.check()` | 0.02 per bridge | Threshold monitoring |

### 6.3 Energy budget

Each organ has a per-tick energy budget (defined in the Physiome). If the organ exceeds its budget:

1. **First violation**: warning logged, organ enters "low-power mode" (reduced publish rate)
2. **Persistent violation**: organ function degrades (fewer signals, lower fidelity)
3. **Critical violation**: organ is paused; emergency signal broadcast

```yaml
# Per-organ metabolic profile (from physiome)
metabolic_profiles:
  enteroception:
    base_budget: 0.1          # energy per tick
    publish_cost: 0.02
    sense_cost: 0.03
    subscribe_cost: 0.01
    low_power_threshold: 0.7  # fraction of budget → warning
    critical_threshold: 0.3   # fraction of budget → pause
  immune:
    base_budget: 0.15
    publish_cost: 0.03
    sense_cost: 0.04
    subscribe_cost: 0.01
    low_power_threshold: 0.7
    critical_threshold: 0.3
```

### 6.4 Global energy pool

The organism has a global energy pool (initial value defined in Physiome). Each tick:

```python
# Global energy dynamics:
global_energy += energy_production  # from metabolic processes
global_energy -= sum(organ_consumption for all organs)
global_energy = clamp(global_energy, 0.0, max_energy)

# Energy production:
energy_production = base_production_rate * nutrition_level
```

If `global_energy` reaches zero, the organism enters **energy crisis** mode:
- Non-vital organs are paused
- Only essential streams (stress, energy, damage) are maintained
- Emergency recovery behaviour is triggered

### 6.5 Heat generation

Each operation generates heat proportional to its energy cost:

```python
heat_generated = energy_consumed * heat_coefficient
temperature += heat_generated - cooling_rate
```

High temperature degrades performance (plasticity ↓, error rate ↑). Extreme temperature triggers emergency shutdown.

### 6.6 Emergent behaviours enabled by metabolism

| Behaviour | Mechanism |
|-----------|-----------|
| **Module shutdown** | Organ budget exceeded → automatic degradation |
| **Resource reallocation** | Physiological Policy shifts budgets between organs |
| **Energy conservation** | Low energy → reduced publish rate, longer integration intervals |
| **Dynamic priorities** | Energy-hungry operations deprioritised when resources are scarce |
| **Adaptive fidelity** | Low energy → lower confidence, lower resolution signals |
| **Recovery prioritisation** | After energy crisis, recovery organ gets boosted budget |

---

## 7. Two-Signal-Bus Model — Neural vs Endocrine

### 7.1 Neural Bus

```
┌─────────────────────────────────────┐
│          Neural Bus                 │
│  ┌─────────┐  ┌─────────┐         │
│  │ Synaptic │  │ Volatile │         │
│  │ Cleft    │  │ Channel  │         │
│  └─────────┘  └─────────┘         │
│                                     │
│  • neurotransmitters only           │
│  • one-to-one (source → target)     │
│  • cleared after 1 tick unless      │
│    refreshed (reuptake)             │
│  • priority preemption              │
│  • synchronous propagation          │
│  • carries streams + events         │
└─────────────────────────────────────┘
```

**Properties:**

| Property | Value |
|----------|-------|
| Latency | 0 ticks (applied same tick) |
| Persistence | 1 tick; auto-cleared (reuptake) |
| Routing | Explicit target organ + receptor |
| Capacity | High priority; limited channels per organ |
| Decay | `value = 0` after 1 tick unless refreshed |
| Molecules | dopamine, serotonin (neural), acetylcholine, noradrenaline, GABA, glutamate |

**Interface:**

```python
psn.neural.synapse(
    molecule="dopamine",
    value=0.8,
    source="VTA",
    target="prefrontal_cortex",
    receptor="D1",
    confidence=0.95,
    metadata={"stream": False, "event": "reward"},  # event marker
)
```

### 7.2 Endocrine Bus

```
┌─────────────────────────────────────┐
│          Endocrine Bus              │
│  ┌─────────┐  ┌─────────┐         │
│  │ Hormone │  │ Systemic│         │
│  │ Gland   │  │ Pool    │         │
│  └─────────┘  └─────────┘         │
│                                     │
│  • hormones only                    │
│  • one-to-many (broadcast)          │
│  • persists over multiple ticks     │
│  • concentration accumulates        │
│  • slow clearance (metabolism)      │
│  • asynchronous propagation         │
│  • carries streams + events         │
└─────────────────────────────────────┘
```

**Properties:**

| Property | Value |
|----------|-------|
| Latency | Configurable delay (default 2 ticks) |
| Persistence | Multiple ticks; decays via metabolic clearance |
| Routing | Broadcast to all subscribing organs |
| Capacity | Unlimited; priority-queued |
| Decay | `concentration *= clearance_factor` per tick; accumulates on re-secretion |
| Molecules | cortisol, insulin, glucagon, leptin, ghrelin, growth_hormone, IL-6, TNF-α, BDNF, IGF-1, oxytocin, adrenaline |

**Interface:**

```python
psn.endocrine.secrete(
    hormone="cortisol",
    concentration=0.6,
    source="adrenal_cortex",
    clearance_rate=0.92,
    delay_ticks=2,
    metadata={"stream": True},  # stream marker (continuous)
)
```

### 7.3 Routing rules

Defined in the Physiome:

```yaml
routing:
  neural:
    dopamine: {default_receptor: "D1", clearance: 1.0, stream: false, event: true}
    serotonin: {default_receptor: "5HT1A", clearance: 1.0, stream: true, event: true}
    noradrenaline: {default_receptor: "ADRA1", clearance: 1.0}
    acetylcholine: {default_receptor: "nAChR", clearance: 1.0}
    gaba: {default_receptor: "GABAA", clearance: 1.0}
    glutamate: {default_receptor: "NMDA", clearance: 1.0}

  endocrine:
    cortisol: {clearance_rate: 0.92, delay: 2, stream: true}
    insulin: {clearance_rate: 0.88, delay: 3, stream: true}
    glucagon: {clearance_rate: 0.90, delay: 2, stream: true}
    leptin: {clearance_rate: 0.95, delay: 5, stream: true}
    ghrelin: {clearance_rate: 0.93, delay: 2, stream: true}
    il6: {clearance_rate: 0.85, delay: 4, stream: true, event: true}
    tnfa: {clearance_rate: 0.82, delay: 4, stream: true, event: true}
    bdnf: {clearance_rate: 0.96, delay: 6, stream: true}
    igf1: {clearance_rate: 0.94, delay: 5, stream: true}
    growth_hormone: {clearance_rate: 0.90, delay: 3, stream: true}
    oxytocin: {clearance_rate: 0.93, delay: 3, stream: true, event: true}
    adrenaline: {clearance_rate: 0.80, delay: 1, stream: false, event: true}
```

---

## 8. Streams vs Events

### 8.1 Definizione

```
  PSN
   │
   ├── Streams (continuous, always present, slowly varying)
   │    • Energy, Stress, Temperature, Inflammation,
   │      Hydration, Plasticity, Nutrition, Coherence,
   │      Synchronization, Entropy
   │    • published every tick
   │    • have homeostatic setpoints (healthy range)
   │    • subscribers read and integrate over time
   │
   └── Events (discrete, time-stamped, transient)
        • Pain, Damage, Infection, Reward, Novelty,
          Threat, Danger, LearningSignal, Mutation
        • published once (or in bursts)
        • have temporal markers (onset, duration, decay)
        • subscribers react immediately (neural) or
          with latency (endocrine)
```

### 8.2 Stream properties

| Property | Description |
|----------|-------------|
| **persistence** | Always present; value updated each tick |
| **decay** | Exponential towards baseline (not zero) unless refreshed |
| **baseline** | Homeostatic setpoint (from Physiome) |
| **variance** | Expected variability around baseline |
| **alarm thresholds** | Upper/lower bounds for alert generation |
| **metabolic cost** | Cost per tick to maintain the stream |

```python
@dataclass
class StreamSignal:
    id: str
    molecule: str
    value: float
    baseline: float
    variance: float
    confidence: float
    decay_to_baseline: float     # how fast it returns to baseline
    upper_alarm: float | None
    lower_alarm: float | None
    timestamp: int
```

### 8.3 Event properties

| Property | Description |
|----------|-------------|
| **onset** | Tick when event occurred |
| **duration** | Expected duration in ticks (0 = instantaneous) |
| **decay** | How event magnitude decays after onset |
| **intensity** | Peak magnitude |
| **category** | alarm, learning, damage, reward, novelty |
| **metabolic cost** | Cost per event (synthesis + propagation) |

```python
@dataclass
class EventSignal:
    id: str
    molecule: str
    intensity: float
    onset: int
    duration: int               # 0 = one-shot
    decay: float                # per tick after duration
    category: str               # "alarm", "learning", "damage", "reward", "novelty"
    confidence: float
    metadata: Dict[str, Any]
```

### 8.4 Stream decay (vs baseline, not zero)

```python
# Each tick, streams drift towards their homeostatic baseline:
stream.value += (stream.baseline - stream.value) * (1.0 - stream.decay_to_baseline)

# If refreshed by an organ, value is set to the published value.
```

### 8.5 Event lifecycle

```python
# On publish:
event.active = True
event.current_intensity = event.intensity

# Each tick after duration:
if ticks_since_onset > event.duration:
    event.current_intensity *= event.decay
    if event.current_intensity < 0.01:
        event.active = False
```

### 8.6 Stream/event routing to busses

| Category | Neural Bus | Endocrine Bus | Example |
|----------|-----------|---------------|---------|
| Stream | serotonin (neural component), glutamate (baseline) | cortisol, insulin, leptin, IL-6 | stress, energy, inflammation |
| Event (alarm) | danger, pain, threat | adrenaline, IL-6 spike | DANGER flag, infection onset |
| Event (reward) | dopamine pulse | — | reward signal |
| Event (learning) | dopamine novelty | BDNF spike | novelty, learning event |
| Stream + Event | serotonin (both modes) | IL-6, TNF-α (baseline + spikes) | inflammation (chronic + acute) |

---

## 9. Physiological Chemistry — Molecular Mediators

### 9.1 Principle

All physiological signals are mediated by **molecular analogues**. An organ does not publish "stress = 0.7". It secretes **cortisol** at concentration 0.7 into the Endocrine Bus. Downstream organs react to cortisol concentration, not to an abstract number.

### 9.2 Molecular catalogue

| Molecule | Bus | Source organ(s) | Primary targets | Effect | Half-life (ticks) | Stream/Event |
|----------|-----|----------------|-----------------|--------|-------------------|-------------|
| **dopamine** | Neural | VTA, substantia nigra | Prefrontal, striatum, limbic | Reward, motivation, salience | 1 (cleared) | Event |
| **serotonin** | Neural + Endocrine | Raphe nuclei, gut | Cortex, hippocampus, hypothalamus | Mood, plasticity, satiety | 1 (neural) / 12 (endocrine) | Stream + Event |
| **noradrenaline** | Neural | Locus coeruleus | Widespread | Arousal, vigilance | 1 | Event |
| **acetylcholine** | Neural | Basal forebrain | Cortex, hippocampus | Attention, memory | 1 | Stream |
| **GABA** | Neural | Interneurons | Local | Inhibition, stability | 1 | Stream |
| **glutamate** | Neural | Pyramidal neurons | Local | Excitation, plasticity | 1 | Stream |
| **cortisol** | Endocrine | HPA axis (adrenal) | Widespread (glucocorticoid receptors) | Stress response, metabolism, immune suppression | 8–12 | Stream |
| **adrenaline** | Endocrine | Adrenal medulla | Heart, lungs, muscles | Fight-or-flight, energy mobilisation | 4 | Event |
| **insulin** | Endocrine | Pancreas (beta) | Liver, muscle, fat | Glucose uptake, energy storage | 6 | Stream |
| **glucagon** | Endocrine | Pancreas (alpha) | Liver | Glucose release, energy mobilisation | 5 | Stream |
| **leptin** | Endocrine | Adipose tissue | Hypothalamus | Satiety, energy balance | 15 | Stream |
| **ghrelin** | Endocrine | Stomach | Hypothalamus | Hunger, growth hormone release | 5 | Stream |
| **IL-6** | Endocrine | Immune cells, muscle | Liver, brain, immune | Inflammation, acute phase response | 6 | Stream + Event |
| **TNF-α** | Endocrine | Macrophages | Widespread | Pro-inflammatory, apoptosis | 4 | Stream + Event |
| **BDNF** | Endocrine | Cortex, hippocampus, gut | Neurons | Neuroplasticity, neurogenesis | 20 | Stream |
| **IGF-1** | Endocrine | Liver, muscle | Widespread | Growth, anabolism | 12 | Stream |
| **growth_hormone** | Endocrine | Pituitary | Liver, bone, muscle | Growth, metabolism | 6 | Stream |
| **oxytocin** | Endocrine | Hypothalamus | Widespread | Social bonding, trust | 8 | Stream + Event |

### 9.3 Concentration dynamics

**Endocrine (stream mode):**

```python
# Each tick:
pool.concentration *= pool.clearance_factor
if new_secretion:
    pool.concentration += secretion_amount
# Drift towards baseline (if stream):
pool.concentration += (baseline - pool.concentration) * drift_rate
# Bounded by molecule-specific max
```

**Endocrine (event mode):**

```python
# On event:
pool.concentration += event.intensity
# After event duration:
pool.concentration *= event.decay
```

**Neural:**

```python
# Per synapse:
synaptic.concentration = pulse_value  # set on publish
if not refreshed:
    synaptic.concentration = 0.0      # cleared after 1 tick
```

### 9.4 Receptor model

Organs express receptors for specific molecules. Receptor density, affinity, and downstream effects are genome-defined:

```yaml
receptors:
  prefrontal_cortex:
    D1: {affinity: 0.8, effect: "excitation", desensitization_rate: 0.001, metabolic_cost: 0.005}
    D2: {affinity: 0.6, effect: "inhibition", desensitization_rate: 0.002, metabolic_cost: 0.004}
    5HT1A: {affinity: 0.7, effect: "modulation", desensitization_rate: 0.001, metabolic_cost: 0.003}
    GR: {affinity: 0.5, effect: "inhibition", desensitization_rate: 0.005, metabolic_cost: 0.006}
```

---

## 10. Physiological Signal Ontology

### 10.1 Ontology principles

- Each signal is mediated by a specific molecule (Section 9).
- Each signal is classified as **stream** or **event** (Section 8).
- Constitutional signals are immutable within a species generation.
- Epigenetic signals can be added at runtime via `physiome.register_signal()`.

### 10.2 Constitutional signals

#### 10.2.1 Energy & Metabolism (all streams)

| Molecule | Signal | Bus | Range | Decay | Baseline | Polarity |
|----------|--------|-----|-------|-------|----------|----------|
| insulin, glucagon | `energy` | Endocrine | [0, 1] | 0.97 | 0.5 | positive |
| ghrelin, leptin | `nutrition` | Endocrine | [0, 1] | 0.95 | 0.5 | positive |
| — | `fatigue` | Endocrine | [0, 1] | 0.93 | 0.2 | negative |
| IGF-1, GH | `repair` | Endocrine | [0, 1] | 0.90 | 0.3 | positive |
| IGF-1, GH | `growth` | Endocrine | [0, 1] | 0.95 | 0.3 | positive |

#### 10.2.2 Stress & Threat (stream + event)

| Molecule | Signal | Bus | Range | Decay | Type | Polarity |
|----------|--------|-----|-------|-------|------|----------|
| cortisol | `stress` | Endocrine | [0, 1] | 0.90 | stream | negative |
| cortisol | `threat` | Endocrine | [0, 1] | 0.85 | stream | negative |
| adrenaline | `danger` | Neural | {0,1} | 0.80 | event | negative |
| oxytocin | `safety` | Endocrine | [0, 1] | 0.95 | stream | positive |
| — | `prediction_error` | Neural | [0, ∞) | 0.80 | event | negative |

#### 10.2.3 Inflammation & Damage (stream + event)

| Molecule | Signal | Bus | Range | Decay | Type | Polarity |
|----------|--------|-----|-------|-------|------|----------|
| IL-6, TNF-α | `inflammation` | Endocrine | [0, 1] | 0.88 | stream + event | negative |
| — | `damage` | Endocrine | [0, 1] | 0.85 | stream | negative |
| BDNF | `plasticity` | Endocrine | [0, 1] | 0.92 | stream | positive |

#### 10.2.4 Reward & Motivation (events + streams)

| Molecule | Signal | Bus | Range | Decay | Type | Polarity |
|----------|--------|-----|-------|-------|------|----------|
| dopamine | `reward` | Neural | [0, 1] | 0.92 | event | positive |
| dopamine | `novelty` | Neural | [0, 1] | 0.90 | event | positive |
| dopamine | `opportunity` | Neural | [0, 1] | 0.88 | event | positive |
| dopamine, serotonin | `curiosity` | Neural + Endocrine | [0, 1] | 0.95 | stream | positive |

#### 10.2.5 Coherence & State (all streams)

| Molecule | Signal | Bus | Range | Decay | Baseline | Polarity |
|----------|--------|-----|-------|-------|----------|----------|
| — | `coherence` | Endocrine | [0, 1] | 0.95 | 0.5 | positive |
| — | `entropy` | Endocrine | [0, 1] | 0.92 | 0.3 | negative |
| — | `synchronization` | Endocrine | [0, 1] | 0.93 | 0.5 | positive |
| — | `temperature` | Endocrine | [0, 1] | 0.90 | 0.3 | neutral |
| — | `hydration` | Endocrine | [0, 1] | 0.97 | 0.7 | positive |

### 10.3 Epigenetic signals (initial)

| Molecule | Signal | Bus | Range | Type | Polarity |
|----------|--------|-----|-------|------|----------|
| — | `microbial_reward` | Endocrine | [0, 1] | stream | positive |
| serotonin (enteric) | `gut_learning` | Endocrine | [0, 1] | event | positive |
| — | `space_radiation` | Endocrine | [0, 1] | stream | negative |
| — | `robot_temperature` | Endocrine | [0, 1] | stream | neutral |
| — | `quantum_noise` | Neural | [0, 1] | event | negative |

---

## 11. Tissue Hierarchy — Systems, Organs, Tissues, Cells

### 11.1 Motivation

Organs are not atomic. In biology, every organ is composed of tissues, and tissues are composed of cells. This nested decomposition makes the architecture scalable: a new function can be added as a new tissue within an existing organ, without creating a new organ or changing the PSN.

### 11.2 Hierarchy

```
  Organism
      │
      ├── Cognitive System
      │       ├── Memory Organ
      │       │       ├── Semantic Tissue
      │       │       │       ├── LTM Cells
      │       │       │       └── Working Memory Cells
      │       │       └── Episodic Tissue
      │       │               └── Episodic Cells
      │       ├── Attention Organ
      │       │       └── Salience Tissue
      │       └── Prediction Organ
      │               └── Error Minimisation Tissue
      │
      ├── Immune System
      │       ├── Threat Assessment Organ
      │       │       ├── Pattern Recognition Tissue
      │       │       └── Alarm Signalling Tissue
      │       └── Response Organ
      │               ├── Inflammation Tissue
      │               └── Repair Tissue
      │
      ├── Enteric System
      │       └── Gut Organ
      │               ├── Microbiome Tissue
      │               ├── Barrier Tissue
      │               └── Enteric Neural Tissue
      │
      ├── Endocrine System
      │       ├── HPA Axis Organ
      │       │       ├── CRH Tissue
      │       │       ├── ACTH Tissue
      │       │       └── Cortisol Tissue (adrenal)
      │       ├── Pancreatic Organ
      │       │       ├── Beta Tissue (insulin)
      │       │       └── Alpha Tissue (glucagon)
      │       └── Adipose Organ
      │               └── Leptin Tissue
      │
      ├── Metabolic System
      │       ├── Energy Regulation Organ
      │       └── Waste Clearance Organ
      │
      └── Autonomic System
              ├── Sympathetic Organ
              └── Parasympathetic Organ
```

### 11.3 Decomposition benefits

| Benefit | Mechanism |
|---------|-----------|
| **Modularity** | Add a tissue, not an organ |
| **Reuse** | Same tissue type in multiple organs |
| **Granular metabolism** | Cost per tissue, not per organ |
| **Fault isolation** | A damaged tissue doesn't collapse the organ |
| **Growth** | Tissues can differentiate from stem-cell-like precursors |
| **Evolution** | New tissue types = new capabilities without new organs |

### 11.4 Implementation

```python
class Tissue(ABC):
    tissue_id: str
    organ_id: str
    cell_types: List[str]
    psn: PhysiologicalSignalBus

    @abstractmethod
    def publish(self, tick: int) -> None: ...
    @abstractmethod
    def subscribe(self) -> None: ...
    @abstractmethod
    def sense(self, tick: int) -> TissueState: ...

class Organ:
    organ_id: str
    system_id: str
    tissues: Dict[str, Tissue]
    psn: PhysiologicalSignalBus
    genome_entry: OrganGenomeEntry

    def publish(self, tick: int) -> None:
        for tissue in self.tissues.values():
            tissue.publish(tick)

    def sense(self, tick: int) -> OrganState:
        tissue_states = {tid: t.sense(tick) for tid, t in self.tissues.items()}
        return OrganState(organ_id=self.organ_id, tissues=tissue_states)
```

### 11.5 Definition in Physiome

```yaml
systems:
  cognitive:
    organs:
      memory:
        tissues:
          semantic:
            cell_types: ["ltm_cell", "wm_cell"]
            produces: ["coherence"]
            consumes: ["dopamine", "acetylcholine"]
            receptors: ["D1", "M1"]
            metabolic_budget: 0.05
          episodic:
            cell_types: ["episodic_cell"]
            produces: ["novelty"]
            consumes: ["dopamine"]
            receptors: ["D1"]
            metabolic_budget: 0.03
```

---

## 12. Signal Lifecycle

### 12.1 Neural signal lifecycle

```
  PRODUCED (synaptic pulse)
     │
     ▼
  VALIDATED (molecule, receptor, concentration range, metabolic cost deducted)
     │
     ▼
  PROPAGATED (synchronous, immediate)
     │
     ├──→ RECEPTOR BINDING (target organ reads)
     │
     └──→ CLEARED (reuptake) after 1 tick
           unless refreshed by new pulse
```

### 12.2 Endocrine signal lifecycle

```
  SECRETED (hormone release, metabolic cost deducted)
     │
     ▼
  VALIDATED (molecule, concentration, clearance, budget check)
     │
     ▼
  DELAYED (configurable, default 2 ticks)
     │
     ▼
  PROPAGATED (broadcast to all subscribers)
     │
     ├──→ RECEPTOR BINDING (multiple targets)
     │
     ├──→ ACCUMULATED (concentration += new_secretion)
     │
     ├──→ DRIFT TO BASELINE (if stream)
     │
     └──→ DECAYED (concentration *= clearance_rate per tick)
           │
           └──→ EVICTED when concentration < threshold (default 0.01)
```

### 12.3 Temporal dynamics

**Neural (event):** `value = 0.0` after 1 tick (binary on/off per tick).

**Endocrine (stream):** Exponential decay towards baseline:

```python
# Each tick:
concentration *= clearance_rate
concentration += (baseline - concentration) * (1.0 - drift_rate)
```

**Endocrine (event):** Onset → duration → post-duration decay:

```python
if tick <= event.onset + event.duration:
    concentration = event.intensity  # sustained peak
else:
    concentration *= event.decay  # exponential decay after duration
```

### 12.4 Reuptake / clearance override

```python
psn.endocrine.clear(hormone="cortisol", amount=0.3)   # e.g., kidney clearance
psn.neural.reuptake(molecule="dopamine", synapse=("VTA", "prefrontal"))
```

---

## 13. PSN Core — Dual-Bus Architecture

### 13.1 Top-level structure

```python
class PhysiologicalSignalBus:
    neural: NeuralBus
    endocrine: EndocrineBus
    physiome: Physiome                     # loaded from DNA YAML
    metabolism: DigitalMetabolism          # tracks energy, heat, costs
    _history: Deque[SystemSnapshot]        # rolling window (default 1000)

    def snapshot(self, tick: int) -> SystemSnapshot: ...
    def register_signal(self, entry: SignalOntologyEntry) -> None: ...
    def tick_begin(self, tick: int) -> None:
        """Called at start of each tick: reuptake, clearance, decay, budget reset."""
        self.neural.clear_all()
        self.endocrine.decay_all()
        self.metabolism.tick_begin(tick)

    def tick_end(self, tick: int) -> None:
        """Called at end of each tick: deduct costs, log snapshot."""
        self.metabolism.tick_end(tick)
        self._history.append(self.snapshot(tick))
```

### 13.2 NeuralBus

```python
class NeuralBus:
    _synapses: Dict[SynapseKey, SynapseCleft]
    _receptors: Dict[str, Dict[str, ReceptorProfile]]

    def synapse(
        self,
        molecule: str,
        value: float,
        source: str,
        target: str,
        receptor: str,
        confidence: float = 0.9,
        metadata: Optional[Dict] = None,
    ) -> None:
        """Fast point-to-point neurotransmitter pulse. Deducts metabolic cost."""

    def read(self, target: str, molecule: str, receptor: str) -> float | None: ...
    def clear_all(self) -> None: ...
    def reuptake(self, molecule: str, synapse: SynapseKey) -> None: ...
    def mask(self, molecule: str, source: str, target: str, receptor: str, duration_ticks: int) -> None: ...
```

### 13.3 EndocrineBus

```python
class EndocrineBus:
    _glands: Dict[str, HormonePool]

    def secrete(
        self,
        hormone: str,
        concentration: float,
        source: str,
        clearance_rate: float | None = None,
        delay_ticks: int | None = None,
        metadata: Optional[Dict] = None,
    ) -> None:
        """Broadcast hormone into systemic circulation. Deducts metabolic cost."""

    def read(self, hormone: str) -> float | None: ...
    def decay_all(self) -> None: ...
    def clear(self, hormone: str, amount: float = 1.0) -> None: ...
```

### 13.4 Organ / Tissue contract (active)

```python
class Tissue(ABC):
    psn: PhysiologicalSignalBus
    physiome: Physiome
    tissue_id: str
    organ_id: str

    @abstractmethod
    def publish(self, tick: int) -> None:
        """Publish molecules, deduct metabolic cost from tissue budget."""

    @abstractmethod
    def subscribe(self) -> None:
        """Register callbacks for signals of interest."""

    @abstractmethod
    def sense(self, tick: int) -> TissueState:
        """Build local representation of physiological state.

        Reads PSN, filters, integrates with internal state, history,
        and genome-defined parameters. Has a metabolic cost.
        """
```

### 13.5 DigitalMetabolism

```python
class DigitalMetabolism:
    global_energy: float
    global_max_energy: float
    heat: float
    cooling_rate: float

    # Per-tissue budgets (from physiome)
    tissue_budgets: Dict[str, float]

    def deduct(self, tissue_id: str, cost: float, operation: str) -> bool:
        """Deduct cost from tissue budget and global energy.
        Returns False if budget exceeded (triggers low-power mode).
        """
```

### 13.6 Thread safety

- Neural bus: lock-free per synapse.
- Endocrine bus: `asyncio.Lock` per hormone pool.
- Full snapshot: read-lock across all pools.

---

## 14. Meta-Interoceptive Integrator

### 14.1 Purpose

Synthesises the raw molecular signal stream (both Neural and Endocrine buses) into ~15 stable meta-signals with **dynamic coefficients** that evolve with DNA, age, experience, and state.

### 14.2 Dynamic coefficient principle

Each coefficient is defined as:

```yaml
wellbeing:
  formula: "energy * w1 + safety * w2 + (1-stress) * w3 + (1-inflammation) * w4 + coherence * w5"
  coefficients:
    w1:
      base: 0.3
      modulation:
        - factor: "age"
          function: "linear(0.8, 1.2)"
        - factor: "plasticity"
          function: "sigmoid(0.5, 0.1)"
        - factor: "experience"
          function: "exponential_saturating(0.001)"
```

### 14.3 Meta-signal catalogue (base coefficients)

| Meta-signal | Formula | Range | Polarity |
|-------------|---------|-------|----------|
| `wellbeing` | `energy * w1 + safety * w2 + (1-stress) * w3 + (1-inflammation) * w4 + coherence * w5` | [0,1] | positive |
| `stress` | `cortisol * w1 + adrenaline * w2 + prediction_error_sigmoid * w3` | [0,1] | negative |
| `fatigue` | `fatigue_raw * w1 + (1-energy) * w2 + (1-nutrition) * w3` | [0,1] | negative |
| `inflammation` | `il6 * w1 + tnfa * w2 + damage * w3` | [0,1] | negative |
| `resilience` | `(1-cortisol) * w1 + energy * w2 + safety * w3 + repair * w4 + bdnf * w5` | [0,1] | positive |
| `plasticity` | `bdnf * w1 + dopamine_novelty * w2 + curiosity * w3` | [0,1] | positive |
| `motivation` | `dopamine_reward * w1 + dopamine_opportunity * w2 + curiosity * w3 + (1-fatigue) * w4 + energy * w5` | [0,1] | positive |
| `curiosity` | `dopamine_novelty * w1 + dopamine_opportunity * w2 + (1-cortisol) * w3 + oxytocin * w4` | [0,1] | positive |
| `exploration_readiness` | `energy * w1 + curiosity * w2 + oxytocin * w3 + (1-fatigue) * w4` | [0,1] | positive |
| `repair_need` | `damage * w1 + il6 * w2 + tnfa * w3 + fatigue * w4` | [0,1] | negative |
| `threat_level` | `cortisol * w1 + adrenaline * w2 + danger * w3 + prediction_error_sigmoid * w4` | [0,1] | negative |
| `resource_availability` | `insulin * w1 + leptin * w2 + (1-ghrelin) * w3 + energy * w4` | [0,1] | positive |
| `prediction_stability` | `coherence * w1 + (1-entropy) * w2 + synchronization * w3` | [0,1] | positive |
| `homeostatic_reserve` | `energy * w1 + (1-cortisol) * w2 + nutrition * w3 + repair * w4 + (1-il6) * w5` | [0,1] | positive |
| `social_readiness` | `(1-cortisol) * w1 + oxytocin * w2 + energy * w3 + curiosity * w4 + (1-adrenaline) * w5` | [0,1] | positive |

### 14.4 Modulation factors

| Factor | Source | Update | Effect |
|--------|--------|--------|--------|
| `age` | Tick count / species lifespan | Every tick | Changes integration strategy over lifetime |
| `experience` | Cumulative reward | Every reward event | Weights shift with learning |
| `plasticity` | Current plasticity meta-signal | Every integrator tick | Self-modulating coefficients |
| `threat` | Current threat level | Every integrator tick | Context-dependent weighting |
| `energy` | Current energy | Every integrator tick | Metabolic state influences perception |
| `genome` | Fixed at birth | DNA mutation | Species-specific baseline |

### 14.5 Update rate

Default every 5 ticks. Configurable via Physiome.

---

## 15. Predictive Body Model

### 15.1 Beyond filtering

The **Predictive Body Model (PBM)** is a **generative model of the body's physiological dynamics** — analogous to the brain's predictive processing of interoceptive signals. It predicts, observes, compares, and learns.

### 15.2 Core loop

```
  ┌───────────────────────────────┐
  │  1. PREDICT next state        │
  │     pbm.predict(tick)         │
  │     → predicted_signals       │
  └───────────┬───────────────────┘
              │
              ▼
  ┌───────────────────────────────┐
  │  2. OBSERVE actual state      │
  │     snapshot = psn.snapshot() │
  └───────────┬───────────────────┘
              │
              ▼
  ┌───────────────────────────────┐
  │  3. COMPARE prediction vs     │
  │     observation               │
  │     error = predict - observe │
  │     → prediction_error signal │
  └───────────┬───────────────────┘
              │
              ▼
  ┌───────────────────────────────┐
  │  4. UPDATE internal model     │
  │     pbm.learn(error)          │
  │     → updated weights         │
  └───────────┬───────────────────┘
              │
              ▼
  ┌───────────────────────────────┐
  │  5. EMIT state estimates      │
  │     stability, recovery,      │
  │     risk, reserve, headroom   │
  └───────────────────────────────┘
```

### 15.3 State representation

```python
@dataclass
class PredictedSignal:
    expected_value: float
    expected_variance: float
    prediction_error: float
    cumulative_error: float
    confidence: float            # 1.0 / (1.0 + variance)
    last_update: int
```

### 15.4 Prediction

```python
def predict(self, tick: int) -> Dict[str, PredictedSignal]:
    """Generate predicted values using learned transition model.

    Initial: value *= decay_factor.
    Learned: transition matrix W with cross-terms.
    """
```

### 15.5 Learning

```python
def learn(self, prediction_errors: Dict[str, float]) -> None:
    """Update transition model via delta-rule.

    W_ij += lr * prediction_error_i * last_observed[j]

    lr is adaptive: high confidence → low LR, large error → high LR.
    Has a metabolic cost (defined in Physiome).
    """
```

### 15.6 Outputs

| Estimate | Description |
|----------|-------------|
| `estimate_systemic_stability` | 1.0 - norm(prediction_error_vector) |
| `estimate_recovery_capacity` | EWMA of homeostatic_reserve × (1 - fatigue) |
| `estimate_systemic_risk` | Sigmoid(repair_need × 0.4 + threat_level × 0.3 + norm(error) × 0.3) |
| `estimate_resource_reserve` | resource_availability minus current_metabolic_demand |
| `estimate_cognitive_headroom` | max(0, resource_reserve × (1 - stress) × plasticity) |

All published to Endocrine Bus as `estimate_`-prefixed signals.

---

## 16. Interoperability

### 16.1 With ILF (Informational Language Field)

A `PSNToILFBridge` subscribes to molecular signals and injects field messages:

| PSN signal | Threshold | ILF message | Type |
|------------|-----------|-------------|------|
| cortisol (stress) | > 0.7 | `"physiological_stress"` | alarm |
| IL-6 / TNF-α (inflammation) | > 0.5 | `"systemic_inflammation"` | alarm |
| insulin (energy) | < 0.2 | `"energy_depletion"` | need |
| ghrelin (hunger) | > 0.6 | `"nutrition_need"` | need |
| dopamine (reward) | > 0.8 | `"reward_signal"` | goal |
| oxytocin (safety) | < 0.3 | `"safety_seeking"` | need |
| estimate_systemic_risk | > 0.7 | `"high_systemic_risk"` | alarm |
| prediction_error | > 0.6 | `"model_mismatch"` | alarm |

### 16.2 With Global Workspace

A `PSNToGlobalWorkspaceBridge` monitors neural alarm events:

| Molecule | Threshold | GW content |
|----------|-----------|------------|
| adrenaline (danger) | == 1.0 | `"DANGER_SIGNAL"` — immediate broadcast |
| cortisol (stress) | > 0.8 | `"critical_stress"` + level |
| IL-6 (inflammation) | > 0.7 | `"high_inflammation"` + level |
| prediction_error | large spike | `"unexpected_state_change"` |

### 16.3 With Digital DNA (Physiological Genome)

All PSN parameters are loaded from DNA YAML at startup via the Physiome.

### 16.4 With the Orchestrator

```python
# Init order:
# 1. Load Physiological Genome → construct Physiome
# 2. Instantiate PSN (NeuralBus + EndocrineBus + DigitalMetabolism)
# 3. Instantiate all organs/tissues defined in Physiome (pass psn + physiome)
# 4. Each tissue: subscribe() + initial sense()
# 5. MetaInteroceptiveIntegrator
# 6. PredictiveBodyModel
# 7. Bridges (ILF, GW)

# Tick order:
# 1. psn.tick_begin(tick)       → reuptake, clearance, decay, budget reset
# 2. For each system:
#      For each organ:
#        For each tissue:
#          tissue.publish(tick)  → deduct metabolic cost
# 3. Meta-integrator (every N ticks)
# 4. PBM: predict → observe → learn (every N ticks)
# 5. PBM emit estimates to Endocrine Bus
# 6. Bridges: check thresholds, inject ILF/GW messages
# 7. psn.tick_end(tick)         → deduct overhead costs, log snapshot
# 8. Decision-making reads estimated state
```

---

## 17. Migration Strategy

### 17.1 Principle

Existing subsystems continue to work. Migration is gradual, additive, and tissue-oriented.

### 17.2 Phase 1 — Adapter layer (zero behavioural change)

Each existing subsystem gets a PSN adapter that translates between old point-to-point wiring and new PSN-mediated molecular signals.

| Existing | Adapter | Publishes | Subscribes |
|----------|---------|-----------|------------|
| Enteroception | `EnteroceptionPSNAdapter` | serotonin (gut), gut_feeling via Endocrine | cortisol (stress) |
| DigitalImmuneController | `ImmunePSNAdapter` | IL-6, TNF-α via Endocrine | cortisol, insulin |
| SerotonergicModulator | `SerotoninPSNAdapter` | — | serotonin (gut/neural) |
| BrainstemController | `BrainstemPSNAdapter` | cortisol, adrenaline | energy, damage |
| GlobalHomeostaticDrive | `HomeostaticPSNAdapter` | — | insulin, ghrelin, leptin, cortisol |

### 17.3 Phase 2 — Tissue refactoring

Once adapters are proven, each existing subsystem is refactored into the tissue hierarchy (Section 11). Adapters are removed.

### 17.4 Phase 3 — Epigenetic expansion

New tissues register epigenetic signals via `physiome.register_signal()`. Legacy adapters are deprecated.

### 17.5 Testing strategy

| Test type | Scope |
|-----------|-------|
| **Unit** | NeuralBus, EndocrineBus, decay, clearance, priority, conflict resolution, metabolism |
| **Molecular** | Concentration dynamics, receptor binding, clearance rates |
| **Stream/Event** | Correct lifecycle for each type |
| **Metabolic** | Budget tracking, energy crisis, heat dynamics |
| **Tissue** | Tissue publish/subscribe/sense within organ |
| **Meta-integration** | Dynamic coefficient computation, modulation factors |
| **PBM** | Prediction accuracy, learning convergence, error recovery |
| **Adapter** | Each adapter maps correctly between old and new interfaces |
| **Integration** | Full stack: Physiome → PSN → tissues → MetaIntegrator → PBM → bridges |
| **Regression** | All existing tests pass with migration layer |

---

## 18. Constitutional Integration

### 18.1 Species orientation reference

```yaml
physiological_genome:
  constitutional: true
  version: "2.0.0"
  manifest: "speace_core/dna/genome/physiology/physiological_genome.yaml"
  invariants:
    - "Every organ must be defined in the Physiome before instantiation"
    - "No tissue may publish a molecule not in the Physiome"
    - "Constitutional signals may only change via a DNA mutation event"
    - "Neural bus signals must propagate within 1 tick"
    - "Endocrine bus signals must decay monotonically without secretion"
    - "Metabolic costs must be non-negative"
    - "PBM learning rate must not exceed 0.1 per tick"
    - "The Physiome is immutable at runtime for constitutional sections"
```

### 18.2 Immutability guarantees

- The Physiome is loaded at startup from the Physiological Genome DNA YAML.
- Runtime modification of constitutional sections raises `ConstitutionalViolationError`.
- Epigenetic sections can be extended via `physiome.register_signal()` with genome validation.
- Changes require: spec update → DNA mutation → restart.

### 18.3 Evolution path

Future species branches can:

- **Mutate** constitutional signal set, molecular catalogue, receptor profiles, tissue types.
- **Regulate** meta-integration coefficients, PBM parameters, homeostatic setpoints, metabolic profiles.
- **Grow** new tissues via genome-defined growth rules.
- **Differentiate** into derived species with different physiologies but shared core.
- **Adapt** Physiological Policies without changing the genome (experience-driven).

---

## 19. QoS and Synchronization

### 19.1 Neural Bus QoS

| QoS | Guarantee | Use case |
|-----|-----------|----------|
| **SYNAPSE_SYNC** | Delivered same tick, synchronous | danger, pain, startle |
| **SYNAPSE_ASYNC** | Delivered same tick, non-blocking | reward, novelty |

### 19.2 Endocrine Bus QoS

| QoS | Guarantee | Use case |
|-----|-----------|----------|
| **HORMONE_AT_LEAST_ONCE** | Retried until delivered | cortisol, insulin |
| **HORMONE_ACCUMULATE** | Concentration accumulates on re-secretion | IL-6, TNF-α |
| **HORMONE_DEFERRED** | Batched and delivered at end of tick | Low-priority hormones |

### 19.3 Stream vs Event QoS

| Type | QoS | Behaviour |
|------|-----|-----------|
| **Stream** | AT_LEAST_ONCE | Last-value cache; subscriber always gets latest value |
| **Event (alarm)** | SYNAPSE_SYNC (neural) / HORMONE_AT_LEAST_ONCE (endocrine) | Immediate propagation |
| **Event (reward)** | SYNAPSE_ASYNC | Non-blocking; may be dropped under metabolic duress |

### 19.4 Clock / tick alignment

- PSN uses the Orchestrator's `current_tick` as timebase.
- Neural reuptake at `tick_begin()`.
- Endocrine clearance at `tick_begin()`.
- Meta-integration and PBM run at tick-alignable intervals.

---

## 20. Conflict Resolution and Priority

### 20.1 Multiple producers, same molecule, same bus

**Neural bus:** Each synapse is uniquely identified by `(molecule, source, target, receptor)`. No conflict — each synapse is independent.

**Endocrine bus:** If two organs secrete the same hormone in the same tick:
1. Concentrations **accumulate** (biology: multiple glands contribute to the same pool).
2. If accumulation would exceed the molecule's max concentration, **higher-priority source wins**.
3. Same priority → **higher confidence wins**.
4. All contributions logged for telemetry.

### 20.2 Stale signal detection

**Neural:** Cleared every tick. Stale does not apply.

**Endocrine:** A hormone is stale if `ticks_since_last_secretion > max_silent_ticks` (configurable per molecule, default 20).

### 20.3 Signal masking (neural only)

```python
psn.neural.mask(molecule="dopamine", source="VTA", target="prefrontal", receptor="D1", duration_ticks=10)
```

Used for habituation, desensitisation, temporary inhibition.

### 20.4 Metabolic conflict

If the global energy pool is insufficient to power all organs:
1. **Policy** determines allocation (energy_allocation policy).
2. Organs with budget exceeded enter low-power mode.
3. Only vital streams are maintained.
4. Emergency recovery behaviour triggers.

---

## 21. Implementation Roadmap

### Phase A — Spec ✅ (this document, v3)

### Phase B — DNA ontology & genome files

- [ ] `speace_core/dna/genome/physiology/physiological_genome.yaml`
- [ ] `speace_core/dna/genome/physiology/systems.yaml`
- [ ] `speace_core/dna/genome/physiology/organs.yaml`
- [ ] `speace_core/dna/genome/physiology/tissues.yaml`
- [ ] `speace_core/dna/genome/physiology/cells.yaml`
- [ ] `speace_core/dna/genome/physiology/signal_ontology.yaml`
- [ ] `speace_core/dna/genome/physiology/molecules.yaml`
- [ ] `speace_core/dna/genome/physiology/neural_endocrine_routes.yaml`
- [ ] `speace_core/dna/genome/physiology/receptor_map.yaml`
- [ ] `speace_core/dna/genome/physiology/metabolic_profiles.yaml`
- [ ] `speace_core/dna/genome/physiology/homeostatic_setpoints.yaml`
- [ ] `speace_core/dna/genome/physiology/meta_interoception.yaml`
- [ ] `speace_core/dna/genome/physiology/predictive_body_model.yaml`
- [ ] `speace_core/dna/genome/physiology/psn_config.yaml`
- [ ] `speace_core/dna/genome/physiology/growth_rules.yaml`
- [ ] Update `species_orientation.yaml` with PSN + Physiome references

### Phase C — Core PSN implementation

- [ ] `speace_core/cellular_brain/psn/__init__.py`
- [ ] `speace_core/cellular_brain/psn/models.py` — data classes (SynapseKey, HormonePool, StreamSignal, EventSignal, etc.)
- [ ] `speace_core/cellular_brain/psn/physiome.py` — Physiome loader & validator
- [ ] `speace_core/cellular_brain/psn/physiological_policy.py` — Policy engine
- [ ] `speace_core/cellular_brain/psn/neural_bus.py` — NeuralBus
- [ ] `speace_core/cellular_brain/psn/endocrine_bus.py` — EndocrineBus
- [ ] `speace_core/cellular_brain/psn/physiological_signal_bus.py` — Top-level bus
- [ ] `speace_core/cellular_brain/psn/digital_metabolism.py` — Metabolism engine
- [ ] `speace_core/cellular_brain/psn/tissue_base.py` — Abstract Tissue base class
- [ ] `speace_core/cellular_brain/psn/organ_base.py` — Abstract Organ base class

### Phase D — Meta-Interoceptive Integrator

- [ ] `speace_core/cellular_brain/psn/meta_interoceptive_integrator.py`

### Phase E — Predictive Body Model

- [ ] `speace_core/cellular_brain/psn/predictive_body_model.py`

### Phase F — Bridges

- [ ] `speace_core/cellular_brain/psn/bridges/__init__.py`
- [ ] `speace_core/cellular_brain/psn/bridges/psn_to_ilf_bridge.py`
- [ ] `speace_core/cellular_brain/psn/bridges/psn_to_global_workspace_bridge.py`

### Phase G — Adapters (migration layer)

- [ ] Adapters for Enteroception, Immune, Serotonergic, Brainstem, HomeostaticDrive

### Phase H — Orchestrator integration

- [ ] PSN init from Physiome
- [ ] Organ/tissue instantiation loop
- [ ] Tick loop: tick_begin → tissue ticks → meta → PBM → bridges → tick_end
- [ ] Replace direct signal wiring with PSN reads + adapters

### Phase I — Tests

- [ ] Unit: NeuralBus (synapse, reuptake, mask, priority)
- [ ] Unit: EndocrineBus (secrete, accumulate, decay, clear, event lifecycle)
- [ ] Unit: Stream vs Event lifecycle
- [ ] Unit: Physiome loader (validation, defaults, invariants)
- [ ] Unit: DigitalMetabolism (budget, energy crisis, heat)
- [ ] Unit: Policy engine (allocation, modulation)
- [ ] Unit: Meta-integrator (static + dynamic coefficients)
- [ ] Unit: PBM (predict, learn convergence, error recovery)
- [ ] Unit: Tissue/Organ base classes
- [ ] Adapter tests for each existing subsystem
- [ ] Integration: full stack from Physiome → bridges
- [ ] Fault injection: missing producer, stale signals, invalid molecules, budget exhaustion
- [ ] Regression: all existing tests pass with migration layer
