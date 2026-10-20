# T-SPB-3-C — LLM response audit trail

**Status**: SHIPPED. Every `SpikingBrainCortex.apply_to_ilf` writes a
JSONL provenance record.

## What is logged

A `BrainAuditLog` writes one line per apply. Each record has the full
provenance needed to reconstruct who said what, when, with which
model, and what the gate decisions were.

| field | meaning |
| --- | --- |
| `ts` | wall-clock timestamp (seconds since epoch) |
| `agent_id` | which ILF agent was updated |
| `backend` | backend name (e.g. `http://localhost:8002`, `stub`) |
| `backend_meta` | backend metadata (`model`, `sidecar_url`, ...) |
| `prompt_hash` | first 16 hex chars of SHA-256(prompt) |
| `prompt_excerpt` | first 120 chars of the prompt |
| `result_text_excerpt` | first 160 chars of the model's reply |
| `result_confidence` | backend-reported confidence |
| `belief` | full belief vector (list of floats) |
| `n_tokens` | token count the backend reported |
| `coherence_phi_pre` | ILF φ BEFORE apply |
| `coherence_phi_post` | ILF φ AFTER apply |
| `sevo` | Sevo gate value at apply time |
| `energy_w` | energy model output (W) |
| `approved` | whether the cortex approved the apply |
| `reason` | cortex reason string |

## Where it lives

- Default path: `~/.q_speace/brain_audit.jsonl`
- Override via `Q_SPEACE_BRAIN_AUDIT_PATH` environment variable.
- Per-instance override by passing a `BrainAuditLog(path=...)` to
  `SpikingBrainCortex.__init__(..., brain_audit_log=log)`.

## How to use

```python
from q_speace.spiking_brain.cortex import SpikingBrainCortex
from q_speace.spiking_brain.audit import BrainAuditLog

cortex = SpikingBrainCortex(
    backend=my_backend,            # stub, http client, etc.
    brain_audit_log=BrainAuditLog(),
)
report = await cortex.tick("explain coherence_phi")
# one line appended to ~/.q_speace/brain_audit.jsonl

# inspect recent records
cortex.brain_audit_log.recent(5)
```

## Why "best-effort"?

The audit trail must never break a live cognition cycle. A
`OSError` or encoding error is logged to stderr but does **not**
raise. The cortex still applies the belief to the ILF. This is a
deliberate design choice (matching the BCEL rule "generated text
is untrusted; only Sevo/coherence-gated belief updates may influence
the organism") — the audit is an **observability** surface, not a
gating mechanism.

## Test coverage

- `test_cortex_apply_to_ilf_writes_audit_record` — direct apply
  writes one line with all fields.
- `test_cortex_tick_audit_record_includes_provenance` — full
  pipeline writes a record with sevo + energy_w + φ pre/post.
- `test_cortex_audit_log_disabled_by_default` — when no
  `brain_audit_log` is passed, no audit file is created and no
  exception is raised.

All 3 pass alongside the 70 existing tests (73 total, 2 skipped).

## Privacy / secret hygiene

The `prompt_excerpt` and `result_text_excerpt` are **plaintext
truncated strings**. Do not include in the audit anything that
should not be on disk (API keys, PII, etc.). If you need to log
prompts with sensitive content, hash them at the caller and pass
the hash through `backend_meta`.

The audit path is **never committed to git** — it lives under
`~/.q_speace/` (home directory) and is added to `.gitignore` in
local clones.

## Files added

- `q_speace/spiking_brain/audit.py` — `BrainAuditLog` + record
  builder + `recent()` reader
- `tests/test_spiking_brain.py` — 3 new tests
- `docs/T-SPB-3-C.md` — this file

## Files modified

- `q_speace/spiking_brain/cortex.py`:
  - imports `BrainAuditLog`
  - `__init__` accepts `brain_audit_log: BrainAuditLog | None = None`
  - `apply_to_ilf` signature gains keyword-only `prompt`, `sevo`,
    `energy_w`, `approved`, `reason` (all with safe defaults so
    legacy callers still work)
  - `apply_to_ilf` writes one record after the ILF update
  - `tick` passes the gate decisions through to `apply_to_ilf`