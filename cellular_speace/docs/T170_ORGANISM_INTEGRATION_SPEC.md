# T170 — Organism Integration: Identity, Homeostasis, Metabolism & Immune System

## Objective

Unify the five core biological properties — identity, homeostasis, metabolism, reproduction, evolution — into a minimal, feature-flagged, incrementally activated organism layer that integrates with the existing orchestrator and cellular brain subsystems.

## Background

SPEACE already has robust implementations under `cellular_brain/organism/` (T59 — lifecycle, bus, coordinator, registry, state synthesizer), `cellular_brain/metabolism/` (T58 — energy/resource tracking), and `cellular_brain/immune/` (pattern anomaly detector, clone deviation monitor, immune response engine, digital immune controller). However:

- Three top-level namespace directories (`speace_core/organism/`, `speace_core/metabolism/`, `speace_core/immune/`) were empty placeholders.
- The orchestrator had no awareness of the organism or metabolism layers.
- No unified identity vector or self/non-self boundary existed.
- No metabolic cycle (energy acquisition → transformation → waste) connected the pieces.
- No waste clearance engine existed.
- All genome defaults for autonomous drives, homeostatic drive, and identity kernel were disabled.

## Architecture

### Layer Overview

```
┌────────────────────────────────────────────────────────┐
│                    Orchestrator                        │
│  tick cycle: organism → immune → metabolic → identity  │
└────────────────────────────────────────────────────────┘
         │              │              │
         ▼              ▼              ▼
┌──────────────┐ ┌──────────┐ ┌────────────────┐
│   Organism   │ │  Immune  │ │   Metabolism   │
│  Facade      │ │  Facade  │ │   Facade       │
│              │ │          │ │                │
│ • Identity   │ │ • Pattern│ │ • Metabolic    │
│   vector     │ │   anomaly│ │   Cycle        │
│ • Self/non-  │ │ • Clone  │ │ • Waste        │
│   self       │ │   monitor│ │   Clearance    │
│ • Lifecycle  │ │ • Immune │ │                │
│ • Digest     │ │   engine │ │                │
└──────────────┘ └──────────┘ └────────────────┘
```

### Identity Vector

A 10-dimensional vector with fixed, defined semantics:

| Index | Name | Range | Default | Description |
|-------|------|-------|---------|-------------|
| 0 | coherence_phi | [0,1] | 0.0 | Coherence measure from IdentityKernel |
| 1 | energy_level | [0,1] | 0.0 | Normalized energy/resource level |
| 2 | developmental_stage_norm | [0,1] | 0.0 | Normalized cognitive stage progress |
| 3 | clone_count_norm | [0,1] | 0.0 | Normalized clone count |
| 4 | narrative_coherence | [0,1] | 0.0 | Narrative engine coherence score |
| 5 | metabolic_mode_norm | [0,1] | 0.0 | Normalized metabolic mode |
| 6 | health_score | [0,1] | 0.0 | Aggregate health metric |
| 7 | identity_divergence | [0,1] | 0.0 | Cumulative divergence from prior identity |
| 8 | self_model_consistency | [0,1] | 0.0 | SelfModel consistency score |
| 9 | bcel_coverage | [0,1] | 0.0 | Ratio of BCEL equivalences tested |

Self/non-self boundary: Euclidean distance < configurable threshold (default 0.15).

## Components

### `Organism` Facade (speace_core/organism/organism_facade.py)

Unifies `GenomeIdentity`, `NodeIdentityManager`, `IdentityKernel`, `SelfModel`, `SelfModelEngine`, and `OrganismLifecycleManager` behind a single `Organism` class.

- `update(identity_kernel_state, self_model_state, energy_level, ...)` — builds the 10D identity vector from subsystem states.
- `is_self(candidate_vector, threshold=0.15)` — Euclidean distance check.
- `self_distance(candidate_vector)` — raw distance for logging/debugging.
- `get_identity_digest()` — SHA-256 truncated to 8 hex chars; deterministic.
- `snapshot()` — serializable dict of all state.
- Lifecycle management: delegates to `OrganismLifecycleManager` with valid transitions: `formation → active → conservation → recovery → critical`.

### `MetabolicCycle` (speace_core/metabolism/metabolic_cycle.py)

