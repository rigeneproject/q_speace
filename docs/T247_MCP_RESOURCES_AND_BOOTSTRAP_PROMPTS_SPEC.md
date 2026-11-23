# T247 — MCP Read-Only Resources & Bootstrap Prompts for Agentic Organism-Loop Integration

- **Status**: Implemented (Agentic Mode)
- **Scope**: Both MCP transports (`q_speace/economy/mcp_server.py` stdio and `q_speace/remote_mcp/server.py` HTTP)
- **Invariants Preserved**:
  - **Zero new MCP tools** (strictly preserves the 12 HTTP / 14 stdio tool surface).
  - All Resources and Prompts are strictly **read-only and advisory** (`advisory_only: true`, `physical_actuation_permitted: false`, `self_approval_permitted: false`).
  - Strict BCEL framing: no claim of quantum consciousness, biological life, or superluminal communication; bio-inspired terms are explicitly mapped to deterministic mathematical rules.
  - On HTTP (`q_speace/remote_mcp/`), `resources/list`, `resources/read`, `prompts/list`, and `prompts/get` enforce OAuth scope `qspeace:catalog.read` fail-closed and record hash-chained audit entries on reads/prompt materializations.

## 1. Motivation

Previously, Q-SPEACE MCP servers exposed only `tools` (`tools/list`, `tools/call`). While the 12 HTTP tools provide the mathematical building blocks for homeostatic, metabolic, epigenetic, and federated multi-agent regulation, a newly connected external AI agent received no standardized protocol explaining *in what sequence* to compose those tools or *which invariants* must remain immutable.

`T247` adds standard MCP **Resources** (read-only reference artifacts) and **Prompts** (session-start workflow templates) backed by a single pure-Python source of truth (`q_speace/singularity/mcp_guidance.py`).

## 2. Read-Only MCP Resources

| URI | MIME Type | Purpose |
|---|---|---|
| `qspeace://guide/organism-loop` | `text/markdown` | Canonical 5-stage homeostatic integration protocol for a single agent or federated swarm |
| `qspeace://guide/tool-workflows` | `application/json` | Deterministic JSON workflow map of the 12 HTTP tools, required OAuth scopes, and minimal example payloads |
| `qspeace://manifest/singularity` | `application/json` | Full `T234` v1.1 machine-readable Singularity & Epigenetic Constitutional Manifest |
| `qspeace://catalog/bcel` | `application/json` | Complete BCEL functional vs. accidental equivalences catalog |

## 3. Read-Only MCP Bootstrap Prompts

| Prompt Name | Arguments | Purpose |
|---|---|---|
| `organism_bootstrap` | `agent_role` (optional, default `"general_agent"`), `mode` (`"single_agent"` \| `"swarm_node"`) | Session-start bootstrap guiding the agent through constitutional bootstrap → metabolic/clock gating → epigenetic/phase gates → federated aggregation |
| `metabolic_action_gate` | `action_summary` (required, 1..256 chars), `coherence_phi` (optional float in `[0, 1]`, default `"0.5"`) | Pre-action metabolic and adaptive-clock gate sequence before committing to high-cost operations |
| `federated_swarm_cycle` | `node_count` (optional int in `[2, 64]`, default `"4"`), `scale_tier` (optional `VALID_IONT_TIERS`, default `"SIMULATION_DIGITAL_TWIN"`) | Slow-plane multi-agent coordination sequence enforcing Layer-0 interlock separation and quorum discipline |

All prompt arguments are strictly validated fail-closed (unknown argument names, non-finite floats, out-of-range counts, control characters, or oversized strings are rejected).

## 4. BCEL Classification

Recorded in `q_speace/bcel/catalog.py` as **functional**:

> `Read-only MCP organism-loop resources and bootstrap prompt templates (T247)` — Keep as deterministic, advisory-only protocol documentation and workflow templates guiding external agents to compose homeostatic, metabolic, epigenetic, and federated consensus tools without mutating state or bypassing invariants.

## 5. Verification

Covered by `tests/test_t247_mcp_resources_and_prompts.py` and updated `tests/test_mcp_protocol.py`:
1. Both stdio JSON-RPC and HTTP (`TestClient` + official `mcp.ClientSession`) advertise `resources` and `prompts` capabilities alongside `tools`.
2. All 4 resources list and read cleanly with deterministic content; unknown URIs fail closed.
3. All 3 prompts list and materialize cleanly with valid arguments; invalid/oversized/unknown arguments fail closed.
4. HTTP Gateway enforces `qspeace:catalog.read` scope (`403` without scope), records hash-chained audit entries, and preserves strictly 12 HTTP / 14 stdio tools.
