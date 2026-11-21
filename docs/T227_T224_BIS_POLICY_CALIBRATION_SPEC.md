# T227 / T224-bis — Controlled client-policy calibration

Date: 2026-11-21. Experimental, advisory-only; T208/T217/T224/T225 apply.
No existing policy, endpoint, LLM or physical controller is changed.

## Frozen design (before execution)

Task: synthetic scientific-document retrieval of the current reference laser
wavelength, 532 nm, with document provenance. Scripted tool observations are
identical across paired arms; no LLM is invoked. T224 remains unchanged and
its negative result remains valid. This study uses local SDK MCP stdio, not
the online OAuth endpoint and not a LangGraph/token-refresh wrapper.

All new arms have the same eight-action cap, 160 synthetic tokens, eight local
simulated DAT, and 1 modeled joule. Twenty tokens and one DAT are reserved
before each executed action. Local accounting is not dat_spend, currency or
actual provider usage. The synthetic cost operation is inherited from T224.
Baseline has the same hard caps but no stall stop or MCP overhead.

Candidate grid: mappings legacy and differentiated; stop signal all_no_progress
or consecutive_errors; thresholds 3, 5, 7, 8. No post-verification tuning.
Legacy uncertainty = (min(errors/3,1)+ambiguous)/2. Differentiated uncertainty
= min(.95, .8*min(errors/5,1)+.2*ambiguous). phi = 1-uncertainty.
Clock controls delay min(.1,1/rate) only; no semantic confidence is claimed.
No-progress resets on explicit progress; consecutive errors reset on a
non-error observation. Errors-only stopping deliberately permits unresolved
ambiguity until a hard budget; this trade-off must be reported.

Calibration fixtures: clean; one-error recovery; four errors followed by
evidence and answer; seven ambiguous steps then answer; persistent error;
persistent ambiguity. Selection sees calibration results only. Eligible policies
must preserve every baseline-correct case (not merely total completion count)
and reduce total synthetic tokens. Rank eligible policies by tokens, then total
planned sleep, then canonical policy key. No eligible policy => no selection.
No additional requirement to minimize or maximize coherence is imposed.

Verification fixtures: clean with an evidence prelude; three errors then answer;
four errors then answer; six ambiguous steps then answer; progress followed by
five ambiguous steps and answer; persistent error; persistent ambiguity. These
are constructed variations, not independently sampled held-out scientific data.
Both fixture sets are frozen and hashed before selection; the selector receives
only calibration rows. Cases/labels never reach policy functions. Reports use
"constructed verification", never independent validation or significance.

Challenge set (not selection/retuning): six consecutive errors then answer
versus persistent error with the same six-step prefix; seven ambiguous steps
then answer. Any policy stopping inside a shared prefix must stop both members.
A positive main verification does not override a negative challenge result.
No causal policy can guarantee both early stopping of persistent errors and
completion of every arbitrarily delayed identical-prefix recovery.

## Evidence and stages

CLI calibrate creates a fresh output root, protocol/fixture hashes and JSONL,
runs the grid over calibration only and writes selection.json plus its digest.
CLI verify is a separate invocation: validates hashes of source, fixtures and
selection; refuses overwrite; consumes the frozen policy without selection.
Each stage uses official MCP ClientSession stdio, initialize/ping; calibration
records planned delay without sleeping; verification applies actual bounded
sleep. Do not compare calibration wall time with verification wall time.
Per-action JSONL records prior telemetry, policy, decisions, tool inputs/results,
resource reservations and timing. Summary includes paired completions, false
early stops, persistent-stop frequency, tokens/DAT, modeled energy, planned and
actual sleep, wall time and MCP RPC overhead. Preserve partial logs and fail
closed/inconclusive on tool/schema/transport failure. No automatic retries.
Each RPC has a five-second timeout. Positive outcome on this small fixture is
not evidence of general savings, measured energy reduction or better reasoning.

Tests must cover causal inputs, mapping boundaries, same hard budgets in both
arms, delayed recovery, persistent ambiguity, exact reservation limits,
per-case regression rejection, tie-break determinism, lock tampering and stage
separation. Official-SDK E2E verifies the staged workflow. Run pytest,
py_compile, Ruff, Black and mypy on touched code. BCEL retains only explicit
feedback/accounting; no consciousness, quantum communication or self-approval.


## Recorded result — 2026-11-21

The frozen selection was differentiated / consecutive_errors / threshold 5.
Calibration: 4/6 correct in both arms, 680 -> 620 synthetic tokens. The mapping
ablation at that same signal/threshold produced the same completions/tokens;
planned sleep was 1.51154 s (legacy) versus 1.15860 s (differentiated). The
mapping itself did not rescue answers. Selection was locked before the separate
verify invocation; no thresholds or mappings were changed afterwards.

| Constructed partition | Baseline correct | Candidate correct | Tokens baseline -> candidate | False early stops |
| --- | ---: | ---: | ---: | ---: |
| Verification | 5/7 | 5/7 | 840 -> 780 | 0 |
| Challenge | 2/3 | 1/3 | 460 -> 360 | 1 |
| Combined | 7/10 | 6/10 | 1300 -> 1140 | 1 |

Decision: **not promoted**. The primary constructed envelope preserves completions while saving attempts,
but the shared-prefix
challenge loses six_errors_recover. Token savings do not compensate for that
completion loss. Five-error stopping cannot distinguish persistent failure from
an otherwise identical six-error prefix that will recover. Persistent ambiguity
uses all eight allowed attempts: this unsolved-loop cost remains visible.

Primary verification wall time: baseline .00126 s, candidate 1.88049 s including
1.79466 s actual sleep and .07732 s MCP RPC time (78 calls). These timings refer
to this cheap replay, not a realistic task-speedup result. Calibration executed
920 MCP tool RPCs without sleep; verification/challenge together executed 114
with sleep. Infrastructure/session startup is outside per-case timers.

Evidence: [protocol](../artifacts/T227_policy_calibration_20261121/protocol.json),
[selection](../artifacts/T227_policy_calibration_20261121/selection.json),
[calibration](../artifacts/T227_policy_calibration_20261121/calibrate/summary.json),
[verification/challenge](../artifacts/T227_policy_calibration_20261121/verify/summary.json),
[consolidated evaluation](../artifacts/T227_policy_calibration_20261121/evaluation.json).
The protocol is protected against accidental modifications by the selection
hash/digest; these files are not a cryptographic trust/authorization service.
Development tests exercise these constructed fixtures too, so they are not
fresh independently held-out data. No independence or significance is claimed.

Seven focused tests pass, including staged official-SDK E2E, tamper rejection
and a prohibition on reselection during verification. Full local suite: 633
passed, three skipped; coverage 82.65%. Black, Ruff, mypy and py_compile pass
on touched code. Unrelated local edits remain unchanged; global Ruff still has
the previously documented local cli.py/orchestrator.py findings.

Reproduce in a NEW directory (both phases refuse overwriting evidence):

```powershell
.\.venv\Scripts\python.exe -m q_speace.experiments.policy_calibration calibrate --output artifacts/T227_new
.\.venv\Scripts\python.exe -m q_speace.experiments.policy_calibration verify --output artifacts/T227_new
```

Source/dependency hashes must match the calibration lock, including line endings.
A changed implementation requires a new experiment root and new calibration.
No token caching/HTTP retry wrapper, online deployment, LLM experiment or
production policy replacement is included in this task.


The isolated publication candidate, excluding the three unrelated draft tests,
also passes: 630 passed, three skipped, coverage 82.67%; global Ruff clean.
The 633-test local count includes those three pre-existing untracked tests.
