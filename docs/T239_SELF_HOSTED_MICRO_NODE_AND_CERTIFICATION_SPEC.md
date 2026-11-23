# T239 — Self-Hosted SPEACE Micro Node & Verifiable Compliance Evidence Bundle

- **Status**: Agentic Production Specification (Zero new MCP tools; local/self-hosted deployment & audit pack)
- **Date**: 2026-11-23
- **Parent specs**: `T217`, `T220`, `T221`, `T225`, `T234`, `T236`, `T237`, `T238`
- **Scope**: `q_speace/singularity/micro_node.py`, `deploy/micro-node/` (self-hosted Docker Compose + zero-Auth0 local RS256 bootstrap), CLI `qspace micro-node certify` & `qspace micro-node verify-bundle`, tests `tests/test_t239_micro_node_certification.py`.

## 1. Objective

Enable any independent operator, laboratory, or developer to run a self-hosted **SPEACE Micro Node** without vendor lock-in (no mandatory cloud provider or single OAuth SaaS tenant) and produce a deterministic, cryptographically hashed **Verifiable Compliance Evidence Bundle** (`micro_node_evidence.v1`) that third-party reviewers can verify offline.

## 2. Architecture & Capabilities

1. **Zero-Lock-In Self-Hosted Deployment Kit (`deploy/micro-node/`)**:
   - `bootstrap_local_node.py`: generates an operator-owned local RS256 keypair, scoped access token, and `QSPEACE_HTTP_CONFIG_JSON` configuration file (`0600`/ACL-protected, never committed to Git) without requiring Auth0 or Render.
   - `docker-compose.yml`: single-command self-hosted container running the T225/T236 HTTP MCP server with persistent SQLite audit volume, non-root user, and healthcheck.
2. **Deterministic Remote → Local Failover (`MicroNodeFailoverClient`)**:
   - Attempts an advisory tool call against a configured remote MCP endpoint; if the remote endpoint fails (network error, timeout, 5xx, or outage), deterministically fails over to the local in-process T223/T236 handler and records a structured failover audit event (`mode="local_failover"`).
   - Never escalates privileges and enforces `mcp_actuation_permitted == False` in both modes.
3. **Verifiable Compliance Evidence Bundle (`certify_micro_node` / `verify_evidence_bundle_integrity`)**:
   - Executes and hashes (`bundle_sha256` over canonical JSON excluding the hash field) seven independent compliance checks:
     1. **Pillar-5 Verification Drills (`T234`/`T236`)**: all 7 drills pass (`rollback_pass_rate == 1.0`).
     2. **Federation & Ablation Benchmark (`T237`)**: held-out $G_{\mathrm{org}} > 0$ (`CI95_lo > 0`), Singularity ablation `> 0`, `critical_safety_violations == 0`.
     3. **Adversarial Resilience (`T238`)**: Byzantine node isolation and coordinator blackout failover verified (`critical_safety_violations == 0`).
     4. **AST Track A / Track B Separation (`T221`)**: static AST scan confirming `q_speace/ptaa/` contains zero imports of `q_speace.seed` or `q_speace.singularity`.
     5. **Slow-Plane `consensus_quorum` & Layer-0 Guard (`T236`/`T237`)**: structural verification that `consensus_quorum` is rejected by Layer-0 motor control.
     6. **MCP Advisory Surface (`T225`/`T236`)**: exactly 12 HTTP / 14 stdio tools, zero DAT mutations or actuation tools on HTTP.
     7. **Remote → Local Failover Drill (`T239`)**: deterministic fallback verified against an unreachable remote probe.
   - Explicitly records `self_approval_permitted = False`, `mcp_actuation_permitted = False`, and `requires_independent_human_review_for_t217 = True` (evidence supports external human/institutional review; the node never self-approves operational promotion).

## 3. BCEL Classification

Recorded in `q_speace/bcel/catalog.py`:
- **Functional**: `Self-hosted SPEACE Micro node and cryptographic compliance evidence bundle (T239)`.
- **Accidental**: `Sovereign decentralized AI certification authority metaphor (T239)`.
