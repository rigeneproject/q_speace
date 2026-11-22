# T230 — Technical Debt Audit, Code Debugging, and Remediation Plan

**Status:** agentic (production remediation & hardening)  
**Date:** 2026-11-22  
**Scope:** Bug fixes, fail-closed validation hardening, real-backend invariant enforcement,
quality-gate/CI recovery, CLI/AACM safety fixes, and regression test coverage across `q_speace/`.  
**Dependencies:** `AGENTS.md`, `T208_DEVELOPMENT_GUIDELINES_SPEC.md`,
`T217_SAFE_ASSIMILATION_LIFECYCLE_SPEC.md`, `PARADIGM_6_0_V2_0_ERRATA.md`.  
**Non-goals:** No new cognitive layer, no physical actuation, no real-QPU execution,
no self-approval, no weakening of no-consciousness or no-communication invariants.

---

## 1. Problem Statement & Audit Findings

A full static, dynamic, and specification-alignment audit of the `q_speace` repository
identified the following concrete defects and technical debt items:

1. **Broken global quality gates & CI gaps (T208 Group A.2)**
   - `ruff check q_speace` fails with 2 errors (`F401` unused import in `q_speace/cli.py:26`,
     `B009` `getattr` with constant attribute in `q_speace/orchestrator.py:215`).
   - `mypy q_speace` fails with 2 errors (`q_speace/cli.py:345` incompatible union assignment
     on `chosen`; `q_speace/cli.py:400` untyped `jsonschema` import).
   - `black --check q_speace tests` fails on 3 files (`evolution_council.py`,
     `quantum_state.py`, `aacm/loop.py`).
   - `pyproject.toml` omits `jsonschema` (imported directly by `cli.py`, `aacm/checkpoint.py`,
     and economy schema tests) and `pytest-asyncio` (required by `asyncio_mode = "auto"`).
   - `.github/workflows/ci.yml` does not run `ruff check tests`, `black --check`, `mypy q_speace`,
     or `python -m py_compile`.

2. **Critical runtime, physics, and numerical bugs**
   - `q_speace/quantum/quantum_state.py`: `apply_lindblad()` computes
     `u_eff = I + effective_h * dt` where `effective_h = -0.5j * sum(rate * L^dag L)`,
     applying a phase rotation instead of the non-Hermitian MCWF no-jump decay
     `I - 1j * effective_h * dt = I - 0.5 * sum(rate * L^dag L) * dt`.
     Additionally, `equal_superposition()` and `from_amplitudes()` lack full bounds and
     finiteness checks.
   - `q_speace/orchestrator.py`: default `max_energy_w=10.0` is below the calibrated cost of
     even a single qubit (`>= 15.5 W` under `RICALIBRATION_FACTOR=30.94`), permanently
     blocking every default tick (`gate_blocked_ratio=1.0`, dead QCA/radio branch).
     When `passes_sevo()` rejects a step, `TickReport.gate_blocked` is wrongly reported as `False`.
     `self._radio_enabled` (`enable_radio`) is stored but never checked before encoding/transmitting.
   - `q_speace/genome/quantum_genes.py` & `q_speace/quantum/backends/`:
     AGENTS.md Invariant #4 ("No real quantum backend without `QuantumGeneSet.noise_model`
     configured and an energy/Sevo gate") is not enforced in `QuantumGeneSet.validate()` or
     `selector.build()`. `QiskitBackend.run()` indexes little-endian bitstrings in reversed
     order (`top[i]` instead of `top[::-1][i]`) and ignores `self._shots` when called with default
     args. `QuantumInspireBackend.run()` mishandles bitstring keys and bit ordering.
     `"qiskit-aer"` is documented in `QuantumGeneSet` but absent from `selector._REGISTRY`.

