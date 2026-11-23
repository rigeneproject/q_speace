"""T247: Read-only MCP Resources & Bootstrap Prompts for agentic organism-loop integration.

Pure-Python single source of truth shared by both the stdio MCP server
(``q_speace/economy/mcp_server.py``) and the authenticated HTTP MCP server
(``q_speace/remote_mcp/server.py``).

Strictly advisory and read-only:
- Exposes zero mutation endpoints and zero new MCP tools.
- Never claims quantum consciousness, biological life, or physical actuation authority.
- Maps all bio-inspired concepts to deterministic BCEL mathematical rules.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict
from typing import Any

from q_speace.bcel.catalog import BCELCatalog

from .iont_node import VALID_IONT_TIERS
from .mcp_tools import build_singularity_framework_manifest

RESOURCE_ORGANISM_LOOP = "qspeace://guide/organism-loop"
RESOURCE_TOOL_WORKFLOWS = "qspeace://guide/tool-workflows"
RESOURCE_SINGULARITY_MANIFEST = "qspeace://manifest/singularity"
RESOURCE_BCEL_CATALOG = "qspeace://catalog/bcel"

_SAFE_ROLE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.-]{0,63}$")
_VALID_BOOTSTRAP_MODES = frozenset({"single_agent", "swarm_node"})

_ORGANISM_LOOP_MARKDOWN = """# Q-SPEACE Canonical Organism-Loop Integration Protocol (T247)

> **Advisory & BCEL Notice**: Q-SPEACE is **not** a living or conscious entity.
> All concepts below are deterministic mathematical/cybernetic rules verified by the BCEL gate.
> This MCP server is strictly read-only/advisory (`advisory_only: true`,
> `physical_actuation_permitted: false`, `self_approval_permitted: false`).

## Purpose

An external AI agent or multi-agent swarm connected to Q-SPEACE achieves resilient,
organism-like self-regulation **only when its own execution loop closes around the
following 5-stage homeostatic cycle** and respects fail-closed refusals.

## Stage 1 — Constitutional Bootstrap (Session Start)

1. Call `singularity_framework_manifest` (or read `qspeace://manifest/singularity`) to load:
   - Immutable constitutional invariants (`no_self_approval`, `no_unreviewed_actuation`,
     `bounded_epigenetic_envelope`, `causal_grounding_required`).
   - Stage thresholds (`PRE_NUCLEATION` → `STAGE_3_CLOSURE_SIM`) and non-compensable brakes.
2. Call `bcel_lookup` (or read `qspeace://catalog/bcel`) to distinguish **functional**
   mathematical rules (keep) from **accidental** biological metaphors (discard).

## Stage 2 — Metabolic & Temporal Homeostasis (Before Every Non-Trivial Action)

3. Call `adaptive_clock_rate` with the current coherence estimate `coherence_phi` in `[0, 1]`
   to obtain the homeostatic cadence proxy `r(t) = 10 / sqrt(S_info)`. Lower coherence
   signals higher informational entropy and requires conservative pacing/verification.
4. Call `metabolism_cost_eval` to estimate operation cost and `Sevo = delta_utility / delta_entropy_info`.
   Reject or defer candidate actions where `passes_sevo` is `false` or `sevo_defined` is `false`.
5. For multi-dimensional trade-offs or shared resource budgets, call `cme_evaluate` (12-dim CME vector)
   and `vtec_allocate` (projected-gradient allocation under hard constraints).

## Stage 3 — Bounded Epigenetic & Phase-Transition Gates (Before Self-Tuning)

6. Never modify immutable constitutional parameters. Express reversible behavioral tuning as a
   bounded proposal and submit it to `epigenetic_step_evaluate`:
   - Requires distinct `proposer_id` and `reviewer_id` (self-approval is rejected fail-closed).
   - Enforces homeostatic decay toward the baseline genome, `Sevo` floor, and semantic/causal
     drift limits.
7. Periodically submit cycle telemetry to `phase_transition_assess` to verify that
   `semantic_entropy_drift`, `causal_grounding_error`, `thermal_load_ratio`, and
   `allopoietic_dependence` remain within admissible bounds.

