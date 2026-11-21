"""Independent contract and runtime tests for the isolated T228 bench."""

import asyncio
import json
import math
from dataclasses import replace
from pathlib import Path

import pytest

from q_speace.bcel.catalog import BCELCatalog
from q_speace.experiments.error_memory import (
    BenchConfig,
    digest,
    experience,
    repair,
    rollout,
    run,
    search,
)
from q_speace.experiments.error_memory_verifier import replay, verify


def test_verifier_valid_invalid_and_numeric_boundary() -> None:
    assert verify(0.875).status == "VALIDA"
    bad = verify(0.5)
    assert bad.status == "INVALIDA"
    assert bad.witness is not None
    assert replay(0.5, bad.witness)["violated"]
    assert verify(0.75).status == "VALIDA"
    assert verify(math.nextafter(0.75, 0.0)).status == "INVALIDA"
    assert verify(math.nextafter(0.75, 1.0)).status == "VALIDA"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -0.1, 0.0, 1.0, 1.1])
def test_outside_model_is_indeterminate(value: float) -> None:
    assert verify(value).status == "INDETERMINATA"


def test_memory_repairs_new_candidate_and_is_frozen() -> None:
    memory = experience()
    before = repr(memory)
    witness = memory[0].witness
    assert verify(repair(0.432123, witness)).status == "VALIDA"
    a = search(12, (), 2)
    b = search(12, memory, 2)
    assert a["traces"][0]["raw"] == b["traces"][0]["raw"]
    assert b["traces"][0]["retrieved"] == memory[0].entry_id
    assert b["first_valid"]
    assert repr(memory) == before
    assert a["raw_count"] <= 2 and b["raw_count"] <= 2
    assert search(12, (), 0)["exhausted"]


def test_real_tick_state_and_function_distinguish_near_frozen() -> None:
    config = BenchConfig()
    adaptive = asyncio.run(rollout(0.8, "step", 1, config))
    frozen = asyncio.run(rollout(math.nextafter(1.0, 0.0), "step", 1, config))
    assert adaptive["ticks"][0]["ema"] != [1.0, 1.0]
    assert all(t["approved"] for t in adaptive["ticks"])
    assert adaptive["recovered"]
    assert not frozen["recovered"]
    assert adaptive["final_tv"] < frozen["final_tv"]
    assert BCELCatalog().is_functional("Counterexample memory for plasticity (T228)")


def test_counterexample_replays_actual_update_and_correction() -> None:
    for entry in experience():
        assert entry.replayed["violated"]
        assert entry.replayed["model_gap"] <= 8 * math.ulp(1.0)
        assert verify(entry.corrected).status == "VALIDA"


def test_preregistration_pairing_fallback_and_no_overwrite(tmp_path: Path) -> None:
    config = replace(BenchConfig(), episodes_per_family=1, raw_budget=0)
    destination = tmp_path / "run"
    asyncio.run(run(destination, config))
    prereg = json.loads((destination / "preregistration.json").read_text())
    assert prereg["evaluation_started"] is False
    assert prereg["config_sha256"] == digest(json.loads((destination / "config.json").read_text()))
    assert prereg["memory_sha256"] == digest(
        json.loads((destination / "frozen_memory.json").read_text())
    )
    rows = [json.loads(line) for line in (destination / "episodes.jsonl").read_text().splitlines()]
    for family in ("step", "pulse"):
        a, b = [r for r in rows if r["family"] == family and r["condition"] in ("A", "B")]
        assert a["snapshot"] == b["snapshot"]
        assert a["perturbation_seed"] == b["perturbation_seed"]
        assert a["ticks"] == b["ticks"]
        assert a["exhausted"] and b["exhausted"]
        assert a["decay"] == b["decay"] == config.default_decay
    with pytest.raises(FileExistsError):
        asyncio.run(run(destination, config))
