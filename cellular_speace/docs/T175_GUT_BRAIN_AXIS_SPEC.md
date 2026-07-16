# T175 — Digital Gut-Brain Axis (Enteroception)

| Field | Value |
|-------|-------|
| **Status** | Draft |
| **Author** | AI Agent |
| **Date** | 2026-07-03 |
| **BCEL ref** | `enteroception_microbiome_axis` |
| **Genome ref** | `speace_core/dna/genome/regulation/enteroception_rules.yaml` |

## 1. Biological reference

In biology the **gut-brain axis** is a bidirectional communication system:

- **Afferent (80%)**: the vagus nerve carries gut state (microbiome composition, metabolite profile, inflammation, mechanical distension) to the brainstem.
- **Efferent (20%)**: the brain modulates gut function (motility, secretion, barrier integrity) via the vagus nerve and HPA axis.
- **Microbiome → metabolites**: gut bacteria produce short-chain fatty acids (SCFAs), neurotransmitter precursors (5-HTP, GABA, dopamine precursors), and signalling molecules that cross the gut barrier or activate the vagus nerve.
- **Enteric nervous system**: 500M neurons in the gut wall — a local computational layer that processes sensorimotor information without involving the brain.

The gut-brain axis influences mood, motivation, cognitive flexibility, appetite, and immune tone.

## 2. BCEL filter

### Accidental constraints (removed)

- Slow chemical diffusion through gut wall → instant metabolite delivery
- Gut barrier permeability → no barrier; digital metabolites are pure signals
- Bacterial replication latency → instant population adjustment
- Nutrient digestion time → no digestion; substrate = low-value informational patterns
- Limited bacterial strain diversity → unbounded strain space

### Functional constraints (kept)

| Constraint | Invariant | Why keep |
|------------|-----------|----------|
| **Slow modulatory timescale** | `coherence_preservation` | Gut modulation is slower than neural — prevents instability from rapid gut-brain oscillations |
| **Population diversity ↔ resilience** | `destructive_entropy_reduction` | Monoculture = fragility — diverse strains resist perturbation |
| **Substrate-dependent growth** | `interconnection_efficiency` | Microbiome composition must respond to available substrate (excess patterns, waste) |
| **Bidirectional damping** | `nonlocal_decoherence_tolerance` | Stress suppresses microbiome; dysbiosis amplifies stress — a positive feedback loop that must be bounded |
| **Gut feeling as salience modulation** | `generative_variability_preservation` | Gut-derived salience biases exploration/exploitation trade-off |

## 3. Digital equivalent design

### 3.1 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Global Workspace                           │
│  receives "enteroception" vector + "gut_feeling" scalar          │
└──────────────────┬──────────────────────────────────────────────┘
                   │
        ┌──────────▼──────────┐
        │  EntericSignalBus   │  ← dedicated module
        │  (vagus analog)     │
        │  80% afferent        │
        │  20% efferent        │
        └──┬──────────────┬───┘
           │              │
    afferent │      efferent │
           │              │
