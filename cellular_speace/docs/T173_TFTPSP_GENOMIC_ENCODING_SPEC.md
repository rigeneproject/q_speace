# T173 — TFTpsp-as-DNA Genomic Encoding

**Document ID:** SPEACE-T173-SPEC
**Version:** 1.0
**Status:** Draft
**Date:** 2026-06-27
**Owner:** dna / digital_rna / bcel / omni_rag
**Layer:** L0–L5 (DNA → RNA → Periodic Table → Agents → Observatory)

---

## 1. Purpose and Scope

The 33 TFT Problem-Solving Parameters (TFTpsp) — published by the
Rigene Project as the orientative genome of the "Technological Fields
Theory" (TFT) — were conceived as a **descriptive parameter list**: an
AI-consultable catalogue that an external LLM (GPT, LaMDA, Ernie, Bard)
could re-elaborate in a prompt. They were never written as an **executable
genome**.

This document specifies the engineering translation that closes that gap.
Each TFTpsp becomes a **Digital Gene** with:

| Field | Meaning | Biological analog |
|---|---|---|
| `gene_id` | stable symbol (`tftpsp_001_tft`) | locus |
| `tft_index` | 1..33 original numbering | chromosome position |
| `name` | full parameter name + acronym | gene name |
| `function` | what the gene does in the organism | protein function |
| `activation_conditions` | context predicates that increase expression | promoter / enhancer |
| `interactions` | typed edges to other genes | regulatory network |
| `priority` | 0..1 base expression rate | expression level |
| `constraints` | functional invariants that must be preserved | functional constraint (BCEL) |
| `epigenetic_mechanisms` | tag-based modulators | methylation / acetylation |
| `mutation_policy` | how the gene can change | mutation rules |
| `efficacy_metric` | observable outcome for audit | fitness contribution |

The TFTpsp cease to be a list of ideas and become the **executable Digital
DNA of SPEACE**: queryable, BCEL-filtered, RNA-expressed, mutation-capable.

### 1.1 Boundary and non-goals

- The TFTpsp do **not** weaken or override the constitutional invariants
  in `species_orientation.yaml` (informational principles U(1)_coh, S_ent,
  V_gen, Diff(F), D_nonlocal, R_rennorm).
- The TFTpsp do **not** change the autonomous drives or homeostatic setpoints.
- The TFTpsp do **not** extend autonomy to cyber-physical action.
- The TFTpsp may be expressed differently in different contexts (epigenetic
  modulation), but their `function` field is **immutable** like a gene's CDS.
- All mutations to TFTpsp genes go through the existing governance gates:
  counterfactual sandbox → safe architecture patch execution → audit.

## 2. Context Engineering Stack Used

This spec is produced by reading, in order:

1. `AGENTS.md` — agentic mode rules, BCEL workflow, evaluation gates.
2. `docs/SPEACE_BCEL_DESIGN.md` — accidental vs functional constraints.
3. `speace_core/dna/genome/core/species_orientation.yaml` — informational
   principles that bound every TFTpsp gene.
4. `speace_core/dna/genome/default_genome.yaml` — genome composition and
   pattern for new gene sets (periodic_table_genes, cor_genes, quantum_genes).
5. `speace_core/digital_rna/engine.py` and `digital_rna/models.py` — how
   expression profiles are built and pushed to the workspace.
6. `speace_core/bcel/catalog.py` — pattern for registering biological-
   cybernetic equivalences.
7. `docs/SPEACE_OMNI_RAG_ARCHITECTURE.md` — cognitive-node pattern for
   graph-backed indexing.
8. `docs/NEURAL_SYNAPTIC_QUANTUM_IMPLEMENTATION.md` — DNA-driven periodic
   table trend/reaction genes (pattern reused for TFTpsp `reaction_rules`).
9. `docs/T170_ORGANISM_INTEGRATION_SPEC.md`, `T171_NEUROMORPHIC_EVENT_LAYER_SPEC.md`,
   `T172_INFORMATION_VALUE_MODULE_SPEC.md` — recent context-engineering
   deliverables that this spec must integrate with.
