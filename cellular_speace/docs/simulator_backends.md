# SPEACE — Simulator Backends (PyNN-like)

**Status**: implemented in `speace_core/cellular_brain/simulator_backends/`
**Tests**: 19 tests passing (`tests/simulator_backends/`)
**Dependencies**: zero required; brian2/nest/neuron/pyNN are optional

## Why

SPEACE's internal simulator (`NeuralCircuit.tick()`) is fast enough
for prototypes but doesn't expose the detailed neuroscience primitives
of established tools. This module adds a **PyNN-style** interface so
that:

1. The internal simulator remains the always-available default.
2. Brian2 can be plugged in for medium-scale prototyping.
3. NEST can be plugged in for very large networks.
4. NEURON can be plugged in for detailed single-neuron morphology.
5. The same `Population` / `Projection` specification works with
   every backend — a `BackendSelector` picks the right one.

This matches the **hybrid strategy** recommended for SPEACE:
native first, then opt into Brian2/NEST/NEURON only where needed.

## Architecture

```
speace_core.cellular_brain.simulator_backends
  ├── simulator_backend.py    # ABC + BackendCapabilities + SimulationResult
  ├── optional_imports.py     # lazy import wrappers, availability cache
  ├── population.py           # Population / Projection / NeuronSpec
  ├── native_backend.py       # default, always available
  ├── brian2_backend.py       # optional (pip install brian2)
  ├── nest_backend.py         # optional (pip install nest-simulator)
  ├── neuron_backend.py       # optional (pip install neuron)
  └── backend_selector.py     # WorkloadSpec + recommend_backend + BackendSelector
```

## Core types

### `Population`

A declarative container of `NeuronSpec`s. Two construction styles:

```python
# By size — generates neuron_id = f"{label}_{i}"
pop = Population(label="p1", cell_type="excitatory", size=100)

# By explicit specs
specs = [NeuronSpec(neuron_id=f"n_{i}", threshold=0.5, tau_ms=10.0)
         for i in range(10)]
pop = Population(label="custom", neurons=specs)
```

`NeuronSpec` is a small dataclass:

| Field            | Default | Meaning                          |
|------------------|---------|----------------------------------|
| `neuron_id`      | (req)   | unique id                        |
| `cell_type`      | generic | SPEACE cell class                |
| `threshold`      | 0.5     | firing threshold                 |
| `reset`          | 0.0     | post-spike voltage               |
| `resting`        | 0.0     | equilibrium voltage              |
| `tau_ms`         | 10.0    | membrane time constant           |
| `refractory_ms`  | 2.0     | refractory period                |
| `initial_voltage`| None    | startup voltage (None → resting) |

### `Projection`

A connection set between two populations:

```python
proj = Projection(source=pop_a, target=pop_b)

# one connection
proj.connect("p1_0", "p1_1", weight=0.7, delay_ms=2.0)

# all-to-all with density
proj.connect_all(weight=0.5, delay_ms=1.0, density=0.3)
```

`ConnectionSpec` records `(source_id, target_id, weight, delay_ms, synapse_type)`.

### `SimulatorBackend` (ABC)

Every backend implements:

```python
def capabilities() -> BackendCapabilities
def setup(populations, projections) -> None
def run(duration_ms, dt_ms=0.1) -> SimulationResult
def reset() -> None
def is_available() -> bool
```

`SimulationResult` exposes `spikes: Dict[neuron_id, List[float]]`,
`state: Dict[neuron_id, List[float]]`, and `runtime_ms`.

### `NativeBackend`

A simple LIF (leaky integrate-and-fire) simulator implemented in
pure Python using only `math` and `time`. The membrane update is:

```
v(t+dt) = v_rest + (v - v_rest) * exp(-dt/tau) + I * dt * 0.05
```

If `v >= threshold`, the neuron spikes, voltage is reset, and a
refractory period applies. Synaptic input from earlier spikes
arrives after `delay_ms`. Always available.

### `Brian2Backend` (optional)

Wraps `brian2.NeuronGroup` and `brian2.Synapses`. Uses a single
NeuronGroup for all neurons (LIF equations: `dv/dt = (v_rest - v + I)/tau`).
Records spikes with `SpikeMonitor` and voltages with `StateMonitor`.
Only available if `brian2` is installed.

### `NESTBackend` (optional)

Wraps `nest.Create("iaf_psc_alpha", ...)` and `nest.Connect(...)`.
Records spikes via `nest.Create("spike_detector")`. Only available
if `nest` is installed.

### `NEURONBackend` (optional)

Wraps `h.Section` and `h.hh` for Hodgkin-Huxley-like single-neuron
simulations. Useful for morphology detail. Only available if
`neuron` (or `NEURON`) is installed.

## BackendSelector

`recommend_backend(WorkloadSpec)` picks the best backend:

```python
recommend_backend(WorkloadSpec(neuron_count=100))                 # native
recommend_backend(WorkloadSpec(neuron_count=200_000))              # nest (if avail)
recommend_backend(WorkloadSpec(neuron_count=100, needs_morphology=True))  # neuron
```

`BackendSelector` is a memoizing factory:

```python
sel = BackendSelector()
backend = sel.build(sel.recommend(neuron_count=50))  # NativeBackend
```

## End-to-end usage

```python
from speace_core.cellular_brain.simulator_backends import (
    BackendSelector, Population, Projection, NeuronSpec, available_backends
)

print(available_backends())  # {'native': True, 'brian2': False, 'nest': False, ...}

sel = BackendSelector()
choice = sel.recommend(neuron_count=20)  # always native by default
backend = sel.build(choice)

# Build populations
p1 = Population(label="p1", cell_type="excitatory", size=5)
p2 = Population(label="p2", cell_type="excitatory", size=3)

# Connect
proj = Projection(p1, p2)
proj.connect_all(weight=0.6, delay_ms=2.0)

# Run
backend.setup([p1, p2], [proj])
backend.set_neurons_input({"p1_0": 5.0, "p1_1": 4.0})
result = backend.run(duration_ms=20.0, dt_ms=0.1)
print(sum(len(v) for v in result.spikes.values()), "spikes")
```

## Optional installation

The optional backends are not in the default dependency set. To
install them:

```bash
pip install brian2                  # brian2 backend
pip install nest-simulator          # NEST backend
pip install neuron                  # NEURON backend
pip install pyNN                    # PyNN interface

# All at once:
pip install speace-core[all-simulators]
```

The corresponding `pyproject.toml` extras are: `brian2`, `nest`,
`neuron`, `pynn`, `all-simulators`.

## Capabilities matrix

| Backend  | Max neurons | Continuous | STDP | Morphology | Always avail |
|----------|-------------|------------|------|------------|--------------|
| native   | 10 000      | ✅         | ❌   | ❌         | ✅           |
| brian2   | 1 000 000   | ✅         | ✅   | ❌         | optional     |
| nest     | 10 000 000  | ❌         | ✅   | ❌         | optional     |
| neuron   | 1 000       | ✅         | ✅   | ✅         | optional     |

## Tests

- `test_native_backend.py`: LIF correctness, spike generation,
  reset, run with projections
- `test_backend_selector.py`: recommendation policy, build caching
- `test_optional_imports.py`: lazy import wrappers

Run with:

```bash
pytest tests/simulator_backends/ -v
```
