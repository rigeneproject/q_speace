# T246 — Remote MCP Persistent State & Replayable Hash-Chained Audit Checkpoints (`T225` §16)

- **Status**: Implemented (Agentic Mode)
- **Roadmap Reference**: `docs/T225_REMOTE_MCP_SERVICE_SPEC.md` §16 (staging/production durability requirements)
- **Invariants Preserved**:
  - Zero new MCP tools added (strictly preserves the `T236` 12 HTTP / 14 stdio tool surface).
  - Default in-memory `Gateway` behavior remains 100% backward-compatible when `HTTPConfig.state_db_path is None`.
  - Operational mutable state (`state_db_path`) is strictly separated from append-only hash-chained audit logs (`audit_path`).
  - No claim of quantum consciousness, no superluminal communication, no automatic actuation or Bridge/DAT mutation exposed over HTTP.

## 1. Motivation

In `T225`, `q_speace/remote_mcp/server.py` kept session ownership/expiry records and per-principal token-bucket rate limits purely in process memory, while `Audit` wrote SHA-256 hash-chained records to SQLite without offline chain verification or signed/hashed checkpoint export. Under process restarts:

1. Per-principal rate limits and active session counts reset to zero, permitting restart-induced quota bypass.
2. Tail truncation or mid-log SQLite tampering in `audit.sqlite` lacked a first-class verifier and externalizable checkpoint anchor.

## 2. Design

### 2.1 Optional Persistent State Store (`SQLiteStateStore`)

- Added optional `state_db_path: Path | None = None` to `HTTPConfig` (validated to be distinct from `audit_path` when set).
- `SQLiteStateStore` in `q_speace/remote_mcp/service.py` persists:
  - `sessions(sid TEXT PRIMARY KEY, owner TEXT NOT NULL, created_at REAL NOT NULL, last_seen REAL NOT NULL)`
  - `rates(owner TEXT PRIMARY KEY, tokens REAL NOT NULL, updated_at REAL NOT NULL)`
- When `config.state_db_path` is configured, `Gateway`:
  - Uses wall-clock epoch timestamps (`time.time()`) with monotonic-safe clamping (`max(0.0, now - previous)`) so timestamps remain meaningful across restarts and immune to negative clock jumps.
  - Hydrates persisted sessions (immediately pruning expired entries) and per-principal rate buckets on startup.
  - Synchronously writes through session creations, touches, deletions, expirations, and rate-bucket updates to SQLite, failing closed with HTTP `503 state_store_unavailable` if the store cannot be written.
  - Closes the SQLite handle cleanly during ASGI lifespan shutdown.

### 2.2 Hash-Chained Audit Verification & Externalizable Checkpoints

- Preserves the existing `audit(seq, payload, previous, digest)` SQLite table schema (100% backward-compatible with existing audit databases).
- `Audit.verify_chain()` / `verify_audit_chain(db_path)`:
  - Scans rows ordered by `seq ASC`, enforcing strict contiguous `seq` (`1, 2, ..., N`), exact `previous` link equality, strict RFC 8259 JSON payload decoding (rejecting `NaN`/`Infinity`), and exact SHA-256 recomputation (`sha256(previous + payload)`).
  - Detects middle-row deletions, payload modifications, chain link tampering, or corrupt payloads.
- `Audit.export_checkpoint(checkpoint_path=None, *, hmac_key=None)`:
  - Fail-closed: verifies the full chain first and raises `ServiceError("audit_chain_corrupted", 500)` if corrupted.
  - Produces a canonical checkpoint JSON record (`schema_version`, `exported_at_ns`, `row_count`, `first_seq`, `last_seq`, `head_digest`, `checkpoint_digest`, and optional `hmac_sha256` when `hmac_key` is supplied).
  - Writes atomically (`temp + flush + fsync + os.replace`) when `checkpoint_path` is provided.
- `verify_audit_checkpoint(db_path, checkpoint, *, hmac_key=None)`:
  - Validates the checkpoint digest (and optional HMAC with `hmac.compare_digest`), re-verifies the entire SQLite audit chain, and proves that row `checkpoint["last_seq"]` still exists with exact `checkpoint["head_digest"]` — catching tail truncation, rollback, and tampering while permitting valid append-only growth after the checkpoint.

## 3. BCEL Classification

Recorded in `q_speace/bcel/catalog.py` as **functional**:

> `Persistent SQLite MCP state store and verifiable hash-chained audit checkpoints (T246)` — Keep as durable write-through session/rate-limit persistence across restarts and tamper-evident SHA-256 audit chain and checkpoint verification.

## 4. Verification Criteria

Covered by `tests/test_t246_remote_mcp_persistence.py` and existing `tests/test_t225_http.py`:
1. Gateway restart with `state_db_path` preserves per-principal rate-limit exhaustion and active session counts, while still pruning expired sessions and reflecting explicit `DELETE /mcp`.
2. `verify_audit_chain` passes on normal HTTP MCP traffic and fails on payload tampering, `previous`-hash tampering, or middle-row deletion.
3. `export_checkpoint` + `verify_audit_checkpoint` pass both immediately and after further append-only traffic, and fail on tail truncation, checkpoint forgery, or wrong HMAC key.
4. `HTTPConfig` rejects `state_db_path == audit_path`.
5. Exposed HTTP MCP tool surface remains strictly 12 tools.