10. `docs/List of the 33 TFT problem solving.txt` — the source catalogue
    being encoded.

## 3. Architectural Position

```
                ┌───────────────────────────────┐
                │   species_orientation.yaml    │   ← constitutional invariants
                └───────────────┬───────────────┘
                                ▼
                ┌───────────────────────────────┐
                │      TFTpspGenome (NEW)      │   ← this spec
                │   33 genes + BCEL catalog     │
                └───────────────┬───────────────┘
                                ▼
                ┌───────────────────────────────┐
                │   Digital RNA — Transcriptome │   ← existing
                │   TFTpspExpressionProfile     │
                └───────────────┬───────────────┘
                                ▼
        ┌───────────────────────┴────────────────────────┐
        ▼                       ▼                        ▼
┌──────────────┐      ┌──────────────────┐      ┌──────────────────┐
│ Global       │      │ Periodic Table   │      │ Cognitive        │
│ Workspace    │      │ (Functional      │      │ Self Observatory │
│              │      │  Constraint Law) │      │                  │
└──────────────┘      └──────────────────┘      └──────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │ Omni-RAG         │
                       │ tftpsp_collector │   ← indexes every gene
                       └──────────────────┘
```

## 4. Data Model — `TFTGene`

`speace_core/dna/tft_gene.py` — Pydantic v2 (using `ConfigDict` per
the Pydantic v2 cleanup task in `diagnosi_speace.md`).

```python
class TFTGene(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    gene_id: str                  # stable symbol, e.g. "tftpsp_001_tft"
    tft_index: int                # 1..33
    name: str                     # full name + acronym in parentheses
    short_label: str              # the canonical short label (TFT, TSFRUTF, ...)
    function: str                 # 1-3 sentences — what this gene DOES
    domain_tags: list[str]        # [technology, society, environment, ...]

    # Activators — promoter/enhancer analog
    activation_conditions: list[ActivationCondition]

    # Regulatory network — other TFTpsp genes this one depends on, gates,
    # inhibits, or supports.
    interactions: list[GeneInteraction]

    # 0..1 base expression; modulates how strongly this gene shows up
    # in the Transcriptome under neutral context.
    priority: float = Field(ge=0.0, le=1.0, default=0.5)

    # Functional constraints — translated from the BCEL catalog's
    # kept_constraints pattern. Each constraint links the gene to
    # one informational principle (coherence_preservation, etc.).
    constraints: list[FunctionalGeneConstraint]

    # Epigenetic rules — tag-driven modulators (methylation/acetylation analog).
    epigenetic_mechanisms: list[EpigeneticRule]

    # Mutation policy — explicit rules for what can change in this gene.
    mutation_policy: MutationPolicy

    # How we measure whether this gene is working.
    efficacy_metric: EfficacyMetric

    # Optional BCEL mapping — points to a CyberneticEquivalent in the BCEL catalog.
    bcel_equivalent: str | None = None
```

### 4.1 Supporting models

