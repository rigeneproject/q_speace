"""Stage-2 cortex prototype (T264): value-driven workspace, role-abstract schemas,
noise-robust evidence and constructed observables.

Addresses the five T263 bottlenecks:

1. **Decisions from the workspace (E2).** Candidates carry *computed* values
   (expected utility of an actuation, expected information gain of a probe or a
   repeat reading). Values are spike-encoded with ``dynamic_spikes``; only
   candidates that emit at least one spike ignite, the highest-valued ignited
   candidate wins, and an empty ignition is an idle tick. ``CriticalityController``
   regulates ``k`` from the ignition count, so the threshold has a causal role.
2. **Informative criticality (E1).** Telemetry reports the MR estimator
   (``q_speace.spiking.criticality_mr``) next to the T248 ratio estimator.
3. **Abstraction (E3b/E4).** A hypothesis is a *schema over causal roles*, not a rule
   over an exact surface: ``block`` = "when feature F holds, the cheapest member of a
   group of interchangeable actions fails"; ``clobber`` = "when F holds, the goal
   action destroys the one precondition that another action can restore". Schemas
   apply to any device whose action graph has that role, and matching uses
   ``preconditions ⊆ beliefs`` instead of surface equality.
4. **Robustness (E5/E6).** Laplace-smoothed balanced accuracy for induction, majority
   of repeated readings, and blame assignment: when a prediction fails, the feature
   probe is re-read and the schema is suppressed only if the feature still holds.
5. **New observables (E7').** When no single probe token discriminates, conjunctions of
   two readings are constructed as derived observables ``obs_k``.

Sandbox only (T217): twins are in-memory, no host actuation, CPU-only.
BCEL: "cortex", "ignition" and "workspace" are scheduling vocabulary; no claim of
awareness (AGENTS.md §2).
"""

from __future__ import annotations

import asyncio
import json
import math
import sqlite3
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from ..routing import GOAPAction, GOAPPlanner
from ..seed.killswitch import KillSwitch
from ..self_improvement_cortex.epigenetics import EpigeneticEngine
from ..spiking.criticality import CriticalityController
from ..spiking.criticality_mr import mr_branching_ratio
from ..spiking.encoder import dynamic_spikes
from .stage1_workspace import MemoryBudgetGuard, default_stage1_seed_genome, read_process_rss_mb

Feature = tuple[tuple[str, str], ...]  # sorted (probe, token) literals, conjunction


# ----------------------------------------------------------------------
# Causal-role helpers over the action graph
# ----------------------------------------------------------------------


def alternative_group(action: GOAPAction, actions: Sequence[GOAPAction]) -> list[GOAPAction]:
    """Actions interchangeable with ``action`` (same preconditions and add-effects)."""
    return sorted(
        (
            a
            for a in actions
            if a.preconditions == action.preconditions and a.add_effects == action.add_effects
        ),
        key=lambda a: (a.cost, a.name),
    )


def restorable_precondition(action: GOAPAction, actions: Sequence[GOAPAction]) -> str | None:
    """The unique precondition of ``action`` that some *other* action can add."""
    cands = sorted(
        f
        for f in action.preconditions
        if any(f in b.add_effects for b in actions if b.name != action.name)
    )
    return cands[0] if len(cands) == 1 else None


def goal_relevant_restorable(action: GOAPAction, actions: Sequence[GOAPAction]) -> bool:
    return restorable_precondition(action, actions) is not None


def remediation_for(fluent: str, actions: Sequence[GOAPAction]) -> str | None:
    adders = sorted((a for a in actions if fluent in a.add_effects), key=lambda a: a.cost)
    return adders[0].name if adders else None


# ----------------------------------------------------------------------
# Evidence and schemas
# ----------------------------------------------------------------------


