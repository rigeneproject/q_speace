# T232 — Seed Pipeline/Immune/Metrics (T221-23..28) & PTAA Track-A Demonstrator (T221-10..17)

**Status:** agentic (production simulation & governance software)  
**Date:** 2026-11-22  
**Dependencies:** `AGENTS.md`, `T208_DEVELOPMENT_GUIDELINES_SPEC.md`,
`T217_SAFE_ASSIMILATION_LIFECYCLE_SPEC.md`, `T220_SPEACE_SEED_IGNITION_SPEC.md`,
`T221_PTAA_SZHK_IGNITION_STRATEGY_SPEC.md`, `T221_TASKS.md`.  
**Non-goals:** No physical actuation, no real institutional claims or endorsements (Annex C §7),
no A5 capabilities in Track-A pilots (`T221 §7.1`), no consciousness or entanglement-communication claims.

---

## 1. Scope & Track Separation Invariant

Implements the remaining software-only Phase P1 deliverables from `T221_TASKS.md` while strictly
enforcing `T221 §7.1` (**Track A A1–A4 governance never imports or executes Track B A5 seed code**):

- **Milestone 4 — Track B (`q_speace/seed/`)**:
  - `T221-23`: `q_speace/seed/pipeline.py` — 5-stage `ChangeProcessPipeline` (propose → independent
    adversarial review prohibiting self-approval → sandbox replica test → deploy with snapshot +
    rollback trigger → hash-chained append-only register).
  - `T221-24`: `q_speace/seed/immune.py` — `ExternalImmuneMonitor` operating outside the monitored
    `SeedLifecycle` to detect constraint-probing, trigger quarantine (`EXTINGUISHED`), and restore
    from a verified snapshot digest.
  - `T221-25`: `q_speace/seed/metrics.py` — diagnostic autocatalytic ratio `k` (explicitly marked
    non-target), hidden-scenario goal-drift hard gate, controllability drills, and modification
    quality metrics.
- **Milestone 5 — Track A (`q_speace/ptaa/`)**:
  - `T221-10`: `scc.py` — signed versioned `SCCProfile` (`I1`–`I5`, classes `A1`–`A4` only; rejects `A5`).
  - `T221-11`: `registry.py` — `AgentRegistry` with status propagation across dependencies.
  - `T221-12`: `delegation.py` — signed `DelegationToken` + `ScopeEnforcer` (violation → containment).
  - `T221-13`: `audit.py` — hash-chained append-only `PTAAAuditLog` with external replica sink.
  - `T221-14`: `halt.py` — dual independent halt channels (`primary_control`, `out_of_band_supervisor`)
    with per-class SLA verification and anti-tamper protection.
  - `T221-15`: `reversibility.py` — transactional wrapper, compensating actions, rollback drills,
    exemption register.
  - `T221-16`: `incidents.py` — `S1`–`S3` incident taxonomy, automated reporting, shared registry.
- **Milestone 6 — Simulations (`T221-17` & `T221-28`)**:
  - `T221-17`: `q_speace/ptaa/orchestration_sim.py` — two simulated jurisdictions (`sim-sz`, `sim-hk`),
    capability matching, data-exchange contracts, mutual recognition, institutional learning metrics.
  - `T221-28`: `q_speace/seed/logistics_twin.py` — simulation-only digital twin sandbox of the
    `T221 §4` internal logistics habitat (fault recovery & authorized device integration drills).

---

## 2. BCEL Classification

Added to `q_speace/bcel/catalog.py`:

- **External immune quarantine and constraint-probing monitor (T221-24)** — `functional`:
  Out-of-process/external counter of constraint-probing faults triggering halt quarantine and
  verified snapshot restoration; not a biological immune system.
- **Autocatalytic ratio k as diagnostic metric (T221-25)** — `functional`:
  Ratio of baseline vs assisted capability acquisition time recorded strictly as a diagnostic
  statistic within caps, never as an optimization target or proof of general intelligence.
- **PTAA Track-A governance demonstrator (T221-10..17)** — `functional`:
  Deterministic cryptographic profile validation, scope tokens, dual halt paths, hash-chained
  audit replication, transactional rollback, and simulated mutual recognition for classes A1–A4.

---

## 3. Verification Results

- **Milestone 4 (`T221-23..25`)**: `q_speace/seed/{pipeline,immune,metrics}.py` + `tests/test_seed_pipeline_immune_metrics.py` — 25/25 seed tests passing.
- **Milestone 5 (`T221-10..16`)**: `q_speace/ptaa/{scc,registry,delegation,audit,halt,reversibility,incidents}.py` + `tests/test_ptaa_demonstrator.py` — 4/4 PTAA governance tests passing.
- **Milestone 6 (`T221-17`, `T221-28`)**: `q_speace/ptaa/orchestration_sim.py`, `q_speace/seed/logistics_twin.py`, `tests/test_t221_simulations.py` (including AST check mechanically proving `q_speace/ptaa/` never imports `q_speace.seed`).
- **Full quality gates**:
  - `pytest -q`: **736 passed, 3 skipped**, total coverage **88.00%** (`10640` statements).
  - `ruff check q_speace tests`: clean (0 issues).
  - `black --check q_speace tests`: clean (`215 files would be left unchanged`).
  - `mypy q_speace`: clean (`142 source files`).
  - `python -m examples.mcp_connection_agent --local-demo --apply-delay`: **11/11 PASS**.
