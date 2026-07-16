# T173 — Cognitive Infant Sensors (Fase 1 read-only)

**Document ID:** SPEACE-SPEC-T173
**Status:** Draft v1
**Author:** Architect agent
**Related:** `docs/Istruzioni_periodiche_di_aggiornamento.md` (Fase 1 — Cognitive Infant), T172
**Scope:** Add a new Omni-RAG collector under
`speace_core/omni_rag/collectors/infant_sensor_collector.py` (review preferred).

---

## 1. Purpose

`docs/Istruzioni_periodiche_di_aggiornamento.md:629-647` describes the
**Fase 1 — Cognitive Infant Stage**: the system develops causalità, memoria,
grounding, linguaggio, metacognizione *without* attuazione autonoma.
This spec instantiates that observation phase by adding five **read-only
digital sensors** that the Cognitive Infant organism can use to learn from
the world without moving in it.

> **Architectural decision.** Every sensor in this spec is **read-only**
> with respect to the organism. It produces `RuntimeEvent` graph nodes that
> *describe* state; it never *writes* back to organism state. This honors
> the Ispettore/Manutentore invariant ("prima comprensione, poi potere
> d'azione").

## 2. Five sensors

| Sensor | Reads | Cadence | Tag | Nodes produced |
|--------|-------|---------|-----|----------------|
| `runtime_event_stream` | `EventBus` (push/pop) | on subscribe | `infant_source:runtime` | `RUNTIME_EVENT` |
| `filesystem_watch`     | `data/logs/*.log` (poll, mtime) | 1 Hz | `infant_source:fslog` | `RUNTIME_EVENT` |
| `gateway_log_stream`   | `data/logs/gateway_*.log` (poll) | 1 Hz | `infant_source:gwlog` | `RUNTIME_EVENT` |
| `health_alerts_watch`  | `data/agi_team/health_alerts.jsonl` (poll) | 1 Hz | `infant_source:health` | `RUNTIME_EVENT` |
| `omni_rag_index_delta` | `data/omni_rag/nodes.jsonl` line count | every OmniIndexer run | `infant_source:omni_delta` | `RUNTIME_EVENT` |

## 3. Sensor specifications

### 3.1 `runtime_event_stream`

- **Source:** `speace_core.organism.organism_facade.OrganismFacade.event_bus`
  (EventBus event aggregator) — graceful if absent (skip with warning).
- **Subprotocol:** subscribe at collector startup; on each event push,
  emit a node with `metadata.event_type`, `metadata.event_source`,
  `metadata.tick`.
- **Backpressure:** if collector cannot keep up, drop oldest and emit a
  `WARNING: buffer_overflow` log entry.
- **Backpressure metric:** exposed as `infant_buffer_depth` (not a
  telescope metric; informational only).

### 3.2 `filesystem_watch`

- **Source:** all `*.log` files under `data/logs/`.
- **Polling:** `os.path.getmtime()` every 1 s; on change, compute the
  delta lines and emit one node per (file, batch) with `metadata.path`,
  `metadata.line_count`, `metadata.tail_hash`.
- **No recursion** beyond one level — keeps the read cheap.

### 3.3 `gateway_log_stream`

- **Source:** `data/logs/gateway_*.log` (already produced by
  `speace_core.organism` gateways).
- Same algorithm as 3.2 but filtered by glob.

### 3.4 `health_alerts_watch`

- **Source:** `data/agi_team/health_alerts.jsonl`.
- Parse last N lines (configurable, default 100); each `health_alert`
  becomes a node with `metadata.severity`, `metadata.module`.

### 3.5 `omni_rag_index_delta`

- **Source:** `data/omni_rag/nodes.jsonl` and `edges.jsonl`.
- On every invocation of the collector, count current line numbers;
  emit a node `metadata.node_count`, `metadata.edge_count`. No continuous
  background poller — only on `index_all(infant_sensor=True)`.

## 4. Data model

```python
def emit(self, infant_source: str, **metadata) -> CognitiveNode:
    return CognitiveNode(
        id=f"infant.{infant_source}.{ts}",
        node_type=NodeType.RUNTIME_EVENT,
        name=f"infant:{infant_source}",
        description="read-only digital observation",
        metadata={
            "infant_source": infant_source,
            **metadata,
        },
        tags=[
            "cognitive_infant",
            f"infant_source:{infant_source}",
            "cognitive_factor:observation",   # ties to T172 (will be added in v2)
        ],
    )
```

All nodes must be created with `cognitive_factor:observation` as a tag so
the telescope query in T172 can include them.

## 5. Configuration knobs

```python
class InfantSensorConfig:
    poll_interval_seconds: float = 1.0
    max_watched_log_size_mb: float = 32.0
    health_alerts_max_lines: int = 100
    enable_runtime_event_stream: bool = True
    enable_filesystem_watch: bool = True
    enable_gateway_log_stream: bool = True
    enable_health_alerts_watch: bool = True
    enable_omni_rag_index_delta: bool = True
```

All defaults are conservative. Operationally *off* toggles are exposed
through the existing CLI `--no-runtime` style flags.

## 6. What the spec forbids

- ❌ NO writes back to organism state.
- ❌ NO cybernetic actuators (no `speace_core/embodiment/` paths).
- ❌ NO autonomous shell execution.
- ❌ NO persistent background thread that survives the indexing run
  (the collector is *batch*: it runs once per `omni index`).
- ❌ NO deletions of watched files (read-only).

## 7. Test plan (task C3)

1. Create 5 stub log/JSONL files in a temp directory.
2. Instantiate `InfantSensorCollector(data_root=<tmp>)`.
3. Call `.collect()` and verify ≥ 5 nodes are produced with distinct
   `metadata.infant_source` values.
4. Verify all nodes have `cognitive_factor:observation` tag.
5. Total wall time < 30 s on a workstation.

## 8. Acceptance criteria

1. `docs/T173_COGNITIVE_INFANT_SENSORS_SPEC.md` checked in.
2. `speace_core/omni_rag/collectors/infant_sensor_collector.py` checked in.
3. `tests/omni_rag/test_infant_sensor_collector.py` passes.
4. `tests/omni_rag/test_infant_pipeline.py` (integration) passes.
5. `speace omni index --infant` produces infant-source tagged nodes
   (CLI option added; if not added this iteration, use Python import).

## 9. Roadmap

- v2: continuous background poller with bounded memory.
- v2: subscribe to `EventBus` (full push) instead of poll-and-scan.
- v3: spatial + acoustic observational sensors (when authorization and
  sandboxing permit).

---

*End of T173 spec.*