@dataclass
class Schema:
    schema_id: str
    kind: str  # "block" | "clobber"
    feature: Feature
    score: float
    induced_on: tuple[str, ...]  # action names whose samples induced it
    applied_on: set[str] = field(default_factory=set)  # actions where transfer was verified
    excluded_on: set[str] = field(default_factory=set)  # actions outside the learned scope
    transfer_fail: dict[str, int] = field(default_factory=dict)
    transfer_ok: dict[str, int] = field(default_factory=dict)
    promotion_count: int = 0
    suppression_count: int = 0
    consolidated: bool = False

    def matches(self, readings: dict[str, str]) -> bool:
        return all(readings.get(p) == t for p, t in self.feature)

    def to_row(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "kind": self.kind,
            "feature": [list(x) for x in self.feature],
            "score": self.score,
            "induced_on": list(self.induced_on),
            "applied_on": sorted(self.applied_on),
            "excluded_on": sorted(self.excluded_on),
            "transfer_fail": dict(self.transfer_fail),
            "transfer_ok": dict(self.transfer_ok),
            "promotion_count": self.promotion_count,
            "suppression_count": self.suppression_count,
            "consolidated": self.consolidated,
        }


@dataclass(frozen=True)
class RoleSample:
    kind: str  # "block" (first attempt of a grouped action) | "clobber" (goal action w/ restorable pre)
    action: str
    readings: tuple[tuple[str, str], ...]
    failed: bool


def _balanced_accuracy(tp: int, nf: int, fp: int, ns: int) -> float:
    """Laplace-smoothed balanced accuracy of feature-predicts-failure."""
    tpr = (tp + 1.0) / (nf + 2.0)
    tnr = (ns - fp + 1.0) / (ns + 2.0)
    return 0.5 * (tpr + tnr)


