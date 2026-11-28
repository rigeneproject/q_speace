"""T264 — AGI-readiness battery for the Stage-2 cortex (sandbox, CPU-only).

Preregistered gates (fixed before the first run on 2026-11-28; any later change
must be reported in docs/T264_*):

A1 workspace causality   computed values beat shuffled and constant values on the
                          mixed stream (fewer failed actuations, or equal failures
                          and >= 10 % fewer ticks); k frozen high yields more idle ticks
                          than adaptive k.
A2 informative sigma     MR estimate within 0.12 of m for driven GW m in
                          {0.5, 0.9}, > 1.1 for m = 1.3, < 0.2 for iid Poisson noise.
A3 abstraction           first encounter of new devices (pump/block role, iceline/
                          clobber role, bus + irrelevant fact): memory arm has fewer
                          failed actuations than amnesic arm; abstraction=False ablation
                          has no advantage.
A4 robustness            40-unit random streams, 10 seeds: both correct schemas
                          consolidated in >= 8/10 at flip 0.0 and 0.1, >= 6/10 at 0.2;
                          zero spurious consolidated schemas.
A5 new observables       conjunctive-latent device: correct 2-literal schema in
                          >= 8/10 seeds; conjunctions=False ablation learns none.
A6 cold boot             separate OS process: loaded schemas reduce held-out failures
                          vs amnesic; Task A retained.
A7 negative controls     unobservable latent and token-shuffled probes: zero
                          consolidated schemas.
A8 resources             peak RSS < 250 MiB, no GPU import.

No single scalar score is reported (T260 BCEL entry).
"""

from __future__ import annotations

import asyncio
import json
import random
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from ..bridge.latent_discovery import TwinActionOutcome
from ..bridge.stage1_workspace import read_process_rss_mb
from ..bridge.stage2_cortex import SchemaLearner, Stage2Agent, ValueWorkspace
from ..routing import GOAPAction
from ..spiking.criticality import CriticalityController
from ..spiking.criticality_mr import driven_branching_process, mr_branching_ratio

PROBES = ("probe_phase_angle", "probe_acoustic_damping", "probe_ambient_hum")
FLIP = {
    "phase_180deg": "phase_0deg",
    "phase_0deg": "phase_180deg",
    "damping_high_frost": "damping_low",
    "damping_low": "damping_high_frost",
}

# device -> (surface, goal, mechanism, names)
DEVICES: dict[str, dict[str, Any]] = {
    "relay": {
        "surface": {"relay_online", "grid_synced"},
        "goal": "load_energized",
        "kind": "plain",
        "primary": "close_breaker",
    },
    "bus": {
        "surface": {"panel_online", "bus_ready"},
        "goal": "bus_locked",
        "kind": "block",
        "primary": "engage_primary_bus",
        "alt": "engage_inverted_bypass",
        "cue": "phase",
    },
    "bus_fan": {
        "surface": {"panel_online", "bus_ready", "cooling_fan_on"},
        "goal": "bus_locked",
        "kind": "block",
        "primary": "engage_primary_bus",
        "alt": "engage_inverted_bypass",
        "cue": "phase",
    },
    "pump": {
        "surface": {"valve_open", "pump_primed"},
        "goal": "flow_established",
        "kind": "block",
        "primary": "start_pump",
        "alt": "start_pump_reverse",
        "cue": "phase",
    },
    "cryo": {
        "surface": {"manifold_cooled", "seal_seated"},
        "goal": "chamber_pressurized",
        "kind": "clobber",
        "primary": "pressurize_chamber",
        "fluent": "seal_seated",
        "remedy": "thermal_purge_seal",
        "base": "manifold_cooled",
        "cue": "damping",
    },
    "iceline": {
        "surface": {"line_chilled", "gasket_set"},
        "goal": "line_open",
        "kind": "clobber",
        "primary": "open_line",
        "fluent": "gasket_set",
        "remedy": "heat_gasket",
        "base": "line_chilled",
        "cue": "damping",
    },
    "coil": {
        "surface": {"coil_powered", "contact_clean"},
        "goal": "circuit_closed",
        "kind": "block",
        "primary": "close_coil",
        "alt": "close_coil_aux",
        "cue": "conj",
    },
    "blindbus": {
        "surface": {"panel_online", "bus_ready"},
        "goal": "bus_locked",
        "kind": "block",
        "primary": "engage_primary_bus",
        "alt": "engage_inverted_bypass",
        "cue": "none",
    },
}