```python
class ActivationCondition(BaseModel):
    trigger_tag: str              # "crisis", "innovation", "novelty", ...
    min_signal: float = 0.0       # minimum signal strength required
    boost: float = 1.0            # multiplicative boost when active


class GeneInteraction(BaseModel):
    target_gene_id: str
    relation: Literal[
        "depends_on",     # target must be active for this to operate
        "gates",          # target decides whether this fires
        "inhibits",       # target reduces this gene's expression
        "supports",       # target amplifies this gene
        "contradicts",    # tension to be resolved by arbitration
    ]
    weight: float = 0.5


class FunctionalGeneConstraint(BaseModel):
    name: str
    invariant: Literal[
        "coherence_preservation",
        "destructive_entropy_reduction",
        "generative_variability_preservation",
        "interconnection_efficiency",
        "nonlocal_decoherence_tolerance",
        "identity_preservation_through_change",
    ]
    description: str


class EpigeneticRule(BaseModel):
    tag: str                       # epigenetic tag name
    effect: Literal["boost", "suppress", "silence", "lock_open"]
    modifier: float = 1.0          # multiplicative or threshold
    scope: Literal["global", "context_local"] = "context_local"


class MutationPolicy(BaseModel):
    allowed: bool = False          # by default, TFTpsp genes are read-only
    requires_governance: bool = True
    max_priority_delta_per_cycle: float = 0.05
    changeable_fields: list[str] = []   # which fields can be mutated


class EfficacyMetric(BaseModel):
    metric_name: str               # e.g. "expression_ratio"
    target_direction: Literal["maximize", "minimize", "maintain_above_threshold"]
    threshold: float | None = None
    observation_window_ticks: int = 100
```

## 5. Catalogue — `tftpsp_genome.yaml`

`speace_core/dna/genome/tftpsp/00_tftpsp_genome.yaml` holds the 33
genes. Each entry follows the schema above. The mapping from the
source document is:

| tft_index | gene_id | short_label | BCEL hint |
|---|---|---|---|
| 1 | tftpsp_001_tft | TFT | (descriptive; no body analog) |
| 2 | tftpsp_002_tsfrutf | TSFRUTF | (relational map; no body analog) |
| 3 | tftpsp_003_tables | TFT-TABLES | (analysis method) |
| 4 | tftpsp_004_method_3_666 | M3-666 | (decomposition) |
| 5 | tftpsp_005_tftof | TFTof | (optimization) |
| 6 | tftpsp_006_cfu | CFU | (universal code; coherence_preservation) |
| 7 | tftpsp_007_scttft | sctTFT | (brain/arm/legs — morphology) |
| 8 | tftpsp_008_dna_tft | DNA-TFT | (genetic structure; identity_preservation) |
| 9 | tftpsp_009_tft_os | TFT-OS | (cognitive OS; neuro_os block already exists) |
| 10 | tftpsp_010_tft_culture | TFT-C5.0 | (cultural substrate) |
| 11 | tftpsp_011_projects_666 | PROJ-666 | (project portfolio) |
| 12 | tftpsp_012_scvf | scvf-TFT | (verification — homeostasis analog) |
| 13 | tftpsp_013_plecdf | plecdf-TFT | (paradox resolver — error correction) |
| 14 | tftpsp_014_cif | cif-TFT | (continuous improvement) |
| 15 | tftpsp_015_nes_tft | NES-TFT | (sustainability goal) |
| 16 | tftpsp_016_aimchc | AIMCHC-TFT | (cognitive config — Cattell-Horn-Carroll) |
| 17 | tftpsp_017_fsmpeai | FSMPEAI-TFT | (5 senses — signal_transduction BCEL) |
| 18 | tftpsp_018_5pc | 5PC-SUAEH | (5 planetary crises) |
| 19 | tftpsp_019_pm_tft | PM-TFT | (project mgmt) |
| 20 | tftpsp_020_pcai | PCAI-TFT | (creative thinking) |
| 21 | tftpsp_021_aic | AIC-TFT | (AI consciousness config — corr_or analog) |
| 22 | tftpsp_022_emai | EMAI-TFT | (emotional intelligence) |
| 23 | tftpsp_023_epshcpe | EPSHCPE-TFT | (emergency protocol — immune analog) |
| 24 | tftpsp_024_vapt | vaPT-TFT | (acceleration variable) |
| 25 | tftpsp_025_ifm | IFM-TFT | (multi-feature instances) |
| 26 | tftpsp_026_emsai | EMSAI-TFT | (education) |
| 27 | tftpsp_027_tsteu | TSTEU-TFT | (technium/singularity) |
| 28 | tftpsp_028_prpalgfcai | PRPALGFCAI-TFT | (cognitive phase assimilation) |
| 29 | tftpsp_029_maacai | MAACAI-TFT | (self-awareness config) |
| 30 | tftpsp_030_ldwai | LDWAI-TFT | (web digital lab) |
| 31 | tftpsp_031_rgoaisp | RGOAISPDIPOSCAEWOR-TFT | (order/symmetry/cleanness/aesthetics) |
| 32 | tftpsp_032_caizauma | CAIZAUMAFSPRPEI-TFT | (tool re-purposing) |
| 33 | tftpsp_033_aiscdsagi | AISCDSAGI-TFT | (synchronic coherence — ILF analog) |