class SchemaLearner:
    """Induces, validates, retracts and persists role-abstract schemas."""

    def __init__(
        self,
        *,
        min_score: float = 0.80,
        min_each: int = 2,
        allow_conjunctions: bool = True,
        abstraction: bool = True,
        retraction_suppressions: int = 3,
    ) -> None:
        self.engine = EpigeneticEngine(min_promotions=3, stability_threshold=0.70)
        self.schemas: dict[str, Schema] = {}
        self.samples: list[RoleSample] = []
        self.retracted: set[tuple[str, Feature]] = set()
        self.min_score = min_score
        self.min_each = min_each
        self.allow_conjunctions = allow_conjunctions
        self.abstraction = abstraction
        self.retraction_suppressions = retraction_suppressions
        self._counter = 0
        # first-attempt outcome statistics per action (prior for p_fail)
        self.attempts: dict[str, list[int]] = {}  # name -> [fails, total]

    # ---- priors ---------------------------------------------------------
    def global_fail_rate(self) -> float:
        f = sum(v[0] for v in self.attempts.values())
        n = sum(v[1] for v in self.attempts.values())
        return (f + 1.0) / (n + 10.0)

    def prior_fail(self, action: str) -> float:
        g = self.global_fail_rate()
        f, n = self.attempts.get(action, [0, 0])
        return (f + 3.0 * g) / (n + 3.0)

    def record_attempt(self, action: str, failed: bool) -> None:
        v = self.attempts.setdefault(action, [0, 0])
        v[0] += int(failed)
        v[1] += 1

    # ---- schema access ---------------------------------------------------
    def applicable(self, kind: str, action: str) -> list[Schema]:
        out = []
        for s in self.schemas.values():
            if s.kind != kind or action in s.excluded_on:
                continue
            if not self.abstraction and action not in s.induced_on:
                continue
            out.append(s)
        return sorted(out, key=lambda s: (-s.consolidated, -s.score, s.schema_id))

    def probe_relevance(self, probe: str) -> float:
        best = 0.0
        for s in self.schemas.values():
            if any(p == probe for p, _ in s.feature):
                best = max(
                    best,
                    0.5
                    + 0.5 * (s.promotion_count + 1) / (s.promotion_count + s.suppression_count + 2),
                )
        return best if best > 0 else 0.6

    # ---- induction -------------------------------------------------------
    def record_sample(self, sample: RoleSample) -> Schema | None:
        self.samples.append(sample)
        return self._induce(sample.kind, sample.action)

    def _candidate_features(self, rel: list[RoleSample]) -> list[Feature]:
        lits = sorted({lit for s in rel if s.failed for lit in s.readings})
        feats: list[Feature] = [(lit,) for lit in lits]
        if self.allow_conjunctions:
            for i in range(len(lits)):
                for j in range(i + 1, len(lits)):
                    if lits[i][0] != lits[j][0]:
                        feats.append((lits[i], lits[j]))
        return feats

    def _score(self, feat: Feature, rel: list[RoleSample]) -> tuple[float, int, int]:
        probes = {p for p, _ in feat}
        meas = [s for s in rel if probes.issubset(dict(s.readings))]
        fails = [s for s in meas if s.failed]
        succ = [s for s in meas if not s.failed]
        if len(fails) < self.min_each or len(succ) < self.min_each:
            return 0.0, len(fails), len(succ)
        tp = sum(all(dict(s.readings).get(p) == t for p, t in feat) for s in fails)
        fp = sum(all(dict(s.readings).get(p) == t for p, t in feat) for s in succ)
        return _balanced_accuracy(tp, len(fails), fp, len(succ)), len(fails), len(succ)

    def _induce(self, kind: str, action: str) -> Schema | None:
        rel_all = [s for s in self.samples if s.kind == kind and s.action == action and s.readings]
        existing = self.applicable(kind, action)

        def explained(smp: RoleSample) -> bool:
            rd = dict(smp.readings)
            return any(sc.matches(rd) for sc in existing)

        fails = [s for s in rel_all if s.failed and not explained(s)]
        if len(fails) < self.min_each:
            return None
        rel = fails + [s for s in rel_all if not s.failed]
        best: tuple[float, int, Feature] | None = None
        cands = self._candidate_features(rel)
        for size in (1, 2):
            for feat in (f for f in cands if len(f) == size):
                if (kind, feat) in self.retracted:
                    continue
                sc, _, _ = self._score(feat, rel)
                if sc >= self.min_score and (best is None or sc > best[0]):
                    best = (sc, -size, feat)
            if best is not None:
                break  # prefer the simplest sufficient observable
        if best is None:
            return None
        sid = f"schema_{kind}_{self._counter}"
        self._counter += 1
        sch = Schema(schema_id=sid, kind=kind, feature=best[2], score=best[0], induced_on=(action,))
        self.engine.register(sid)
        self.schemas[sid] = sch
        return sch

    # ---- validation ------------------------------------------------------
    def validate(self, sid: str, *, verified: bool, action: str) -> None:
        sch = self.schemas.get(sid)
        if sch is None:
            return
        if action not in sch.induced_on:
            # Transfer evidence is kept per target action: scope learning, not global blame.
            if verified:
                sch.applied_on.add(action)
                sch.transfer_ok[action] = sch.transfer_ok.get(action, 0) + 1
            else:
                sch.transfer_fail[action] = sch.transfer_fail.get(action, 0) + 1
            # Exclude only when failures dominate verified transfers (red-team T264 #2).
            fails, oks = sch.transfer_fail.get(action, 0), sch.transfer_ok.get(action, 0)
            if fails >= 2 and fails > 2 * oks:
                sch.excluded_on.add(action)
            elif action in sch.excluded_on and oks >= 2 * fails:
                sch.excluded_on.discard(action)
            return
        if verified:
            self.engine.promote(sid, confidence=0.9, source="schema_prediction_verified")
        else:
            self.engine.suppress(sid, confidence=0.9, source="schema_prediction_falsified")
        st = self.engine.state_of(sid)
        assert st is not None
        sch.promotion_count, sch.suppression_count = st.promotion_count, st.suppression_count
        sch.consolidated = st.consolidated
        if st.suppression_count >= self.retraction_suppressions and st.stability_ratio < 0.70:
            self._retract(sch)
        elif not verified:
            self._compete(sch)

    def _retract(self, sch: Schema) -> None:
        self.retracted.add((sch.kind, sch.feature))
        self.schemas.pop(sch.schema_id, None)

    def _compete(self, sch: Schema) -> None:
        """Hypothesis competition: replace a falsified schema by a clearly better feature."""
        for action in sch.induced_on:
            rel = [
                s for s in self.samples if s.kind == sch.kind and s.action == action and s.readings
            ]
            own, _, _ = self._score(sch.feature, rel)
            best = max(
                (
                    self._score(f, rel)[0]
                    for f in self._candidate_features(rel)
                    if f != sch.feature and (sch.kind, f) not in self.retracted
                ),
                default=0.0,
            )
            if best >= self.min_score and best >= own + 0.10:
                self._retract(sch)
                self._induce(sch.kind, action)
                return

    # ---- persistence -----------------------------------------------------
    def save(self, db: Path) -> int:
        conn = sqlite3.connect(str(db))
        conn.execute("CREATE TABLE IF NOT EXISTS t264_state (id INTEGER PRIMARY KEY, blob TEXT)")
        keep = [s.to_row() for s in self.schemas.values() if s.consolidated]
        blob = {
            "schemas": keep,
            "retracted": [[k, [list(x) for x in f]] for k, f in sorted(self.retracted)],
            "attempts": self.attempts,
            "counter": self._counter,
        }
        conn.execute(
            "INSERT OR REPLACE INTO t264_state (id, blob) VALUES (1, ?)", (json.dumps(blob),)
        )
        conn.commit()
        conn.close()
        return len(keep)

    def load(self, db: Path) -> int:
        if not db.exists():
            return 0
        conn = sqlite3.connect(str(db))
        try:
            row = conn.execute("SELECT blob FROM t264_state WHERE id = 1").fetchone()
        except sqlite3.OperationalError:
            row = None
        conn.close()
        if row is None:
            return 0
        blob = json.loads(row[0])
        for r in blob["schemas"]:
            sch = Schema(
                schema_id=r["schema_id"],
                kind=r["kind"],
                feature=tuple((str(p), str(t)) for p, t in r["feature"]),
                score=float(r["score"]),
                induced_on=tuple(r["induced_on"]),
                applied_on=set(r["applied_on"]),
                excluded_on=set(r.get("excluded_on", [])),
                transfer_fail={str(k): int(v) for k, v in r.get("transfer_fail", {}).items()},
                transfer_ok={str(k): int(v) for k, v in r.get("transfer_ok", {}).items()},
                promotion_count=int(r["promotion_count"]),
                suppression_count=int(r["suppression_count"]),
                consolidated=bool(r["consolidated"]),
            )
            st = self.engine.register(sch.schema_id)
            st.promotion_count, st.suppression_count = sch.promotion_count, sch.suppression_count
            st.consolidated = sch.consolidated
            self.schemas[sch.schema_id] = sch
        self.retracted = {(k, tuple((p, t) for p, t in f)) for k, f in blob["retracted"]}
        self.attempts = {k: list(v) for k, v in blob["attempts"].items()}
        self._counter = int(blob["counter"])
        return len(self.schemas)