def build_actions() -> tuple[GOAPAction, ...]:
    acts: dict[str, GOAPAction] = {}
    for d in DEVICES.values():
        pre = frozenset(d["surface"] - {"cooling_fan_on"})
        g = frozenset({d["goal"]})
        if d["kind"] in ("plain", "block"):
            acts[d["primary"]] = GOAPAction(d["primary"], pre, g, cost=1.0)
            if d["kind"] == "block":
                acts[d["alt"]] = GOAPAction(d["alt"], pre, g, cost=1.8)
        else:
            acts[d["primary"]] = GOAPAction(d["primary"], pre, g, cost=1.0)
            acts[d["remedy"]] = GOAPAction(
                d["remedy"], frozenset({d["base"]}), frozenset({d["fluent"]}), cost=1.2
            )
    return tuple(acts.values())


class GenericTwin:
    """Sandbox twin parameterised by device spec, latent flag, noise and probe shuffle."""

    mcp_actuation_permitted = False

    def __init__(
        self,
        unit_id: str,
        device: str,
        latent: bool,
        *,
        seed: int = 0,
        flip_p: float = 0.0,
        shuffle_tokens: bool = False,
    ) -> None:
        self.unit_id = unit_id
        self.device = device
        self.spec = DEVICES[device]
        self.latent = latent
        self.rng = random.Random(seed)
        self.flip_p = flip_p
        self.surface_facts = frozenset(self.spec["surface"])
        self.goal_facts = frozenset({self.spec["goal"]})
        cue = self.spec.get("cue")
        phase = damp = False
        if cue == "phase":
            phase = latent
        elif cue == "damping":
            damp = latent
        elif cue == "conj":
            if latent:
                phase = damp = True
            else:
                phase, damp = self.rng.choice([(True, False), (False, True), (False, False)])
        if shuffle_tokens:
            phase, damp = self.rng.random() < 0.5, self.rng.random() < 0.5
        self._tok = {
            "probe_phase_angle": "phase_180deg" if phase else "phase_0deg",
            "probe_acoustic_damping": "damping_high_frost" if damp else "damping_low",
            "probe_ambient_hum": f"hum_{40 + self.rng.randrange(2)}pct",
        }

    def execute_probe(self, name: str) -> TwinActionOutcome:
        tok = self._tok[name]
        if self.flip_p and self.rng.random() < self.flip_p:
            tok = FLIP.get(tok, tok)
        return TwinActionOutcome(name, True, True, self.surface_facts, frozenset(), probe_token=tok)

    def execute_actuation(self, name: str) -> TwinActionOutcome:
        sp, prior = self.spec, self.surface_facts
        fail = TwinActionOutcome(name, False, False, prior, frozenset())
        pre = sp["surface"] - {"cooling_fan_on"}
        if sp["kind"] in ("plain", "block") and name in (sp["primary"], sp.get("alt")):
            if not pre.issubset(prior):
                return fail
            ok = (name == sp["primary"]) != (sp["kind"] == "block" and self.latent)
            if not ok:
                return fail
        elif sp["kind"] == "clobber" and name == sp["primary"]:
            if not pre.issubset(prior):
                return fail
            if self.latent:
                self.surface_facts = prior - {sp["fluent"]}
                return TwinActionOutcome(
                    name, False, False, self.surface_facts, frozenset({sp["fluent"]})
                )
        elif sp["kind"] == "clobber" and name == sp["remedy"]:
            if sp["base"] not in prior:
                return fail
            self.latent = False
            self.surface_facts = prior | {sp["fluent"]}
            return TwinActionOutcome(name, False, True, self.surface_facts, frozenset())
        else:
            return fail
        self.surface_facts = prior | {sp["goal"]}
        return TwinActionOutcome(name, False, True, self.surface_facts, frozenset())


