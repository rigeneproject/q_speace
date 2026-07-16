# T174 — BCEL Equivalence for the Ten Cognitive Factors

**Document ID:** SPEACE-SPEC-T174
**Status:** Draft v1
**Author:** Architect agent
**Related:** T172 (telescope), `species_orientation.yaml`, `docs/SPEACE_BCEL_DESIGN.md`
**Scope:** Additive on `speace_core/bcel/catalog.py` (does **not** edit existing entries).

---

## 1. Purpose

The BCEL catalog at `speace_core/bcel/catalog.py` (read in part) registers
biological-digital equivalences for *organic* components — synapse,
homeostasis, immune system, metabolism, apoptosis, etc. The ten cognitive
factors from the analysis (working memory, speed, pattern, knowledge,
abstraction, relational reasoning, metacognition, attention, motivation,
flexibility) are *not yet* represented there. This spec adds them so that:

1. Each factor has a canonical name + invariant mapping (the **why**).
2. The stress-tester (`speace bcel-stress-test`) can be run on each factor
   by name.
3. The Omni-RAG BCEL graph `omni-query` covers the full cognitive stack.

## 2. Constraint taxonomy

For each cognitive factor we follow BCEL-design §3:

- **Removed (accidental)** — any property that would have existed *only*
  in carbon chemistry (slow diffusion, thermal noise, vesicular depletion).
- **Kept (functional)** — any mathematical rule that *preserves the
  informational invariant* the cognitive factor protects.

## 3. Ten entries

### 3.1 Cognitive Factor 1 — Working Memory

```python
CyberneticEquivalent(
    component_name="cognitive factor: working memory",
    preserved_function="maintain multiple items active simultaneously for relational comparisons",
    removed_constraints=[
        "limited neuron firing rate in biological cortex",
        "synaptic interference from competing representations",
        "slow prefrontal bandwidth",
    ],
    kept_constraints=[
        FunctionalConstraint(
            name="wm_slot_span",
            invariant="generative_variability_preservation",
            biological_form="prefrontal cortex holds N items in active state",
            mathematical_form="bounded list of MemorySlot objects",
            parameters={"max_slots": 4, "overflow_threshold": 0.9},
            stability_test="overflow_increases_entropy",
        ),
    ],
    digital_implementation="cognition.subgrid_attention_working_memory.SubgridAttentionWorkingMemory",
    configuration={"max_slots_initial": 4},
)
```

### 3.2 Cognitive Factor 2 — Processing Speed

```python
CyberneticEquivalent(
    component_name="cognitive factor: processing speed",
    preserved_function="complete comparison/classification/inference operations within a bounded cognitive budget",
    removed_constraints=[
        "action potential propagation delay",
        "myelination quality variability",
        "neurotransmitter clearance latency",
    ],
    kept_constraints=[
        FunctionalConstraint(
            name="bounded_cost_per_tick",
            invariant="destructive_entropy_reduction",
            biological_form="metabolic budget per cognitive operation",
            mathematical_form="cognitive_cost_model with per-module cost caps",
            parameters={"cost_cap_per_tick": 0.5, "rolling_window": 200},
            stability_test="cost_rising_triggers_throttle",
        ),
    ],
    digital_implementation="metabolism.cognitive_cost_model.CognitiveCostModel",
    configuration={"rolling_window": 200},
)
```

### 3.3 Cognitive Factor 3 — Pattern Recognition

```python
CyberneticEquivalent(
    component_name="cognitive factor: pattern recognition",
    preserved_function="compress many examples into fewer, reusable schemas",
    removed_constraints=[
        "limited visual working memory in V1",
        "temporal cortex pattern-binding latency",
    ],
    kept_constraints=[
        FunctionalConstraint(
            name="abstraction_compression_ratio",
            invariant="generative_variability_preservation",
            biological_form="expert sees 3 structures / 2 anomalies / 1 hidden rule",
            mathematical_form="concept_graph abstraction ratio",
            parameters={"min_compression_ratio": 0.05},
            stability_test="low_compression_yields_more_entropy",
        ),
    ],
    digital_implementation="cognition.concept_graph + cognition.arc_primitive_discovery_engine",
    configuration={"min_compression_ratio": 0.05},
)
```

### 3.4 Cognitive Factor 4 — Prior Knowledge

```python
CyberneticEquivalent(
    component_name="cognitive factor: prior knowledge",
    preserved_function="route new inputs through an existing conceptual network",
    removed_constraints=[
        "hippocampal indexing delay",
        "slow neocortical myelination of memory traces",
    ],
    kept_constraints=[
        FunctionalConstraint(
            name="memory_link_density_floor",
            invariant="interconnection_efficiency",
            biological_form="semantic network grows denser with expertise",
            mathematical_form="edge_count / node_count^2",
            parameters={"min_density_floor": 0.0},
            stability_test="density_below_floor_stalls_abstraction",
        ),
    ],
    digital_implementation="evolutionary_memory + semantic_memory_store",
    configuration={"min_density_floor": 0.0},
)
```

### 3.5 Cognitive Factor 5 — Abstraction

```python
CyberneticEquivalent(
    component_name="cognitive factor: abstraction",
    preserved_function="climb several levels of generality without losing fidelity",
    removed_constraints=[
        "single-shot semantic encoding per neuron assembly",
        "limited range of categorical depth in IT cortex",
    ],
    kept_constraints=[
        FunctionalConstraint(
            name="abstraction_levels_active",
            invariant="generative_variability_preservation",
            biological_form="expert can move apple → fruit → organism → strategy",
            mathematical_form="HierarchicalConceptAbstractionLayer.active_levels()",
            parameters={"min_active_levels": 2},
            stability_test="levels_below_min_reduces_flexibility_score",
        ),
    ],
    digital_implementation="cognition.hierarchical_concept_abstraction_layer",
    configuration={"min_active_levels": 2},
)
```

