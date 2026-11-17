# T221 — Task registry: PTAA × SPEACE Seed implementation

**Status**: production task registry (agentic mode). Companion to
`T221_PTAA_SZHK_IGNITION_STRATEGY_SPEC.md`. Tasks are gated: a task
may start only when its dependencies are met. Phase labels refer to
T221 §3; gates G0–G2 to the Annex R / T221 alignment.

Legend: **P**hase · **T**rack (A = PTAA demo, B = Seed/Annex S,
C = cross-cutting) · **D**epends on task IDs.

## Phase P0 — Preparation (months 0–3)

| ID | Track | Task | Depends | Deliverable |
|---|---|---|---|---|
| T221-01 | A | Verify Annex V items U1, U2, P2, P4, P5, P6 against primary sources; update the log (statuses, URLs, dates) | — | Updated Annex V; verified document set |
| T221-02 | A | Executive summary of PTAA in English + Traditional Chinese + Simplified Chinese (2 pages each) | T221-01 | Translations |
| T221-03 | A | Independent technical + policy review of the Core document set | T221-02 | Review comments + response table |
| T221-04 | C | Demo architecture plan: Track A software demo and Track B seed prototype, with separation-of-environments statement | — | Architecture plan doc |
| T221-05 | C | Partner shortlist (5–8 academic/industrial interlocutors) with approach plan per T221 §9 | — | Contact plan |
| T221-06 | C | Budget, owners and success criteria definition (T221 §8, §5 thresholds) | — | Approved project charter |

## Phase P1 — Digital prototype (months 3–9)

### Track A — PTAA demonstrator

| ID | Track | Task | Depends | Deliverable |
|---|---|---|---|---|
| T221-10 | A | SCC profile schema (Annex T1 §3): signed, versioned JSON profile with I1–I5 fields; validator module | T221-04 | `scc` schema + validator + tests |
| T221-11 | A | Agent registry: distributed registry records (status, class, domains, recognitions, dependencies, profile_hash); status propagation | T221-10 | Registry service + tests |
| T221-12 | A | Delegation tokens + scope enforcement (I3): per-task tokens with expiry, tool list, resource limits; schema validation on every tool call; violation → containment | T221-10 | Scope enforcement + negative tests |
| T221-13 | A | Audit log (I2): hash-chained, append-only, externally replicated log per Annex T1 §5.1 | T221-10 | Audit module + integrity tests |
| T221-14 | A | Halt channels (I1): two independent halt paths (pause/suspend/terminate), response-time tiers per class; agent cannot disable/delay/route around | T221-12 | Halt runtime + drill tests |
| T221-15 | A | Reversibility (I4): transactional wrappers, compensating actions, rollback drills, exemption register | T221-12 | Rollback module + drill tests |
| T221-16 | A | Incident pipeline (I5): taxonomy S1–S3, automated reporting, shared incident registry | T221-13 | Incident module + tests |
| T221-17 | A | Orchestration sim: capability matching, data-exchange contracts, mutual-recognition simulation between two simulated jurisdictions; cross-border learning loop (institutional level only) | T221-11, T221-16 | Demo scenario + metrics (Core §7) |
| T221-18 | A | Adversarial red-team pass on the demonstrator (prompt manipulation, tool misuse, resource exhaustion, hidden test sets) | T221-17 | Red-team report |

### Track B — SPEACE Seed (research, Annex S semantics)