# ----------------------------------------------------------------------
# Value-driven workspace
# ----------------------------------------------------------------------


@dataclass(frozen=True)
class Candidate:
    intent: str  # "act" | "probe"
    target: str
    value: float


def _entropy(p: float) -> float:
    p = min(max(p, 1e-6), 1 - 1e-6)
    return -(p * math.log2(p) + (1 - p) * math.log2(1 - p))


class ValueWorkspace:
    """Spike-gated arbitration over computed candidate values."""

    IDLE_COST = 0.15

    def __init__(
        self,
        *,
        initial_k: float = 2.0,
        adaptive_k: bool = True,
        value_mode: str = "computed",  # "computed" | "shuffled" | "constant"
        seed: int = 0,
        max_rss_mb: float = 250.0,
    ) -> None:
        self.k = initial_k
        self.adaptive_k = adaptive_k
        self.value_mode = value_mode
        self._rng = np.random.default_rng(seed)
        self.criticality = CriticalityController(target_sigma=1.0, kp=0.3, k_min=0.5, k_max=8.0)
        self.kill_switch = KillSwitch(default_stage1_seed_genome())
        self.guard = MemoryBudgetGuard(max_rss_mb=max_rss_mb, kill_switch=self.kill_switch)
        self.ignitions: list[int] = []
        self.idle_ticks = 0
        self.ticks = 0

    def _transform(self, cands: list[Candidate]) -> list[float]:
        vals = [c.value for c in cands]
        if self.value_mode == "shuffled":
            vals = list(self._rng.permutation(vals))
        elif self.value_mode == "constant":
            order = {"probe": 0.6, "act": 0.5}
            vals = [order[c.intent] for c in cands]
        return vals

    async def arbitrate(self, cands: list[Candidate]) -> Candidate | None:
        await asyncio.sleep(0)
        self.guard.check(context_state=f"T264_TICK_{self.ticks}")
        self.ticks += 1
        if not cands:
            self.idle_ticks += 1
            self.ignitions.append(0)
            return None
        vals = np.asarray(self._transform(cands), dtype=float)
        # Reference point is the value of waiting one tick (-IDLE_COST): only candidates
        # better than idling can ignite.
        drive = np.clip(vals + self.IDLE_COST, 0.0, None)
        spikes = dynamic_spikes(np.append(drive, 0.05), k=self.k).spikes[:-1]
        ignited = [i for i, s in enumerate(spikes) if s >= 1.0 and drive[i] > 0.0]
        self.ignitions.append(len(ignited))
        if self.adaptive_k:
            # Homeostasis on ignition: aim for exactly one ignited coalition per tick.
            n = len(ignited)
            # Homeostatic band [1, 3] ignited coalitions per tick.
            if n == 0:
                self.k = min(self.criticality.k_max, self.k * 1.5)
            elif n > 3:
                self.k = max(self.criticality.k_min, self.k / 1.1)
            # NB (T264 red team): the T248 controller output is not used to set k; the
            # homeostatic rule above does. Kept only as legacy telemetry.
            self.criticality.step(int(np.sum(np.abs(spikes))), self.k)
        if not ignited:
            self.idle_ticks += 1
            return None
        best = max(ignited, key=lambda i: (vals[i], -i))
        return cands[best]

    def telemetry(self) -> dict[str, Any]:
        mr = mr_branching_ratio(self.ignitions) if len(self.ignitions) >= 9 else None
        return {
            "ticks": self.ticks,
            "idle_ticks": self.idle_ticks,
            "final_k": round(self.k, 3),
            "mean_ignitions": float(np.mean(self.ignitions)) if self.ignitions else 0.0,
            "mr_m": None if mr is None or not mr.defined else round(mr.m, 3),
            "mr_reason": None if mr is None else mr.reason,
            "peak_rss_mb": round(self.guard.peak_rss_mb, 2),
        }


