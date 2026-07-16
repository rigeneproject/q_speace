# T171 — Neuromorphic Event-Driven Computation Layer

## Objective

Bridge SPEACE's static Neural Periodic Table with runtime spike dynamics, implementing the paradigm shift from `data → numbers → algorithm → result` to `event → propagation → adaptation → emergence`.

## Background

SPEACE's neuroperiodic system (`neural_periodic_table.py`, `synaptic_bond.py`, `periodic_law.py`, `neuroperiodic_integrator.py`) is currently a **static ontology** — it classifies cell types by period/group/block, predicts bond properties between element pairs, and defines valence/reaction rules. It has **zero runtime dynamics**: no spike representation, no membrane potential, no propagation, no plasticity loop.

Meanwhile, SPEACE already has:
- `EventDrivenBurstEngine` (`burst_engine.py`) — sparse burst firing with `FireCandidate` prioritization
- `STDPEngine` (`stdp_engine.py`) — spike-timing-dependent plasticity with LTP/LTD windows
- `GlobalWorkspace` (`global_workspace.py`) — recurrent activation with phase-gated broadcast
- `PlasticityEngine` (`plasticity_engine.py`) — Hebbian reinforcement
- `DigitalSignal` (`base/digital_signal.py`) — typed signal propagation

The gap: the periodic table's structural predictions (bond type, strength, plasticity, delay, valence rules) are **not used** by the runtime burst/plasticity engines. The periodic table predicts what a synapse *should be*, but no code feeds those predictions into actual computation.

## Architecture

### Paradigm Pipeline

```
     ┌──────────┐    ┌──────────────┐    ┌───────────┐    ┌───────────┐
     │  EVENT   │ →  │ PROPAGATION  │ →  │ ADAPTATION│ →  │ EMERGENCE │
     │ (spike)  │    │ (bond-based) │    │ (STDP +   │    │ (pattern  │
     │          │    │              │    │  plastic) │    │  monitor) │
     └──────────┘    └──────────────┘    └───────────┘    └───────────┘
```

### Layer Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                  NeuroPeriodicIntegrator (updated)               │
│  • tick() — one step of spike propagation                       │
│  • connect to burst engine for FireCandidate collection          │
│  • connect to STDP engine for plasticity updates                 │
└──────────────────────────────────────────────────────────────────┘
         │                    │                     │
         ▼                    ▼                     ▼
┌──────────────┐  ┌──────────────────┐  ┌───────────────────┐
│  SpikeEvent  │  │ PropagationEngine │  │ MembraneDynamics  │
│  (datatype)  │  │ (routing + delay) │  │ (LIF + periodic   │
│              │  │                   │  │  properties)      │
└──────────────┘  └──────────────────┘  └───────────────────┘
                                              │
                                              ▼
                                   ┌──────────────────┐
                                   │PhysioNeuralTrans- │
                                   │ducer (signal →    │
                                   │ spike pattern)    │
                                   └──────────────────┘