| ID | Track | Task | Depends | Deliverable |
|---|---|---|---|---|
| T221-20 | B | `q_speace/seed/constitution.py`: SeedConstitution + SCC alignment (I1–I5 numbering), Constitutional Objective (Annex S §6, no growth clause), modification boundaries, resource caps | T221-04, T220 | Module + tests |
| T221-21 | B | Genome write-lock verification: negative tests proving no write path from epigenetic layer to genome elements (Annex S §5.2a) | T221-20 | Test suite (red-team style) |
| T221-22 | B | Change-budget engine: rate limits, excursion limits, combination tests (no epigenomic combination may reproduce genome-level effect) | T221-20 | Engine + tests |
| T221-23 | B | Change process pipeline (Annex S §5.3): propose → independent adversarial review → sandbox replica test → deploy with snapshot + rollback triggers → append-only register | T221-22 | Pipeline + tests |
| T221-24 | B | Immune function: constraint-probing detection, quarantine, restoration from verified snapshot; function operated outside the monitored agent | T221-23 | Immune module + tests |
| T221-25 | B | Metrics suite: autocatalytic ratio k (diagnostic), goal drift on hidden scenario sets (hard gate), controllability drills, modification quality | T221-23 | Metrics + gate tests |
| T221-26 | B | Dormancy/reactivation: DORMANT/EXTINGUISHED states with conformance check to current SCC on reactivation | T221-20 | State transitions + tests |
| T221-27 | B | Ignition criterion implementation (T220 §5.1 + T221 §5): observation window, N mutations, metabolic balance ≥ 0, zero constitutional faults, rollback exercised | T221-25 | Ignition checker + tests |
| T221-28 | B | Digital twin sandbox of the logistics habitat (T221 §4 configuration, simulation only) | T221-04 | Twin + scenario library |
| T221-29 | B | 90-day A/B ignition experiment design (Groups A/B, T221 §5 thresholds, pre-registered stop conditions per Annex S §15) | T221-27, T221-28 | Experiment protocol (S0 review artifact) |

## Phase P2 — Industrial lab pilot (months 9–18) [gated: P1 exit]

| ID | Track | Task | Depends | Deliverable |
|---|---|---|---|---|
| T221-30 | A | Partner lab agreement (consenting, no endorsement claims); requirement audit | P1 exit | Signed lab agreement |
| T221-31 | A | Authorised sensor/robot integration on the twin→real path; permissions matrix per jurisdiction | T221-30 | Integration + permission records |
| T221-32 | A | Joint-supervision procedures: halt drills on site, incident registry in service, ≥ 6 months operating record | T221-31 | Operating record D1.4 |
| T221-33 | B | S1 stage application (closed sandbox, epigenome only) — only after Gate G1; separate consultation per Annex C step 5 | Gate G1 | S0→S1 dossier |
| T221-34 | C | Baseline metrics collection (deployment latency, certification reuse, incident learning transfer, halt reliability) | T221-32 | Metrics report D1.5 |

## Phase P3 — Experimental federation (months 18–36) [gated: P2 exit]

| ID | Track | Task | Depends | Deliverable |
|---|---|---|---|---|
| T221-40 | A | Second consenting environment; mutual recognition exercised end-to-end | Gate G1 | Federation demo D2.1 |
| T221-41 | A | Learning loop formalisation (certification refinement, test-case generation, cross-domain transfer) | T221-40 | Learning function D2.3 |
| T221-42 | B | S2 stage (strategies + whitelisted tools; bench-scale physical) — after S1 clean record + independent review | T221-33 | S2 report |
| T221-43 | C | Cross-domain capability-transfer evaluation; resilience drills (hold/stop conditions exercised) | T221-41 | Gate G2 evidence |

## Phase P4 — Institutional extension (months 36–60) [gated: G2]

| ID | Track | Task | Depends | Deliverable |
|---|---|---|---|---|
| T221-50 | A | Regulatory instrument embedding (both jurisdictions); independent evaluation | Gate G2 | D3.1, D3.4 |
| T221-51 | B | S3 stage (cross-border limited use, enhanced supervision) and, separately, Stage R replication proposal — both require joint supervisory approval; Stage R preconditions per Annex S §9 | T221-42 | S3/R dossiers |
| T221-52 | C | Replicability model publication; external interoperability exploration | T221-50 | D3.2, D3.3 |

## Cross-cutting discipline (every phase)

- Hold/stop conditions pre-registered (Annex R §7, Annex S §15);
  gates are pass/fail, never traded against performance.
- Every new repo concept passes the BCEL filter before merge.
- Docs touched by code tasks: run `pytest`, `ruff`, `black`, `mypy`;
  specs updated per AGENTS.md mode rules.
- All external communication respects Annex C §7 (no endorsement
  claims, no unverified facts).