# ----------------------------------------------------------------------
# Agent
# ----------------------------------------------------------------------


@dataclass
class EpisodeResult:
    unit_id: str
    goal_reached: bool
    ticks: int
    idle_ticks: int
    failed_actuations: int
    probes: list[str]
    actions: list[str]
    applied_schemas: list[str]


class Stage2Agent:
    """Sandbox agent with value-driven workspace and role-abstract schema memory."""

    PROBE_COST = 0.08

    def __init__(
        self,
        actions: Sequence[GOAPAction],
        probes: Sequence[str],
        *,
        learner: SchemaLearner | None = None,
        workspace: ValueWorkspace | None = None,
        max_repeats: int = 3,
        blame_assignment: bool = True,
    ) -> None:
        self.actions = tuple(actions)
        self.probes = tuple(probes)
        self.learner = learner or SchemaLearner()
        self.ws = workspace or ValueWorkspace()
        self.max_repeats = max_repeats
        self.blame_assignment = blame_assignment
        self._by_name = {a.name: a for a in self.actions}

    @staticmethod
    def _majority(reads: list[str]) -> str | None:
        if not reads:
            return None
        vals, counts = np.unique(np.asarray(reads), return_counts=True)
        top = counts.max()
        winners = sorted(v for v, c in zip(vals, counts, strict=True) if c == top)
        return str(winners[0]) if len(winners) == 1 else None

    def _readings(self, raw: dict[str, list[str]]) -> dict[str, str]:
        out = {}
        for p, rs in raw.items():
            m = self._majority(rs)
            if m is not None:
                out[p] = m
        return out

    def _p_fail(self, a: GOAPAction, readings: dict[str, str]) -> tuple[float, list[str]]:
        group = alternative_group(a, self.actions)
        fired: list[str] = []
        p = self.learner.prior_fail(a.name)
        vetoed = False
        if len(group) >= 2 and group[0].name == a.name:
            for s in self.learner.applicable("block", a.name):
                if s.matches(readings):
                    fired.append(s.schema_id)
                elif all(pp in readings for pp, _ in s.feature):
                    vetoed = True
        if goal_relevant_restorable(a, self.actions):
            for s in self.learner.applicable("clobber", a.name):
                if all(pp in readings for pp, _ in s.feature) and not s.matches(readings):
                    vetoed = True
        # A matching schema always wins over a measured-but-silent one (red-team T264 bug a).
        if fired:
            best = max(self.learner.schemas[sid].consolidated for sid in fired)
            p = max(p, 0.9 if best else 0.75)
        elif vetoed:
            p = min(p, 0.15)
        return p, fired

    async def run_episode(self, twin: Any, *, max_ticks: int = 24) -> EpisodeResult:
        beliefs = frozenset(twin.surface_facts)
        goal = frozenset(twin.goal_facts)
        raw: dict[str, list[str]] = {}
        failed: set[str] = set()
        blocked: set[str] = set()
        applied: dict[str, str] = {}  # schema_id -> action it was applied to
        retracted_by: dict[str, str] = {}  # clobber schema -> fluent
        probes_run: list[str] = []
        acts: list[str] = []
        n_fail = 0
        first_attempts: dict[str, tuple[bool, dict[str, str]]] = {}
        surprise_probes: set[str] = set()
        t0, idle0 = self.ws.ticks, self.ws.idle_ticks

        for _ in range(max_ticks):
            if goal.issubset(twin.surface_facts):
                break
            readings = self._readings(raw)
            # clobber schemas: retract the restorable precondition before acting
            for a in self.actions:
                if not goal & a.add_effects:
                    continue
                f = restorable_precondition(a, self.actions)
                if f is None or f not in beliefs:
                    continue
                for s in self.learner.applicable("clobber", a.name):
                    if s.matches(readings) and s.schema_id not in retracted_by:
                        retracted_by[s.schema_id] = f
                        applied[s.schema_id] = a.name
                        beliefs = beliefs - {f}
            cands: list[Candidate] = []
            allowed = [a for a in self.actions if a.name not in failed | blocked]
            plan, _ = GOAPPlanner(allowed, simulate_only=True, max_expansions=64).plan_with_stats(
                beliefs, goal
            )
            if not plan and blocked:
                blocked.clear()  # schemas are advisory: with no alternative left, try anyway
                continue
            p_next = 0.0
            if plan:
                a = plan[0]
                p_next, fired = self._p_fail(a, readings)
                if fired and p_next >= 0.7:
                    for sid in fired:
                        applied[sid] = a.name
                    blocked.add(a.name)
                    continue  # schema blocks the action; replan without spending a tick
                ev = (1.0 - p_next) * 1.0 - 0.6 * p_next - 0.05 * a.cost
                cands.append(Candidate("act", a.name, ev))
            # Information value of probes. Normal regime: value of information
            # rel * (H(p_fail) + 1.6 * p_fail). After a prediction error: diagnostic drive.
            h = _entropy(p_next) if plan else 0.0
            feat_probes = {pp for sc in self.learner.schemas.values() for pp, _ in sc.feature}
            for p in self.probes:
                n = len(raw.get(p, []))
                rel = self.learner.probe_relevance(p)
                if p in surprise_probes:
                    if n == 0:
                        v = rel + 0.4 - self.PROBE_COST
                    elif n < self.max_repeats and p in feat_probes:
                        v = rel + 0.3 - self.PROBE_COST
                    else:
                        continue
                elif n == 0 and plan:
                    v = rel * (h + 1.6 * p_next) - self.PROBE_COST
                else:
                    continue
                cands.append(Candidate("probe", p, v))
            if plan and not any(c.intent == "probe" for c in cands):
                # Nothing left to learn here: acting dominates waiting.
                cands = [
                    Candidate(c.intent, c.target, max(c.value, 0.05)) if c.intent == "act" else c
                    for c in cands
                ]
            win = await self.ws.arbitrate(cands)
            if win is None:
                continue
            if win.intent == "probe":
                out = twin.execute_probe(win.target)
                probes_run.append(win.target)
                raw.setdefault(win.target, []).append(str(out.probe_token))
                if len(raw[win.target]) >= self.max_repeats:
                    surprise_probes.discard(win.target)
                continue
            act = self._by_name[win.target]
            out = twin.execute_actuation(act.name)
            acts.append(act.name)
            if act.name not in first_attempts:
                first_attempts[act.name] = (not out.succeeded, dict(readings))
            if out.succeeded:
                beliefs = frozenset(out.surface_facts)
                continue
            n_fail += 1
            if out.clobbered_facts:
                beliefs = frozenset(out.surface_facts)
            else:
                failed.add(act.name)
            # Prediction error: unread probes get a diagnostic drive; schema-feature
            # probes may be re-read (blame assignment between world and measurement).
            if self.blame_assignment:
                surprise_probes |= {
                    p for p in self.probes if len(raw.get(p, [])) < self.max_repeats
                }
            else:
                surprise_probes |= {p for p in self.probes if not raw.get(p)}

        goal_ok = goal.issubset(twin.surface_facts)
        final = self._readings(raw)

        # ---- learning: role samples from first attempts
        for name, (was_fail, _rd_at_attempt) in first_attempts.items():
            a = self._by_name[name]
            rd = dict(final)
            group = alternative_group(a, self.actions)
            if len(group) >= 2 and group[0].name == name:
                self.learner.record_attempt(name, was_fail)
                if rd:
                    self.learner.record_sample(
                        RoleSample("block", name, tuple(sorted(rd.items())), was_fail)
                    )
            elif goal & a.add_effects and restorable_precondition(a, self.actions):
                self.learner.record_attempt(name, was_fail)
                if rd:
                    self.learner.record_sample(
                        RoleSample("clobber", name, tuple(sorted(rd.items())), was_fail)
                    )
            else:
                self.learner.record_attempt(name, was_fail)
        # ---- validation of applied schemas (with blame assignment on final readings)
        for sid, target in applied.items():
            sch = self.learner.schemas.get(sid)
            if sch is None:
                continue
            ok = goal_ok and n_fail == 0
            if not ok and self.blame_assignment and not sch.matches(final):
                continue  # the feature was a mis-reading, not a wrong schema
            self.learner.validate(sid, verified=ok, action=target)
        # ---- two-sided evidence: an unapplied schema whose feature was measured makes a
        # prediction about the first attempt ("fails iff F"); score it either way.
        for name, (was_fail, _rd) in first_attempts.items():
            a = self._by_name[name]
            group = alternative_group(a, self.actions)
            if len(group) >= 2 and group[0].name == name:
                kind = "block"
            elif goal & a.add_effects and restorable_precondition(a, self.actions):
                kind = "clobber"
            else:
                continue
            for s in self.learner.applicable(kind, name):
                if s.schema_id in applied or not all(p in final for p, _ in s.feature):
                    continue
                self.learner.validate(
                    s.schema_id, verified=(s.matches(final) == was_fail), action=name
                )

        return EpisodeResult(
            unit_id=twin.unit_id,
            goal_reached=goal_ok,
            ticks=self.ws.ticks - t0,
            idle_ticks=self.ws.idle_ticks - idle0,
            failed_actuations=n_fail,
            probes=probes_run,
            actions=acts,
            applied_schemas=sorted(applied),
        )


def read_rss() -> float:
    return read_process_rss_mb()


if __name__ == "__main__":  # pragma: no cover
    print("use q_speace.vertical_slice.t264_agi_readiness_battery", file=sys.stderr)