```

## Components

### 1. `SpikeEvent` (speace_core/cellular_brain/neuroperiodic/spike_event.py)

A first-class spike datatype that bridges the periodic table with runtime dynamics.

Fields:
- `spike_id` — unique ID (tick_counter + index)
- `source_z` — presynaptic element atomic number
- `target_z` — postsynaptic element atomic number (None if spontaneous)
- `timestamp` — tick number
- `phase` — oscillation phase at firing [0, 2π)
- `inter_spike_interval` — time since last spike from same source
- `strength` — normalized amplitude [0, 1]
- `bond_id` — which bond this spike traverses (None for spontaneous)
- `payload` — optional typed data (for non-neural signals)

Methods:
- `temporal_code()` — return (ISI, phase, strength) as a 3D temporal code
- `with_propagation(bond)` — return a copy adjusted for bond attenuation/delay

### 2. `PropagationEngine` (speace_core/cellular_brain/neuroperiodic/propagation_engine.py)

Routes spikes through the periodic bond network using bond properties for delay, attenuation, and plasticity.

Key methods:
- `emit(spike, circuit)` — inject a spike into the circuit; collect postsynaptic neurons as FireCandidates
- `propagate_burst(burst_result, circuit, bond_registry)` — after a burst, propagate each spike through its target bonds
- `apply_periodic_stdp(spikes, bond_registry)` — STDP update using bond-specific plasticity from periodic table
- `signal_delay(bond)` — delay computed from bond_length × bond_type factor (uses existing SynapticBond.signal_delay)

Integration with existing burst engine:
- `collect_fire_candidates_from_spikes(circuit, spikes)` — convert SpikeEvents to FireCandidates

### 3. `MembraneDynamics` (speace_core/cellular_brain/neuroperiodic/membrane_dynamics.py)

Leaky Integrate-and-Fire model where periodic element properties determine neuron parameters.

Mapping:
- `ionization_energy` → firing threshold
- `atomic_radius` → receptive field / input integration window
- `electronegativity` → lateral inhibition strength
- `mass` → metabolic cost per spike
- `period` → integration time constant (τ): deeper period = longer integration
- `block` (S/P/D/F) → neurotransmitter effect (S=inhibitory, P=excitatory, D=modulatory)

Methods:
- `step(neuron, input_current, dt, element)` — update membrane potential using element properties
- `should_fire(neuron, element)` — threshold check with element-specific dynamics
- `reset(neuron, element)` — reset after firing with refractory period based on bond_type

### 4. `PhysioNeuralTransducer` (speace_core/cellular_brain/embodiment/physio_neural_transducer.py)

Principled signal transduction that preserves signal structure through frequency decomposition, phase-preserving encoding, and spike-train generation — avoiding ADC-style quantization artifacts.

Methods:
- `transduce(signal_array, sample_rate, signal_type)` → returns list of SpikeEvents
  - Frequency decomposition via filter bank (simulated cochlea)
  - Phase-preserving encoding (preserve temporal structure)
  - Spike generation with ISI and phase encoding
- `signal_types`: "audio", "visual", "temperature", "pressure", "proprioceptive"

### 5. Integrator Updates

`NeuroPeriodicIntegrator.tick(circuit, dt=1.0)`:
1. Collect fired neurons from circuit → create SpikeEvents with periodic table properties
2. Propagate through bonds (apply delay, attenuation, molecular orbital amplification)
3. Collect postsynaptic candidates → push to burst engine
4. Apply periodic-informed STDP to bonds that carried spikes
5. Update bond states (short-term depression, facilitation)

### 6. BCEL Catalog Updates

Three new equivalences:
- **Temporal coding** — spike timing as information channel (preserves nonlocal_decoherence_tolerance)
- **Event-driven computation** — only active elements consume energy (preserves interconnection_efficiency)
- **Signal transduction** — structure-preserving sensor encoding (preserves coherence_preservation)

## BCEL Classification

### Temporal Coding (Spike Timing as Information)

| Aspect | Classification |
|--------|---------------|
| Biological structure | Auditory system phase locking, hippocampal phase precession |
| Function | Encode information in precise timing of neural events |
| Accidental | Ion channel kinetics, neurotransmitter jitter, propagation noise |
| Functional | Temporal precision as information channel; coincidence detection enables binding |
| Digital synthesis | (ISI, phase, strength) triple as first-class signal property in SpikeEvent |
| Invariant | `nonlocal_decoherence_tolerance` (D_nonlocal): temporal precision enables distributed synchrony |

### Event-Driven Computation (Only Active Neurons Fire)

| Aspect | Classification |
|--------|---------------|
| Biological structure | Sparse neural coding; silent until stimulated |
| Function | Minimize energy by activating only relevant pathways |
| Accidental | Axonal propagation delay, synaptic vesicle cycling cost |
| Functional | Energy efficiency through sparse activation; prevents runaway excitation |
| Digital synthesis | Formalize burst engine as primary execution mode; periodic table predicts which elements fire |
| Invariant | `interconnection_efficiency` (Diff(F)): sparsity maximizes useful signal per energy unit |

### Signal Transduction (Not ADC)

| Aspect | Classification |
|--------|---------------|
| Biological structure | Cochlear frequency decomposition, retinal center-surround |
| Function | Preserve signal structure through physical transformation |
| Accidental | Limited frequency range, mechanical resonance constraints |
| Functional | Signal structure preservation through frequency/phase decomposition |
| Digital synthesis | PhysioNeuralTransducer: filter bank → phase encoding → spike train |
| Invariant | `coherence_preservation` (U(1)_coh): phase coherence maintained through transduction |

## Integration Points

- **Burst Engine**: PropagationEngine.collect_fire_candidates_from_spikes() feeds FireCandidates to EventDrivenBurstEngine
- **STDP Engine**: PropagationEngine.apply_periodic_stdp() calls existing STDPEngine with bond-specific plasticity rates
- **GlobalWorkspace**: SpikeEvents with phase encoding feed into phase-gated broadcast
- **Digital RNA**: Periodic table adapter pushes functional constraints that affect membrane dynamics parameters
- **Genome**: New genome sections for each element's membrane parameters (override defaults)

## Governance & Safety

- All spike propagation is opt-in via genome flag `neuroperiodic.enable_runtime_dynamics`
- Temporal coding is informational; no execution gating based on phase
- Transducer operates only on explicitly connected sensors
- STDP rates are capped by bond.plasticity (which is predicted by periodic table and bounded [0,1])
- Propagation engine logs all spikes at configurable detail level (none/summary/full)
- No autonomous modification of periodic table structure; only bond.energy and bond.plasticity are updated

## Acceptance Criteria

1. `SpikeEvent` created with source_z, timestamp, phase, ISI; temporal_code() returns 3D vector
2. `PropagationEngine.emit()` injects a spike and produces at least one FireCandidate
3. `PropagationEngine.signal_delay()` returns different delays for different bond types
4. `MembraneDynamics.step()` updates membrane potential using element properties from periodic table
5. `MembraneDynamics.should_fire()` returns True only when threshold (from ionization_energy) is exceeded
6. `PhysioNeuralTransducer.transduce()` produces spike train with phase and ISI encoding
7. `NeuroPeriodicIntegrator.tick()` runs one step without error
8. `NeuroPeriodicIntegrator.tick()` produces at least one bond state change after 2+ ticks
9. BCEL catalog contains entries for temporal coding, event-driven computation, signal transduction
10. All new components have unit tests
11. No regressions in existing neuroperiodic tests