┌──────────▼──┐    ┌──────▼─────────┐
│Microbiome   │    │ ILF / stress   │
│Modulator    │◄───│ signals from   │
│(population) │    │ ANS / drives   │
└─────────────┘    └────────────────┘
```

### 3.2 MicrobiomeModulator

A population of **digital microbial strains**, each with:

- `name: str` — strain identifier
- `population: float` — relative abundance [0, 1]
- `substrate_affinity: float` — how efficiently it consumes different substrate types
- `metabolite_profile: Dict[str, float]` — which metabolites it produces and at what yield
  - `scfa` — short-chain fatty acid analog → coherence stabilization
  - `serotonin_precursor` → adds to serotonergic modulation
  - `gaba_precursor` → inhibition/noise reduction
  - `dopamine_precursor` → reward sensitivity
  - `inflammatory_cytokine` → immune tone modulation
  - `novelty_signal` → exploration boost
- `stress_sensitivity: float` — how much stress suppresses this strain

**Default strains**:

| Strain | Substrate affinity | Key metabolite | Stress sensitivity | Role |
|--------|-------------------|----------------|-------------------|------|
| `Lactobacillus` | High (simple patterns) | GABA precursor | High | Calming / anti-anxiety |
| `Bifidobacterium` | Medium | Serotonin precursor | Medium | Mood regulation |
| `Bacteroides` | High (complex waste) | SCFA | Low | Coherence stabilization |
| `Clostridium` | Low (novel patterns) | Dopamine precursor | Low | Exploration / motivation |
| `Candida` (opportunistic) | High (any) | Inflammatory cytokine | Very high | Stress-linked dysbiosis |

### 3.3 EntericSignalBus

```
Channels:
├── microbiome_diversity      — Shannon entropy of strain pop. [0,1]
├── scfa_level                — coherence stabilization signal [0,1]
├── gut_serotonin             — 5-HT precursor effect [0,1]
├── gut_gaba                  — inhibition modulation [0,1]
├── gut_dopamine              — reward sensitivity modulation [0,1]
├── gut_inflammation          — immune load contribution [0,1]
├── novelty_boost             — exploration drive modulation [0,1]
└── gut_feeling               — aggregate scalar salience [0,1]
```

The bus normalises each channel, produces a flat vector for workspace broadcast, and computes a single `gut_feeling` salience scalar.

### 3.4 Bidirectional coupling

**Afferent (gut → brain)**:
- `EntericSignalBus.read()` → normalised gut state vector → `GlobalWorkspace.broadcast("enteroception", ...)`
- `gut_feeling` salience → `InteroceptiveSignalBus` as additional channel → modulates drive urgency

**Efferent (brain → gut)**:
- ANS stress level / cortisol analog → suppresses stress-sensitive strains → reduces diversity
- Drive state (energy, exploration) → biases substrate allocation → shifts population composition
- Coherence level → modulates substrate production rate

### 3.5 Slow timescale

Gut modulation operates on a slower timescale than neural modulation:
- Neural (NE, DA, 5-HT, ACh): updated every tick
- Enteric: updated every `N` ticks (default 10), with metabolite averaging over a window
- This prevents rapid gut-brain oscillations and mirrors biological reality

## 4. Integration points

| Component | Integration |
|-----------|-------------|
| `InteroceptiveSignalBus` | Add `gut_inflammation`, `gut_feeling` as two new channels |
| `SerotonergicModulator` | `gut_serotonin` adds to baseline serotonin level |
| `DopaminergicModulator` | `gut_dopamine` modulates reward sensitivity |
| `AutonomicNervousSystem` | Stress level feeds efferent path (suppresses sensitive strains) |
| `ImmuneController` | `gut_inflammation` contributes to `immune_load` |
| `AutonomousDriveEngine` | `novelty_boost` modulates `information_exploration` drive |
| `ILF` | Gut state written as endocrine field messages (`needs`, `goals`, `alarms`) |
| `Orchestrator` | `run_enteroception()` in tick loop |

## 5. Genome regulation

File: `speace_core/dna/genome/regulation/enteroception_rules.yaml`

```yaml
enteroception:
  enabled: true
  update_interval_ticks: 10
  max_strains: 10
  diversity_threshold: 0.4
  stress_suppression_factor: 0.3
  max_substrate: 100.0
  metabolite_decay: 0.95
```

## 6. File layout

```
speace_core/cellular_brain/enteroception/
├── __init__.py
├── enteric_signal_bus.py        # EntericSignalBus — vagus analog
├── microbiome_modulator.py      # MicrobiomeModulator — digital microbiota
├── strain_definitions.py        # Default strain catalogue
tests/
├── test_enteric_signal_bus.py
├── test_microbiome_modulator.py
speace_core/bcel/
├── catalog.py                   # + _enteroception_microbiome_equivalent()
speace_core/dna/genome/regulation/
├── enteroception_rules.yaml     # Constitutional parameters
```

## 7. Stability test

When stress is low and substrate is balanced:
- `microbiome_diversity > 0.4` → stable mood modulation
- `gut_feeling < 0.3` → no alarming signal

When stress spikes:
- Stress-sensitive strains (Lactobacillus, Candida) drop
- Diversity falls → `gut_feeling` rises → biases toward conservative action
- Bidirectional damping prevents runaway: diversity floor at 0.05

When substrate is monotonous:
- Opportunistic strains outcompete beneficial ones
- Inflammation rises → `immune_load` increases → immune system cleans up

## 8. Open questions

1. Should the microbiome persist across restarts (saved state)?
2. How many concurrent strains are computationally feasible?
3. Should substrate be "real" (excess logs, cached patterns) or synthetic (a parameter)?