### 3.6 Cognitive Factor 6 — Relational Reasoning

```python
CyberneticEquivalent(
    component_name="cognitive factor: relational reasoning",
    preserved_function="detect cycles, feedback, indirect causation in causal graphs",
    removed_constraints=[
        "limited short-term memory in dlPFC",
        "linear chaining bias in human reasoning",
    ],
    kept_constraints=[
        FunctionalConstraint(
            name="causal_cycle_detection",
            invariant="nonlocal_decoherence_tolerance",
            biological_form="A influences B, B influences C, C modulates A",
            mathematical_form="cycle_count() on TemporalCausalReasoningLayer",
            parameters={"min_cycles_for_relational": 1},
            stability_test="absence_of_cycles_marks_symbolic_only_reasoning",
        ),
    ],
    digital_implementation="cognition.temporal_causal_reasoning_layer",
    configuration={"min_cycles_for_relational": 1},
)
```

### 3.7 Cognitive Factor 7 — Metacognition

```python
CyberneticEquivalent(
    component_name="cognitive factor: metacognition",
    preserved_function="monitor own reasoning quality and reduce errors",
    removed_constraints=[
        "humans confabulate when introspecting",
        "cognitive reappraisal lag (seconds)",
    ],
    kept_constraints=[
        FunctionalConstraint(
            name="metacognitive_probe_rate",
            invariant="identity_preservation_through_change",
            biological_form="self-questioning: am I understanding? what is weak?",
            mathematical_form="metacognitive_probes_per_minute ≥ threshold",
            parameters={"min_probes_per_minute": 0.1},
            stability_test="below_threshold_doubles_error_rate_in_stress",
        ),
    ],
    digital_implementation="metacognition.metacognitive_monitor",
    configuration={"min_probes_per_minute": 0.1},
)
```

### 3.8 Cognitive Factor 8 — Sustained Attention

```python
CyberneticEquivalent(
    component_name="cognitive factor: sustained attention",
    preserved_function="suppress distractions while building a mental model",
    removed_constraints=[
        "default-mode network interruption frequency",
        "thalamic burst-mode dominance in drowsiness",
    ],
    kept_constraints=[
        FunctionalConstraint(
            name="attention_gap_budget",
            invariant="coherence_preservation",
            biological_form="thalamic tonic mode suppresses distractor inputs",
            mathematical_form="attention_gap_count ≤ 2 per 200 ticks",
            parameters={"gap_budget": 2},
            stability_test="gap_overshoot_degrades_coherence_phi",
        ),
    ],
    digital_implementation="regions.thalamic_relay_engine",
    configuration={"gap_budget": 2},
)
```

### 3.9 Cognitive Factor 9 — Motivation

```python
CyberneticEquivalent(
    component_name="cognitive factor: motivation",
    preserved_function="allocate cognitive resources by internal drive pressure",
    removed_constraints=[
        "hormonal diffusion latency",
        "metabolic cost of dopamine release",
    ],
    kept_constraints=[
        FunctionalConstraint(
            name="drive_pressure_cap",
            invariant="identity_preservation_through_change",
            biological_form="homeostatic drives stabilise allocation",
            mathematical_form="max(setpoint for drives) ≤ cap",
            parameters={"max_setpoint_cap": 0.8},
            stability_test="overshoot_pushes_exploratory_drift",
        ),
    ],
    digital_implementation="dna.genome.morphology.autonomous_drives",
    configuration={"max_setpoint_cap": 0.8},
)
```

### 3.10 Cognitive Factor 10 — Cognitive Flexibility

```python
CyberneticEquivalent(
    component_name="cognitive factor: cognitive flexibility",
    preserved_function="switch perspective (math/bio/econ/philo/info) on demand",
    removed_constraints=[
        "task-set reconfiguration lag (200-500 ms)",
        "anterior cingulate switch-cost penalty",
    ],
    kept_constraints=[
        FunctionalConstraint(
            name="perspective_switch_rate",
            invariant="generative_variability_preservation",
            biological_form="set-shifting ability",
            mathematical_form="perspective_switches_per_minute ≥ threshold",
            parameters={"min_switches_per_minute": 0.2},
            stability_test="below_threshold_impairs_synthesis",
        ),
    ],
    digital_implementation="cognition.mmapr_council",
    configuration={"min_switches_per_minute": 0.2},
)
```

## 4. Stress-test plan

For each of the ten entries, write a `tests/bcel/test_cognitive_factors/test_<factor>.py`
that:

1. Instantiates the digital implementation in **degraded** mode (mock with
   parameter below the kept-constraint threshold).
2. Asserts that the stability test signature fires (a metric that the
   cognitive factor is supposed to protect flips its direction).

These are simple unit tests; they do not require a live organism.

## 5. What this spec forbids

- ❌ NO edits to existing BCEL entries.
- ❌ NO writes to `species_orientation.yaml`.
- ❌ NO new cognitive modules — only *registrations*.

## 6. Acceptance criteria

1. `docs/T174_BCEL_COGNITIVE_FACTORS_SPEC.md` checked in.
2. `speace_core/bcel/catalog.py` exposes 10 new
   `cognitive_factor_*_equivalent()` functions.
3. `speace bcel-catalog | grep "cognitive factor"` returns 10 lines.
4. `tests/bcel/test_cognitive_factors/test_*.py` (10 files) all pass.
5. `pytest tests/bcel/` reports "10 cognitive factor tests passed".

---

*End of T174 spec.*