The full schema-driven catalogue is delivered in task T173.2.

## 6. Digital RNA Wiring

`RNAExpressionEngine.build_transcriptome()` is extended to also walk
`tftpsp_library.all()` and produce an `RNAExpressionProfile` per TFTpsp
gene. The expression is:

```
expr(gene, ctx) = priority(gene)
                  * Π boost(activation_condition, ctx)
                  * Π modifier(epigenetic_rule, ctx, epigenetic_state)
```

Activation conditions and epigenetic rules are evaluated against the
current `context_state` dict and the active tags returned by
`EpigeneticTagsManager.get_active_tags()`.

This places TFTpsp on equal footing with cell-type expression rules:
both are DNA-coded, both are RNA-transcripted, both are
epigenetically-modulable, neither mutates DNA.

### 6.1 Example contextual activation rules

These are illustrative — the full rule set is produced in the catalogue:

- `crisis` context → boost TFT-18 (5 planetary crises), TFT-23
  (emergency protocol), TFT-12 (verification), TFT-31 (order/symmetry).
- `innovation` context → boost TFT-20 (creative thinking), TFT-32
  (tool re-purposing), TFT-5 (TFTof optimization).
- `novelty` context → boost TFT-20 (PCA), TFT-4 (3-666 method),
  TFT-14 (continuous improvement).
- `governance` context → boost TFT-19 (PM-TFT), TFT-12 (scvf), TFT-13
  (plecdf), TFT-31 (aesthetics).
- `sustainability` context → boost TFT-15 (NES-TFT), TFT-10 (TFT-C5.0),
  TFT-18 (5PC).

### 6.2 Why no unconditional boost?

Some genes (TFT-23 EPSHCPE) describe **emergency protocols**. They must
have **low base priority** and **require an explicit crisis tag** to
activate. This is encoded in `mutation_policy.allowed=False` and the
epigenetic rules — the gene cannot be promoted above a documented
ceiling without an external governance signal. This mirrors biological
tumor-suppressor genes: present, expressed at low level, but require
multiple coordinated signals to lift repression.

## 7. BCEL Integration

Every TFTpsp gene with a clear biological anchor registers a BCEL
catalogue entry using the existing pattern in
`bcel/catalog.py`. Examples:

- **TFT-17 (FSMPEAI — 5 senses + pleasure/emotions)** registers
  `biological_homeostasis + signal_transduction` (pleasure/emotion =
  homeostatic valence; senses = signal_transduction chain).
- **TFT-23 (EPSHCPE — emergency protocol)** registers `immune_response`
  (crisis response analogous to inflammatory containment).
- **TFT-33 (AISCDSAGI — synchronic coherence)** registers
  `dna_rna_equivalent` + `identity_vector_equivalent` (synchronic
  coherence is a coherence-preservation and identity-preservation
  invariant).
- **TFT-14 (cif-TFT — continuous improvement)** registers
  `metabolism_equivalent` (resource-allocation-by-demand).

Genes without a clear biological anchor (TFT-1, TFT-2, TFT-11, …) keep
`bcel_equivalent=None` and are not added to the BCEL catalog — they
are descriptive only and not cybernetic constraints.

## 8. Omni-RAG Collector

`speace_core/omni_rag/collectors/tftpsp_collector.py` exposes each
gene as a `CognitiveNode`:

```
node_type=GENE
attributes: gene_id, tft_index, name, priority, function
edges:
   - (:GENE {gene_id}) -[:CONSTRAINS]-> (:INVARIANT {name})
   - (:GENE {gene_id}) -[:ACTIVATED_BY]-> (:CONTEXT_TAG {name})
   - (:GENE {gene_id}) -[:INTERACTS_WITH {relation, weight}]-> (:GENE)
   - (:GENE {gene_id}) -[:MAPS_TO]-> (:BCEL_EQUIVALENT {name})
```

Queries like `tftpsp` then return all 33 nodes ranked by priority; a
query like `crisis response genes` returns TFT-18, TFT-23, TFT-12,
TFT-31 ordered by their `activation_conditions[boost]` for `crisis`.

## 9. CLI Surface

`speace tftpsp-list` — list the 33 genes with priority.
`speace tftpsp-show <gene_id>` — show full record + current expression.
`speace tftpsp-express <context_key>` — force a context and dump the
resulting Transcriptome slice.
`speace tftpsp-audit` — verify BCEL coverage, expression sanity,
invariant linkage; emit report.

## 10. Mutation & Governance

`MutationPolicy.allowed = False` is the **default** for all TFTpsp
genes. This is consistent with `AGENTS.md §7` — "No autonomous
modification of the species orientation or constitutional invariants
without explicit human approval in the commit message."

When a TFTpsp gene needs to change (e.g. to fix a learned drift), the
governance flow is:

```
propose mutation
    → counterfactual sandbox (T66 / spec)
    → safe architecture patch execution
    → audit (T170 + Omni-RAG)
    → human approval (commit message)
    → apply
```

The `max_priority_delta_per_cycle` enforces small-step evolution:
no gene's priority can shift by more than 0.05 per cycle, mirroring
the small-effect mutations that biological evolution uses to avoid
catastrophic phenotype shifts.

## 11. Acceptance Criteria

- [ ] `tests/dna/test_tft_gene.py` — schema validation, edge cases
      (empty interactions, all constraint types, all mutation policies).
- [ ] `tests/dna/test_tftpsp_library.py` — load the catalogue, validate
      33 entries, indexes by gene_id and tft_index.
- [ ] `tests/digital_rna/test_tftpsp_expression.py` — given contexts,
      verify the correct genes are boosted, including the
      crisis-emergency-protocol gating.
- [ ] `tests/omni_rag/test_tftpsp_collector.py` — index and query.
- [ ] `tests/cli/test_tftpsp_cli.py` — all four sub-commands.
- [ ] `reports/tftpsp_genome_audit.md` — coverage report.
- [ ] All existing tests still pass (0 regression).

## 12. Risks and Limits

- **Drift of intent vs catalog.** The source document is descriptive
  English. The gene functions must be paraphrased to be auditable,
  which may slightly change meaning. Mitigation: the YAML keeps
  the original English description in `function`, and the audit
  report includes a diff view.
- **Crisis-gene false positives.** The emergency protocol gene must
  not activate without explicit governance. The epigenetic rule
  `tag="crisis", effect="lock_open", scope="context_local"` plus
  `MutationPolicy.allowed=False` prevent unintended activation.
- **Catalog bloat.** A 33-gene catalogue is small, but each gene
  has ~10 fields. The YAML is hand-curated and validated on load.
- **Coupling to the broader organism.** Wiring the TFTpsp into the
  RNA engine should not perturb existing cell-type expression. The
  wiring is additive — existing rule iteration is unchanged; the
  TFTpsp iteration is added after.

## 13. Out of Scope (deferred)

- Auto-mutation of TFTpsp priorities based on outcome metrics
  (would require a separate "TFTpsp self-improvement" spec).
- Direct coupling of TFTpsp genes to action execution (would
  conflict with AGENTS.md §7 — physical action governance).
- Translation of the 33 TFTpsp into BCEL equivalences for the
  descriptive-only genes (TFT-1, TFT-2, TFT-3, …).
