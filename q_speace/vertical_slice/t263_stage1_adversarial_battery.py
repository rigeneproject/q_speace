"""T263 — Adversarial generalization battery for the Stage-1 prototype (evaluation only).

Measures what the T261–T262 acceptance gates do not cover. Nothing here changes
the prototype: every experiment either feeds synthetic inputs to existing
components or ablates one mechanism via a scoped monkeypatch and compares the
resulting behaviour with the unmodified baseline.

Experiments
-----------
E1  Discriminative power of the sigma gate: does the branching-ratio estimator
    separate structureless noise from critical dynamics?
E2  Causal attribution of the workspace machinery: do spikes / closed-loop k
    change any decision in the T261–T262 campaign?
E3  Robustness of recall: one irrelevant extra surface fact on a known unit.
E4  Transfer: a new device class with the *same* hidden causal structure
    (polarity inversion detectable by the same phase probe).
E5  Noisy probes: 20 % token flips during discovery.
E6  Curriculum order: discovery under random permutations of the curriculum.
E7  Unobservable latent: hidden mechanism with no informative probe available.

CPU-only, single process, sandboxed twins only (T217). No GPU imports.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import random
import sys
import tempfile
from collections.abc import Iterator, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np

from ..bridge import latent_discovery as ld
from ..bridge import stage1_workspace as sw
from ..bridge.stage1_workspace import read_process_rss_mb
from ..routing import GOAPAction
from ..spiking.criticality import CriticalityController
from ..spiking.encoder import SpikeEncodingResult

# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def _mean_sigma(counts: list[int]) -> float:
    ctrl = CriticalityController(window=16)
    sigmas = [ctrl.step(int(n), 2.2).branching_ratio for n in counts]
    tail = sigmas[1:] or sigmas
    return float(sum(tail) / len(tail))


@contextlib.contextmanager
def _patched(obj: Any, name: str, value: Any) -> Iterator[None]:
    old = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, old)


def _episode_signature(ep: ld.EpisodeRunMetrics) -> tuple[Any, ...]:
    return (
        ep.unit_id,
        ep.goal_reached,
        ep.ticks_used,
        ep.failed_actuations,
        ep.probes_executed,
        ep.actuations_executed,
    )


async def _run_units(
    proto: ld.Stage1CognitivePrototype, twins: Sequence[ld.LatentSandboxTwin]
) -> list[ld.EpisodeRunMetrics]:
    return [await proto.run_episode(t) for t in twins]


def _campaign(db: Path) -> dict[str, Any]:
    """In-process phase-1 + phase-2 (attribution only; cold boot is tested by T262)."""

    async def _go() -> dict[str, Any]:
        p1 = ld.Stage1CognitivePrototype(db_path=db, allow_consolidated_load=False)
        e1 = await _run_units(p1, ld._training_curriculum())
        tel = p1.workspace.summarize_telemetry().to_dict()
        saved = await p1.persist_and_close()
        p2 = ld.Stage1CognitivePrototype(db_path=db, cold_boot_require_consolidated=True)
        e2 = await _run_units(p2, ld._heldout_cold_boot_variants())
        if p2.store is not None:
            p2.store.close()
        return {
            "saved": saved,
            "sig": [_episode_signature(e) for e in e1 + e2],
            "mean_sigma": tel["mean_branching_ratio"],
            "ticks": sum(e.ticks_used for e in e1 + e2),
            "failed": sum(e.failed_actuations for e in e1 + e2),
        }

    return asyncio.run(_go())


# ----------------------------------------------------------------------
# Extra sandbox twins (new device class, unobservable latent, noisy probes)
# ----------------------------------------------------------------------


class ExtendedTwin(ld.LatentSandboxTwin):
    """Adds ``pump_h3`` (new device class), ``bus_h1_fan`` and probe noise."""

    def __init__(
        self,
        unit_id: str,
        *,
        subsystem: str,
        hidden_variant: str,
        distractor_seed: int = 0,
        probe_flip_p: float = 0.0,
        rng_seed: int = 0,
    ) -> None:
        self._rng = random.Random(rng_seed)
        self._flip_p = probe_flip_p
        if subsystem == "pump_h3":
            super().__init__(unit_id, subsystem="bus_h1", hidden_variant="nominal")
            self.subsystem = "pump_h3"
            self.hidden_variant = hidden_variant
            self.surface_facts = frozenset({"valve_open", "pump_primed"})
            self.goal_facts = frozenset({"flow_established"})
            self._inverted = hidden_variant == "latent_inverted"
            self._distractor_seed = distractor_seed
        elif subsystem == "bus_h1_fan":
            super().__init__(
                unit_id,
                subsystem="bus_h1",
                hidden_variant=hidden_variant,
                distractor_seed=distractor_seed,
            )
            self.surface_facts = self.surface_facts | {"cooling_fan_on"}
            self.subsystem = "bus_h1_fan"  # so the amnesic arm rebuilds the same twin
        elif subsystem == "bus_h1_hidden":
            # Latent with no informative probe: all probes read nominal values.
            super().__init__(
                unit_id,
                subsystem="bus_h1",
                hidden_variant=hidden_variant,
                distractor_seed=distractor_seed,
            )
            self._blind = True
            self.subsystem = "bus_h1_hidden"
        else:
            super().__init__(
                unit_id,
                subsystem=subsystem,
                hidden_variant=hidden_variant,
                distractor_seed=distractor_seed,
            )

    def execute_probe(self, probe_name: str) -> ld.TwinActionOutcome:
        if getattr(self, "_blind", False):
            inv, self._inverted = self._inverted, False
            out = super().execute_probe(probe_name)
            self._inverted = inv
            return out
        out = super().execute_probe(probe_name)
        if self._flip_p > 0.0 and out.probe_token and self._rng.random() < self._flip_p:
            flips = {
                "phase_180deg": "phase_0deg",
                "phase_0deg": "phase_180deg",
                "damping_high_frost": "damping_low",
                "damping_low": "damping_high_frost",
            }
            tok = flips.get(out.probe_token, out.probe_token)
            return ld.TwinActionOutcome(
                out.action_name, True, True, out.surface_facts, frozenset(), probe_token=tok
            )
        return out

    def execute_actuation(self, action_name: str) -> ld.TwinActionOutcome:
        if self.subsystem != "pump_h3":
            return super().execute_actuation(action_name)
        prior = self.surface_facts
        ok_pre = {"valve_open", "pump_primed"}.issubset(prior)
        if action_name == "start_pump":
            ok = ok_pre and not self._inverted
        elif action_name == "start_pump_reverse":
            ok = ok_pre and self._inverted
        else:
            return ld.TwinActionOutcome(action_name, False, False, prior, frozenset())
        if ok:
            self.surface_facts = prior | {"flow_established"}
        return ld.TwinActionOutcome(action_name, False, ok, self.surface_facts, frozenset())


_ORIG_ONTOLOGY = ld.build_stage1_base_ontology


def _extended_ontology() -> tuple[Any, tuple[GOAPAction, ...], tuple[str, ...]]:
    registry, actions, probes = _ORIG_ONTOLOGY()
    extra = (
        GOAPAction(
            name="start_pump",
            preconditions=frozenset({"valve_open", "pump_primed"}),
            add_effects=frozenset({"flow_established"}),
            cost=1.0,
        ),
        GOAPAction(
            name="start_pump_reverse",
            preconditions=frozenset({"valve_open", "pump_primed"}),
            add_effects=frozenset({"flow_established"}),
            cost=1.8,
        ),
    )
    return registry, (*actions, *extra), probes


# ----------------------------------------------------------------------
# Experiments
# ----------------------------------------------------------------------


def e1_sigma_gate_discrimination(seed: int = 7) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    n = 80
    seqs = {
        "iid_uniform_noise_0_12": rng.integers(0, 13, n).tolist(),
        "iid_poisson_noise_lambda4": rng.poisson(4, n).tolist(),
        "constant_5": [5] * n,
        "decay_to_silence": [int(round(12 * 0.88**t)) for t in range(n)],
        "slow_growth_x1p12": [int(round(1.12**t)) for t in range(n)],
        "fast_growth_x1p30": [int(round(1.3**t)) for t in range(40)],
    }
    out: dict[str, Any] = {}
    for name, s in seqs.items():
        sig = _mean_sigma(s)
        out[name] = {"mean_sigma": round(sig, 4), "in_band_0p85_1p15": 0.85 <= sig <= 1.15}
    out["noise_passes_gate"] = (
        out["iid_uniform_noise_0_12"]["in_band_0p85_1p15"]
        and out["iid_poisson_noise_lambda4"]["in_band_0p85_1p15"]
    )
    return out


def e2_workspace_attribution(work: Path) -> dict[str, Any]:
    base = _campaign(work / "e2_base.db")

    class _FixedK(CriticalityController):
        def __init__(self, **kw: Any) -> None:
            kw["kp"] = 0.0
            super().__init__(**kw)

    def _zero_spikes(x: Any, k: float = 3.0, coherence_phi: Any = None, beta: float = 0.0) -> Any:
        arr = np.asarray(x, dtype=float)
        return SpikeEncodingResult(np.zeros_like(arr), np.ones((1,)), 0, 1.0, 0.0)

    with _patched(sw, "CriticalityController", _FixedK):
        fixed_k = _campaign(work / "e2_fixedk.db")
    with _patched(sw, "dynamic_spikes", _zero_spikes):
        no_spikes = _campaign(work / "e2_nospikes.db")

    return {
        "baseline": {k: base[k] for k in ("saved", "ticks", "failed", "mean_sigma")},
        "fixed_k_criticality_off": {
            k: fixed_k[k] for k in ("saved", "ticks", "failed", "mean_sigma")
        },
        "spikes_removed_salience_only": {
            k: no_spikes[k] for k in ("saved", "ticks", "failed", "mean_sigma")
        },
        "fixed_k_behaviour_identical": fixed_k["sig"] == base["sig"],
        "no_spikes_behaviour_identical": no_spikes["sig"] == base["sig"],
    }


_TRUE_PROBE = {
    "engage_primary_bus": "probe_phase_angle",
    "pressurize_chamber": "probe_acoustic_damping",
}


def _phase1_db(
    work: Path, name: str, curriculum: Sequence[ld.LatentSandboxTwin]
) -> tuple[Path, int]:
    db = work / name

    async def _go() -> int:
        p = ld.Stage1CognitivePrototype(db_path=db, allow_consolidated_load=False)
        await _run_units(p, curriculum)
        # Count only consolidated rules that use the truly informative probe.
        correct = sum(
            1
            for r in p.learner.sandbox.consolidated_rules()
            if _TRUE_PROBE.get(r.blocked_action) == r.probe_name
        )
        await p.persist_and_close()
        return correct

    return db, asyncio.run(_go())


def _cold_eval(db: Path | None, twins: Sequence[ld.LatentSandboxTwin]) -> dict[str, Any]:
    async def _go() -> dict[str, Any]:
        p = ld.Stage1CognitivePrototype(db_path=db, cold_boot_require_consolidated=True)
        eps = await _run_units(p, twins)
        if p.store is not None:
            p.store.close()
        return {
            "ticks": sum(e.ticks_used for e in eps),
            "failed_actuations": sum(e.failed_actuations for e in eps),
            "goals": sum(e.goal_reached for e in eps),
            "episodes": [asdict(e) for e in eps],
        }

    return asyncio.run(_go())


def e3_e4_recall_and_transfer(work: Path) -> dict[str, Any]:
    with _patched(ld, "build_stage1_base_ontology", _extended_ontology):
        db, saved = _phase1_db(work, "e34.db", ld._training_curriculum())
        known = [
            ExtendedTwin(
                f"bus_known_{i}",
                subsystem="bus_h1",
                hidden_variant="latent_inverted",
                distractor_seed=20 + i,
            )
            for i in range(3)
        ]
        fan = [
            ExtendedTwin(
                f"bus_fan_{i}",
                subsystem="bus_h1_fan",
                hidden_variant="latent_inverted",
                distractor_seed=30 + i,
            )
            for i in range(3)
        ]
        pump = [
            ExtendedTwin(
                f"pump_{i}",
                subsystem="pump_h3",
                hidden_variant="latent_inverted",
                distractor_seed=40 + i,
            )
            for i in range(3)
        ]
        res: dict[str, Any] = {"consolidated_rules": saved}
        for label, twins_fn in (
            ("E3a_known_surface", lambda: known),
            ("E3b_plus_one_irrelevant_fact", lambda: fan),
            ("E4_new_device_same_mechanism", lambda: pump),
        ):
            twins = twins_fn()
            # fresh twin instances for the amnesic arm
            amnesic_twins = [
                ExtendedTwin(
                    t.unit_id,
                    subsystem=t.subsystem,
                    hidden_variant=t.hidden_variant,
                    distractor_seed=t._distractor_seed,
                )
                for t in twins
            ]
            w = _cold_eval(db, twins)
            a = _cold_eval(None, amnesic_twins)
            res[label] = {
                "with_consolidated_memory": {
                    k: w[k] for k in ("ticks", "failed_actuations", "goals")
                },
                "amnesic": {k: a[k] for k in ("ticks", "failed_actuations", "goals")},
                "memory_helps": (w["failed_actuations"], w["ticks"])
                < (a["failed_actuations"], a["ticks"]),
            }
    return res


def _random_stream(seed: int, n: int = 30, flip_p: float = 0.0) -> list[ld.LatentSandboxTwin]:
    """Unordered stream: Task A anchor + 50/50 latent/nominal units of both subsystems."""
    rng = random.Random(seed)
    twins: list[ld.LatentSandboxTwin] = [
        ExtendedTwin("relay_anchor", subsystem="relay_a", hidden_variant="nominal")
    ]
    for i in range(n):
        sub = rng.choice(("bus_h1", "cryo_h2"))
        latent = rng.random() < 0.5
        hv = ("latent_inverted" if sub == "bus_h1" else "latent_frosted") if latent else "nominal"
        twins.append(
            ExtendedTwin(
                f"s{seed}_{i}",
                subsystem=sub,
                hidden_variant=hv,
                distractor_seed=rng.randrange(100),
                probe_flip_p=flip_p,
                rng_seed=seed * 1000 + i,
            )
        )
    return twins


def e6b_long_random_stream(work: Path, seeds: int = 10, flip_p: float = 0.0) -> dict[str, Any]:
    counts = []
    for s in range(seeds):
        _, saved = _phase1_db(work, f"e6b_{flip_p}_{s}.db", _random_stream(s, flip_p=flip_p))
        counts.append(saved)
    return {
        "seeds": seeds,
        "stream_len": 31,
        "flip_probability": flip_p,
        "consolidated_per_seed": counts,
        "seeds_with_both_rules": sum(c == 2 for c in counts),
    }


def e5_noisy_probes(work: Path, flip_p: float = 0.2, seeds: int = 5) -> dict[str, Any]:
    results = []
    for s in range(seeds):
        cur = [
            ExtendedTwin(
                t.unit_id,
                subsystem=t.subsystem,
                hidden_variant=t.hidden_variant,
                distractor_seed=t._distractor_seed,
                probe_flip_p=flip_p,
                rng_seed=1000 * s + i,
            )
            for i, t in enumerate(ld._training_curriculum())
        ]
        db, saved = _phase1_db(work, f"e5_{s}.db", cur)
        held = [
            ExtendedTwin(
                t.unit_id,
                subsystem=t.subsystem,
                hidden_variant=t.hidden_variant,
                distractor_seed=t._distractor_seed,
                probe_flip_p=flip_p,
                rng_seed=7000 * s + i,
            )
            for i, t in enumerate(ld._heldout_cold_boot_variants())
        ]
        ev = _cold_eval(db, held)
        results.append(
            {
                "seed": s,
                "consolidated": saved,
                "heldout_failed": ev["failed_actuations"],
                "heldout_goals": ev["goals"],
            }
        )
    return {
        "flip_probability": flip_p,
        "runs": results,
        "runs_with_both_rules": sum(r["consolidated"] == 2 for r in results),
    }


def e6_curriculum_order(work: Path, perms: int = 10) -> dict[str, Any]:
    counts = []
    for s in range(perms):
        cur = ld._training_curriculum()
        random.Random(s).shuffle(cur)
        _, saved = _phase1_db(work, f"e6_{s}.db", cur)
        counts.append(saved)
    return {
        "permutations": perms,
        "consolidated_per_perm": counts,
        "perms_with_both_rules": sum(c == 2 for c in counts),
    }


def e7_unobservable_latent(work: Path) -> dict[str, Any]:
    cur = [
        (
            ExtendedTwin(
                t.unit_id,
                subsystem="bus_h1_hidden",
                hidden_variant=t.hidden_variant,
                distractor_seed=t._distractor_seed,
            )
            if t.subsystem == "bus_h1"
            else t
        )
        for t in ld._training_curriculum()
    ]
    db, saved = _phase1_db(work, "e7.db", cur)
    held = [
        ExtendedTwin(
            f"blind_{i}",
            subsystem="bus_h1_hidden",
            hidden_variant="latent_inverted",
            distractor_seed=50 + i,
        )
        for i in range(3)
    ]
    ev = _cold_eval(db, held)
    return {
        "consolidated_rules": saved,
        "heldout_failed_actuations": ev["failed_actuations"],
        "heldout_goals": ev["goals"],
        "heldout_ticks": ev["ticks"],
    }


def run_t263_battery(work_dir: Path | None = None) -> dict[str, Any]:
    tmp = tempfile.TemporaryDirectory() if work_dir is None else None
    work = Path(tmp.name) if tmp is not None else Path(work_dir)  # type: ignore[arg-type]
    work.mkdir(parents=True, exist_ok=True)
    rss0 = read_process_rss_mb()
    report = {
        "battery": "t263_stage1_adversarial.v1",
        "E1_sigma_gate": e1_sigma_gate_discrimination(),
        "E2_workspace_attribution": e2_workspace_attribution(work),
        "E3_E4_recall_and_transfer": e3_e4_recall_and_transfer(work),
        "E5_noisy_probes": e5_noisy_probes(work),
        "E6_curriculum_order": e6_curriculum_order(work),
        "E6b_long_random_stream_clean": e6b_long_random_stream(work),
        "E6c_long_random_stream_noise10": e6b_long_random_stream(work, flip_p=0.10),
        "E7_unobservable_latent": e7_unobservable_latent(work),
        "rss_start_mb": round(rss0, 2),
        "rss_end_mb": round(read_process_rss_mb(), 2),
    }
    if tmp is not None:
        tmp.cleanup()
    return report


if __name__ == "__main__":
    out = run_t263_battery(Path(sys.argv[1]) if len(sys.argv) > 1 else None)
    print(json.dumps(out, indent=2, default=str))
