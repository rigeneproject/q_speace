"""MCP server wrapper for the q_speace_economy primitives (T6.11).

Exposes the 6 core primitives as Model Context Protocol (MCP) tools:

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

The stdio mode reads newline-delimited JSON-RPC 2.0 messages from
stdin and writes responses to stdout. The schema is intentionally
minimal — we implement the JSON-RPC ``method`` / ``params`` / ``result``
fields only, not the full MCP framing.

BCEL: the MCP server is *functional*: each tool is a deterministic
function on the SPEACE primitives. None of the tools is a "decision"
of any conscious entity — the gate decisions (VTEC constraints,
elasticity ACCEPT/REJECT) are mechanical.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

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
)


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


def list_tools() -> list[dict[str, str]]:
    """Return the list of registered tools (for MCP discovery)."""
    return [{"name": s.name, "description": s.description} for s in TOOL_REGISTRY]


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------


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
        assert j["confidence"] == 1.0
    except Exception as e:
        failures.append(f"compute_jc: {e}")
    try:
        bary = _handle_kl_barycentre(
            {
                "distributions": [[0.7, 0.2, 0.1], [0.1, 0.2, 0.7]],
            }
        )
        assert abs(sum(bary["barycentre"]) - 1.0) < 1e-6
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
        assert v["feasible"]
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
        assert len(cme["cme"]) == 12
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
        assert m["token_id"] == "self-test"
        s = _handle_dat_spend(
            {
                "token_id": "self-test",
                "amount": 10.0,
                "target": "exergy",
                "t": 0.0,
            }
        )
        assert s["remaining_amount"] == 90.0
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
        assert e_test["decision"] == "ACCEPT"
    except Exception as e:
        failures.append(f"elasticity_test: {e}")
    if failures:
        for f in failures:
            print(f"  FAIL: {f}")
        return 1
    print("[mcp_server] all 7 tools green")
    return 0


# ---------------------------------------------------------------------------
# stdio entry point
# ---------------------------------------------------------------------------


def _stdio_loop() -> int:
    """Read newline-delimited JSON-RPC 2.0 from stdin, write to stdout."""
    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError as e:
            sys.stdout.write(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32700, "message": f"parse error: {e}"},
                    }
                )
                + "\n"
            )
            sys.stdout.flush()
            continue
        rpc_id = msg.get("id")
        method = msg.get("method")
        params = msg.get("params") or {}
        try:
            if method == "tools/list":
                result: Any = {"tools": list_tools()}
            elif method == "tools/call":
                # MCP framing: params = {"name": ..., "arguments": ...}
                inner_name = params["name"]
                inner_args = params.get("arguments") or {}
                result = _dispatch(inner_name, inner_args)
            else:
                result = _dispatch(method, params)
            sys.stdout.write(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": rpc_id,
                        "result": result,
                    }
                )
                + "\n"
            )
        except Exception as e:
            sys.stdout.write(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": rpc_id,
                        "error": {"code": -32603, "message": f"{type(e).__name__}: {e}"},
                    }
                )
                + "\n"
            )
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
