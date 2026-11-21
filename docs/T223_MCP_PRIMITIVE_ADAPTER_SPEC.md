# T223 — MCP primitive adapter

Status: implemented experimental stdio integration; no operational promotion.
Date: 2026-11-21.

## Scope and contract

Extend economy/mcp_server.py without new dependencies. Support MCP protocol
2025-03-26 and 2024-11-05, negotiate unsupported versions to 2025-03-26,
advertise tools only, consume notifications without replies, answer ping,
and terminate at stdin EOF. After initialize, tool operations wait for
notifications/initialized. Preserve pre-initialize legacy direct JSON-RPC calls
and discovery for existing callers; this compatibility extension is deliberate.

All ten tools advertise JSON Schema derived from Pydantic input models and
validate arguments before dispatch. tools/call returns JSON encoded in MCP
text content with isError; unknown tools and malformed call envelopes use -32602; input-schema violations
for known tools return isError=true,
unknown methods -32601, invalid envelopes -32600 and invalid JSON -32700.
Execution-domain failures use isError=true. Unsupported capabilities are not
advertised. No HTTP transport, resources, prompts or asynchronous cancellation.
Requests execute sequentially; clients own timeouts and process termination.

## Added primitives

- adaptive_clock_rate requires finite coherence_phi in [0,1]. Return rate,
  s_info and coherence_phi using InformationalLogicalField unchanged. This
  proxy is not a measurement of document contradiction and performs no sleep.
- metabolism_cost_eval requires nonnegative integer num_qubits and num_gates,
  finite delta_utility and delta_entropy_info; accepts optional operation
  fields, nonnegative duration_s and sevo_threshold. Return estimated watts,
  joules, Sevo and passes_sevo. Nonfinite Sevo is represented as null with
  sevo_defined=false; the underlying rejection behavior remains unchanged.
- bcel_lookup optionally takes an exact concept string; omission lists all
  entries. It is read-only. Unknown concepts are tool execution errors.

## Responsibility and invariants

Consulted T208 and T217. This adapter does not implement qualification,
sandboxing, self-approval, real quantum execution, actuation, or host release.
BCEL classifies the adapter as functional classical message passing. Existing
no-consciousness and no-communication invariants remain unchanged.
DAT balances are process-local, mutable simulated accounting, lost at exit;
callers can mint them and therefore cannot use them as a security boundary or
an authoritative external spending cap. No authentication or multi-tenant
isolation is claimed. The parent client controls access to the local process.
External scheduling, token budgets, audit logs and independent promotion checks
belong to the orchestrator. Energy numbers remain estimates, not telemetry.

## Verification and experimental baseline

Retain all existing tests, updating only registry counts and self-test text.
Cover version negotiation, notifications, ping, discovery schemas, standard
call envelopes, validation, errors, stream recovery, and each added primitive.
Compare wrapper outputs with native primitive calls. No efficiency improvement
is claimed: future experiments compare the same workload with and without
client-enforced scheduling/budget policies under T208.

## Local launch

From the repository root: `python -m q_speace.economy.mcp_server`.
A stdio client should use the absolute Python executable for this environment,
arguments `-m`, `q_speace.economy.mcp_server`, and this repository as cwd.
Diagnostics/self-test: append `--self-test` (not for MCP sessions).

Protocol references:
- https://modelcontextprotocol.io/specification/2025-03-26/basic/lifecycle
- https://modelcontextprotocol.io/specification/2025-03-26/server/tools

## Verification outcome

On the project `.venv` with official MCP SDK 1.30.0 (Python 3.12.10), full pytest
reports 572 passed, 3 skipped, coverage 82.77%. The focused MCP selection reports
34 passed, including test_official_sdk_stdio_session (previously skipped).
The original fifteen economy MCP tests remain present and pass. Ruff, Black,
mypy and py_compile pass for the changed adapter/test files. Global
`ruff check q_speace` still reports two existing issues outside this change:
F401 in cli.py and B009 in orchestrator.py. Both files already had local
modifications before T223; no unrelated edits were made.

A separate temporary client script, executed outside pytest with ClientSession
and stdio_client, negotiated 2025-03-26, pinged, discovered all ten tools and
successfully invoked bcel_lookup, adaptive_clock_rate and metabolism_cost_eval.
A schema-invalid coherence_phi=2 returned isError=true; a subsequent ping and
valid clock call succeeded on the same session. No stdout parser errors were
observed. This verifies the exercised official Python SDK path, not every client
or all optional protocol features.

## Official-SDK verification follow-up

The optional `mcp` extra installs the official Python SDK (`mcp>=1,<2`). A local
`.venv` uses the installed project development packages via system-site-packages.
Run `.venv/Scripts/python.exe -m pytest -k mcp -v --no-cov` to execute the focused
checks without the repository-wide coverage threshold on a selected subset.
The SDK test verifies initialize, ping, ten-tool discovery, each added primitive,
isError=true for a schema-invalid clock value, and a successful ping and valid
call afterwards. The stdio parser must remain free of non-protocol stdout.
This is interoperability evidence, not host-system qualification under T217.

## Proposed remote extension

[T225 - Remote MCP service](T225_REMOTE_MCP_SERVICE_SPEC.md) specifies a separate,
opt-in Streamable HTTP service with OAuth, principal/session isolation, bounded
work and audit. An experimental HTTP adapter is now implemented and locally tested; it is not
a verified public OAuth deployment. Its initial
remote allowlist contains eight consultative tools and excludes DAT mutation;
the ten-tool local stdio contract above remains unchanged.

[Manifesto v2.0 errata](PARADIGM_6_0_V2_0_ERRATA.md) corrects the Sevo gate,
metric semantics and repository mapping before future integration. T224 remains
an independent experiment with its recorded negative policy result.