3. **Fail-open NaN/Inf & domain validation bugs (Errata E03, T208 §6)**
   - `QuantumCostModel` accepts negative qubit/gate/depth/decoherence values and `NaN`/`inf`,
     allowing fail-open bypass of energy/Sevo gates.
   - `InformationalLogicalField` does not validate finite `coherence_phi` in `[0, 1]`;
     `update(zeros)` reports `coherence_phi=1.0`; `NaN` poisons `adaptive_clock_rate()`.
   - `DAT`, `J_c`, and `V` (`q_speace/economy/`) allow `NaN`/`inf` past `<`/`>` checks
     (e.g. `dat.spend(float("nan"), ...)` succeeds and corrupts balance to `NaN`).
   - `dynamic_spikes` and `spike_rate` (`q_speace/spiking/encoder.py`) crash with
     `ZeroDivisionError` or return `NaN` on empty arrays; negative `coherence_phi` can yield
     a non-positive denominator.
   - `ComplianceFilter._check_spurious` (`q_speace/radio/compliance_filter.py`) does not
     reject non-finite `iq_samples`.

4. **SpikingBrainCortex, Audit, Client & EarthFeed defects**
   - `SpikingBrainCortex.report()` emits `NaN` (with NumPy RuntimeWarning) when all ticks
     have `sevo == -inf`. `tick()` does not guard non-finite `confidence` before computing
     `energy_w`, and has no optional `max_energy_w` gate.
   - `BrainAuditLog.recent(k=0)` returns all lines (`lines[-0:]`). Non-finite floats serialize
     as non-standard JSON `NaN`/`Infinity`. Add privacy-safe `redact_raw_text` option per T208 §4.3.
   - `HTTPSpikingBrainClient._parse_think_result()` assumes `body` is a `dict` and does not
     validate finite confidence; stale `# noqa: F821` comment.
   - `EarthFeed._fetch_real()` skips `resp.raise_for_status()`, lacks empty/malformed payload
     guards, keeps an unused `self._rng`, and swallows exceptions silently.

5. **SelfImprovementCortex, Benchmark, AACM CLI, MCP Self-Test & CLI defects**
   - `SelfImprovementCortex.tick()` mutates the caller's `context` dict in place, queries
     `evo_memory.has_failed_before(str(proposal.level), ...)` while `store()` uses
     `str(ctx.get("coherence_phi", 0))`, never records rejected proposals as failures, and
     leaves `SIAReport.verdict` permanently `None`.
   - `self_improvement_cortex/benchmark.py` (0% coverage) double-adds classical registers with
     `QuantumCircuit(n, n)` + `measure_all()`, stores `np.float64` instead of `float`, and
     lacks input validation.
   - `q_speace/aacm/__main__.py` (0% coverage) exits with code `0` on safety failures
     (`GATE_BYPASS_ATTEMPTED`, `OMEGA_COLLAPSE`, `VALIDATION_OVERFIT_DETECTED`,
     `REPUTATION_DRIFT`), opens draft PRs under `--create-pr-on-success` without checking
     `StopReason.CONVERGED`, and ignores the `--human-abort-sentinel` CLI option.
   - `q_speace/economy/mcp_server.py`: `_self_test()` relies on `assert` (disabled under `-O`)
     and runs the last 3 tools outside `try/except`.
   - `q_speace/cli.py` (0% coverage): prints raw Rich markup (`[green]...[/green]`) via stdlib
     `print`/`typer.echo`, crashes on `quantum run --ticks 0 --radio`, discards `build(backend)`
     in `quantum benchmark`, does not allowlist schema names in `economy validate-schema`, and
     carries stale docstrings.

---

## 2. BCEL Classification

All remediation tasks preserve existing invariants and add no biological/consciousness claim.
One explicit entry is added to `q_speace/bcel/catalog.py`:

- **Real quantum backend noise-model and energy gate (T230)** — `functional`:
  Enforce non-ideal `QuantumGeneSet.noise_model` and explicit energy/Sevo gating before
  constructing or executing any non-numpy quantum backend. This is a software safety and
  resource contract (AGENTS.md §2, T208 §3.5), not a claim of physical hardware qualification
  or quantum advantage.

---

## 3. Sequential Execution Plan

