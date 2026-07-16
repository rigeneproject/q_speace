# T172 — Cognitive Factors Telescope

**Document ID:** SPEACE-SPEC-T172
**Status:** Draft v1
**Author:** Architect agent
**Related:** T171 (DNA↔Periodic binding), `docs/SPEACE_OMNI_RAG_ARCHITECTURE.md`
**Scope:** Only `docs/`, `scripts/`, `tests/`, `reports/` and additive Omni-RAG nodes.

---

## 1. Purpose

The cognitive psychology literature describes ten reproducible factors that
distinguish expert information processing from novice. This spec turns each
factor into an **observable, auditable telemetry** of SPEACE so that:

1. An Ispettore/Manutentore loop can ask "what is my working-memory span
   utilization right now?" and get a number, not a guess.
2. Any change to a cognitive module can be traced to a before/after delta on
   its corresponding metric.
3. The Omni-RAG cognitive graph becomes the single place to ask the question
   "how well am I reasoning?".

We **do not** add new cognitive modules. We **add 10 measurement points**
that read existing state.

## 2. The ten factors and their measurement points

| # | Factor | Producing module (current SPEACE) | Observable signal | ILF metric id | Omni-RAG tag |
|---|--------|----------------------------------|-------------------|---------------|-------------|
| 1 | **Working memory** | `cognition.subgrid_attention_working_memory` (`SubgridAttentionWorkingMemory`) | `len(slots)/max_slots` per task | `wm_slot_utilization` | `cognitive_factor:wm` |
| 2 | **Processing speed** | `metabolism.cognitive_cost_model` | mean cost/tick over last N ticks | `cognitive_cost_per_tick` | `cognitive_factor:speed` |
| 3 | **Pattern recognition** | `cognition.arc_primitive_discovery_engine` + `concept_graph` | ratio (concepts / raw items) | `pattern_compression_ratio` | `cognitive_factor:pattern` |
| 4 | **Prior knowledge** | `evolutionary_memory.evolutionary_memory_store` + `memory.semantic.semantic_memory_store` | edge_density of memory graph | `memory_link_density` | `cognitive_factor:knowledge` |
| 5 | **Abstraction (multi-level)** | `cognition.hierarchical_concept_abstraction_layer` | distinct levels actually activated | `abstraction_levels_active` | `cognitive_factor:abstraction` |
| 6 | **Relational reasoning** | `cognition.temporal_causal_reasoning_layer` | cycles detected / linear pairs | `causal_cycles_detected` | `cognitive_factor:relational` |
| 7 | **Metacognition** | `metacognition.metacognitive_monitor` | probe events / wall-clock | `metacognitive_probes_per_minute` | `cognitive_factor:metacognition` |
| 8 | **Sustained attention** | `regions.thalamic_relay_engine.ThalamicRelayEngine` | gap count between tonic intervals | `attention_gap_count` | `cognitive_factor:attention` |
| 9 | **Motivation** | `dna.genome.morphology.autonomous_drives` (read-only) | max activation across 7 drives | `drive_pressure_max` | `cognitive_factor:motivation` |
| 10 | **Cognitive flexibility** | `cognition.mmapr_council` | perspective switches / minute | `perspective_switches_per_minute` | `cognitive_factor:flexibility` |

### 2.1 Tags convention

All ten metrics are tagged with `cognitive_factor:<key>` so that an `omni-query`
can filter by tag.

### 2.2 Sampling

Each metric is sampled **on demand** by the telescope. There is no
continuous background poller in this iteration — sampling a metric is the
equivalent of a single snapshot. Continuous poller is in v2 (out of scope).

## 3. The 10 metrics, defined precisely

### 3.1 `wm_slot_utilization` (factor 1)

```python
def wm_slot_utilization(wm: SubgridAttentionWorkingMemory) -> float:
    return len(wm.slots) / max(1, wm.max_slots)
```

Range [0, 1]. Healthy: 0.4-0.8. Alert if > 0.9 *or* < 0.2 for sustained period.

