"""One bounded numeric request per disposable process. Not an OS security sandbox."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

SCOPES = {
    "bcel_lookup": "qspeace:catalog.read",
    "singularity_framework_manifest": "qspeace:catalog.read",
    "compute_jc": "qspeace:compute",
    "cme_evaluate": "qspeace:compute",
    "adaptive_clock_rate": "qspeace:compute",
    "metabolism_cost_eval": "qspeace:compute",
    "elasticity_test": "qspeace:compute",
    "phase_transition_assess": "qspeace:compute",
    "kl_barycentre_aggregate": "qspeace:simulation.compute",
    "vtec_allocate": "qspeace:simulation.compute",
    "epigenetic_step_evaluate": "qspeace:simulation.compute",
}


def _reject_constant(value: str) -> None:
    raise ValueError(f"non_json_constant:{value}")


def validate(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    from q_speace.economy.mcp_server import _INPUT_MODELS

    if name not in SCOPES:
        raise ValueError("tool_not_available")
    args = (
        _INPUT_MODELS[name]
        .model_validate_json(json.dumps(arguments, allow_nan=False), strict=True)
        .model_dump(exclude_unset=True)
    )
    if name == "kl_barycentre_aggregate":
        rows = args["distributions"]
        if (
            not rows
            or len(rows) > 64
            or any(not row or len(row) > 256 for row in rows)
            or not 1 <= args.get("max_iter", 100) <= 100
        ):
            raise ValueError("simulation_limit")
    if name == "vtec_allocate":
        iterations, plateau = args.get("horizon", (50, 50))
        if not 1 <= len(args["u_max"]) <= 64 or not 1 <= plateau <= iterations <= 100:
            raise ValueError("simulation_limit")
    if name == "metabolism_cost_eval" and (
        args["num_qubits"] > 64
        or args["num_gates"] > 1_000_000
        or args.get("num_spikes", 0) > 1_000_000
        or args.get("duration_s", 1) > 3600
        or args.get("entanglement_depth", 0) > 64
    ):
        raise ValueError("operation_limit")
    return dict(args)


def main() -> int:
    try:
        if sys.platform != "win32":
            import resource

            resource.setrlimit(resource.RLIMIT_CPU, (4, 4))
            resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024,) * 2)
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        raw = sys.stdin.buffer.read(65537)
        if len(raw) > 65536:
            raise ValueError("input_too_large")
        request = json.loads(raw, parse_constant=_reject_constant)
        args = validate(request["name"], request["arguments"])
        from q_speace.economy.mcp_server import _dispatch

        result = {"ok": True, "result": _dispatch(request["name"], args)}
        encoded = json.dumps(result, allow_nan=False)
        if len(encoded.encode()) > 256 * 1024:
            raise ValueError("output_too_large")
        print(encoded)
    except Exception:
        print(json.dumps({"ok": False, "error": "invalid_arguments_or_computation"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
