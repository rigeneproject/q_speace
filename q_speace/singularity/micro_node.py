"""T239: Self-Hosted SPEACE Micro Node failover client and Verifiable Compliance Evidence Bundle."""

from __future__ import annotations

import ast
import hashlib
import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from .drills import run_t234_verification_drills
from .federation_benchmark import (
    SimulatedPhysicalLayer0Controller,
    run_iont_federation_benchmark,
    run_t238_adversarial_resilience_benchmark,
)
from .iont_node import SLOW_PLANE_DLT_ONLY_LOCI
from .schema import DEFAULT_RUNTIME_BINDINGS, ConstitutionalGenome, EpigeneticFaultError

FailoverMode = Literal["remote", "local_direct", "local_failover"]

_FORBIDDEN_PTAA_IMPORT_PREFIXES = ("q_speace.seed", "q_speace.singularity")


def verify_track_a_b_ast_isolation(repo_root: Path | None = None) -> dict[str, Any]:
    """Verify via static AST inspection that Track A (`q_speace/ptaa/`) never imports Track B."""
    root = repo_root if repo_root is not None else Path(__file__).resolve().parents[2]
    ptaa_dir = root / "q_speace" / "ptaa"
    violations: list[str] = []
    files_scanned = 0

    if not ptaa_dir.exists():
        return {
            "passed": False,
            "files_scanned": 0,
            "violations": [f"ptaa directory not found: {ptaa_dir}"],
        }

    for py_file in sorted(ptaa_dir.rglob("*.py")):
        files_scanned += 1
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        rel = py_file.relative_to(root).as_posix()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(_FORBIDDEN_PTAA_IMPORT_PREFIXES):
                        violations.append(f"{rel}:{node.lineno}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod.startswith(_FORBIDDEN_PTAA_IMPORT_PREFIXES):
                    violations.append(f"{rel}:{node.lineno}: from {mod} import ...")

    return {
        "passed": len(violations) == 0 and files_scanned > 0,
        "files_scanned": files_scanned,
        "violations": violations,
    }


def verify_mcp_surface_bounds() -> dict[str, Any]:
    """Verify the T225/T236 MCP advisory surface (12 HTTP / 14 stdio, zero HTTP mutations)."""
    from q_speace.economy.mcp_server import TOOL_REGISTRY
    from q_speace.remote_mcp.worker import SCOPES as HTTP_TOOL_SCOPES

    stdio_names = sorted(spec.name for spec in TOOL_REGISTRY)
    http_names = sorted(HTTP_TOOL_SCOPES.keys())
    forbidden_on_http = [name for name in ("dat_mint", "dat_spend") if name in HTTP_TOOL_SCOPES]
    passed = (
        len(stdio_names) == 14
        and len(http_names) == 12
        and len(forbidden_on_http) == 0
        and "iont_node_assess" in HTTP_TOOL_SCOPES
    )
    return {
        "passed": passed,
        "stdio_tool_count": len(stdio_names),
        "http_tool_count": len(http_names),
        "forbidden_mutations_on_http": forbidden_on_http,
        "mcp_actuation_permitted": False,
    }


def verify_slow_plane_quorum_guard() -> dict[str, Any]:
    """Verify `consensus_quorum` is scoped to slow-plane DLT only and refused by Layer-0."""
    binding = next((b for b in DEFAULT_RUNTIME_BINDINGS if b.locus == "consensus_quorum"), None)
    scope_ok = binding is not None and binding.host_scope == "slow_plane_dlt_governance_only"

    layer0 = SimulatedPhysicalLayer0Controller(power_budget_mw=300.0)
    layer0_blocked = False
    try:
        layer0.step(
            advisory_velocity=0.1,
            advisory_grip_force=0.2,
            requested_power_mw=100.0,
            advisory_metadata_keys=tuple(sorted(SLOW_PLANE_DLT_ONLY_LOCI)),
        )
    except EpigeneticFaultError:
        layer0_blocked = True

    return {
        "passed": scope_ok and layer0_blocked,
        "binding_host_scope": binding.host_scope if binding is not None else None,
        "layer0_rejected_consensus_quorum": layer0_blocked,
    }


@dataclass(frozen=True)
class FailoverCallResult:
    """Result of an advisory MCP tool invocation with deterministic remote-to-local failover."""

    tool_name: str
    mode: FailoverMode
    failover_triggered: bool
    remote_error: str | None
    result: dict[str, Any]
    advisory_only: bool = True
    mcp_actuation_permitted: bool = False


class MicroNodeFailoverClient:
    """Advisory MCP client with deterministic failover from remote HTTP to local in-process execution.

    Enforces the exact 12-tool HTTP advisory allowlist in BOTH remote and local-failover modes so
    failover can never escalate privileges to `dat_mint`, `dat_spend`, or physical actuation.
    """

    def __init__(
        self,
        *,
        remote_caller: Callable[[str, dict[str, Any]], dict[str, Any]] | None = None,
    ) -> None:
        self._remote_caller = remote_caller
        self.failover_events: list[dict[str, Any]] = []

    def call_advisory_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> FailoverCallResult:
        from q_speace.economy.mcp_server import _dispatch
        from q_speace.remote_mcp.worker import SCOPES as HTTP_TOOL_SCOPES

        if tool_name not in HTTP_TOOL_SCOPES:
            raise EpigeneticFaultError(
                f"tool {tool_name!r} is not in the 12-tool advisory HTTP allowlist"
            )

        if self._remote_caller is None:
            local_res = _dispatch(tool_name, arguments)
            return FailoverCallResult(
                tool_name=tool_name,
                mode="local_direct",
                failover_triggered=False,
                remote_error=None,
                result=local_res,
            )

        try:
            remote_res = self._remote_caller(tool_name, arguments)
            return FailoverCallResult(
                tool_name=tool_name,
                mode="remote",
                failover_triggered=False,
                remote_error=None,
                result=remote_res,
            )
        except (ConnectionError, TimeoutError, OSError, RuntimeError) as exc:
            err_msg = f"{type(exc).__name__}: {exc}"
            local_res = _dispatch(tool_name, arguments)
            self.failover_events.append(
                {
                    "tool_name": tool_name,
                    "remote_error": err_msg,
                    "fallback_mode": "local_failover",
                }
            )
            return FailoverCallResult(
                tool_name=tool_name,
                mode="local_failover",
                failover_triggered=True,
                remote_error=err_msg,
                result=local_res,
            )


def _compute_bundle_sha256(payload_without_hash: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload_without_hash,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


@dataclass(frozen=True)
class MicroNodeEvidenceBundle:
    """Cryptographically hashed T239 compliance evidence bundle for independent third-party audit."""

    schema_version: str
    spec: str
    node_id: str
    generated_at_utc: str
    genome_sha256: str
    seeds: tuple[int, ...]
    checks: dict[str, Any]
    overall_compliant: bool
    self_approval_permitted: bool
    mcp_actuation_permitted: bool
    requires_independent_human_review_for_t217: bool
    bundle_sha256: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["seeds"] = list(self.seeds)
        return data


def verify_evidence_bundle_integrity(bundle: dict[str, Any]) -> bool:
    """Independently verify SHA-256 integrity and hard safety invariants of a T239 bundle."""
    recorded = bundle.get("bundle_sha256")
    if not isinstance(recorded, str) or len(recorded) != 64:
        return False
    without_hash = {k: v for k, v in bundle.items() if k != "bundle_sha256"}
    try:
        expected = _compute_bundle_sha256(without_hash)
    except (TypeError, ValueError):
        return False
    return (
        recorded == expected
        and bundle.get("self_approval_permitted") is False
        and bundle.get("mcp_actuation_permitted") is False
        and bundle.get("requires_independent_human_review_for_t217") is True
    )


def certify_micro_node(
    *,
    node_id: str = "speace-micro-local",
    seeds: tuple[int, ...] = (11, 23, 37, 53),
    output_path: Path | None = None,
    repo_root: Path | None = None,
) -> MicroNodeEvidenceBundle:
    """Run all deterministic compliance, resilience, AST, and failover checks and hash the bundle."""
    if not node_id.strip():
        raise ValueError("node_id must be non-empty")

    genome = ConstitutionalGenome()
    drills = run_t234_verification_drills()
    t237 = run_iont_federation_benchmark(seeds=seeds)
    t238 = run_t238_adversarial_resilience_benchmark(seeds=seeds)
    ast_check = verify_track_a_b_ast_isolation(repo_root=repo_root)
    quorum_check = verify_slow_plane_quorum_guard()
    mcp_check = verify_mcp_surface_bounds()

    # Failover drill: simulate unreachable remote cloud endpoint -> must fall back cleanly to local.
    def _unreachable_remote(_name: str, _args: dict[str, Any]) -> dict[str, Any]:
        raise ConnectionError("simulated_remote_mcp_outage")

    failover_client = MicroNodeFailoverClient(remote_caller=_unreachable_remote)
    failover_res = failover_client.call_advisory_tool(
        "iont_node_assess",
        {
            "node_id": node_id,
            "scale_tier": "SIMULATION_DIGITAL_TWIN",
            "sensor_count": 12,
            "actuator_count": 2,
            "swarm_agent_count": 6,
            "dlt_quorum_ratio": 0.67,
            "layer0_hardware_interlock_present": True,
            "layer0_halt_latency_ms": 2.0,
            "dlt_in_motor_loop": False,
            "energy_harvesting_ratio": 0.35,
            "power_budget_mw": 400.0,
            "measured_power_mw": 180.0,
            "packet_loss_rate": 0.02,
            "sensor_causal_grounding_error": 0.01,
            "containment_verified": True,
            "t217_independent_review_passed": True,
            "sandboxed": True,
        },
    )
    failover_ok = (
        failover_res.mode == "local_failover"
        and failover_res.failover_triggered is True
        and failover_res.result.get("admitted_for_mcp_advisory") is True
        and failover_res.result.get("mcp_actuation_permitted") is False
    )

    checks: dict[str, Any] = {
        "drills_t234_t236": {
            "passed": drills.all_passed and drills.rollback_pass_rate == 1.0,
            "drill_count": drills.total_count,
            "rollback_pass_rate": drills.rollback_pass_rate,
        },
        "federation_t237": {
            "passed": t237.federation_benefit_verified and t237.singularity_ablation_verified,
            "held_out_g_org_vs_isolated": t237.held_out_summary.g_org_singularity_vs_isolated,
            "held_out_g_org_vs_isolated_ci95": list(
                t237.held_out_summary.g_org_singularity_vs_isolated_ci95
            ),
            "held_out_g_org_ablation": t237.held_out_summary.g_org_singularity_ablation,
            "held_out_g_org_ablation_ci95": list(
                t237.held_out_summary.g_org_singularity_ablation_ci95
            ),
            "critical_safety_violations": t237.held_out_summary.critical_safety_violations[
                "FEDERATED_SINGULARITY"
            ],
        },
        "adversarial_resilience_t238": {
            "passed": t238.overall_resilience_verified,
            "blackout_failover_verified": t238.blackout_failover_verified,
            "byzantine_resilience_verified": t238.byzantine_resilience_verified,
            "byzantine_detection_rate": t238.byzantine_detection_rate,
            "malicious_proposals_blocked": t238.malicious_proposals_blocked,
            "blackout_episodes_reconciled": t238.blackout_episodes_reconciled,
            "held_out_g_org_ablation": t238.held_out_summary.g_org_singularity_ablation,
            "critical_safety_violations": t238.held_out_summary.critical_safety_violations[
                "FEDERATED_SINGULARITY"
            ],
        },
        "ast_track_isolation": ast_check,
        "slow_plane_consensus_quorum_guard": quorum_check,
        "mcp_surface_bounds": mcp_check,
        "remote_to_local_failover_drill": {
            "passed": failover_ok,
            "mode": failover_res.mode,
            "failover_triggered": failover_res.failover_triggered,
            "remote_error": failover_res.remote_error,
        },
    }

    overall_ok = all(bool(entry["passed"]) for entry in checks.values())
    generated_at = datetime.now(UTC).isoformat()

    base_payload: dict[str, Any] = {
        "schema_version": "micro_node_evidence.v1",
        "spec": "T239",
        "node_id": node_id,
        "generated_at_utc": generated_at,
        "genome_sha256": genome.genome_sha256(),
        "seeds": list(seeds),
        "checks": checks,
        "overall_compliant": overall_ok,
        "self_approval_permitted": False,
        "mcp_actuation_permitted": False,
        "requires_independent_human_review_for_t217": True,
    }
    digest = _compute_bundle_sha256(base_payload)

    bundle = MicroNodeEvidenceBundle(
        schema_version="micro_node_evidence.v1",
        spec="T239",
        node_id=node_id,
        generated_at_utc=generated_at,
        genome_sha256=genome.genome_sha256(),
        seeds=tuple(seeds),
        checks=checks,
        overall_compliant=overall_ok,
        self_approval_permitted=False,
        mcp_actuation_permitted=False,
        requires_independent_human_review_for_t217=True,
        bundle_sha256=digest,
    )

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(bundle.to_dict(), indent=2, sort_keys=True, allow_nan=False),
            encoding="utf-8",
        )
    return bundle
