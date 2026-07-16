# T171 — DNA ↔ Neural-Synaptic Periodic Table Binding

**Document ID:** SPEACE-SPEC-T171
**Status:** Draft v1
**Author:** Architect agent
**Related:** `species_orientation.yaml`, `docs/SPEACE_BCEL_DESIGN.md`, `docs/SPEACE_OMNI_RAG_ARCHITECTURE.md`
**Scope:** Read-only on constitutional paths; additive on `speace_core/omni_rag/`.

---

## 1. Purpose

`species_orientation.informational_principles` (six constitutional invariants) is
the **source of truth** for *why* a module exists. Today there is no formal
binding between these invariants and the periodic trends encoded in
`NeuralPeriodicTable`. This spec:

1. Maps each of the six invariants to at least one `PeriodicTrendGene` /
   interaction law that codifies it as a *functional constraint* (BCEL-design §3).
2. Establishes a **mechanical** invariant test (A2): a trend removal must
   degrade an associated `ILF_METRIC` node, otherwise the binding is decorative.
3. Makes the invariants **queryable** through the Omni-RAG cognitive graph so
   agents can answer "which periodic trend protects R_renorm?" in one query.

This is a *cognitive infrastructure* task, not an expansion task. Per
`docs/diagnosi_speace.md:1-5`, the next evolution is **stabilization**, not
new biology. The expected output is a *few added tests + a few added graph
nodes*, no new cognitive modules.

## 2. Constitutional anchors (read-only)

From `species_orientation.yaml:133-180`:

| Symbol | Invariant | Metric | Direction |
|--------|-----------|--------|-----------|
| `U(1)_coh` | coherence_preservation | `coherence_phi` | maximize |
| `S_ent`    | destructive_entropy_reduction | `systemic_entropy` | minimize |
| `V_gen`    | generative_variability_preservation | `generative_variability` | maintain above threshold |
| `Diff(F)`  | interconnection_efficiency | `network_interconnection_index` | maximize |
| `D_nonlocal` | nonlocal_decoherence_tolerance | `decoherence_stability_margin` | maintain above threshold |
| `R_renorm` | identity_preservation_through_change | `identity_kernel_distance` | minimize |

## 3. Periodic trends available today

`NeuralPeriodicTable` (read in `neural_periodic_table.py:81-129`) currently
exposes three baseline trends:

| Trend | Across period | Down group | Functional role |
|-------|--------------|------------|-----------------|
| electronegativity | increases | decreases | preferential signal routing |
| ionization_energy | increases | decreases | activation cost |
| atomic_radius | decreases | increases | receptive-field size |

Plus `predict_connection` returning `compatibility / strength / polarity /
plasticity / reciprocal`. The PeriodicLaw additionally encodes `noise_amplitude
= 0.05` and accepts `_safe_eval_expression` for arbitrary trend strings.

DNA already provides `PeriodicTableGeneSet` with `PeriodicTrendGene`,
`ValenceRuleGene`, `ReactionRuleGene` (imported at `periodic_law.py:24-31`).
These are the binding carriers.

## 4. Binding mapping (six invariants → six trends)

Each binding is **functional**: the trend keeps the organism stable under
removal of the underlying accidental biological machinery (BCEL-design §3).

| Invariant | Periodic representation | Mathematical form | Element mapping | ILF test (positive ↔ removal = degrade) |
|-----------|-------------------------|-------------------|-----------------|---------------------------------------|
| `U(1)_coh` | **coherence_trend** (across period) | `0.5 + 0.5 * (1 - abs(g - g_mid) / 9)` — peaks at mid-group, decays at the borders, mimicking thalamic relaying attention phase-locking | `EXECUTIVE_LIMBIC ↔ NOBLE_BACKGROUND` | `coherence_phi` drops ≥ 5 % when trend removed |
| `S_ent`    | **gain_decay_trend**     | `exp(-decay_per_spike * n)` — short-term depression from `catalog.py:55-67` | `REGULATORY_INHIBITORY ↔ S_BLOCK` | `systemic_entropy` rises ≥ 5 % when trend removed |
| `V_gen`    | **plasticity_trend**     | `0.4 + 0.6 * (p / 7)` — deeper periods more plastic | `EXECUTIVE_PFC ↔ ASSOCIATION_SEMANTIC` | `generative_variability` falls below threshold |
| `Diff(F)`  | **affinity_trend**       | `1.0 - abs(z1 - z2) / 30.0` — closeness favours connection; already in `_add_affinities` (`neural_periodic_table.py:217-239`) | all ↔ all | `network_interconnection_index` drops ≥ 5 % |
| `D_nonlocal` | **rate_limit_trend**   | `1.0 / (1.0 + rate * 0.01)` — refractory-style `catalog.py:179-199` | `EXECUTIVE_BRAINSTEM` | `decoherence_stability_margin` falls below threshold |
| `R_renorm` | **identity_anchor_trend** | `bce(mid, e) < theta` — identity vector distance from kernel center; identity equivalent at `catalog.py:100-128` | `EXECUTIVE_DMN ↔ NOBLE_BACKGROUND` | `identity_kernel_distance` rises ≥ 5 % |