# ----------------------------------------------------------------------
# Streams and runners
# ----------------------------------------------------------------------


def stream(
    seed: int,
    n: int,
    devices: Sequence[str],
    *,
    flip_p: float = 0.0,
    shuffle_tokens: bool = False,
    p_latent: float = 0.5,
) -> list[GenericTwin]:
    rng = random.Random(seed)
    out = [GenericTwin(f"relay_anchor_{seed}", "relay", False, seed=seed)]
    for i in range(n):
        d = rng.choice(list(devices))
        out.append(
            GenericTwin(
                f"{d}_{seed}_{i}",
                d,
                rng.random() < p_latent,
                seed=seed * 10_000 + i,
                flip_p=flip_p,
                shuffle_tokens=shuffle_tokens,
            )
        )
    return out


def make_agent(**kw: Any) -> Stage2Agent:
    lk = {k: kw.pop(k) for k in list(kw) if k in ("allow_conjunctions", "abstraction")}
    wk = {k: kw.pop(k) for k in list(kw) if k in ("value_mode", "adaptive_k", "initial_k", "seed")}
    return Stage2Agent(
        build_actions(), PROBES, learner=SchemaLearner(**lk), workspace=ValueWorkspace(**wk), **kw
    )


def run(agent: Stage2Agent, twins: Sequence[GenericTwin]) -> dict[str, Any]:
    async def _go() -> list[Any]:
        return [await agent.run_episode(t) for t in twins]

    eps = asyncio.run(_go())
    return {
        "ticks": sum(e.ticks for e in eps),
        "idle": sum(e.idle_ticks for e in eps),
        "failed": sum(e.failed_actuations for e in eps),
        "goals": sum(e.goal_reached for e in eps),
        "n": len(eps),
        "episodes": [asdict(e) for e in eps],
    }


TRUE_FEATURES = {
    ("block", (("probe_phase_angle", "phase_180deg"),)),
    ("clobber", (("probe_acoustic_damping", "damping_high_frost"),)),
    (
        "block",
        (("probe_acoustic_damping", "damping_high_frost"), ("probe_phase_angle", "phase_180deg")),
    ),
}


def schema_audit(agent: Stage2Agent) -> dict[str, Any]:
    cons = [s for s in agent.learner.schemas.values() if s.consolidated]
    correct = [s for s in cons if (s.kind, s.feature) in TRUE_FEATURES]
    return {
        "consolidated": [(s.kind, s.feature, s.induced_on) for s in cons],
        "n_correct": len(correct),
        "n_spurious": len(cons) - len(correct),
    }


# ----------------------------------------------------------------------
# Axes
# ----------------------------------------------------------------------


def a1_workspace_causality(seeds: int = 5) -> dict[str, Any]:
    res: dict[str, dict[str, int]] = {}
    for mode, kw in (
        ("computed", {}),
        ("shuffled", {"value_mode": "shuffled"}),
        ("constant", {"value_mode": "constant"}),
        ("k_frozen_high_threshold", {"adaptive_k": False, "initial_k": 0.6}),
    ):
        tot = {"ticks": 0, "failed": 0, "idle": 0, "goals": 0, "n": 0}
        for s in range(seeds):
            r = run(make_agent(**kw, seed=s), stream(100 + s, 40, ("bus", "cryo", "relay")))
            for k in tot:
                tot[k] += r[k]
        res[mode] = tot

    def better(a: dict[str, int], b: dict[str, int]) -> bool:
        return a["failed"] < b["failed"] or (
            a["failed"] == b["failed"] and a["ticks"] <= 0.9 * b["ticks"]
        )

    c = res["computed"]
    return {
        **res,
        "gate_beats_shuffled": better(c, res["shuffled"]),
        "gate_beats_constant": better(c, res["constant"]),
        "gate_frozen_k_more_idle": res["k_frozen_high_threshold"]["idle"] > c["idle"],
    }


