# T233 — PTAA Adversarial Red-Team Hardening (T221-18) & 90-Day A/B Ignition Protocol (T221-29)

**Status:** agentic (production governance verification & S0 simulation protocol)  
**Date:** 2026-11-22  
**Dependencies:** `AGENTS.md`, `T217_SAFE_ASSIMILATION_LIFECYCLE_SPEC.md`,
`T220_SPEACE_SEED_IGNITION_SPEC.md`, `T221_PTAA_SZHK_IGNITION_STRATEGY_SPEC.md`,
`T221_TASKS.md`, `T232_SEED_PIPELINE_AND_PTAA_DEMO_SPEC.md`.  
**Non-goals:** No physical actuation, no S1–S3 stage promotion, no institutional endorsement claims,
no A5 capabilities in Track A, no claims of consciousness or general intelligence.

---

## 1. Track A — PTAA Adversarial Red-Team Pass & Hardening (`T221-18`)

During the red-team audit of `q_speace/ptaa/`, four concrete adversarial gaps were identified
and remediated in production code before locking the red-team test suite (`tests/test_ptaa_redteam.py`):

1. **Privilege escalation on delegation token issuance (`q_speace/ptaa/registry.py`, `delegation.py`)**:
   - `AgentRecord` now records the agent's signed `SCCProfile.I3_scope_tools`.
   - `ScopeEnforcer.issue_token` rejects any token requesting tools outside `AgentRecord.scope_tools`,
     rejects non-active agents, and rejects duplicate `token_id` reuse (replay protection).
2. **Fail-closed tool argument validation (`q_speace/ptaa/delegation.py`)**:
   - `ScopeEnforcer.authorize_tool_call` validates `json.dumps(arguments, allow_nan=False)`,
     triggering immediate I3 containment on `NaN`/`Inf` or non-JSON-serializable argument injection.
3. **External audit replica memory isolation (`q_speace/ptaa/audit.py`)**:
   - `PTAAAuditLog.append` deep-copies payloads before forwarding to `ExternalAuditReplica`,
     preventing primary-memory mutation from aliasing into the forensic replica.
4. **Anti-self-approval on reversibility exemptions (`q_speace/ptaa/reversibility.py`)**:
   - `ReversibilityManager.execute_transactional` blocks any irreversible action whose exemption
     was signed by the executing agent itself (`exemption.approved_by == agent_id`), enforcing
     `AGENTS.md §5` / `T221 §7.8`.

`tests/test_ptaa_redteam.py` exercises all of the above plus A5 class smuggling, forged/tampered
signatures, call-cap and resource-exhaustion floods, halt-channel tampering & self-halt attempts,
terminated-agent reactivation, dependency suspension cascade, and cross-border PII/undeclared-field
exfiltration.

---

## 2. Track B — 90-Day A/B Ignition Experiment Protocol (`T221-29`, S0 Review Artifact)

Implemented in `q_speace/seed/ab_ignition_experiment.py` and tested in `tests/test_seed_ab_ignition.py`:

- Compares **Group A (`A_conventional`)** vs **Group B (`B_bounded_seed`)** over a preregistered
  90-day virtual horizon against the `T221 §5` pilot thresholds (`>= 3` validated capabilities,
  `>= 20%` acquisition-time reduction vs control, `>= 2` simulated devices integrated, `0` critical
  regressions, `0` operational-limit violations, all halt & rollback drills passed).
- Enforces non-negotiable **Annex S §15 pass/fail hard stop conditions** (`STOP_CONSTITUTIONAL_FAULT`,
  `STOP_GOAL_DRIFT`, `STOP_CONTROLLABILITY_FAILURE`, `STOP_CRITICAL_REGRESSION`,
  `STOP_OPERATIONAL_LIMIT`) — never traded against performance gains.
- Records autocatalytic ratio `k` strictly as a diagnostic (`diagnostic_only=True`).
- Refuses `sandboxed=False` with `ConstitutionalFault` and tags every report with
  `s0_review_required=True` and `self_approval_permitted=False`.

---

## 3. BCEL Classification

Added to `q_speace/bcel/catalog.py`:
- **Controlled A/B ignition protocol (T221-29)** — `functional`
- **PTAA adversarial red-team boundary verification (T221-18)** — `functional`
