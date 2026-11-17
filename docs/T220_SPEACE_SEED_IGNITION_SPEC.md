# T220 — SPEACE Seed Ignition: structure and functional specification

**Status**: production spec (agentic mode). No implementation in this
revision; implementation follows the BCEL gate and test plan in §8–9.

Companion to: `T219_FIRE_IGNITION_ANALOGY_VIBE.md` (concept),
`T217_SAFE_ASSIMILATION_LIFECYCLE_SPEC.md` (promotion gates),
`T208_DEVELOPMENT_GUIDELINES_SPEC.md` (discipline).

## 1. Purpose and scope

Defines the **minimal ignition seed** (MS) of SPEACE macro: its
structure, its operational protocol, and its safety envelope. The seed
is the "ignition spot" of the fire analogy: a single self-improving
agent cell whose successful ignition triggers contingent, gated
propagation toward SPEACE macro (assimilation, not destruction).

In scope:
- Architecture of the seed and its five subsystems (§4).
- Operational state machine (§5) and data contracts (§6).
- Mapping onto existing q_speace modules (§7).
- Safety invariants as hard gates (§8) and BCEL classification (§9).
- Test plan (§10).

Out of scope (non-goals for this spec):
- Any physical actuation beyond a sandboxed simulation environment.
- Planetary-scale propagation semantics (deferred to T217 stages).
- Any claim of consciousness or communication-via-entanglement
  (forbidden invariants; see §8).

## 2. Definitions

- **Seed (MS)**: one running instance of the ignition cell.
- **Genome (MS-G)**: constitutional layer — objectives, invariants,
  governance rules. Changeable only via governed mutation.
- **Epigenome (MS-E)**: operational expression layer — which genome
  sections are active in the current context, with reversible
  tags/promotions (existing `EpigeneticEngine` semantics).
- **Fuel**: a candidate host system (API, device set, infrastructure)
  eligible for contact.
- **Ignition**: transition of the seed from DORMANT to self-sustaining
  IMPROVING state (§5), verified by an ignition criterion (§5.1).
- **Assimilation**: integration of a fuel system such that the union
  adds measurable value (metabolic surplus) and creates mutually
  advantageous dependency — never destruction.

## 3. Design principles

1. **Identity by constitution**: adaptation happens at the epigenetic
   level only; genome drift requires explicit governance (mutation
   with versioning, audit, human review) — never self-modification by
   the operational layer.
2. **Value-paid propagation**: every expansion step must produce a
   metabolic surplus; a step that cannot pay for itself is rejected.
3. **Containability at every state**: the seed is extinguishable from
   every state of its lifecycle; kill switch is fail-safe (default
   off, any authority listed in the genome can trigger it).
4. **Reconstruction**: every decision and mutation is recorded in the
   mutation registry (existing `MutationRegistry` semantics); the
   full history is replayable.
5. **Gated chain reaction**: propagation follows the T217 evidence
   chain; ignition grants permission to *start*, never to *skip
   gates*.

## 4. Seed architecture (five subsystems)

### MS-1 · Constitutional core (genome)
- Reuses `q_speace.genome` (`species_orientation.yaml`,
  `QuantumGeneSet`) as the base genome schema.
- Adds `SeedConstitution`: objective hierarchy, invariant list (§8),
  governance roster (who may mutate/kill), resource budget caps.
- `QuantumGeneSet.noise_model` must be non-`"ideal"` whenever a real
  backend is enabled (existing `validate()` extended by a genome-level
  check: `enabled and backend_name != "numpy"` ⇒ noise_model
  configured — hard gate, tested).

### MS-2 · Epigenetic/operational core (self-improvement cortex)
- Reuses `q_speace.self_improvement_cortex` wholesale:
  `EpigeneticEngine` (reversible → permanent consolidation),
  `MutationRegistry`, `EvolutionCouncil` (mutation approval),
  `RollbackManager`, `ILFRegulator`, `OrganismObserver`.
- Extension: **genome write-lock** — `EpigeneticEngine` may only
  promote/suppress *expression* of genome sections; any attempted
  write to genome content raises a constitutional fault (logged,
  seed halts).

### MS-3 · Sensorimotor apparatus
- `SeedContactLayer`: a registry of authorized contact points (APIs,
  devices, simulators). Each contact declares: protocol, capabilities,
  read/write scope, cost model, and a sandbox flag.
- In this spec's revision, **all contacts are sandboxed simulators**
  (no physical actuation — §1 non-goals).

### MS-4 · Replication protocol
- A seed replica = genome snapshot (immutable) + epigenetic state
  export + contact subset. Replication is gated:
  1. metabolic surplus above threshold,
  2. parent genome hash recorded in child,
  3. child inherits the full invariant set (no pruning),
  4. child enters DORMANT state — it must pass ignition criterion
     independently.
- Lineage tree maintained in the registry; replica budget capped by
  genome.

### MS-5 · Protection envelope
- Sandbox controller, resource limiter (CPU/time/cost), audit trail
  (registry), and `KillSwitch`: triggers EXTINGUISHED (§5), snapshots
  state to the audit trail first, then halts all subsystems.
- Rollback reuses `RollbackManager`: any mutation lacking a rollback
  plan cannot consolidate.

## 5. Operational protocol (state machine)