## 5. Implementation plan (read-only / additive)

### 5.1 `speace_core/dna/genome/core/dna_periodic_binding.yaml` (additive)

```yaml
dna_periodic_binding:
  - invariant: coherence_preservation
    symbol: U(1)_coh
    trend_name: coherence_trend
    expression: "0.5 + 0.5 * (1 - abs(g - 9.5) / 9)"
    element_pair: ["EXECUTIVE_LIMBIC", "NOBLE_BACKGROUND"]
    ilf_metric: coherence_phi
    test_direction: maximize

  - invariant: destructive_entropy_reduction
    symbol: S_ent
    trend_name: gain_decay_trend
    expression: "pow(2.71828, -0.05 * n)"
    element_pair: ["REGULATORY_INHIBITORY", "S_BLOCK"]
    ilf_metric: systemic_entropy
    test_direction: minimize

  - invariant: generative_variability_preservation
    symbol: V_gen
    trend_name: plasticity_trend
    expression: "0.4 + 0.6 * (p / 7.0)"
    element_pair: ["EXECUTIVE_PFC", "ASSOCIATION_SEMANTIC"]
    ilf_metric: generative_variability
    test_direction: maintain

  - invariant: interconnection_efficiency
    symbol: Diff(F)
    trend_name: affinity_trend
    expression: "1.0 - abs(z1 - z2) / 30.0"
    element_pair: ["ALL", "ALL"]
    ilf_metric: network_interconnection_index
    test_direction: maximize

  - invariant: nonlocal_decoherence_tolerance
    symbol: D_nonlocal
    trend_name: rate_limit_trend
    expression: "1.0 / (1.0 + rate * 0.01)"
    element_pair: ["REGULATORY_BRAINSTEM", "REGULATORY_INHIBITORY"]
    ilf_metric: decoherence_stability_margin
    test_direction: maintain

  - invariant: identity_preservation_through_change
    symbol: R_renorm
    trend_name: identity_anchor_trend
    expression: "1.0 if 0.0 < abs(mid - e) < 0.4 else 0.0"
    element_pair: ["EXECUTIVE_DMN", "NOBLE_BACKGROUND"]
    ilf_metric: identity_kernel_distance
    test_direction: minimize
```

**Criticità:** questo YAML è *read-only* per il flusso di esecuzione — viene
solo caricato nei test A2. **Non** viene passato automaticamente a
`PeriodicLaw` nel ciclo produttivo (per evitare auto-modifica
dell'organismo in modalità A/B).

### 5.2 OMNI-RAG nodes (additive su percorso *review preferred*)

`scripts/register_dna_periodic_binding.py` (in `scripts/`, non in
`speace_core/`):

- crea 6 nodi `NodeType.METRIC` con id `ilf.coherence_phi`,
  `ilf.systemic_entropy`, … taggati `dna_periodic_binding`,
  `informational_principle:<symbol>`.
- crea 6 nodi `NodeType.CONSTRAINT` uno per trend, con
  `metadata.expression` ed `metadata.element_pair`.
- 6 archi `CONSTRAINTS → METRIC` con `RelationType.CONSTRAINS`.

### 5.3 Test `tests/dna/test_dna_periodic_table_binding.py`

Vedi task **A2**.

## 6. What this spec explicitly forbids

- ❌ **NO** writes to `species_orientation.yaml`.
- ❌ **NO** writes to `orchestrator.py`.
- ❌ **NO** writes to `dna/genome/core/species_orientation.yaml`.
- ❌ **NO** auto-injection of trends into `PeriodicLaw` at runtime in this
  iteration. Trends are *registered as constraints*, not *activated*.
  Activation comes only after a future human review (per `AGENTS.md:59`).

## 7. Acceptance criteria

1. `docs/T171_DNA_PERIODIC_TABLE_BINDING_SPEC.md` checked in.
2. `speace_core/dna/genome/core/dna_periodic_binding.yaml` written.
3. `speace omni index` includes the new `CONSTRAINT` and `METRIC` nodes.
4. `tests/dna/test_dna_periodic_table_binding.py` passes.
5. `omni-query "informational_principle:R_renorm"` returns ≥ 1 `CONSTRAINT`
   node + 1 `METRIC` node.

## 8. Roadmap (post-human-review, future)

- v2: render these 6 trends real `PeriodicTrend` objects in `PeriodicLaw`,
  gated by a kill-switch in `species_orientation.dev_flags`.
- v3: drive trend tuning from `digital_rna` (epigenetic modulation of
  trend parameters) once governance policy allows.

---

*End of T171 spec.*