def a2_informative_sigma() -> dict[str, Any]:
    out: dict[str, Any] = {}
    for m, n in ((0.5, 2000), (0.9, 2000), (1.3, 30)):
        seq = driven_branching_process(m, n=n, seed=3)
        ctrl = CriticalityController(window=16)
        ratio = [ctrl.step(int(x), 2.0).branching_ratio for x in seq][1:]
        out[f"gw_m{m}"] = {
            "mr": round(mr_branching_ratio(seq).m, 3),
            "ratio_estimator": round(float(np.mean(ratio)), 3),
        }
    noise = np.random.default_rng(5).poisson(4, 300).tolist()
    ctrl = CriticalityController(window=16)
    out["iid_poisson"] = {
        "mr": mr_branching_ratio(noise).m,
        "ratio_estimator": round(
            float(np.mean([ctrl.step(int(x), 2.0).branching_ratio for x in noise][1:])), 3
        ),
    }
    out["gate"] = (
        abs(out["gw_m0.5"]["mr"] - 0.5) <= 0.12
        and abs(out["gw_m0.9"]["mr"] - 0.9) <= 0.12
        and out["gw_m1.3"]["mr"] > 1.1
        and out["iid_poisson"]["mr"] < 0.2
    )
    return out


def _train(agent: Stage2Agent, seed: int = 7) -> None:
    run(agent, stream(seed, 40, ("bus", "cryo", "relay")))


def a3_abstraction(seeds: int = 5) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for dev in ("pump", "iceline", "bus_fan"):
        arms = {"memory": [0, 0], "amnesic": [0, 0], "no_abstraction": [0, 0]}
        for s in range(seeds):

            def test(dev: str = dev, s: int = s) -> list[GenericTwin]:
                return [
                    GenericTwin(f"{dev}_t{s}_{i}", dev, True, seed=900 + 10 * s + i)
                    for i in range(3)
                ]

            mem = make_agent(seed=s)
            _train(mem, 7 + s)
            noab = make_agent(seed=s, abstraction=False)
            _train(noab, 7 + s)
            for arm, ag in (
                ("memory", mem),
                ("amnesic", make_agent(seed=s)),
                ("no_abstraction", noab),
            ):
                r = run(ag, test())
                arms[arm][0] += r["failed"]
                arms[arm][1] += r["ticks"]
        out[dev] = {k: {"failed": v[0], "ticks": v[1]} for k, v in arms.items()}
        out[dev]["gate"] = (
            arms["memory"][0] < arms["amnesic"][0]
            and arms["no_abstraction"][0] >= arms["amnesic"][0] - 1
        )
    out["gate"] = all(out[d]["gate"] for d in ("pump", "iceline", "bus_fan"))
    return out


def a4_robustness(seeds: int = 10) -> dict[str, Any]:
    out: dict[str, Any] = {}
    need = {0.0: 8, 0.1: 8, 0.2: 6}
    for flip in (0.0, 0.1, 0.2):
        ok = spur = 0
        for s in range(seeds):
            ag = make_agent(seed=s)
            run(ag, stream(300 + s, 40, ("bus", "cryo", "relay"), flip_p=flip))
            au = schema_audit(ag)
            ok += au["n_correct"] >= 2
            spur += au["n_spurious"]
        out[f"flip_{flip}"] = {
            "both_correct": ok,
            "spurious": spur,
            "gate": ok >= need[flip] and spur == 0,
        }
    out["gate"] = all(v["gate"] for v in out.values() if isinstance(v, dict))
    return out


def a5_constructed_observables(seeds: int = 10) -> dict[str, Any]:
    res = {}
    for label, kw in (("conjunctions_on", {}), ("conjunctions_off", {"allow_conjunctions": False})):
        hits = 0
        for s in range(seeds):
            ag = make_agent(seed=s, **kw)
            run(ag, stream(500 + s, 40, ("coil",)))
            hits += any(
                len(sc.feature) == 2 and sc.consolidated and ("block", sc.feature) in TRUE_FEATURES
                for sc in ag.learner.schemas.values()
            )
        res[label] = hits
    return {**res, "gate": res["conjunctions_on"] >= 8 and res["conjunctions_off"] == 0}


