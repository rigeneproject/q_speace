"""T265 — Transfer under a new sensor vocabulary (evaluation only, sandbox, CPU-only).

Question (from the T264 red team): is the Stage-2 "role abstraction" more than a lookup
on shared probe tokens?  Test devices of the *block* role whose hidden state is revealed
only by a probe/token never informative during training (``probe_torque`` /
``torque_inverted``).  A decoy family shares the old cue token (``phase_180deg``) but
its primary action always works.

Preregistered reading (fixed before the first run):
- H1 (token lookup): on ``rotor`` the trained agent is no better than amnesic.
- H2 (structural prior): the trained agent learns the new cue in fewer units / with
  fewer failures than amnesic, because it knows *that* block-role failures are
  predictable from probes.
- Decoy cost: extra failures of the trained agent on ``decoy`` vs amnesic.
Arms: TRAINED (bus/cryo/relay stream first), AMNESIC, ALWAYS_PROBE_ALL is not applicable
(no schema), ORACLE lower bound = 0 failures.
"""

from __future__ import annotations

import json
import random
import sys
from typing import Any

from ..routing import GOAPAction
from . import t264_agi_readiness_battery as b

PROBES4 = (*b.PROBES, "probe_torque")

EXTRA_DEVICES: dict[str, dict[str, Any]] = {
    "rotor": {
        "surface": {"shaft_free", "drive_armed"},
        "goal": "rotor_spinning",
        "kind": "block",
        "primary": "spin_forward",
        "alt": "spin_reverse",
        "cue": "torque",
    },
    "decoy": {
        "surface": {"gate_closed", "latch_armed"},
        "goal": "gate_open",
        "kind": "block",
        "primary": "open_gate",
        "alt": "open_gate_slow",
        "cue": "decoy",
    },
}


class VocabTwin(b.GenericTwin):
    """GenericTwin plus a fourth probe and the two T265 device families."""

    def __init__(self, unit_id: str, device: str, latent: bool, *, seed: int = 0) -> None:
        if device in EXTRA_DEVICES:
            b.DEVICES.setdefault(device, EXTRA_DEVICES[device])
        cue = b.DEVICES[device].get("cue")
        super().__init__(unit_id, device, latent if cue != "decoy" else False, seed=seed)
        self._tok["probe_torque"] = "torque_normal"
        if cue == "torque":
            self._tok["probe_torque"] = "torque_inverted" if latent else "torque_normal"
            self._tok["probe_phase_angle"] = "phase_0deg"
        elif cue == "decoy":
            # old cue token always present, primary action always works
            self._tok["probe_phase_angle"] = "phase_180deg"


def _actions() -> tuple[GOAPAction, ...]:
    for name, spec in EXTRA_DEVICES.items():
        b.DEVICES.setdefault(name, spec)
    return b.build_actions()


def _agent(seed: int) -> Any:
    from ..bridge.stage2_cortex import SchemaLearner, Stage2Agent, ValueWorkspace

    return Stage2Agent(
        _actions(), PROBES4, learner=SchemaLearner(), workspace=ValueWorkspace(seed=seed)
    )


def _stream(seed: int, n: int, devices: tuple[str, ...]) -> list[VocabTwin]:
    rng = random.Random(seed)
    return [
        VocabTwin(f"{d}_{seed}_{i}", d, rng.random() < 0.5, seed=seed * 10_000 + i)
        for i, d in ((i, rng.choice(devices)) for i in range(n))
    ]


def _first_correct_unit(agent: Any, twins: list[VocabTwin]) -> tuple[int | None, list[int]]:
    """Index of the unit after which a torque schema exists; per-unit failure list."""
    import asyncio

    fails: list[int] = []
    first: int | None = None
    for i, t in enumerate(twins):
        ep = asyncio.run(agent.run_episode(t))
        fails.append(ep.failed_actuations)
        if first is None and any(
            s.feature == (("probe_torque", "torque_inverted"),)
            for s in agent.learner.schemas.values()
        ):
            first = i + 1
    return first, fails


def run_t265(seeds: int = 10, n: int = 24) -> dict[str, Any]:
    rows = []
    for s in range(seeds):
        trained = _agent(s)
        b.run(trained, _stream(7 + s, 40, ("bus", "cryo", "relay")))
        amnesic = _agent(s)
        r_first_t, r_fail_t = _first_correct_unit(trained, _stream(500 + s, n, ("rotor",)))
        r_first_a, r_fail_a = _first_correct_unit(amnesic, _stream(500 + s, n, ("rotor",)))
        trained_d, amnesic_d = _agent(s), _agent(s)
        b.run(trained_d, _stream(7 + s, 40, ("bus", "cryo", "relay")))
        d_t = b.run(trained_d, _stream(900 + s, 10, ("decoy",)))["failed"]
        d_a = b.run(amnesic_d, _stream(900 + s, 10, ("decoy",)))["failed"]
        rows.append(
            {
                "seed": s,
                "rotor_fail_trained": sum(r_fail_t),
                "rotor_fail_amnesic": sum(r_fail_a),
                "rotor_fail_first6_trained": sum(r_fail_t[:6]),
                "rotor_fail_first6_amnesic": sum(r_fail_a[:6]),
                "units_to_schema_trained": r_first_t,
                "units_to_schema_amnesic": r_first_a,
                "decoy_fail_trained": d_t,
                "decoy_fail_amnesic": d_a,
            }
        )

    def tot(k: str) -> int:
        return sum(r[k] for r in rows)

    def med(k: str) -> float | None:
        v = sorted(r[k] for r in rows if r[k] is not None)
        return float(v[len(v) // 2]) if v else None

    summary: dict[str, Any] = {
        "rotor_fail_trained": tot("rotor_fail_trained"),
        "rotor_fail_amnesic": tot("rotor_fail_amnesic"),
        "rotor_fail_first6_trained": tot("rotor_fail_first6_trained"),
        "rotor_fail_first6_amnesic": tot("rotor_fail_first6_amnesic"),
        "median_units_to_schema_trained": med("units_to_schema_trained"),
        "median_units_to_schema_amnesic": med("units_to_schema_amnesic"),
        "schema_learned_trained": sum(r["units_to_schema_trained"] is not None for r in rows),
        "schema_learned_amnesic": sum(r["units_to_schema_amnesic"] is not None for r in rows),
        "decoy_fail_trained": tot("decoy_fail_trained"),
        "decoy_fail_amnesic": tot("decoy_fail_amnesic"),
    }
    summary["verdict"] = (
        "H2_structural_prior"
        if summary["rotor_fail_trained"] <= 0.8 * summary["rotor_fail_amnesic"]
        else "H1_token_lookup"
    )
    return {"experiment": "t265_new_vocabulary_transfer.v1", "summary": summary, "rows": rows}


if __name__ == "__main__":
    json.dump(run_t265(), sys.stdout, indent=1)
