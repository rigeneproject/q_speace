# SPEACE — Biological-Cybernetic Equivalence Layer (BCEL) Design

## 1. Purpose

SPEACE is a distributed digital-physical organism. Its long-term risk is not a
lack of modules, but the accumulation of bio-mimetic complexity that copies
mechanisms born for carbon-chemistry constraints that do not exist in silicon.

The **Biological-Cybernetic Equivalence Layer (BCEL)** is the architectural
filter that translates biological structures into digital principles without
falling into two opposite errors:

- **Naive biomimesis** — copying timers, molecules, or organs literally.
- **Blind engineering** — ignoring the stabilizing functions that evolution
discovered.

## 2. Guiding question

> *Which informational invariant is this biological structure protecting, and
> what is the simplest digital implementation that preserves the same
> invariant?*

The invariants are anchored in the
`species_orientation.informational_principles` genome block:

- `coherence_preservation` (U(1)_coh)
- `destructive_entropy_reduction` (S_ent)
- `generative_variability_preservation` (V_gen)
- `interconnection_efficiency` (Diff(F))
- `nonlocal_decoherence_tolerance` (D_nonlocal)
- `identity_preservation_through_change` (R_renorm)

## 3. Constraint taxonomy

For every biological construct the BCEL runs a two-way classification:

```text
Vincolo Biologico Rilevato
        │
        ├──▶ Accidental (limit of carbon)  ──▶ remove / optimize in silicon
        │
        └──▶ Functional (emergent stabilizer) ──▶ keep as mathematical rule
```

### Accidental constraints

Properties that exist only because organic matter is wet, noisy, thermal, and
spatially constrained:

- slow macromolecular diffusion
- thermal degradation
- ion-channel latency
- limited energy budget per neuron

### Functional constraints

Restrictions that the system uses to stay stable:

- synaptic delay as a low-pass filter against epileptic oscillations
- short-term depression as gain control
- slow protein synthesis as a statistical sampling / pruning gate
- refractory periods as spike-rate limiting

## 4. Translation pipeline

The BCEL produces digital equivalents through a four-stage pipeline:

```text
Biological Structure
        │
        ▼
[ Functional Abstraction ]
        │
        ▼
(Accidental vs Functional classification)
        │
        ▼
[ Digital Synthesis ]
        │
        ▼
SPEACE architecture: DNA → Digital RNA → Periodic Table → Agents
```

- **DNA** — immutable constitutional invariants and orientation.
- **Digital RNA** — context-dependent working copy; volatile sandbox that
  protects DNA from operational corruption.
- **Neural-Synaptic Periodic Table** — dynamic interaction laws that encode
  functional constraints as tunable mathematical rules.
- **Agents / Circuits** — the executing phenotype.

## 5. Runtime architecture

```text
speace_core/
├── dna/                     # Digital DNA (SharedGenome)
├── digital_rna/             # Transcriptome + expression engine
│   ├── engine.py            # builds the transcriptome from DNA + epigenetics
│   ├── workspace_adapter.py # pushes transcriptome to GlobalWorkspace
│   └── periodic_table_adapter.py # configures PeriodicLaw
├── bcel/                    # Biological-Cybernetic Equivalence Layer
│   ├── catalog.py           # catalog of biological-digital equivalences
│   ├── classifier.py        # accidental vs functional constraint classifier
│   ├── synthesizer.py       # generates cybernetic equivalents
│   └── stress_tester.py     # validates a constraint by perturbation
└── cellular_brain/neuroperiodic/
    └── functional_constraint_law.py # adds functional-constraint laws to PeriodicLaw
```

## 6. Example: synaptic delay

| Phase | Output |
|-------|--------|
| Biological structure | Chemical synaptic delay (~1 ms) |
| Function | Low-pass filter / anti-oscillation stabilizer |
| Accidental part | Diffusion of neurotransmitters across the cleft |
| Functional part | Rate-limiting property that prevents runaway feedback |
| Digital synthesis | `LeakyIntegrator` + `RateLimiter` in PeriodicLaw |
| Integration | `functional_constraint_law` adds a rule: if pre→post firing rate > θ, apply decay |

## 7. Acceptance criteria

- Every new bio-inspired module must pass through the BCEL catalog.
- Functional constraints must be encoded in `PeriodicLaw`, not as ad-hoc patches.
- The `Digital RNA` must be the only volatile layer between DNA and execution.
- All translations must be stress-tested before merge.
- The genome orientation block remains the source of truth for "why" a module exists.

## 8. Registered equivalences

The following entries are registered in `speace_core/bcel/catalog.py`:

### Identity Vector / Self-Nonself Boundary

| Phase | Output |
|-------|--------|
| Biological structure | Immune self-recognition / cellular identity markers (MHC) |
| Function | Distinguish self from non-self to prevent autoimmunity |
| Accidental part | MHC polymorphism, clonal selection latency |
| Functional part | Identity preservation through change; tolerance for diversity |
| Digital synthesis | 10D identity vector + Euclidean distance threshold (`is_self`, `self_distance`) |
| Integration | `Organism.identity_vector` built from kernel state each tick; advisory check only |

### Metabolic Cycle (Energy Acquisition & Transformation)

| Phase | Output |
|-------|--------|
| Biological structure | Cellular metabolism (glycolysis → Krebs cycle → oxidative phosphorylation) |
| Function | Extract energy from resources, transform for use, produce waste |
| Accidental part | ATP yield per glucose, enzyme kinetics, mitochondrial density |
| Functional part | Resource allocation weighted by activity; interconnection efficiency |
| Digital synthesis | `MetabolicCycle.tick()`: acquire → transform → waste → store |
| Integration | Called after organism update in orchestrator tick; energy stored in `_energy_reserve` |

### Waste Clearance

| Phase | Output |
|-------|--------|
| Biological structure | Lysosomal degradation / autophagy / excretory system |
| Function | Remove metabolic byproducts that would poison the system |
| Accidental part | Slow enzyme degradation rates, limited lysosome capacity |
| Functional part | Programmed removal threshold prevents runaway entropy accumulation |
| Digital synthesis | `WasteClearanceEngine`: scan-interval clearance + forced clearance above threshold |
| Integration | Called by `MetabolicCycle.tick()`; forced clearance prevents freeze when waste > limit |

## 9. Next immediate tasks

1. Implement `speace_core/bcel/` core classes.
2. Implement `speace_core/digital_rna/` transcriptome engine.
3. Add `FunctionalConstraintLaw` to the neural-synaptic periodic table.
4. Wire `Digital RNA` into `GlobalWorkspace` and `PeriodicLaw`.
5. Add unit tests and update the capability assessment.
6. Register identity vector, metabolic cycle, and waste clearance equivalences.