def a7_negative_controls(seeds: int = 5) -> dict[str, Any]:
    blind = shuf = 0
    for s in range(seeds):
        ag = make_agent(seed=s)
        run(ag, stream(700 + s, 40, ("blindbus", "relay")))
        blind += sum(sc.consolidated for sc in ag.learner.schemas.values())
        ag2 = make_agent(seed=s)
        run(ag2, stream(800 + s, 40, ("bus", "cryo"), shuffle_tokens=True))
        shuf += sum(sc.consolidated for sc in ag2.learner.schemas.values())
    return {
        "unobservable_consolidated": blind,
        "shuffled_consolidated": shuf,
        "gate": blind == 0 and shuf == 0,
    }


# ---- A6: cold boot across OS processes ---------------------------------


def _phase(mode: str, db: str) -> dict[str, Any]:
    if mode == "train":
        ag = make_agent(seed=0)
        _train(ag, 7)
        return {"saved": ag.learner.save(Path(db)), "rss": read_process_rss_mb()}
    ag = make_agent(seed=0)
    loaded = ag.learner.load(Path(db)) if mode == "eval_memory" else 0
    held = [GenericTwin("relay_hold", "relay", False, seed=1)] + [
        GenericTwin(f"{d}_hold_{i}", d, True, seed=1000 + 10 * j + i)
        for j, d in enumerate(("bus", "cryo", "pump", "iceline"))
        for i in range(2)
    ]
    r = run(ag, held)
    return {
        "loaded": loaded,
        "failed": r["failed"],
        "ticks": r["ticks"],
        "task_a": r["episodes"][0]["goal_reached"] and r["episodes"][0]["failed_actuations"] == 0,
        "rss": read_process_rss_mb(),
    }


def a6_cold_boot(work: Path) -> dict[str, Any]:
    db = str(work / "t264.db")
    res = {}
    for mode in ("train", "eval_memory", "eval_amnesic"):
        cp = subprocess.run(
            [
                sys.executable,
                "-m",
                "q_speace.vertical_slice.t264_agi_readiness_battery",
                "--phase",
                mode,
                db,
            ],
            capture_output=True,
            text=True,
            timeout=170,
            check=True,
        )
        res[mode] = json.loads(cp.stdout.strip().splitlines()[-1])
    m, a = res["eval_memory"], res["eval_amnesic"]
    res["gate"] = m["loaded"] >= 2 and m["failed"] < a["failed"] and m["task_a"]
    return res


def run_battery(work: Path | None = None) -> dict[str, Any]:
    tmp = tempfile.TemporaryDirectory() if work is None else None
    wd = Path(tmp.name) if tmp else Path(work)  # type: ignore[arg-type]
    wd.mkdir(parents=True, exist_ok=True)
    rep: dict[str, Any] = {"battery": "t264_agi_readiness.v1"}
    rep["A1_workspace_causality"] = a1_workspace_causality()
    rep["A2_informative_sigma"] = a2_informative_sigma()
    rep["A3_abstraction"] = a3_abstraction()
    rep["A4_robustness"] = a4_robustness()
    rep["A5_constructed_observables"] = a5_constructed_observables()
    rep["A6_cold_boot"] = a6_cold_boot(wd)
    rep["A7_negative_controls"] = a7_negative_controls()
    peak = max(
        read_process_rss_mb(),
        *(rep["A6_cold_boot"][k]["rss"] for k in ("train", "eval_memory", "eval_amnesic")),
    )
    rep["A8_resources"] = {
        "peak_rss_mb": round(peak, 2),
        "gpu_imported": "torch" in sys.modules,
        "gate": peak < 250.0,
    }
    rep["gates"] = {k: v["gate"] for k, v in rep.items() if isinstance(v, dict) and "gate" in v}
    if tmp:
        tmp.cleanup()
    return rep


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "--phase":
        print(json.dumps(_phase(sys.argv[2], sys.argv[3]), default=str))
    else:
        out = run_battery(Path(sys.argv[1]) if len(sys.argv) > 1 else None)
        print(json.dumps(out, indent=1, default=str))
