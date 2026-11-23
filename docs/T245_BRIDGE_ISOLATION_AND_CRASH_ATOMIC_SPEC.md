# T245 — T218 §13 Bridge-v0 Hardening: Process-Isolated Preemptive Validator & Crash-Atomic Coupled Commit

- **Status**: Agentic Production Specification (Zero new MCP tools; resolves T218 §13 gaps)
- **Date**: 2026-11-23
- **Parent specs**: `AGENTS.md`, `T218`, `T225`
- **Scope**: `ProcessIsolatedValidator` with preemptive OS-level worker termination (`q_speace/bridge/validator.py`), `CrashAtomicCoupledCommit` + `recover_coupled_wal` with fsync+`os.replace` WAL (`q_speace/bridge/protocol.py`), exports in `q_speace/bridge/__init__.py`, and crash-injection + hang-kill tests (`tests/test_t245_bridge_hardening.py`).

## 1. T218 §13 Gaps Addressed

1. **Process & Credential Isolation + Preemptive Timeout (`ProcessIsolatedValidator`)**:
   - Executes untrusted `plant_check` targets inside a dedicated child Python process (`subprocess.run([sys.executable, ...], timeout=max_eval_seconds)`).
   - The HMAC signing key (`ValidatorKey.key`) **never enters** the worker process memory or environment; only the parent validator signs attestations after verifying the child's structured JSON verdict.
   - Hanging or runaway `plant_check` functions are **preemptively terminated by the OS** on timeout and raise `ValidationBudgetExhaustedError` (fixing T218 §13's post-return timeout limitation).
   - Check targets are restricted to an explicit allowlist of module prefixes (`q_speace.`) to prevent arbitrary module import execution.
2. **Crash-Atomic Coupled Commit (`CrashAtomicCoupledCommit` & `recover_coupled_wal`)**:
   - Persists durable WAL state transitions (`PREPARED -> COMMITTING -> COMMITTED | ROLLED_BACK`) using temporary-file write + `fsync` + atomic `os.replace`.
   - On crash mid-activation (`COMMITTING` left on disk with partially activated members), `recover_coupled_wal()` deterministically aborts and reconciles **every** member back to `ABORTED` (eliminating partial `1,0` / `0,1` coupled states).

## 2. BCEL Classification

Recorded in `q_speace/bcel/catalog.py`:
- **Functional**: `Process-isolated preemptive Bridge validator and crash-atomic coupled WAL (T245)`.