### 3.2 `cognitive_cost_per_tick` (factor 2)

```python
def cognitive_cost_per_tick(cost_model, last_n_ticks=200) -> float:
    return cost_model.rolling_mean_cost(window=last_n_ticks)
```

Healthy: stable. Alert if rising > 20 % above baseline (cheap proxy for
"speed has slowed down").

### 3.3 `pattern_compression_ratio` (factor 3)

```python
def pattern_compression_ratio(concept_graph) -> float:
    n_raw = concept_graph.total_observations()
    n_abstract = concept_graph.distinct_concept_count()
    return n_abstract / max(1, n_raw)
```

Healthy: ≥ 0.05 (5 % of observations yield distinct concepts).

### 3.4 `memory_link_density` (factor 4)

```python
def memory_link_density(semantic_store) -> float:
    n = semantic_store.node_count()
    e = semantic_store.edge_count()
    return e / max(1, n * (n - 1))
```

Healthy: any positive value. Healthy range depends on corpus; the trend
matters more than the absolute.

### 3.5 `abstraction_levels_active` (factor 5)

```python
def abstraction_levels_active(abstraction_layer) -> int:
    return len(abstraction_layer.active_levels())
```

Healthy: ≥ 2 (level-1 + level-2 concepts both observed).

### 3.6 `causal_cycles_detected` (factor 6)

```python
def causal_cycles_detected(temporal_layer) -> int:
    return temporal_layer.cycle_count()
```

Healthy: any non-zero (signals relational reach).

### 3.7 `metacognitive_probes_per_minute` (factor 7)

```python
def probes_per_minute(metacog_monitor, window_min=5) -> float:
    return metacog_monitor.probe_count(window=window_min) / max(1, window_min)
```

Healthy: ≥ 0.1.

### 3.8 `attention_gap_count` (factor 8)

```python
def attention_gap_count(thalamic_engine) -> int:
    return thalamic_engine.burst_to_tonic_gap_count(window=200)
```

Healthy: 0-2. Alert if monotonic increase (sustained distraction).

### 3.9 `drive_pressure_max` (factor 9)

```python
def drive_pressure_max(drives_yaml) -> float:
    return max(p["setpoint"] for p in drives_yaml["autonomous_drives"]["parameters"]["drives"].values())
```

Healthy: max ∈ {self_preservation, homeostatic_equilibrium} ≤ 0.8.

### 3.10 `perspective_switches_per_minute` (factor 10)

```python
def perspective_switches(mmapr_council, window_min=10) -> float:
    return mmapr_council.view_change_count(window=window_min) / max(1, window_min)
```

Healthy: ≥ 0.2.

## 4. Implementation files

| Path | Action | Owner |
|------|--------|-------|
| `scripts/print_cognitive_telescope.py` | new — runs all 10 measurements, prints JSON | Core |
| `speace_core/cli.py` | register `omni-telescope` sub-app | Core |
| `tests/cli/test_omni_telescope.py` | new — smoke test of CLI command | Test |
| `tests/cognitive_factors/test_telescope_units.py` | unit tests for 10 metric functions | Test |
| `reports/cognitive_telescope/` | output dir (smoke reports) | — |

## 5. What the spec forbids

- ❌ No persistent background poller in v1.
- ❌ No writes to `species_orientation.yaml` or `dna/genome/core/`.
- ❌ No new cognitive modules — only *measurement hooks* on existing ones.
- ❌ No score composition (a "cognitive score" that mixes the 10 metrics).

## 6. Acceptance criteria

1. `speace omni-telescope --format json` prints a JSON object with 10 keys,
   one per factor, each with `{value, healthy_range, tag}`.
2. Each metric function has a unit test in `tests/cognitive_factors/`.
3. The 10 `ILF_METRIC` nodes are visible in Omni-RAG after a re-index.
4. `pytest tests/cognitive_factors tests/cli/test_omni_telescope.py` green.

---

*End of T172 spec.*
