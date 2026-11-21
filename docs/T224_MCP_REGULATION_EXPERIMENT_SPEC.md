# T224 — Controlled MCP client regulation experiment

Status: experimental; isolated synthetic benchmark, no host promotion.
Date: 2026-11-21. Prerequisites: T223, T208; T217 consulted.

## Hypothesis and frozen comparison

A deterministic client policy may reduce wasted attempts on persistent failures,
but must not hide lost completions or the latency/MCP overhead it introduces.
Retain the policy only if regulated correct completions are at least baseline
completions and regulated executed synthetic tokens are strictly lower. Otherwise
report rejected (completion loss) or inconclusive (no token reduction). This is
a mechanical result for this fixture, not independent operational approval.
No energy-efficiency, LLM-quality, statistical-significance or generality claim.

The versioned benchmark contains four fixed document-retrieval transcripts:
clean, transient failure, persistent failure, delayed resolution. Each attempt
returns tool_error, ambiguous, evidence or answer, with a progress flag and an
optional answer/document reference. Only the offline evaluator reads expected
answers. The policy uses previous observations and next-action resource bounds;
it must never inspect future events or ground-truth correctness.
Persistent failures repeat the last observation up to max_iterations; delayed
resolution explicitly measures false preventive stops. The runner is a scripted
agent/tool substitute, not a real LLM. Tokens and DAT are synthetic units.

Both arms receive identical cases, action bounds and max_iterations. A baseline
executes without MCP consultation, sleeping, or preventive budget/stall gates.
The regulated arm uses MCP per candidate step; order is counterbalanced AB/BA
by case index. One server session is initialized outside case timers; startup
seconds are recorded separately. No VTEC allocation is introduced in this slice.

## Frozen policy and units

Prior consecutive tool errors e and latest ambiguity indicator d determine
S_info = (min(e/3, 1) + d)/2; coherence_phi = 1 - S_info.
These are declared software proxies; no semantic uncertainty measurement is
claimed. Query adaptive_clock_rate and apply actual asyncio.sleep with
backoff_seconds = min(max_backoff_seconds, 1/rate). Default cap is 0.1 s.
Every attempted action has a known upper bound of 20 synthetic tokens and
1 DAT. The synthetic metabolism operation is num_qubits=0, num_gates=1,
duration_s=0.01, delta_utility=2, delta_entropy_info=1: an API exercise, not an
energy model of language generation. Log its estimated watts/joules separately.

Before work, enforce independent client totals: token_budget=120, dat_budget=6,
estimated_energy_budget_joules=1; deny if the next reservation would exceed any
bound. Also deny when prior consecutive no-progress attempts reach stall_limit=3
or Sevo refuses. All limits/configuration are frozen in the manifest. DAT is
minted once per case with a unique routing key; mint_time=t=0 and half-life=1e9
hold decay fixed to isolate the accounting experiment. dat_spend precedes task
execution. Check its receipt matches the expected remaining balance; no remint,
no retries after an uncertain spend and no automatic server restart. Reservations
remain charged conservatively if a spend has an uncertain outcome. No work is
allowed after a failed or malformed MCP response. Hard bounds belong to this
controlled runner; this is not a security boundary for an unconstrained agent.

## Evidence contract

Create a fresh output directory; refuse to overwrite prior evidence. Write
manifest.json, events.jsonl and summary.json. The manifest records schema/policy
versions, config, benchmark SHA256 and contents, implementation SHA256, Git HEAD
and dirty status, Python/SDK versions, and server startup time. Each step logs
run/case/arm identifiers, action index, proposed and reserved/executed resources,
prior signals, MCP inputs/outputs (clock, cost and DAT), planned/applied sleep,
monotonic elapsed seconds, decision/reason and observed outcome. Flush each row.
Terminal rows record answer correctness against independent fixture labels,
stop reason, wall-clock seconds, attempted iterations, executed synthetic tokens,
reserved DAT and estimated joules. MCP failure is an infrastructure failure,
not a completed task or a successful resource saving. Write its failure evidence
and exit nonzero; partial comparisons are inconclusive.

The summary includes per-case paired results/deltas and per-arm totals,
completion rate, preventive-stop frequency and measured wall-clock seconds.
No bootstrap interval is appropriate for four constructed deterministic cases.
Preserve failures and false stops in the report; do not tune thresholds after
seeing these cases and then describe the same run as held-out validation.

## Boundaries and checks

Use official optional SDK via ClientSession over stdio. Limit individual calls
and initialization using timeouts. All calls target the local simulation server;
no remote model, arbitrary code execution, quantum backend, credentials, real
economic resources, sensors or actuators are used. BCEL retains only numerical
feedback and classical accounting; no consciousness or quantum communication.
No production routing or existing orchestrator defaults change.

Tests cover identical baseline transcripts, causal scheduling, pre-execution
budget bounds including exact equality, stalled loops, delayed false stops,
fail-closed invalid tool results/timeouts, JSONL/manifest reproducibility and
an actual official-SDK A/B run. Run pytest, py_compile, Ruff, Black and mypy.

Launch: `.venv/Scripts/python.exe -m q_speace.experiments.mcp_regulation --output OUTPUT`.
Install optional dependencies with `python -m pip install -e ".[mcp]"` if needed.

## Recorded verification and decision (2026-11-21)

Final default run: [manifest](../artifacts/T224_default_final_20261121/manifest.json),
[JSONL](../artifacts/T224_default_final_20261121/events.jsonl),
[summary](../artifacts/T224_default_final_20261121/summary.json).
The implementation hash matches the recorded source. One earlier development
run remains preserved under artifacts/T224_default_20261121; the final run above
uses the final summary fields and is the reference evidence.

| Metric | Baseline | MCP-regulated |
| --- | ---: | ---: |
| Cases completed correctly | 3/4 | 2/4 |
| Executed iterations | 18 | 11 |
| Synthetic tokens | 360 | 220 |
| Simulated DAT (sum across cases) | 18 | 11 |
| Preventive stops | 0 | 2 |
| Wall seconds, case timers | 0.0010183 | 0.4067854 |

Decision: **rejected** under the frozen criterion. One preventive stop occurs on
the baseline-incomplete persistent-failure case; another is a false preventive
stop on delayed_resolution, which the baseline solves. Lower synthetic token
usage does not compensate for losing a completion. The deliberately cheap replay
makes communication and actual backoff dominate wall time; no performance or
physical-energy advantage is inferred. Limits are per case, not aggregate totals.

A separate failure-path check with dat_budget=2 is retained at
[budget-check summary](../artifacts/T224_budget_check_20261121/summary.json).
Each regulated case reserves at most 2 DAT before refusing further work; exact
budget equality allows the clean two-step task to complete. The three remaining
cases stop with dat_budget. This run exercises the live budget block, not a tuned
candidate or an additional validation set.

Verification: 27 new tests pass, including the official-SDK full experiment.
Full suite: 599 passed, 3 skipped, coverage 82.83%. Ruff on touched files, Black,
mypy and py_compile pass. Global Ruff retains the same two pre-existing findings
in cli.py (F401) and orchestrator.py (B009), outside this intervention. Existing
unrelated local modifications were preserved. No production integration or
operational promotion is authorized by these results.