## Stage 4 — Cellular / Swarm Federation (Multi-Agent Mode)

8. Keep fast-plane safety interlocks **strictly local (Layer-0)** — never place slow consensus
   or DLT verification inside a motor/real-time loop (`dlt_in_motor_loop: false`).
9. Evaluate cellular/edge node posture via `iont_node_assess` (4-layer architecture).
10. Combine beliefs across independent agents using `kl_barycentre_aggregate` (instead of
    monolithic authority or naive majority vote), summarize system telemetry with `compute_jc`,
    and screen external standards/policies with `elasticity_test` (`ACCEPT`/`REJECT`).

## Stage 5 — Fail-Closed Discipline & Independent Review

- Any `isError: true`, rejected gate, non-finite metric, or missing independent review MUST
  halt promotion/adaptation rather than silently degrading.
- Host-system integration, physical actuation, and regulatory compliance remain governed by
  `T217` (Safe Assimilation Lifecycle) and external human/organizational review (`T240`/`T241`).
"""


def _build_tool_workflows_json() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "spec": "T247",
        "advisory_only": True,
        "physical_actuation_permitted": False,
        "self_approval_permitted": False,
        "http_tool_count": 12,
        "excluded_over_http": ["dat_mint", "dat_spend", "bridge_activate", "physical_actuation"],
        "phases": [
            {
                "phase": "1_constitutional_bootstrap",
                "goal": "Load immutable invariants, stage thresholds, and BCEL rules.",
                "tools": [
                    {
                        "name": "singularity_framework_manifest",
                        "scope": "qspeace:catalog.read",
                        "example_arguments": {"section": "invariants"},
                    },
                    {
                        "name": "bcel_lookup",
                        "scope": "qspeace:catalog.read",
                        "example_arguments": {"concept": "Homeostasis"},
                    },
                ],
            },
            {
                "phase": "2_metabolic_and_temporal_homeostasis",
                "goal": "Gate candidate actions by adaptive cadence, Sevo efficiency, CME balance, and VTEC constraints.",
                "tools": [
                    {
                        "name": "adaptive_clock_rate",
                        "scope": "qspeace:compute",
                        "example_arguments": {"coherence_phi": 0.65},
                    },
                    {
                        "name": "metabolism_cost_eval",
                        "scope": "qspeace:compute",
                        "example_arguments": {
                            "num_qubits": 0,
                            "num_gates": 16,
                            "delta_utility": 3.0,
                            "delta_entropy_info": 1.0,
                        },
                    },
                    {
                        "name": "cme_evaluate",
                        "scope": "qspeace:compute",
                        "example_arguments": {
                            "energy": 0.7,
                            "matter": 0.7,
                            "information": 0.8,
                            "time": 0.7,
                            "ecology": 0.8,
                            "resilience": 0.85,
                            "wellbeing": 0.8,
                            "innovation": 0.75,
                            "reversibility": 0.9,
                            "distribution": 0.75,
                            "coherence": 0.8,
                            "regeneration": 0.7,
                        },
                    },
                    {
                        "name": "vtec_allocate",
                        "scope": "qspeace:simulation.compute",
                        "example_arguments": {
                            "objective_kind": "log_utility",
                            "u_max": [10.0, 10.0],
                            "constraints": {"budget_total": 12.0},
                        },
                    },
                ],
            },
            {
                "phase": "3_epigenetic_and_phase_gates",
                "goal": "Verify reversible parameter adaptations and non-compensable phase-transition brakes.",
                "tools": [
                    {
                        "name": "epigenetic_step_evaluate",
                        "scope": "qspeace:simulation.compute",
                        "example_arguments": {
                            "locus": "verification_depth",
                            "delta": 0.05,
                            "proposer_id": "agent-planner",
                            "reviewer_id": "independent-verifier",
                            "reviewer_approved": True,
                            "semantic_entropy_drift": 0.01,
                            "causal_benchmark_delta": 0.03,
                            "sevo": 2.0,
                            "power_watts": 120.0,
                        },
                    },
                    {
                        "name": "phase_transition_assess",
                        "scope": "qspeace:compute",
                        "example_arguments": {
                            "timescale_decoupling_ratio": 12.0,
                            "autocatalytic_k": 1.35,
                            "independent_validation_rate": 0.97,
                            "semantic_entropy_drift": 0.02,
                            "net_verified_improvement": 0.04,
                            "consecutive_verified_cycles": 4,
                            "allopoietic_dependence": 0.85,
                            "sevo": 2.2,
                            "thermal_load_ratio": 0.6,
                            "independent_review_passed": True,
                        },
                    },
                ],
            },
            {
                "phase": "4_federation_and_consensus",
                "goal": "Coordinate multiple agents on the slow plane while preserving local Layer-0 safety interlocks.",
                "tools": [
                    {
                        "name": "iont_node_assess",
                        "scope": "qspeace:compute",
                        "example_arguments": {
                            "node_id": "agent-cell-01",
                            "scale_tier": "SIMULATION_DIGITAL_TWIN",
                            "sensor_count": 12,
                            "actuator_count": 2,
                            "swarm_agent_count": 4,
                            "dlt_quorum_ratio": 0.67,
                            "layer0_hardware_interlock_present": True,
                            "layer0_halt_latency_ms": 2.5,
                            "dlt_in_motor_loop": False,
                            "energy_harvesting_ratio": 0.3,
                            "power_budget_mw": 500.0,
                            "measured_power_mw": 180.0,
                            "packet_loss_rate": 0.02,
                            "sensor_causal_grounding_error": 0.01,
                        },
                    },
                    {
                        "name": "kl_barycentre_aggregate",
                        "scope": "qspeace:simulation.compute",
                        "example_arguments": {
                            "distributions": [[0.7, 0.2, 0.1], [0.5, 0.3, 0.2]],
                        },
                    },
                    {
                        "name": "compute_jc",
                        "scope": "qspeace:compute",
                        "example_arguments": {
                            "J": 1.0,
                            "delta_S": 0.1,
                            "delta_I_c": 0.4,
                            "R_b": 0.9,
                            "delta_C": 0.2,
                            "measured_components": 5,
                        },
                    },
                    {
                        "name": "elasticity_test",
                        "scope": "qspeace:compute",
                        "example_arguments": {
                            "claim": {
                                "metric_name": "latency_ms",
                                "claimed_value": 10.0,
                                "observed_value": 10.2,
                            },
                            "external": {
                                "standard_id": "std-v1",
                                "min_value": 0.0,
                                "max_value": 20.0,
                            },
                        },
                    },
                ],
            },
        ],
    }


def list_mcp_resources() -> list[dict[str, Any]]:
    """Return MCP ``resources/list`` descriptors (strictly read-only)."""
    return [
        {
            "uri": RESOURCE_ORGANISM_LOOP,
            "name": "organism-loop-guide",
            "title": "Q-SPEACE Canonical Organism-Loop Integration Protocol",
            "description": (
                "Read-only 5-stage homeostatic protocol explaining how a single AI agent or "
                "federated swarm composes Q-SPEACE MCP tools under BCEL invariants."
            ),
            "mimeType": "text/markdown",
        },
        {
            "uri": RESOURCE_TOOL_WORKFLOWS,
            "name": "tool-workflows",
            "title": "Q-SPEACE 12-Tool HTTP Sequence & Scope Matrix",
            "description": (
                "Machine-readable JSON workflow map of the 12 advisory HTTP MCP tools, "
                "their OAuth scopes, and canonical example payloads."
            ),
            "mimeType": "application/json",
        },
        {
            "uri": RESOURCE_SINGULARITY_MANIFEST,
            "name": "singularity-manifest",
            "title": "Singularity Phase-Transition & Epigenetic Constitutional Manifest (T234)",
            "description": (
                "Full machine-readable T234 v1.1 constitutional genome, epigenetic envelope, "
                "physical brakes, and assimilation rules (advisory only)."
            ),
            "mimeType": "application/json",
        },
        {
            "uri": RESOURCE_BCEL_CATALOG,
            "name": "bcel-catalog",
            "title": "BCEL Functional vs. Accidental Equivalences Catalog",
            "description": (
                "Complete BCEL classification separating functional mathematical rules from "
                "accidental carbon-biology metaphors."
            ),
            "mimeType": "application/json",
        },
    ]


def read_mcp_resource(uri: str) -> dict[str, str]:
    """Read one static read-only MCP resource by exact URI.

    Returns ``{"uri": uri, "mimeType": ..., "text": ...}``.
    Raises ``KeyError`` for unknown URIs (fail-closed).
    """
    if uri == RESOURCE_ORGANISM_LOOP:
        return {
            "uri": uri,
            "mimeType": "text/markdown",
            "text": _ORGANISM_LOOP_MARKDOWN,
        }
    if uri == RESOURCE_TOOL_WORKFLOWS:
        return {
            "uri": uri,
            "mimeType": "application/json",
            "text": json.dumps(
                _build_tool_workflows_json(), indent=2, sort_keys=True, allow_nan=False
            ),
        }
    if uri == RESOURCE_SINGULARITY_MANIFEST:
        manifest = build_singularity_framework_manifest()
        return {
            "uri": uri,
            "mimeType": "application/json",
            "text": json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False),
        }
    if uri == RESOURCE_BCEL_CATALOG:
        entries = [asdict(entry) for entry in BCELCatalog().all()]
        payload = {
            "schema_version": 1,
            "advisory_only": True,
            "functional_count": sum(1 for e in entries if e["classification"] == "functional"),
            "accidental_count": sum(1 for e in entries if e["classification"] == "accidental"),
            "entries": entries,
        }
        return {
            "uri": uri,
            "mimeType": "application/json",
            "text": json.dumps(payload, indent=2, sort_keys=True, allow_nan=False),
        }
    raise KeyError(f"unknown_resource_uri:{uri}")


def list_mcp_prompts() -> list[dict[str, Any]]:
    """Return MCP ``prompts/list`` descriptors (session-start bootstrap templates)."""
    return [
        {
            "name": "organism_bootstrap",
            "title": "Q-SPEACE Organism-Loop Session Bootstrap",
            "description": (
                "Guided session-start sequence taking a connected AI agent through "
                "constitutional bootstrap -> metabolic/clock gating -> epigenetic/phase gates -> "
                "federated aggregation across the 12 Q-SPEACE MCP tools."
            ),
            "arguments": [
                {
                    "name": "agent_role",
                    "description": "Short role label for the connecting agent (e.g. planner, coordinator).",
                    "required": False,
                },
                {
                    "name": "mode",
                    "description": "Operating mode: 'single_agent' (default) or 'swarm_node'.",
                    "required": False,
                },
            ],
        },
        {
            "name": "metabolic_action_gate",
            "title": "Pre-Action Metabolic & Adaptive-Clock Gate",
            "description": (
                "Evaluate a candidate action before execution using adaptive_clock_rate, "
                "metabolism_cost_eval (Sevo gate), cme_evaluate, and vtec_allocate."
            ),
            "arguments": [
                {
                    "name": "action_summary",
                    "description": "Concise description of the proposed action (1..256 chars).",
                    "required": True,
                },
                {
                    "name": "coherence_phi",
                    "description": "Current coherence estimate in [0.0, 1.0] (default 0.5).",
                    "required": False,
                },
            ],
        },
        {
            "name": "federated_swarm_cycle",
            "title": "Federated Swarm Slow-Plane Coordination Cycle",
            "description": (
                "Coordinate multiple agents using iont_node_assess (Layer-0 interlock separation), "
                "kl_barycentre_aggregate, elasticity_test, and phase_transition_assess."
            ),
            "arguments": [
                {
                    "name": "node_count",
                    "description": "Number of participating swarm nodes in [2, 64] (default 4).",
                    "required": False,
                },
                {
                    "name": "scale_tier",
                    "description": (
                        "IoNT/cellular tier: one of " + ", ".join(sorted(VALID_IONT_TIERS)) + "."
                    ),
                    "required": False,
                },
            ],
        },
    ]


def _validate_clean_text(value: Any, *, field: str, min_len: int, max_len: int) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    stripped = value.strip()
    if not (min_len <= len(stripped) <= max_len):
        raise ValueError(f"{field} length must be in [{min_len}, {max_len}]")
    if any(ord(ch) < 32 for ch in stripped):
        raise ValueError(f"{field} must not contain control characters")
    return stripped


def _check_allowed_args(
    arguments: dict[str, Any] | None, allowed: frozenset[str]
) -> dict[str, Any]:
    if arguments is None:
        return {}
    if not isinstance(arguments, dict):
        raise ValueError("arguments must be an object")
    unknown = set(arguments) - allowed
    if unknown:
        raise ValueError(f"unknown_prompt_arguments:{sorted(unknown)}")
    return arguments


def get_mcp_prompt(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    """Materialize one MCP prompt template with strict fail-closed argument validation.

    Returns ``{"description": ..., "messages": [{"role": "user", "content": {"type": "text", "text": ...}}]}``.
    """
    if name == "organism_bootstrap":
        args = _check_allowed_args(arguments, frozenset({"agent_role", "mode"}))
        role_raw = args.get("agent_role", "general_agent")
        role = _validate_clean_text(role_raw, field="agent_role", min_len=1, max_len=64)
        if not _SAFE_ROLE_RE.match(role):
            raise ValueError("agent_role must match ^[A-Za-z0-9][A-Za-z0-9 _.-]{0,63}$")
        mode = args.get("mode", "single_agent")
        if not isinstance(mode, str) or mode not in _VALID_BOOTSTRAP_MODES:
            raise ValueError(f"mode must be one of {sorted(_VALID_BOOTSTRAP_MODES)}")

        federation_step = (
            "4. **Federated Swarm Coordination (`swarm_node` mode)**:\n"
            "   - Call `iont_node_assess` to verify local Layer-0 safety interlocks and confirm `dlt_in_motor_loop=false`.\n"
            "   - Aggregate peer probability estimates via `kl_barycentre_aggregate` instead of unilateral override.\n"
            "   - Summarize telemetry with `compute_jc` and screen external standards with `elasticity_test`."
            if mode == "swarm_node"
            else "4. **Multi-Signal Consolidation (`single_agent` mode)**:\n"
            "   - When reconciling multiple candidate hypotheses or sub-tool estimates, call `kl_barycentre_aggregate`.\n"
            "   - Summarize cycle telemetry via `compute_jc` and validate external tolerances with `elasticity_test`."
        )
        text = (
            f"You are operating as `{role}` in `{mode}` mode connected to the Q-SPEACE MCP server.\n"
            "Treat Q-SPEACE strictly as an advisory mathematical governance layer (BCEL-filtered: "
            "no consciousness claim, no self-approval, no physical actuation authority).\n\n"
            "Execute the following 4-stage homeostatic loop before committing to high-impact actions:\n"
            "1. **Constitutional Bootstrap**:\n"
            "   - Read `qspeace://guide/organism-loop` and call `singularity_framework_manifest` "
            "(section=`invariants`) + `bcel_lookup` to anchor immutable constraints.\n"
            "2. **Metabolic & Temporal Gating**:\n"
            "   - Call `adaptive_clock_rate` with your current `coherence_phi` in `[0, 1]` to set verification cadence.\n"
            "   - Call `metabolism_cost_eval` to verify `passes_sevo=true` before executing resource-intensive steps; "
            "use `cme_evaluate` and `vtec_allocate` for multi-objective resource allocation.\n"
            "3. **Epigenetic & Phase-Transition Verification**:\n"
            "   - Before adjusting policy/hyperparameters, call `epigenetic_step_evaluate` with a distinct `reviewer_id` "
            "(never self-approve) and check `phase_transition_assess` for semantic/causal drift or thermal overload.\n"
            f"{federation_step}\n\n"
            "Fail-closed rule: if any Q-SPEACE gate rejects a proposal or returns an error, halt promotion "
            "and surface the exact rejection reason for independent review."
        )
        return {
            "description": f"Q-SPEACE organism-loop session bootstrap ({role}, {mode}).",
            "messages": [{"role": "user", "content": {"type": "text", "text": text}}],
        }

    if name == "metabolic_action_gate":
        args = _check_allowed_args(arguments, frozenset({"action_summary", "coherence_phi"}))
        if "action_summary" not in args:
            raise ValueError("action_summary is required")
        action = _validate_clean_text(
            args["action_summary"], field="action_summary", min_len=1, max_len=256
        )
        phi_raw = args.get("coherence_phi", "0.5")
        if isinstance(phi_raw, bool):
            raise ValueError("coherence_phi must be a finite number in [0.0, 1.0]")
        try:
            phi = float(phi_raw)
        except (TypeError, ValueError) as exc:
            raise ValueError("coherence_phi must be a finite number in [0.0, 1.0]") from exc
        if not math.isfinite(phi) or not (0.0 <= phi <= 1.0):
            raise ValueError("coherence_phi must be a finite number in [0.0, 1.0]")

        text = (
            f"Evaluate the following candidate action through Q-SPEACE metabolic and homeostatic gates "
            f"before execution:\n- Candidate action: {action}\n- Current coherence_phi: {phi:.4f}\n\n"
            "Required tool sequence (strictly advisory, fail-closed on rejection):\n"
            f'1. Call `adaptive_clock_rate` with `{{"coherence_phi": {phi:.4f}}}` and record `s_info` and `rate`.\n'
            "2. Call `metabolism_cost_eval` with estimated operation complexity (`num_qubits`, `num_gates`, "
            "`delta_utility`, `delta_entropy_info`). Proceed only if `sevo_defined` is true and `passes_sevo` is true.\n"
            "3. Call `cme_evaluate` on the 12-dimensional sustainability/resilience vector to verify no dimension collapses.\n"
            "4. If the action competes for shared budgets, call `vtec_allocate` under explicit hard constraints.\n"
            "5. Return a concise go/no-go recommendation citing exact numeric outputs; do not perform unreviewed actuation."
        )
        return {
            "description": "Pre-action Q-SPEACE metabolic & adaptive-clock gate workflow.",
            "messages": [{"role": "user", "content": {"type": "text", "text": text}}],
        }

    if name == "federated_swarm_cycle":
        args = _check_allowed_args(arguments, frozenset({"node_count", "scale_tier"}))
        count_raw = args.get("node_count", "4")
        if isinstance(count_raw, bool):
            raise ValueError("node_count must be an integer in [2, 64]")
        try:
            node_count = int(str(count_raw).strip())
        except (TypeError, ValueError) as exc:
            raise ValueError("node_count must be an integer in [2, 64]") from exc
        if not (2 <= node_count <= 64):
            raise ValueError("node_count must be an integer in [2, 64]")

        tier = args.get("scale_tier", "SIMULATION_DIGITAL_TWIN")
        if not isinstance(tier, str) or tier not in VALID_IONT_TIERS:
            raise ValueError(f"scale_tier must be one of {sorted(VALID_IONT_TIERS)}")

        text = (
            f"Run a slow-plane Q-SPEACE federated swarm coordination cycle for `{node_count}` nodes "
            f"at scale tier `{tier}` (advisory/simulation only; never authorize physical actuation):\n\n"
            "Required tool sequence:\n"
            "1. Call `iont_node_assess` for each participating node profile; enforce "
            "`layer0_hardware_interlock_present=true` and `dlt_in_motor_loop=false`.\n"
            "2. Collect normalized state/action distributions from healthy nodes and call "
            "`kl_barycentre_aggregate` to form a consensus belief without single-node dominance.\n"
            "3. Validate any external coordination standard or SLA delta with `elasticity_test`.\n"
            "4. Submit aggregate swarm telemetry to `phase_transition_assess` to check "
            "`semantic_entropy_drift`, `causal_grounding_error`, `sevo`, and `thermal_load_ratio`.\n"
            "5. If any node fails Layer-0 interlock, causal grounding, or quorum checks, isolate its "
            "proposal on the slow plane while keeping local Layer-0 fail-safe control autonomous."
        )
        return {
            "description": f"Federated Q-SPEACE swarm cycle ({node_count} nodes, {tier}).",
            "messages": [{"role": "user", "content": {"type": "text", "text": text}}],
        }

    raise KeyError(f"unknown_prompt:{name}")
