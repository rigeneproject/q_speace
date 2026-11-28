"""T264 — Stage-2 cortex: MR criticality, role-abstract schemas, scope learning, persistence."""

from __future__ import annotations

import asyncio
from pathlib import Path

import numpy as np

from q_speace.bridge.stage2_cortex import (
    Candidate,
    RoleSample,
    SchemaLearner,
    ValueWorkspace,
)
from q_speace.spiking.criticality_mr import driven_branching_process, mr_branching_ratio
from q_speace.vertical_slice import t264_agi_readiness_battery as bat


def test_mr_estimator_separates_regimes_where_ratio_estimator_cannot() -> None:
    assert abs(mr_branching_ratio(driven_branching_process(0.9, n=2000, seed=1)).m - 0.9) < 0.1
    assert mr_branching_ratio(driven_branching_process(1.3, n=30, seed=1)).m > 1.1
    assert mr_branching_ratio(np.random.default_rng(0).poisson(4, 300)).m < 0.2
    assert mr_branching_ratio([5] * 100).defined is False


def _samples(feature_hits: list[tuple[bool, dict[str, str]]]) -> list[RoleSample]:
    return [
        RoleSample("block", "act_x", tuple(sorted(rd.items())), failed)
        for failed, rd in feature_hits
    ]


def test_learner_constructs_conjunction_when_no_single_probe_discriminates() -> None:
    lr = SchemaLearner()
    data = [
        (True, {"a": "1", "b": "1"}),
        (True, {"a": "1", "b": "1"}),
        (True, {"a": "1", "b": "1"}),
        (False, {"a": "1", "b": "0"}),
        (False, {"a": "0", "b": "1"}),
        (False, {"a": "1", "b": "0"}),
        (False, {"a": "0", "b": "1"}),
    ]
    sch = None
    for s in _samples(data):
        sch = lr.record_sample(s) or sch
    assert sch is not None and sch.feature == (("a", "1"), ("b", "1"))
    off = SchemaLearner(allow_conjunctions=False)
    for s in _samples(data):
        assert off.record_sample(s) is None


def test_transfer_failures_shrink_scope_instead_of_global_suppression() -> None:
    lr = SchemaLearner()
    for s in _samples(
        [
            (True, {"a": "1"}),
            (True, {"a": "1"}),
            (False, {"a": "0"}),
            (False, {"a": "0"}),
            (True, {"a": "1"}),
            (False, {"a": "0"}),
        ]
    ):
        lr.record_sample(s)
    (sid,) = lr.schemas
    lr.validate(sid, verified=False, action="other_device_action")
    lr.validate(sid, verified=False, action="other_device_action")
    sch = lr.schemas[sid]
    assert "other_device_action" in sch.excluded_on
    assert sch.suppression_count == 0
    assert lr.applicable("block", "other_device_action") == []
    assert lr.applicable("block", "act_x") == [sch]


def test_schema_persistence_roundtrip_keeps_lifecycle_counters(tmp_path: Path) -> None:
    lr = SchemaLearner()
    for s in _samples(
        [
            (True, {"a": "1"}),
            (True, {"a": "1"}),
            (True, {"a": "1"}),
            (False, {"a": "0"}),
            (False, {"a": "0"}),
            (False, {"a": "0"}),
        ]
    ):
        lr.record_sample(s)
    (sid,) = lr.schemas
    for _ in range(3):
        lr.validate(sid, verified=True, action="act_x")
    assert lr.schemas[sid].consolidated
    db = tmp_path / "t264.db"
    assert lr.save(db) == 1
    lr2 = SchemaLearner()
    assert lr2.load(db) == 1
    lr2.validate(sid, verified=True, action="act_x")  # must not de-consolidate (T263-1 class)
    assert lr2.schemas[sid].consolidated and lr2.schemas[sid].promotion_count == 4


def test_workspace_idles_only_when_nothing_beats_waiting() -> None:
    ws = ValueWorkspace()
    win = asyncio.run(ws.arbitrate([Candidate("act", "x", -0.05), Candidate("probe", "p", -0.5)]))
    assert win is not None and win.target == "x"
    assert asyncio.run(ws.arbitrate([Candidate("probe", "p", -0.5)])) is None
    assert ws.idle_ticks == 1


def test_role_schema_transfers_to_unseen_device_class() -> None:
    mem = bat.make_agent(seed=0)
    bat._train(mem, 7)

    def test() -> list[bat.GenericTwin]:
        return [bat.GenericTwin(f"pump_{i}", "pump", True, seed=900 + i) for i in range(3)]

    with_mem = bat.run(mem, test())
    amnesic = bat.run(bat.make_agent(seed=0), test())
    assert with_mem["failed"] < amnesic["failed"]
