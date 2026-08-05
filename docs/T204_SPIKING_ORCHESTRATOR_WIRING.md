# T204 — Spiking layer wiring into QuantumOrchestrator (P1 closure)

**Status**: agentic (production)
**Scope**: close P1 of T202 — make `num_spikes` reach `QuantumOperation` /
Sevo / energy gate end-to-end.
**Predecessor**: T202 (pseudo-spiking layer shipped as library, but the
orchestrator never invokes it).
**Out of scope**: P3 (correlation binding) and P5 (CV on QCA weights)
remain as `q_speace.spiking` utilities, with no orchestrator call sites.
P4 stays vibe-only per T203.

## 1. Why this ticket exists

T202 §10 honestly deferred the orchestrator wire-up. The cost model is
ready (`QuantumOperation.num_spikes`, `W_PER_SPIKE` in
`metabolism/cognitive_cost_model.py:25,40,55`) but
`orchestrator.py:78-83` never sets `num_spikes` on the operation it
builds, so the Sevo gate today reflects qubit/gate/depth/decoherence
cost only — not spike sparsity. The spec's central claim
("attività sparsa = tick economico") is asserted in prose but absent
from the runtime. T204 closes that one connection.

## 2. What T204 changes

### 2.1 `QuantumNeuralBridge` — minimal activity accessor

Add one property and one method, no semantic change to entanglement
semantics:

- `activity: np.ndarray` — per-neuron "amplitude" proxy: a vector of
  shape `(num_neurons,)`, non-negative, sum 1. Initial value:
  uniform `1/N`. Updated only by an explicit `set_activity(...)` call
  from the orchestrator; the bridge never invents activity on its own
  (no fake Gaussian, no QCA weights — see the option we picked).
- `set_activity(values: np.ndarray) -> None` — accepts a length-N
  vector; normalizes to a probability-like distribution; raises
  `ValueError` on length mismatch.

This is the minimum surface T204 needs. The bridge remains a
binding/mapping primitive; the orchestrator owns the lifecycle of the
activity vector.

### 2.2 `QuantumOrchestrator`

New constructor parameters (all default `False` → fully backward
compatible):

- `enable_spikes: bool = False`
- `spike_k: float = 3.0`           # SpikingBrain default
- `spike_beta: float = 0.0`        # ILF modulation strength

New private state when `enable_spikes=True`:

- `self._activity: np.ndarray` of shape `(num_neurons,)` — refreshed
  every tick from a deterministic function of `(tick, coherence_phi,
  num_entanglements)` (see §2.3). The activity is set on the bridge via
  `set_activity` *before* spike encoding so the bridge remains the
  single source of truth for neuron state.
- `self._spike_history: deque[int]` — last 64 tick spike counts, kept
  for diagnostics and any future P3/P5 follow-up.

Tick loop change (single hunk, in `_run_quantum_step`, between the ILF
update and the `QuantumOperation(...)` construction):

```python
num_spikes = 0
if self._enable_spikes:
    self._refresh_activity(tick=tick)
    enc = dynamic_spikes(
        self._activity.reshape(1, -1),  # 1 sample x N neurons
        k=self._spike_k,
        coherence_phi=self._ilf.coherence_phi,
        beta=self._spike_beta,
    )
    num_spikes = enc.num_spikes
    self._spike_history.append(num_spikes)
```

Then `QuantumOperation(..., num_spikes=num_spikes)` — the only line
that completes P1.

### 2.3 `_refresh_activity`

Deterministic, no new dependencies. Formula:

```
seed  = (self._seed or 0) + tick
base  = rng.uniform(0, 1, size=N) ** (1 / (1 + coherence_phi))
boost = 1 + 0.5 * num_entanglements / max(N, 1)
activity = base * boost
```

Rationale: high coherence → flatter distribution (more neurons firing);
many entanglements → mild amplification (binding-rich state is
slightly denser). Result always normalized to sum 1 before being
passed to the bridge. **No QCA weights, no ILF beliefs, no Earth
signal** — those are already represented elsewhere in the tick; T204
does not couple them to spike activity.

