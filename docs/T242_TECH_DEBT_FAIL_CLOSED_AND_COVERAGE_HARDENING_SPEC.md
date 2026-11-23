# T242 — Tech Debt Hardening: Fail-Closed Guards & Lowest-Coverage Module Remediation

- **Status**: Agentic Production Specification (Zero new MCP tools; core hardening)
- **Date**: 2026-11-23
- **Parent specs**: `AGENTS.md`, `T230`, `T235`
- **Scope**: Fail-closed numerical & RFC 8259 hardening across six lower-coverage modules (`evolutionary_memory.py`, `experiments/online_agent.py`, `experiments/context_decay.py`, `spiking/bridge.py`, `spiking/linear.py`, `earth_feed.py`) plus comprehensive regression coverage in `tests/test_t242_tech_debt_hardening.py` (including `self_improvement_cortex/benchmark.py` and `quantum/backends/selector.py`).

## 1. Discovered Technical Debt & Defects

1. **`q_speace/self_improvement_cortex/evolutionary_memory.py` (78% cov)**:
   - `EvolutionaryMemory(max_entries <= 0)` was accepted without raising `ValueError`.
   - `MemoryEntry.net_impact` propagated `NaN`/`Inf`, allowing `has_failed_before()` and `success_rate()` to fail open silently.
2. **`q_speace/experiments/online_agent.py` (66% cov)**:
   - `Adapter.call()` parsed tool JSON without RFC 8259 `parse_constant` rejection, allowing non-finite `NaN`/`Infinity`.
   - `Budget` accepted negative or non-finite `tool_limit` / `energy_limit`.
3. **`q_speace/experiments/context_decay.py` (41% cov)**:
   - `audit_development(())` raised `KeyError`/`ZeroDivisionError` on empty archives instead of a clear `ValueError`.
   - Full `develop` → `freeze` → tamper detection → `evaluate` pipeline lacked fast deterministic test coverage.
4. **`q_speace/spiking/bridge.py` (82% cov)**:
   - `to_state()` and `to_qca_rotations()` did not reject non-finite (`NaN`/`Inf`) or empty spike arrays.
5. **`q_speace/spiking/linear.py` (81% cov)**:
   - `__init__()` did not validate finite `k > 0`; `forward()` raised `IndexError` instead of `ValueError` on 0-D scalar input.
6. **`q_speace/earth_feed.py` (80% cov)**:
   - `EarthSignals` did not validate finite `[0, 1]` bounds in `__post_init__`.

## 2. Verification Goals

- All six defects fixed fail-closed without breaking any existing test or public signature.
- Every targeted low-coverage module raised above **90%** coverage (lifting total repository coverage above **91.5%**).
- `pytest`, `black`, `ruff`, `mypy`, `compileall`, and `mcp_server --self-test` 100% green.

## 3. BCEL Classification

Recorded in `q_speace/bcel/catalog.py`:
- **Functional**: `Fail-closed numeric and RFC 8259 input guards across core and experiment modules (T242)`.
