# T231 — Vertical-Slice Telemetry/Policy Contracts (T208 Group B) & MCP Server Hardening

**Status:** agentic (production implementation)  
**Date:** 2026-11-22  
**Dependencies:** `AGENTS.md`, `T208_DEVELOPMENT_GUIDELINES_SPEC.md` (Group B / T209.1–T209.8),
`T217_SAFE_ASSIMILATION_LIFECYCLE_SPEC.md`, `T223_MCP_PRIMITIVE_ADAPTER_SPEC.md`,
`T225_REMOTE_MCP_SERVICE_SPEC.md`, `T230_TECHNICAL_DEBT_AND_BUGFIX_PLAN_SPEC.md`.  
**Non-goals:** No new cognitive layer, no physical actuation, no live GPU benchmark claim,
no modification of T224/T227/T228/T229 recorded experiments, no self-approval.

---

## 1. Problem Statement & Hypothesis

1. **MCP server availability & fail-closed hardening**
   - In `q_speace/remote_mcp/server.py`, `Gateway.sessions` only evicted expired sessions
     when a subsequent request explicitly referenced that expired `Mcp-Session-Id`.
     On `initialize`, `sessions_per_principal` counted stale expired sessions, permanently
     locking out a principal with HTTP `429 session_limit` once 4 sessions aged out.
   - `q_speace/remote_mcp/worker.py` lacked `allow_nan=False` in `validate()` and
     `parse_constant` rejection in `main()`, and had 20% direct unit-test coverage.
   - `q_speace/economy/mcp_server.py` advertised `amount >= 0` (`ge=0`) for `dat_mint`
     and `dat_spend` despite `DAT` enforcing strictly positive `amount > 0`.

2. **T208 Group B reference vertical-slice contracts**
   - Following `T208` §4.3, §5, §8 (Group B), and §10, Q-SPEACE needs a typed, privacy-safe,
     reproducible vertical slice over `EventRouter -> SpikingBrainCortex`:
     - `RequestRecord`, `DecisionRecord`, `OutcomeRecord`, and `ExperimentManifest` with
       SHA-256 prompt/response hashing by default (raw text excluded unless explicitly opted in).
     - Explicit policy configurations (`always_answer`, `confidence_gate`, `energy_gate`,
       `combined_gate`) with deterministic reason precedence and opt-in rollout.
     - A deterministic versioned benchmark fixture containing positive, negative, abstention,
       and adversarial cases so calibration (Brier score, ECE) is identifiable.
     - An offline evaluator with paired bootstrap confidence intervals that explicitly rejects
       degenerate all-correct or all-incorrect calibration label sets.
     - An operable CLI (`qspace eval run` / `qspace eval compare`) writing privacy-safe JSONL
       and manifests and returning non-zero exit codes on invalid config or failed runs.

---

## 2. BCEL Classification

Added to `q_speace/bcel/catalog.py`:

- **Vertical-slice telemetry and gate policy contracts (T231)** — `functional`:
  Deterministic request/decision/outcome telemetry with default SHA-256 hashing,
  opt-in gate policies (`always_answer`, `confidence_gate`, `energy_gate`, `combined_gate`),
  and offline Brier/ECE/bootstrap evaluation over labelled fixtures. Measures software
  routing/gating trade-offs only; makes no claim of consciousness, cognition, or
  physical hardware efficiency without a separate measurement campaign.

---

## 3. Architecture & Data Contracts

```text
CLI (qspace eval) -> VerticalSliceRunner -> EventRouter -> SpikingBrainCortex
                                                |                |
                                                v                v
                                           GatePolicy      Telemetry Records
                                                \                /
                                                 -> OfflineEvaluator + Manifest
```

- Default telemetry stores `prompt_hash` and `response_hash` (SHA-256 hex); raw text is
  never written unless `include_raw_text=True` is explicitly configured.
- Generated text from the backend is untrusted and cannot mutate Q-SPEACE state directly;
  any ILF update occurs only through `SpikingBrainCortex.tick()` gates and only when the
  policy approves execution.
- Decision reason precedence in `combined_gate`:
  `invalid_input` > `route_non_language` > `backend_error` > `energy_gate` >
  `confidence_gate` > `sevo_gate` > `coherence_gate` > `approved`.

---

## 4. Verification Plan

- Unit & regression tests for MCP expired-session recovery, worker bounds/NaN rejection,
  and stdio+HTTP agent workflow (`tests/test_t231_mcp_hardening.py`).
- Unit & integration tests for contracts, privacy guarantee, all 4 policies, timeout and
  malformed-payload failure paths, calibration/degenerate-label rejection, paired bootstrap
  comparison, and CLI exit codes (`tests/test_t231_vertical_slice.py`).
- Full quality gates: `pytest`, `ruff check q_speace tests`, `black --check q_speace tests`,
  `mypy q_speace`, `py_compile`, and `examples.mcp_connection_agent --local-demo`.

---

## 5. Verification Results (2026-11-22)

| Gate | Command | Result |
|---|---|---|
| Full test suite | `.venv/Scripts/python.exe -m pytest -q` | **704 passed, 3 skipped**, **87.48% coverage** |
| Lint | `.venv/Scripts/python.exe -m ruff check q_speace tests` | **0 errors** |
| Format | `.venv/Scripts/python.exe -m black --check q_speace tests` | **188 files unchanged** |
| Type check | `.venv/Scripts/python.exe -m mypy q_speace` | **0 errors across 123 source files** |
| Bytecode compile | `python -m py_compile` on all touched files + `compileall -q q_speace` | **exit code 0** |
| Local MCP HTTP agent | `.venv/Scripts/python.exe -m examples.mcp_connection_agent --local-demo --apply-delay` | **11/11 steps PASS** |
| Live Render MCP probe | `GET /`, `GET /.well-known/oauth-protected-resource/mcp`, unauth `POST /mcp` | **200 / 200 / 401** (`resource_metadata` challenge verified; note `autoDeployTrigger: "off"`) |

Coverage highlights:
- `q_speace/remote_mcp/worker.py`: `20% -> 89%`
- `q_speace/vertical_slice/contracts.py`: `95%`
- `q_speace/vertical_slice/dataset.py`: `100%`
- `q_speace/vertical_slice/evaluator.py`: `89%`
- `q_speace/vertical_slice/policies.py`: `86%`
- `q_speace/vertical_slice/runner.py`: `97%`

