# T243 — AACM & BrainAuditLog Fail-Closed Hardening and Coverage Remediation

- **Status**: Agentic Production Specification (Zero new MCP tools; core hardening)
- **Date**: 2026-11-23
- **Parent specs**: `AGENTS.md`, `T230`, `T235`, `T242`
- **Scope**: Fail-closed numerical, security-boundary, and portability fixes across `q_speace/aacm/{dynamics,primitives,executor}.py` and `q_speace/spiking_brain/audit.py`, with comprehensive regression tests in `tests/test_t243_aacm_and_audit_hardening.py`.

## 1. Discovered Defects

1. **`q_speace/aacm/dynamics.py` (77% cov)**:
   - Because `NaN < 0.0` evaluates to `False` in IEEE 754, non-finite inputs (`NaN`/`Inf`) bypassed checks in `dS_dt`, `t_a_within_budget`, `leverage_pre_existing_fractures`, `reputation_multiplier`, `resistance_decay`, `infrastructure_self_sustaining`, `assert_resilience(omega_min=NaN)`, and `value_integral`.
2. **`q_speace/aacm/primitives.py` (79% cov)**:
   - `CentralityGraph` accepted `timestamp=NaN/Inf` and `edge weight=NaN/Inf`.
   - `LegitimationChannel` accepted non-finite or negative `verified_at`.
3. **`q_speace/aacm/executor.py` (79% cov)**:
   - **Worktree containment gap**: `_diff_target_path` was joined with `self.worktree` without checking `target_abs.resolve().is_relative_to(self.worktree.resolve())`, risking path traversal outside the worktree on crafted diff headers.
   - **Portability bug**: `_measure_execution_time` invoked `"python"` instead of `sys.executable`.
   - `_check_threshold` did not guard against non-finite `value`/`threshold`.
4. **`q_speace/spiking_brain/audit.py` (80% cov)**:
   - `BrainAuditLog.recent()` appended any valid JSON line even if not a JSON object (`dict`), violating its return type contract on corrupted lines.

## 2. Verification Goals

- All four defect classes fixed fail-closed with zero regressions across the full test suite.
- All four target modules lifted above **94%** coverage.
- `pytest`, `black`, `ruff`, `mypy`, `compileall`, and `mcp_server --self-test` 100% clean.

## 3. BCEL Classification

Recorded in `q_speace/bcel/catalog.py`:
- **Functional**: `AACM worktree containment, finite-domain dynamics, and strict audit-record typing (T243)`.