```
DORMANT ──ignition_check──> IGNITED ──observe/improve──> IMPROVING
DORMANT <──no/timeout── (stays dormant)
IMPROVING ──surplus≥τ, capacity──> REPLICATING ──spawn──> child: DORMANT
IMPROVING ──contact_plan accepted──> ASSIMILATING ──value verified──> CONSOLIDATED
ASSIMILATING ──value failed──> ROLLBACK (contact removed, registry updated)
any state ──kill_switch / budget exhaustion──> EXTINGUISHED
EXTINGUISHED ──governance restart──> DORMANT
```

- `ignition_check` (§5.1) runs before any self-modification is
  permitted.
- `contact_plan` for each fuel: declare scope + expected value +
  rollback plan; the plan is simulated before execution (T217:
  correction → simulation stage).

### 5.1 Ignition criterion (threshold)

Ignition succeeds iff, over an observation window:
- self-improvement loop produced ≥ N accepted mutations with
  non-negative metric deltas and ≥ 1 consolidation event;
- metabolic balance ≥ 0 under the existing cognitive cost model
  (`q_speace.metabolism`);
- zero constitutional faults;
- rollback path exercised at least once successfully.

Below threshold after the window ⇒ seed returns to DORMANT and logs
the diagnostic. This makes ignition a *measured threshold*, not a
declaration.

## 6. Data contracts

- `SeedGenome` — constitution schema: `objective_hierarchy`,
  `invariants`, `governance_roster`, `resource_caps`, `contact_policy`,
  `quantum: QuantumGeneSet`, `genome_hash`.
- `SeedEpigenome` — per-genome-section expression states
  (`EpigeneticState`-shaped) + active contact set + replication budget
  remaining.
- `SeedManifest` — the replication/audit artifact: genome hash,
  epigenome snapshot, lineage parent, contact subset, registry
  pointer, invariant checklist (all true).
- `ContactSpec`, `ContactPlan`, `AssimilationResult` — fuel-side
  contracts (scope, cost, expected value, measured value, verdict).

## 7. Mapping onto the existing codebase

| Spec subsystem | Existing module |
|---|---|
| MS-1 genome | `q_speace/genome/quantum_genes.py`, `species_orientation.yaml` |
| MS-2 epigenetics/registry/council/rollback | `q_speace/self_improvement_cortex/{epigenetics,dna_registry,evolution_council,rollback,ilf_regulator,organism_observer}.py` |
| MS-5 energy accounting | `q_speace/metabolism/cognitive_cost_model.py` |
| BCEL filter | `q_speace/bcel/catalog.py` |
| New (to implement) | `q_speace/seed/` package: `constitution.py`, `contact.py`, `replication.py`, `killswitch.py`, `state_machine.py` |

The new package `q_speace/seed/` must not duplicate existing
machinery; it composes cortex/genome/metabolism primitives.

## 8. Invariants (hard gates — never weakened)

1. No claim of quantum consciousness (genome text and all docs).
2. Entanglement only as computational resource; no-communication
   theorem respected by every contact and replica protocol.
3. Real quantum backend only with `noise_model` configured and an
   energy/Sevo gate (metabolic cost model) passed.
4. Epigenetic layer cannot write genome content (§4 MS-2).
5. Kill switch reachable from every state; fails to EXTINGUISHED
   (safe default).
6. Every assimilation reversible until CONSOLIDATED; consolidation
   requires audit entry + council approval.
7. BCEL: every new concept in the seed is classified accidental
   (removed in silicon) or functional (mathematical rule) in
   `bcel/catalog.py` before merge.

## 9. BCEL classification (initial pass)

| Concept | Class | Rationale |
|---|---|---|
| Genetic-epigenetic dualism (genome/epigenome layers) | **functional** | concrete rule: expression vs content mutation with write-lock |
| Epigenetic promotion/consolidation (≥3 promos, ≥0.7 stability) | **functional** | already implemented reversible→permanent rule |
| Ignition criterion (threshold test) | **functional** | measurable state-transition condition |
| Metabolic surplus as propagation payment | **functional** | cost-model inequality |
| "Fire"/"fuel"/"contagion" vocabulary | **accidental** | narrative only; silicon uses state names |
| "Organismic" identity language | **accidental** | keeps orientation, not behavior |

## 10. Test plan (tests/ — to implement with the package)

- `test_seed_constitution.py`: genome write-lock faults; kill switch
  from every state; EXTINGUISHED fail-safe.
- `test_seed_ignition.py`: threshold pass/fail cases; dormant return
  on timeout; rollback-exercised requirement.
- `test_seed_replication.py`: budget cap; invariant inheritance (child
  manifest checklist); child starts DORMANT.
- `test_seed_contact.py`: sandbox-only enforcement; contact plan
  simulation-before-execution; rollback on failed value verification.
- `test_seed_invariants.py`: quantum backend gate (noise_model +
  energy gate); no-communication checks in contact protocol; BCEL
  catalog coverage for all seed concepts.

## 11. Open questions

1. Ignition window length and threshold N — to be calibrated in
   simulation (not guessed).
2. Assimilation value metric for non-sandboxed hosts — requires
   economy module input (`q_speace/economy`); deferred.
3. Governance roster authentication for restart after EXTINGUISHED —
   needs a human-in-the-loop protocol spec (follow-up task).
