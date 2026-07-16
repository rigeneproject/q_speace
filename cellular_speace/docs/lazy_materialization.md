# SPEACE — Lazy Materialization Manager

**Status**: implemented in `speace_core/cellular_brain/lazy/`
**Tests**: `tests/lazy/test_lazy_materialization.py` (19 tests passing)

## Why

A biological brain has ~86 billion neurons and ~150 trillion synapses.
Materializing all of them would saturate RAM, hard disk and CPU even
for a prototype. SPEACE solves this with a **parametric catalog**:
one record per *functional role*, not per neuron. Neurons are
materialized only when a signal requires that function.

## Architecture

```
LazyMaterializationManager
  ├── ParametricCatalog      # region/function -> FunctionSpec
  ├── SignalRouter            # DigitalSignal -> SignalKey (region.function)
  ├── _by_key: dict           # currently-materialized neurons
  └── stats: MaterializationStats
```

### ParametricCatalog

A `FunctionSpec` is a *parametric* description of a neuron role:

| Field            | Meaning                                  |
|------------------|------------------------------------------|
| `key`            | e.g. `"hippocampus.encoding"`             |
| `region`         | brain region (sensory, hippocampus, …)   |
| `function`       | functional subrole (encoding, decision…) |
| `cell_type`      | SPEACE cell class name                   |
| `threshold`      | default activation threshold             |
| `plasticity_rate`| learning rate                            |
| `tau_ms`         | membrane time constant                   |
| `math_function`  | description of underlying math model     |

The default catalog has **16 functional specs** spanning all major
brain regions (sensory, hippocampus, prefrontal, language, motor,
cerebellar, limbic, default mode, brainstem, generic).

### SignalRouter

Extracts `(region, function)` from a `DigitalSignal.meaning`. If the
field is empty, falls back to the target_region parameter, or to
`generic.processing`.

### LazyMaterializationManager

- `demand(signal, target_region) -> MaterializedNeuron`:
  1. Resolve `SignalKey` from signal
  2. If a neuron for that key is already materialized, return it (hit)
  3. Otherwise, look up `FunctionSpec` in catalog
  4. Instantiate a `DigitalNeuron` with the spec's parameters
  5. Register and return

- `connect(source, target) -> DigitalSynapse`: create a synapse
  between two materialized neurons.

- `unmaterialize_idle(idle_threshold_seconds)`: remove neurons that
  have not been used recently. Lets the brain release resources
  when functions are no longer needed.

- `stats()`: returns `MaterializationStats` (demands, materializations,
  hits, unmaterializations, active neurons, unique functions).

## Usage

```python
from speace_core.cellular_brain.lazy import LazyMaterializationManager
from speace_core.cellular_brain.base.digital_signal import DigitalSignal

mgr = LazyMaterializationManager()

# Demand a neuron for a function
sig = DigitalSignal(source="ext", meaning="hippocampus.encoding",
                    strength=1.0)
mn = mgr.demand(sig)
print(mn.neuron.cell_id)         # lazy_hippocampus_encoding_<uuid>
print(mn.spec.math_function)     # "LIF + STDP + pattern_separation"

# Re-demand -> hit (no new neuron)
mn2 = mgr.demand(sig)
assert mn.neuron.cell_id == mn2.neuron.cell_id

# Connect two functions
mn_a = mgr.demand_specific("prefrontal", "decision")
syn = mgr.connect(mn, mn_a, weight=0.7, delay_ms=2.0)

# Inspect
print(mgr.stats())  # demands=2, materializations=2, hits=1
```

## Mathematical functions

Each `FunctionSpec` declares a `math_function` string describing
its underlying mathematical model. Examples:

- `sensory.visual` → `LIF + lateral_inhibition`
- `hippocampus.encoding` → `LIF + STDP + pattern_separation`
- `prefrontal.decision` → `LIF + accumulation_to_bound`
- `language.semantic_grounding` → `LIF + HRR_binding`
- `default_mode.consolidation` → `LIF + replay_during_offline`

The lazy layer treats these as **labels** — the actual math is
performed by the backend (native LIF, Brian2, etc.).

## Statistics

```python
stats = mgr.stats()
# MaterializationStats(
#   demands=10, materializations=3, hits=7, unmaterializations=0,
#   active_neurons=3, unique_functions=3
# )
```

## Future work

- Integration with `ContinuousRuntimeEngine`: route incoming
  signals through the manager before they reach `NeuralCircuit`.
- Per-region `lazy_criterion` predicates: e.g. only materialize
  a `prefrontal.decision` neuron if the prefrontal is above a
  minimum energy level.
