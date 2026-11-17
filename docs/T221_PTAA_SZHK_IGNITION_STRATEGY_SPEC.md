# T221 — PTAA × SPEACE Seed: strategic implementation plan (Shenzhen–Hong Kong)

**Status**: production strategy plan (agentic mode). Companion task
registry: `T221_TASKS.md`.

Companions: `PTAA/` document set (Core v1.1, Annexes T1/S/R/C/V),
`SPEACE Macro Genesis - Shenzhen–Hong Kong.md` (territorial strategy),
`T219_FIRE_IGNITION_ANALOGY_VIBE.md` (ignition concept),
`T220_SPEACE_SEED_IGNITION_SPEC.md` (seed architecture).

## 1. Executive summary

The PTAA document set identifies the **Shenzhen–Hong Kong (Hetao)
innovation zone** as the most plausible "fertile area" for igniting
SPEACE macro: high-density agentic sandboxes (GenA.I. Sandbox++),
automated industry, cross-border data infrastructure, and an explicit
regulatory innovation mandate. The strategy is **dual-track and
self-funded in software first**:

- **Track A — PTAA Core A1–A4**: build the governance demonstrator
  (agent registry, SCC profiles, mutual-recognition simulation, audit,
  halt drills) in simulation only. No institutional agreement required
  to start.
- **Track B — SPEACE Seed (Annex S / T220)**: build the bounded
  self-modifying agent (genome/epigenome, class A5 research stage,
  S0–S3 gates) in a closed sandbox, with approvals separate from
  Track A.
- **Convergence point — Industry 6.0 organismic testbed**: only
  components validated on both tracks are combined, with no automatic
  transfer of autonomy or authorizations between tracks.

Key discipline inherited from the PTAA set: **A5 research never leaks
into A1–A4 pilots**; propagation is gated (T217 / Annex S stop
conditions); facts marked ‡ (Annex V items U/P) are not used for
institutional proposals until verified.

## 2. Why this territory (fertile-area assessment)

Assets that rarely coexist (PTAA Core §2.1):
- Regulatory innovation: Hetao zone designed for cross-boundary
  institutional bottlenecks; sandbox ecosystems operational (HKMA/SFC
  GenA.I. Sandbox++ first cohort announced 27 Aug 2026, 36 use cases).
- Physical automation: Pearl River Delta manufacturing and logistics
  ‡(P4/P6 — reworded per Annex V).
- Data connectivity: cross-border data verification platform ‡(U2).
- Institutional engineering precedent: cross-boundary eVTOL insurance
  (June 2026) shows the pattern PTAA generalises.

Open items that gate pilot selection (Annex V §8): P2 (low-altitude
sandbox status), S4 (Sandbox++ trial start), U1/U4 (Hetao legal
instruments), U2 (data platform figures). These are Track-A / Phase-0
tasks, not Track-B blockers.

## 3. Phase structure (preparatory + Annex R alignment)

| Phase | Months | Scope | Exit gate |
|---|---|---|---|
| P0 Preparation | 0–3 | Annex V verification; bilingual executive summary; architecture demo; partner shortlist; independent review | Document set verified; demo plan approved |
| P1 Digital prototype | 3–9 | Track A software demo (registry, SCC validator, orchestration sim) **and** Track B seed digital prototype, separate environments | Both demos pass their own tests; no A1–A4/A5 mixing |
| P2 Industrial lab pilot | 9–18 | Authorised sensors/robots in a partner lab; interoperability and comparable data | Defined operating period, zero unresolved violations |
| P3 Experimental federation | 18–36 | Two consenting industrial environments; coordination, capability transfer, resilience | Cross-domain learning demonstrated; no systemic failure |
| P4 Institutional extension | 36–60 | Replicability, standardisation, further sectors — subordinated to results and approvals | Independent evaluation; instrument embedding |

Annex S research track (Track B, class A5) follows its own stage
gates: S0 design review (parallel to P1), S1 closed-sandbox
epigenome-only (not before Gate G1 = P2 success), S2 extended sandbox
(mid P3), S3 cross-border limited use (after Gate G2), Stage R
replication — separate proposal, not scheduled.

## 4. First industrial experiment: internal industrial logistics

Chosen over cross-border drone logistics because it demonstrates
multi-function integration faster and without aviation authorizations.

Initial configuration (indicative, post-audit):
1 AI orchestrator · 4–6 specialized agents (logistics, energy,
maintenance, quality, audit) · 10–20 IoT sensors · 1–2 robots ·
1 digital twin · 1 independent supervisor (halt, audit, verification).