Simulates energy acquisition, transformation, and waste per tick.

- **Acquisition**: base (1.0) + neural (0.001/neuron) + episodic (0.002/episode) + assembly (0.001/assembly)
- **Transformation**: 0.002 per active neuron (converted to energy)
- **Waste computation**: 0.01 * energy_acquired (baseline) + 0.005 per active episode
- `tick(orchestrator)` — acquires, transforms, computes waste, clears, stores energy.
- `snapshot()` — serializable dict.

### `WasteClearanceEngine` (speace_core/metabolism/waste_clearance.py)

Manages accumulation and periodic removal of metabolic waste.

- Scan interval: clear waste every `scan_interval_ticks` (default 10).
- **Forced clearance**: if `pending_waste > max_waste_before_forced` (default 0.3), clear immediately regardless of scan interval.
- Clearance rate: `clearance_rate` per tick (default 0.01).
- Waste is capped at `max_waste` (default 1.0).

### Facade `__init__` Files

- `speace_core/organism/__init__.py` — re-exports `OrganismLifecycleManager`, `OrganismBus`, `lifecycle models`, plus the new `Organism` and `OrganismFacade`.
- `speace_core/metabolism/__init__.py` — re-exports T58 modules, plus `MetabolicCycle` and `WasteClearanceEngine`.
- `speace_core/immune/__init__.py` — re-exports all 4 `cellular_brain/immune/` modules.

### Orchestrator Integration

- New boolean flags: `organism_enabled`, `metabolic_cycle_enabled` (both default `False`).
- Init block creates `_organism = Organism(genome)` and `_metabolic_cycle = MetabolicCycle(genome)` after `IdentityKernel` creation.
- Tick entry runs after `IdentityKernel.tick()` and before `GlobalWorkspace`:
  1. `self._organism.update(...)` — builds identity vector from current kernel state.
  2. `self._metabolic_cycle.tick(self)` — runs metabolic acquisition/transformation/waste.

### Genome Changes

- `autonomous_drives.yaml`: enabled with conservative setpoints (`self_preservation=0.7`, `homeostatic_equilibrium=0.7`, `adaptive_exploration=0.3`).
- `dynamics_substrate.yaml`: `homeostatic_drive` enabled with setpoints (`survival=0.5`, `stability=0.6`).
- `homeostasis.yaml`: added `hysteresis` block (`deadband_fraction=0.05`, `min_dwell_ticks=3`).
- `default_genome.yaml`: added `identity_kernel` enabled in `minimal` mode.

## Governance & Safety

- All new features are opt-in via feature flags (`organism_enabled`, `metabolic_cycle_enabled`).
- Identity vector is informational (logging, anomaly detection) — it does not gate any execution by default.
- Self/non-self boundary is advisory; no autonomous rejection is triggered by it.
- Waste clearance forced threshold prevents runaway waste accumulation.
- No changes to immune system effectiveness; facade is purely re-export.
- Existing organism lifecycle (T59) remains the authority for lifecycle transitions.

## BCEL Equivalences

Three new entries in the BCEL catalog (see `SPEACE_BCEL_DESIGN.md`):

1. **Identity vector / self-nonself boundary** — functional constraint: identity preservation through change, non-local coherence tolerance.
2. **Metabolic cycle** — functional constraint: resource allocation by demand, interconnection efficiency.
3. **Waste clearance** — functional constraint: programmed removal threshold, destructive entropy reduction.

## Acceptance Criteria

1. `Organism` facade creates, updates, and snapshots correctly with 10D identity vector.
2. Self/non-self boundary correctly identifies identical and different vectors.
3. Identity digest is deterministic and stable for identical states.
4. Lifecycle property returns current lifecycle state from T59.
5. `MetabolicCycle` produces non-zero energy after a tick (acquisition > transformation base).
6. Waste accumulates and is cleared at scan interval or forced above threshold.
7. Facade `__init__` files import without errors.
8. Orchestrator creates organism and metabolic cycle objects when enabled.
9. Orchestrator tick calls organism update and metabolic cycle tick (in order) when enabled.
10. All genome YAML files parse without schema errors.
11. BCEL catalog entries exist for identity, metabolism, and waste clearance.
12. No regressions in existing T59, T58, immune, or identity kernel tests.
