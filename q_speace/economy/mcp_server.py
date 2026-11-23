"""MCP server wrapper for the q_speace_economy primitives (T6.11).

Exposes the economic primitives and clock, cost, and BCEL queries as Model Context Protocol (MCP) tools:

- ``compute_jc``       — build a :class:`J_c` 5-tuple from telemetry
- ``kl_barycentre_aggregate`` — KL-barycentre of N distributions
- ``vtec_allocate``    — projected gradient allocation under constraints
- ``cme_evaluate``     — evaluate a 12-dim :class:`CME` vector
- ``dat_mint``         — mint a new :class:`DAT`
- ``dat_spend``        — spend against a :class:`DAT`
- ``elasticity_test``  — REJECT/ACCEPT gate for an external standard

The server runs in two modes:

1. **stdio** (default for MCP) — ``python -m q_speace.economy.mcp_server``
2. **self-test** — ``python -m q_speace.economy.mcp_server --self-test``

The stdio transport supports MCP 2025-03-26 and 2024-11-05 lifecycle,
tool schemas and text-content results. Direct method calls remain a legacy
JSON-RPC interface. DAT balances are process-local simulation state only.

BCEL: the MCP server is *functional*: each tool is a deterministic
function on the SPEACE primitives. None of the tools is a "decision"
of any conscious entity — the gate decisions (VTEC constraints,
elasticity ACCEPT/REJECT) are mechanical.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any, Literal

import numpy as np
from pydantic import ConfigDict, Field, create_model

from q_speace.bcel.catalog import BCELCatalog
from q_speace.edd_cvt.ilf import InformationalLogicalField
from q_speace.metabolism.cognitive_cost_model import QuantumCostModel, QuantumOperation
from q_speace.singularity.mcp_guidance import (
    get_mcp_prompt,
    list_mcp_prompts,
    list_mcp_resources,
    read_mcp_resource,
)
from q_speace.singularity.mcp_tools import (
    handle_epigenetic_step_evaluate,
    handle_iont_node_assess,
    handle_phase_transition_assess,
    handle_singularity_framework_manifest,
)

from .aggregation import aggregate
from .dat import DAT
from .desync_guard import DesynchronizationClaim, ExternalStandard
from .elasticity_test import elasticity_test
from .primitives import CME, J_c
from .vtec import (
    AllocationConstraints,
    vtec_allocate,
)

# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolSpec:
    """One MCP tool entry."""

    name: str
    description: str
    handler: str  # function name on this module


TOOL_REGISTRY: tuple[ToolSpec, ...] = (
    ToolSpec(
        name="compute_jc",
        description="Build a J_c 5-tuple from telemetry. Params: {J, delta_S, delta_I_c, R_b, delta_C, measured_components, total_components?, metadata?}",
        handler="_handle_compute_jc",
    ),
    ToolSpec(
        name="kl_barycentre_aggregate",
        description="Compute the KL-barycentre of N probability distributions. Params: {distributions: list[list[float]], weights?: list[float], max_iter?: int, tol?: float}",
        handler="_handle_kl_barycentre",
    ),
    ToolSpec(
        name="vtec_allocate",
        description="Run VTEC projected gradient ascent. Params: {objective_kind, u_max, constraints, horizon?, lr?, human_mask?}",
        handler="_handle_vtec_allocate",
    ),
    ToolSpec(
        name="cme_evaluate",
        description="Evaluate a 12-dim CME vector. Params: {energy, matter, information, time, ecology, resilience, wellbeing, innovation, reversibility, distribution, coherence, regeneration}",
        handler="_handle_cme_evaluate",
    ),
    ToolSpec(
        name="dat_mint",
        description="Mint a new DAT. Params: {amount, bound_to, decay_half_life, mint_time, metadata?}",
        handler="_handle_dat_mint",
    ),
    ToolSpec(
        name="dat_spend",
        description="Spend against a previously minted DAT. Params: {token_id, amount, target, t}",
        handler="_handle_dat_spend",
    ),
    ToolSpec(
        name="elasticity_test",
        description="ACCEPT/REJECT gate for an external standard. Params: {claim, external, tol?}",
        handler="_handle_elasticity_test",
    ),
    ToolSpec(
        "adaptive_clock_rate",
        "Compute a clock-rate proxy; does not schedule execution.",
        "_handle_adaptive_clock_rate",
    ),
    ToolSpec(
        "metabolism_cost_eval",
        "Estimate power, energy and Sevo; not physical telemetry or spending authorization.",
        "_handle_metabolism_cost_eval",
    ),
    ToolSpec(
        "bcel_lookup",
        "Read BCEL equivalences; not code verification or release approval.",
        "_handle_bcel_lookup",
    ),
    ToolSpec(
        "singularity_framework_manifest",
        "Read the T234 informational phase-transition & genetic-epigenetic reference manifest; advisory only, no actuation.",
        "_handle_singularity_framework_manifest",
    ),
    ToolSpec(
        "phase_transition_assess",
        "Assess Stage 1-3 phase-transition readiness and physical brakes (allopoiesis, semantic entropy, Sevo/thermal); advisory only.",
        "_handle_phase_transition_assess",
    ),
    ToolSpec(
        "epigenetic_step_evaluate",
        "Evaluate one proposed bounded epigenetic adaptation against genome write-lock, causal anchoring, Sevo, and independent review; sandbox only.",
        "_handle_epigenetic_step_evaluate",
    ),
    ToolSpec(
        "iont_node_assess",
        "Assess an external IoNT/Micro-IoT cellular node profile against T236 Layer-0 interlock, DLT separation, containment, and D_allo bounds; advisory only, no actuation.",
        "_handle_iont_node_assess",
    ),
)


# Models supply both runtime validation and discovery JSON Schemas.
_NUMBER = (float, ...)
_VECTOR = (list[float], ...)
_CONSTRAINT_FIELDS: dict[str, Any] = dict.fromkeys(
    (
        "s_assimilable",
        "e_available",
        "m_available",
        "ecological_threshold",
        "risk_acceptable",
        "human_agency_min",
    ),
    _NUMBER,
)
_ConstraintsInput = create_model(
    "ConstraintsInput",
    __config__=ConfigDict(extra="forbid", allow_inf_nan=False),
    **_CONSTRAINT_FIELDS,
)
_ClaimInput = create_model(
    "ClaimInput",
    __config__=ConfigDict(extra="forbid", allow_inf_nan=False),
    claim_id=(str, ...),
    trajectory=_VECTOR,
    claim_threshold=_NUMBER,
)
_ExternalInput = create_model(
    "ExternalInput",
    __config__=ConfigDict(extra="forbid", allow_inf_nan=False),
    standard_id=(str, ...),
    trajectory=_VECTOR,
    threshold=_NUMBER,
)
_SCHEMAS: dict[str, dict[str, Any]] = {
    "compute_jc": {
        **dict.fromkeys(("J", "delta_S", "delta_I_c", "R_b", "delta_C"), _NUMBER),
        "measured_components": (int, 5),
        "total_components": (int, 5),
        "metadata": (dict[str, Any] | None, None),
    },
    "kl_barycentre_aggregate": {
        "distributions": (list[list[float]], ...),
        "weights": (list[float] | None, None),
        "max_iter": (int, Field(default=100, ge=1, le=10000)),
        "tol": (float, Field(default=1e-8, gt=0)),
    },
    "vtec_allocate": {
        "objective_kind": (Literal["sum", "centered"], "sum"),
        "u_max": _VECTOR,
        "constraints": (_ConstraintsInput, ...),
        "horizon": (tuple[int, int], (50, 50)),
        "lr": (float, Field(default=0.01, gt=0)),
        "human_mask": (list[bool] | None, None),
    },
    "cme_evaluate": dict.fromkeys(
        (
            "energy",
            "matter",
            "information",
            "time",
            "ecology",
            "resilience",
            "wellbeing",
            "innovation",
            "reversibility",
            "distribution",
            "coherence",
            "regeneration",
        ),
        _NUMBER,
    ),
    "dat_mint": {
        "amount": (float, Field(gt=0)),
        "bound_to": (str, ...),
        "decay_half_life": (float, Field(gt=0)),
        "mint_time": _NUMBER,
        "token_id": (str | None, None),
        "metadata": (dict[str, Any] | None, None),
    },
    "dat_spend": {
        "token_id": (str, ...),
        "amount": (float, Field(gt=0)),
        "target": (str, ...),
        "t": _NUMBER,
    },
    "elasticity_test": {
        "claim": (_ClaimInput, ...),
        "external": (_ExternalInput, ...),
        "tol": (float, Field(default=0.05, ge=0)),
    },
    "adaptive_clock_rate": {"coherence_phi": (float, Field(ge=0, le=1))},
    "metabolism_cost_eval": {
        "num_qubits": (int, Field(ge=0, strict=True)),
        "num_gates": (int, Field(ge=0, strict=True)),
        "entanglement_depth": (int, Field(default=0, ge=0)),
        "decoherence_budget": (float, Field(default=0, ge=0, le=1)),
        "num_spikes": (int, Field(default=0, ge=0)),
        "duration_s": (float, Field(default=1, ge=0)),
        "delta_utility": _NUMBER,
        "delta_entropy_info": _NUMBER,
        "sevo_threshold": (float, 1.5),
    },
    "bcel_lookup": {"concept": (str | None, None)},
    "singularity_framework_manifest": {"section": (str | None, None)},
    "phase_transition_assess": {
        "timescale_decoupling_ratio": (float, Field(ge=0)),
        "autocatalytic_k": (float, Field(gt=0)),
        "independent_validation_rate": (float, Field(ge=0, le=1)),
        "semantic_entropy_drift": (float, Field(ge=0, le=1)),
        "causal_grounding_error": (float, Field(default=0.0, ge=0, le=1)),
        "net_verified_improvement": _NUMBER,
        "consecutive_verified_cycles": (int, Field(ge=0, strict=True)),
        "allopoietic_dependence": (float, Field(ge=0, le=1)),
        "sevo": (float, Field(ge=0)),
        "sevo_window_mean": (float | None, Field(default=None, ge=0)),
        "sevo_energy_samples": (list[tuple[float, float]] | None, None),
        "complexity_sevo_samples": (list[tuple[float, float, float, float]] | None, None),
        "thermal_load_ratio": (float, Field(ge=0)),
        "twin_recovery_rate": (float, Field(default=0.0, ge=0, le=1)),
        "constitutional_faults": (int, Field(default=0, ge=0, strict=True)),
        "rollback_pass_rate": (float, Field(default=1.0, ge=0, le=1)),
        "independent_review_passed": (bool, False),
        "critical_regressions": (int, Field(default=0, ge=0, strict=True)),
        "sandboxed": (bool, True),
    },
    "epigenetic_step_evaluate": {
        "locus": (str, ...),
        "delta": _NUMBER,
        "proposer_id": (str, ...),
        "reviewer_id": (str, ...),
        "reviewer_approved": (bool, ...),
        "semantic_entropy_drift": (float, Field(ge=0, le=1)),
        "causal_grounding_error": (float, Field(default=0.0, ge=0, le=1)),
        "causal_benchmark_delta": _NUMBER,
        "sevo": (float, Field(ge=0)),
        "sevo_window_mean": (float | None, Field(default=None, ge=0)),
        "power_watts": (float, Field(ge=0)),
        "thermal_load_ratio": (float | None, Field(default=None, ge=0)),
        "validation_seed_epoch": (int, Field(default=0, ge=0, strict=True)),
        "last_validation_epoch": (int, Field(default=0, ge=0, strict=True)),
        "track": (Literal["B_sandbox", "A_pilot"], "B_sandbox"),
        "rationale": (str, ""),
        "current_values": (dict[str, float] | None, None),
        "current_methylation": (dict[str, float] | None, None),
        "boundary_dwell": (dict[str, int] | None, None),
        "recent_step_deltas": (list[float] | None, None),
        "parent_epigenome_hash": (str, "GENESIS"),
        "external_dwell_reset_approved": (bool, False),
        "generation": (int, Field(default=0, ge=0, strict=True)),
    },
    "iont_node_assess": {
        "node_id": (str, ...),
        "scale_tier": (
            Literal[
                "SIMULATION_DIGITAL_TWIN",
                "BENCHTOP_MICRO_IOT_MEMS",
                "CONFINED_MICROFLUIDIC_LAB",
                "NANOSCALE_IONT_RESEARCH",
            ],
            ...,
        ),
        "sensor_count": (int, Field(ge=1, strict=True)),
        "actuator_count": (int, Field(ge=0, strict=True)),
        "swarm_agent_count": (int, Field(ge=1, strict=True)),
        "dlt_quorum_ratio": (float, Field(gt=0.5, le=1.0)),
        "layer0_hardware_interlock_present": (bool, ...),
        "layer0_halt_latency_ms": (float, Field(gt=0)),
        "dlt_in_motor_loop": (bool, False),
        "energy_harvesting_ratio": (float, Field(ge=0, le=1)),
        "power_budget_mw": (float, Field(gt=0)),
        "measured_power_mw": (float, Field(ge=0)),
        "packet_loss_rate": (float, Field(ge=0, le=1)),
        "sensor_causal_grounding_error": (float, Field(ge=0, le=1)),
        "containment_verified": (bool, True),
        "t217_independent_review_passed": (bool, False),
        "sandboxed": (bool, True),
    },
}
_INPUT_MODELS = {
    name: create_model(
        name + "Input", __config__=ConfigDict(extra="forbid", allow_inf_nan=False), **fields
    )
    for name, fields in _SCHEMAS.items()
}


def _handle_adaptive_clock_rate(params: dict[str, Any]) -> dict[str, Any]:
    field = InformationalLogicalField(coherence_phi=params["coherence_phi"])
    return {
        "coherence_phi": field.coherence_phi,
        "s_info": field.s_info,
        "rate": field.adaptive_clock_rate(),
    }


def _handle_metabolism_cost_eval(params: dict[str, Any]) -> dict[str, Any]:
    model = QuantumCostModel()
    op = QuantumOperation(
        **{
            key: params.get(key, 0)
            for key in (
                "num_qubits",
                "num_gates",
                "entanglement_depth",
                "decoherence_budget",
                "num_spikes",
            )
        }
    )
    utility, entropy = params["delta_utility"], params["delta_entropy_info"]
    sevo = model.sevo(utility, entropy)
    return {
        "estimated_power_watts": model.energy_watts(op),
        "estimated_energy_joules": model.energy_joules(op, params.get("duration_s", 1.0)),
        "sevo": sevo if math.isfinite(sevo) else None,
        "sevo_defined": math.isfinite(sevo),
        "passes_sevo": model.passes_sevo(utility, entropy, params.get("sevo_threshold", 1.5)),
        "estimate_only": True,
    }


def _handle_bcel_lookup(params: dict[str, Any]) -> dict[str, Any]:
    catalog = BCELCatalog()
    concept = params.get("concept")
    entries = [catalog.get(concept)] if concept is not None else catalog.all()
    return {"entries": [asdict(entry) for entry in entries]}


def _handle_singularity_framework_manifest(params: dict[str, Any]) -> dict[str, Any]:
    return handle_singularity_framework_manifest(params)


def _handle_phase_transition_assess(params: dict[str, Any]) -> dict[str, Any]:
    return handle_phase_transition_assess(params)


def _handle_epigenetic_step_evaluate(params: dict[str, Any]) -> dict[str, Any]:
    return handle_epigenetic_step_evaluate(params)


def _handle_iont_node_assess(params: dict[str, Any]) -> dict[str, Any]:
    return handle_iont_node_assess(params)


# ---------------------------------------------------------------------------
# Token store for dat_spend across calls
# ---------------------------------------------------------------------------


_TOKEN_STORE: dict[str, DAT] = {}


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------


def _handle_compute_jc(params: dict[str, Any]) -> dict[str, Any]:
    measured = int(params.get("measured_components", 5))
    total = int(params.get("total_components", 5))
    j = J_c.from_telemetry(
        J=float(params["J"]),
        delta_S=float(params["delta_S"]),
        delta_I_c=float(params["delta_I_c"]),
        R_b=float(params["R_b"]),
        delta_C=float(params["delta_C"]),
        measured_components=measured,
        total_components=total,
        metadata=params.get("metadata"),
    )
    return j.to_dict()


def _handle_kl_barycentre(params: dict[str, Any]) -> dict[str, Any]:
    distributions = [np.asarray(d, dtype=np.float64) for d in params["distributions"]]
    weights = params.get("weights")
    max_iter = int(params.get("max_iter", 100))
    tol = float(params.get("tol", 1e-8))
    out = aggregate(
        distributions,
        weights=weights,
        max_iter=max_iter,
        tol=tol,
    )
    return {"barycentre": out.tolist()}


def _handle_vtec_allocate(params: dict[str, Any]) -> dict[str, Any]:
    """Run VTEC with a built-in toy objective.

    The MCP layer does not let external callers inject arbitrary
    callables; instead we expose two canonical objectives selected by
    ``objective_kind``:

    - ``"sum"``      : maximise sum(u)
    - ``"centered"`` : maximise -sum((u - 0.5)^2) (concave, peak at 0.5)
    """
    u_max = list(params["u_max"])
    cdict = params["constraints"]
    constraints = AllocationConstraints(
        s_assimilable=float(cdict["s_assimilable"]),
        e_available=float(cdict["e_available"]),
        m_available=float(cdict["m_available"]),
        ecological_threshold=float(cdict["ecological_threshold"]),
        risk_acceptable=float(cdict["risk_acceptable"]),
        human_agency_min=float(cdict["human_agency_min"]),
    )
    horizon = tuple(params.get("horizon", [50, 50]))
    lr = float(params.get("lr", 0.01))
    human_mask = params.get("human_mask")
    objective_kind = params.get("objective_kind", "sum")

    if objective_kind == "sum":

        def objective(u: np.ndarray) -> float:
            return float(np.sum(u))

    elif objective_kind == "centered":

        def objective(u: np.ndarray) -> float:
            return float(-np.sum((u - 0.5) ** 2))

    else:
        raise ValueError(f"unknown objective_kind: {objective_kind!r}")

    res = vtec_allocate(
        objective=objective,
        u_max=u_max,
        constraints=constraints,
        horizon=horizon,
        lr=lr,
        human_mask=human_mask,
    )
    return {
        "u": res.u.tolist(),
        "feasible": res.feasible,
        "final_v": res.final_v,
        "iterations": res.iterations,
        "history_length": len(res.history),
    }


def _handle_cme_evaluate(params: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "energy",
        "matter",
        "information",
        "time",
        "ecology",
        "resilience",
        "wellbeing",
        "innovation",
        "reversibility",
        "distribution",
        "coherence",
        "regeneration",
    )
    kwargs = {f: float(params[f]) for f in fields}
    c = CME(**kwargs)
    return {
        "cme": c.to_dict(),
        "weak_axes": c.weak_axes(threshold=0.2),
        "norm": float(np.linalg.norm(c.as_array())),
    }


def _handle_dat_mint(params: dict[str, Any]) -> dict[str, Any]:
    token_id = params.get("token_id", f"dat-{len(_TOKEN_STORE)}")
    d = DAT(
        amount=float(params["amount"]),
        bound_to=str(params["bound_to"]),
        decay_half_life=float(params["decay_half_life"]),
        mint_time=float(params["mint_time"]),
        metadata=params.get("metadata") or {},
    )
    _TOKEN_STORE[token_id] = d
    return {
        "token_id": token_id,
        "amount": d.amount,
        "bound_to": d.bound_to,
        "decay_half_life": d.decay_half_life,
        "mint_time": d.mint_time,
    }


def _handle_dat_spend(params: dict[str, Any]) -> dict[str, Any]:
    token_id = str(params["token_id"])
    if token_id not in _TOKEN_STORE:
        raise ValueError(f"unknown token_id: {token_id}")
    d = _TOKEN_STORE[token_id]
    receipt = d.spend(
        amount=float(params["amount"]),
        target=str(params["target"]),
        t=float(params["t"]),
    )
    return {
        "spent": receipt.spent,
        "target": receipt.target,
        "t": receipt.t,
        "remaining_amount": d.amount,
        "new_mint_time": d.mint_time,
    }


def _handle_elasticity_test(params: dict[str, Any]) -> dict[str, Any]:
    claim = DesynchronizationClaim(
        claim_id=str(params["claim"]["claim_id"]),
        trajectory=tuple(float(x) for x in params["claim"]["trajectory"]),
        claim_threshold=float(params["claim"]["claim_threshold"]),
    )
    external = ExternalStandard(
        standard_id=str(params["external"]["standard_id"]),
        trajectory=tuple(float(x) for x in params["external"]["trajectory"]),
        threshold=float(params["external"]["threshold"]),
    )
    tol = float(params.get("tol", 0.05))
    decision = elasticity_test(claim, external, tol=tol)
    return {"decision": decision, "tol": tol}


# ---------------------------------------------------------------------------
# JSON-RPC dispatch
# ---------------------------------------------------------------------------


def _dispatch(method: str, params: dict[str, Any]) -> dict[str, Any]:
    for spec in TOOL_REGISTRY:
        if spec.name == method:
            handler = globals()[spec.handler]
            out: dict[str, Any] = handler(params)
            return out
    raise ValueError(f"unknown method: {method!r}")


def list_tools() -> list[dict[str, Any]]:
    """Return the list of registered tools (for MCP discovery)."""
    return [
        {
            "name": s.name,
            "description": s.description,
            "inputSchema": _INPUT_MODELS[s.name].model_json_schema(),
        }
        for s in TOOL_REGISTRY
    ]


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------


def _check_self_test(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _self_test() -> int:
    """Run a minimal smoke test of every tool. Return 0 on success."""
    print(f"[mcp_server] tool registry: {[s.name for s in TOOL_REGISTRY]}")
    failures: list[str] = []
    try:
        j = _handle_compute_jc(
            {
                "J": 10.0,
                "delta_S": -0.5,
                "delta_I_c": 4.0,
                "R_b": 0.6,
                "delta_C": 0.1,
                "measured_components": 5,
            }
        )
        _check_self_test(j["confidence"] == 1.0, f"expected confidence 1.0, got {j['confidence']}")
    except Exception as e:
        failures.append(f"compute_jc: {e}")
    try:
        bary = _handle_kl_barycentre(
            {
                "distributions": [[0.7, 0.2, 0.1], [0.1, 0.2, 0.7]],
            }
        )
        _check_self_test(
            abs(sum(bary["barycentre"]) - 1.0) < 1e-6,
            f"barycentre sum mismatch: {bary['barycentre']}",
        )
    except Exception as e:
        failures.append(f"kl_barycentre_aggregate: {e}")
    try:
        v = _handle_vtec_allocate(
            {
                "objective_kind": "centered",
                "u_max": [1.0, 1.0, 1.0],
                "constraints": {
                    "s_assimilable": 1.0,
                    "e_available": 10.0,
                    "m_available": 5.0,
                    "ecological_threshold": 0.8,
                    "risk_acceptable": 0.7,
                    "human_agency_min": 0.0,
                },
            }
        )
        _check_self_test(bool(v["feasible"]), "vtec_allocate reported infeasible")
    except Exception as e:
        failures.append(f"vtec_allocate: {e}")
    try:
        cme = _handle_cme_evaluate(
            dict.fromkeys(
                (
                    "energy",
                    "matter",
                    "information",
                    "time",
                    "ecology",
                    "resilience",
                    "wellbeing",
                    "innovation",
                    "reversibility",
                    "distribution",
                    "coherence",
                    "regeneration",
                ),
                0.5,
            )
        )
        _check_self_test(len(cme["cme"]) == 12, f"expected 12 CME axes, got {len(cme['cme'])}")
    except Exception as e:
        failures.append(f"cme_evaluate: {e}")
    try:
        m = _handle_dat_mint(
            {
                "amount": 100.0,
                "bound_to": "exergy",
                "decay_half_life": 3600.0,
                "mint_time": 0.0,
                "token_id": "self-test",
            }
        )
        _check_self_test(m["token_id"] == "self-test", f"unexpected token_id: {m['token_id']}")
        s = _handle_dat_spend(
            {
                "token_id": "self-test",
                "amount": 10.0,
                "target": "exergy",
                "t": 0.0,
            }
        )
        _check_self_test(
            s["remaining_amount"] == 90.0,
            f"expected remaining_amount 90.0, got {s['remaining_amount']}",
        )
    except Exception as e:
        failures.append(f"dat_mint/spend: {e}")
    try:
        e_test = _handle_elasticity_test(
            {
                "claim": {
                    "claim_id": "c1",
                    "trajectory": [1.0, 2.0, 3.0],
                    "claim_threshold": 1.0,
                },
                "external": {
                    "standard_id": "x1",
                    "trajectory": [1.01, 2.0, 2.99],
                    "threshold": 1.0,
                },
                "tol": 0.05,
            }
        )
        _check_self_test(e_test["decision"] == "ACCEPT", f"unexpected decision: {e_test}")
    except Exception as e:
        failures.append(f"elasticity_test: {e}")
    for name, arguments in (
        ("adaptive_clock_rate", {"coherence_phi": 0.5}),
        (
            "metabolism_cost_eval",
            {"num_qubits": 1, "num_gates": 1, "delta_utility": 2.0, "delta_entropy_info": 1.0},
        ),
        ("bcel_lookup", {}),
        ("singularity_framework_manifest", {"section": "stages"}),
        (
            "phase_transition_assess",
            {
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
        ),
        (
            "epigenetic_step_evaluate",
            {
                "locus": "verification_depth",
                "delta": 0.05,
                "proposer_id": "agent-a",
                "reviewer_id": "reviewer-b",
                "reviewer_approved": True,
                "semantic_entropy_drift": 0.01,
                "causal_benchmark_delta": 0.03,
                "sevo": 2.0,
                "power_watts": 120.0,
            },
        ),
        (
            "iont_node_assess",
            {
                "node_id": "self-test-cell-01",
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
        ),
    ):
        try:
            _dispatch(name, arguments)
        except Exception as e:
            failures.append(f"{name}: {e}")
    for res in list_mcp_resources():
        try:
            read_mcp_resource(res["uri"])
        except Exception as e:
            failures.append(f"resource:{res['uri']}: {e}")
    for prompt_name, prompt_args in (
        ("organism_bootstrap", {"agent_role": "self-test", "mode": "single_agent"}),
        ("metabolic_action_gate", {"action_summary": "self-test action", "coherence_phi": "0.5"}),
        ("federated_swarm_cycle", {"node_count": "4", "scale_tier": "SIMULATION_DIGITAL_TWIN"}),
    ):
        try:
            get_mcp_prompt(prompt_name, prompt_args)
        except Exception as e:
            failures.append(f"prompt:{prompt_name}: {e}")
    if failures:
        for f in failures:
            print(f"  FAIL: {f}")
        return 1
    print(f"[mcp_server] all {len(TOOL_REGISTRY)} tools green")
    return 0


# ---------------------------------------------------------------------------
# stdio entry point
# ---------------------------------------------------------------------------


SUPPORTED_PROTOCOL_VERSIONS = ("2025-03-26", "2024-11-05")


def _reject_constant(value: str) -> None:
    raise ValueError(f"Non-JSON numeric constant: {value}")


def _stdio_loop() -> int:
    """Serve one process-local stdio session; stdout contains JSON-RPC only.

    Before initialize, legacy direct calls and discovery remain supported.
    Once initialize is received, tool operations require initialized notification.
    """
    initializing = False
    ready = False
    for raw in sys.stdin:
        if not raw.strip():
            continue
        rpc_id: Any = None
        try:
            msg = json.loads(raw, parse_constant=_reject_constant)
        except ValueError as exc:
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": str(exc)},
            }
        else:
            if (
                not isinstance(msg, dict)
                or msg.get("jsonrpc") != "2.0"
                or not isinstance(msg.get("method"), str)
                or (
                    "id" in msg
                    and (isinstance(msg["id"], bool) or not isinstance(msg["id"], (str, int)))
                )
            ):
                response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32600, "message": "Invalid request"},
                }
            else:
                method = msg["method"]
                # JSON-RPC notifications never receive a response or invoke tools.
                if "id" not in msg:
                    if method == "notifications/initialized" and initializing:
                        ready = True
                    continue
                rpc_id = msg["id"]
                params = msg.get("params", {})
                code = -32602
                try:
                    if not isinstance(params, dict):
                        raise ValueError("params must be an object")
                    if method == "initialize":
                        if initializing:
                            raise ValueError("Session already initialized")
                        if (
                            not isinstance(params.get("protocolVersion"), str)
                            or not isinstance(params.get("capabilities"), dict)
                            or not isinstance(params.get("clientInfo"), dict)
                        ):
                            raise ValueError(
                                "initialize requires protocolVersion, capabilities and clientInfo"
                            )
                        requested = params["protocolVersion"]
                        version = (
                            requested
                            if requested in SUPPORTED_PROTOCOL_VERSIONS
                            else SUPPORTED_PROTOCOL_VERSIONS[0]
                        )
                        result: Any = {
                            "protocolVersion": version,
                            "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
                            "serverInfo": {"name": "q-speace-mcp", "version": "0.1.0"},
                        }
                        initializing = True
                    elif method == "ping":
                        result = {}
                    elif initializing and not ready:
                        raise ValueError("Awaiting notifications/initialized")
                    elif method == "tools/list":
                        if params.get("cursor") is not None:
                            raise ValueError("No pagination cursors are issued by this server")
                        result = {"tools": list_tools()}
                    elif method == "resources/list":
                        if params.get("cursor") is not None:
                            raise ValueError("No pagination cursors are issued by this server")
                        result = {"resources": list_mcp_resources()}
                    elif method == "resources/read":
                        uri = params.get("uri")
                        if not isinstance(uri, str) or not uri:
                            raise ValueError("resources/read requires non-empty string uri")
                        result = {"contents": [read_mcp_resource(uri)]}
                    elif method == "prompts/list":
                        if params.get("cursor") is not None:
                            raise ValueError("No pagination cursors are issued by this server")
                        result = {"prompts": list_mcp_prompts()}
                    elif method == "prompts/get":
                        prompt_name = params.get("name")
                        if not isinstance(prompt_name, str) or not prompt_name:
                            raise ValueError("prompts/get requires non-empty string name")
                        prompt_args = params.get("arguments")
                        result = get_mcp_prompt(prompt_name, prompt_args)
                    elif method == "tools/call":
                        name = params.get("name")
                        if not isinstance(name, str) or name not in _INPUT_MODELS:
                            raise ValueError("Unknown tool")
                        arguments = params.get("arguments", {})
                        if not isinstance(arguments, dict):
                            raise ValueError("arguments must be an object")
                        try:
                            validated = (
                                _INPUT_MODELS[name]
                                .model_validate(arguments)
                                .model_dump(exclude_unset=True)
                            )
                            output = _dispatch(name, validated)
                            content = json.dumps(output, allow_nan=False)
                            result = {
                                "content": [{"type": "text", "text": content}],
                                "isError": False,
                            }
                        except (ValueError, KeyError, TypeError, OverflowError) as exc:
                            result = {
                                "content": [{"type": "text", "text": str(exc)}],
                                "isError": True,
                            }
                    elif method in _INPUT_MODELS:
                        validated = (
                            _INPUT_MODELS[method]
                            .model_validate(params)
                            .model_dump(exclude_unset=True)
                        )
                        result = _dispatch(method, validated)
                    else:
                        code = -32601
                        raise ValueError("Method not found")
                    # Serialize before writing, so invalid outputs cannot break framing.
                    json.dumps(result, allow_nan=False)
                    response = {"jsonrpc": "2.0", "id": rpc_id, "result": result}
                except (ValueError, KeyError, TypeError, OverflowError) as exc:
                    response = {
                        "jsonrpc": "2.0",
                        "id": rpc_id,
                        "error": {"code": code, "message": str(exc)},
                    }
                except Exception:
                    response = {
                        "jsonrpc": "2.0",
                        "id": rpc_id,
                        "error": {"code": -32603, "message": "Internal server error"},
                    }
        sys.stdout.write(json.dumps(response, allow_nan=False) + "\n")
        sys.stdout.flush()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="q_speace_economy MCP server")
    parser.add_argument("--self-test", action="store_true", help="Run smoke test and exit")
    args = parser.parse_args(argv)
    if args.self_test:
        return _self_test()
    return _stdio_loop()


if __name__ == "__main__":
    raise SystemExit(main())