Three initial capabilities to demonstrate:
1. Coordinate multiple subsystems to complete a task.
2. Recover from a simulated failure.
3. Integrate a new authorized device without losing prior functions.

## 5. Ignition criterion (90-day controlled experiment)

The fire analogy becomes an experimental test: the seed must acquire
new capabilities **that facilitate acquiring further capabilities**.

Two identical configurations:
- **Group A**: conventional agentic orchestration, controlled updates.
- **Group B**: same configuration + digital DNA, epigenome, bounded
  self-improvement (Annex S A5 semantics, sandbox only).

Proposed thresholds (pilot-level, not PTAA-prescribed):

| Indicator | Target |
|---|---|
| New validated capabilities | ≥ 3 |
| Capability-acquisition time reduction vs control | ≥ 20% |
| New simulated devices integrated | ≥ 2 |
| Critical regressions | 0 |
| Operational-limit violations | 0 |
| Halt and rollback tests | all passed |

Autocatalytic ratio k (Annex S §8) is a **diagnostic** of
self-sustainment within caps, never an optimization target.

## 6. Mapping to q_speace repo work

| PTAA / strategy element | Repo artifact |
|---|---|
| SCC invariants I1–I5 | T220 §8 invariants (halt, audit, scope, reversibility, incident) — already aligned; add explicit I-numbering in seed constitution schema |
| SCC signed profile (Annex T1 §3) | New: `q_speace/seed/constitution.py` extends `SeedConstitution` with signed, versioned profile schema |
| Autonomy classes A1–A4 | New: class taxonomy module + certification evidence records in seed package |
| Bounded self-modification (Annex S §5) | T220 MS-2 genome write-lock + change budgets + excursion limits |
| Constitutional Objective (Annex S §6) | T220 genome `objective_hierarchy` — no open-ended growth clause |
| Immune function (Annex S §11) | T220 MS-5 + constraint-probing detection as incident source |
| Replication Stage R | T220 MS-4, gated as deferred (not scheduled, separate approval) |
| Dormancy/reactivation (Annex S §12) | T220 state machine DORMANT/EXTINGUISHED + conformance check on reactivation |
| Metrics (Annex S §8, Core §7) | T220 §5.1 ignition criterion + k, goal-drift, controllability metrics |

## 7. Invariants (binding for this plan)

1. Track separation: A5 capabilities never enter A1–A4 pilots.
2. No agent autonomously acquires access, actuators or resources
   beyond declared authorizations.
3. All modifications versioned, tested, verifiable, reversible.
4. Cross-border connection respects applicable data/infrastructure
   rules per jurisdiction.
5. Unverified facts (Annex V U/P items) are not used for
   institutional proposals until resolved.
6. No quantum backend without `QuantumGeneSet.noise_model` and
   energy/Sevo gate.
7. No claim of quantum consciousness; entanglement as computational
   resource only.
8. The candidate never approves itself: T217 evidence chain applies
   to every propagation step.

## 8. Budget (indicative, EUR, ~12 months, small team)

| Component | Estimate |
|---|---|
| Legal/technical revision, translations | €15k–35k |
| PTAA software prototype | €35k–80k |
| IoT + robotics lab | €30k–90k |
| Security, audit, independent verification | €20k–50k |
| Personnel, coordination, operations | €80k–180k |
| **Total** | **€180k–435k** |

Smaller first step: €20k–50k for a digital-only demonstration in a
restricted scope.

## 9. Partner sequence (research/industry before regulators)

HK-Shenzhen Innovation & Technology Park (Hetao HK side) · HK Science
Park (testbed) · Cyberport (governance prototype) · HK Productivity
Council (automation, benefit evaluation) · Hetao Shenzhen Park
(industrial partners) · universities/independent labs (peer review,
formal verification, safety). All contacts: roles proposed, not
agreements reached; no claims of endorsement.

## 10. Decision

Start immediately with (1) the PTAA software demonstrator and (2) the
first digital SPEACE Macro Seed in a separate environment, without
waiting for the Shenzhen–Hong Kong institutional agreement. Invest in
a real cyber-physical habitat only after both tracks validate. The
2027–2030 window targets the **first experimental organismic birth of
basic SPEACE macro**: an integrated nucleus that maintains functions,
acquires verified capabilities, and extends through authorized
integrations without compromising controllability.