| Task | Title | Scope | Verification |
|---|---|---|---|
| **T230-01** | Spec, BCEL gate & plan | `docs/T230_*_SPEC.md`, `q_speace/bcel/catalog.py` | BCEL catalog tests |
| **T230-02** | Quality gates, packaging & CI | `cli.py`, `orchestrator.py`, `evolution_council.py`, `quantum_state.py`, `aacm/loop.py`, `pyproject.toml`, `.github/workflows/ci.yml` | `ruff`, `black --check`, `mypy` green |
| **T230-03** | Numerical, physics & fail-closed hardening | `quantum_state.py`, `cognitive_cost_model.py`, `ilf.py`, `economy/dat.py`, `economy/primitives.py`, `spiking/encoder.py`, `radio/compliance_filter.py` | Unit + negative NaN/Inf/Lindblad tests |
| **T230-04** | Orchestrator & real-backend invariants | `orchestrator.py`, `genome/quantum_genes.py`, `quantum/backends/{selector,qiskit_backend,quantum_inspire_backend}.py` | Orchestrator + backend gate & bit-order tests |
| **T230-05** | SpikingBrain, Audit, Client & EarthFeed | `spiking_brain/{cortex,audit,client}.py`, `earth_feed.py` | Cortex/audit/client/earth regression tests |
| **T230-06** | SIA, Benchmark, AACM CLI & MCP self-test | `self_improvement_cortex/{cortex,benchmark}.py`, `aacm/{loop,__main__}.py`, `economy/mcp_server.py` | SIA, AACM CLI, MCP self-test tests |
| **T230-07** | CLI hardening & regression test suites | `cli.py`, `tests/test_cli.py`, `tests/test_aacm_cli.py`, `tests/test_t230_bugfixes.py` | Full pytest & coverage verification |
| **T230-08** | Documentation reconciliation & final gates | `README.md`, `docs/T230_*_SPEC.md` | Full `pytest`, `ruff`, `black`, `mypy`, `py_compile` |

---

## 4. Safety, Rollback & Deferred Roadmap

- **Rollback:** All changes are modular and backwards-compatible with existing public APIs
  (`RICALIBRATION_FACTOR`, `BrainAuditLog` default record schema, `SpikingBrainCortex` default
  `max_energy_w=None`, `selector.build()` numpy fallback).
- **Deferred (not executed in T230, tracked for subsequent tickets):**
  - `T222-07..11` (NCM Phase 0 calibration lock — requires human parameter decision per `T222_TASKS.md`).
  - `T208` Group B/C (`T209`/`T210` reference vertical-slice telemetry & live hardware campaign).
  - `T221` Phase P1 (`q_speace/seed/constitution.py` & PTAA demonstrator).
  - `spiking_brain_server/` WSL2 hardware helper scripts (hardcoded `/home/roby/...` dev paths).

---

## 5. Verification Results (2026-11-22)

All 8 sequential tasks (`T230-01` .. `T230-08`) completed and verified locally:

| Gate | Command | Result |
|---|---|---|
| Full test suite | `.venv/Scripts/python.exe -m pytest -q` | **692 passed, 3 skipped** (up from 655; +37 regression tests), **86.82% coverage** (up from 82.69%) |
| Lint | `.venv/Scripts/python.exe -m ruff check q_speace tests` | **0 errors** (clean) |
| Format | `.venv/Scripts/python.exe -m black --check q_speace tests` | **180 files unchanged** (clean) |
| Type check | `.venv/Scripts/python.exe -m mypy q_speace` | **0 errors across 117 source files** (clean) |
| Bytecode compile | `python -m py_compile` (all 30 touched files) + `compileall -q q_speace` | **exit code 0** |
| MCP self-test (`-O`) | `python -O -m q_speace.economy.mcp_server --self-test` | **all 10 tools green** (exit code 0) |

Notable module coverage improvements:
- `q_speace/cli.py`: `0% -> 90%`
- `q_speace/aacm/__main__.py`: `0% -> 81%`
- `q_speace/self_improvement_cortex/benchmark.py`: `0% -> 65%`
- `q_speace/orchestrator.py`: `86% -> 95%`
- `q_speace/edd_cvt/ilf.py`: `79% -> 88%`
- `q_speace/spiking_brain/audit.py`: `64% -> 80%`
- `q_speace/spiking_brain/cortex.py`: `88% -> 93%`
- `q_speace/self_improvement_cortex/cortex.py`: `88% -> 95%`