### 2.4 `TickReport`

Add two fields, default-initialized so existing call sites stay valid:

- `num_spikes: int = 0`
- `sparsity: float = 1.0`

`QuantumOrchestrator.report()` gains two keys (always present, 0 / 1.0
when spikes are off):

- `mean_num_spikes: float`
- `mean_sparsity: float`

### 2.5 Tests (`tests/test_orchestrator_spiking.py`, new file)

Four tests, modeled on the T202 style (deterministic, no torch):

1. `test_spikes_off_by_default` — `enable_spikes=False` (default);
   every `TickReport.num_spikes == 0` and `sparsity == 1.0`.
2. `test_spikes_on_injects_num_spikes_into_cost` — run with
   `enable_spikes=True`; assert at least one tick has
   `num_spikes > 0`; assert
   `op.num_spikes == TickReport.num_spikes` for every tick (capture via
   a fake cost model or by inspecting `mean_energy_w`).
3. `test_sparse_activity_cheaper_than_dense` — two runs with identical
   seed, one with high coherence (force `coherence_phi=0.9` via a
   stubbed ILF) and one with low (`coherence_phi=0.1`); assert the
   high-coherence run has lower `mean_num_spikes` *or* (when both are
   non-zero) strictly lower `mean_energy_w`.
4. `test_bridge_activity_accessor_round_trip` — direct unit test on
   `QuantumNeuralBridge.set_activity` / `.activity`: shape, sum=1,
   mismatch raises.

### 2.6 BCEL — no new entries

The T202 catalog already covers spike firing (accidental), spike-timing
synchrony (functional, classical fidelity-proxy), event-driven energy
(functional), STDP-like plasticity (functional), ILF-modulated
threshold (functional). T204 is purely a wire-up; nothing new enters
the conceptual vocabulary.

## 3. Invariants

- Backward compatible: every existing test continues to pass with
  `enable_spikes=False`. No change to public CLI flags or to the
  `QuantumOperation` default.
- `num_spikes` only enters the cost; it does not alter the QCA weights,
  the entanglement registry, or any state vector.
- The bridge remains a binding primitive — T204 does not let it invent
  activity. The orchestrator owns the lifecycle.
- No new dependencies. Pure numpy + dataclasses, consistent with T202.

## 4. Quality gates (run after stage, before commit)

- [ ] `pytest tests/test_orchestrator_spiking.py tests/test_spiking.py -x`
- [ ] `pytest` (full suite, no regressions)
- [ ] `ruff check q_speace tests`
- [ ] `python -m py_compile` on touched files
- [ ] `black --check` on touched files

## 5. Out of scope (explicit)

- **P3 binding**: `entangle_by_correlation` is callable; the
  orchestrator does not call it. A future T205 may add an
  opt-in `enable_spike_binding` flag (off by default) — kept out of
  T204 to keep the diff minimal and the test surface small.
- **P5 entropy-gradient on QCA**: `spike_entropy_gradient` is callable
  and tested against `CosmicVirusOptimizer` in T202; the orchestrator
  does not drive QCA weights through it. Future T206 territory.
- **P4 GLA in RG cascade**: vibe-only per T203, frozen.

## 6. File-level diff summary

Modified:

- `q_speace/quantum/quantum_neural_bridge.py` — add `activity`,
  `set_activity`.
- `q_speace/orchestrator.py` — three new params, `_refresh_activity`,
  ~5 lines in `_run_quantum_step`, two fields on `TickReport`, two
  keys in `report()`.

New:

- `tests/test_orchestrator_spiking.py` — four tests as above.

No changes to: `metabolism/cognitive_cost_model.py`, `edd_cvt/`,
`fractal_qca.py`, `cli.py`, `__init__.py`, BCEL catalog,
`docs/T202_SPIKING_SPEC.md`, `docs/T203_GLA_RG_VIBE.md`.
