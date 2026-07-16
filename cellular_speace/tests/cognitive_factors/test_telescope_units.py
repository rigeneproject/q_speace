"""Unit tests for the 10 cognitive-factor probes.

Each probe returns a dict with the keys defined in T172 §3:
    {value, healthy_range, tag, module, ...}
This suite asserts that each probe responds to a minimal live state and
returns the *expected structural shape*.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "print_cognitive_telescope.py"

FACTOR_KEYS = {
    "wm",
    "speed",
    "pattern",
    "knowledge",
    "abstraction",
    "relational",
    "metacognition",
    "attention",
    "motivation",
    "flexibility",
}


@pytest.fixture(scope="module")
def snapshot() -> dict:
    return {
        k: v
        for k, v in _run_cli().get("factors", {}).items()
    }


def _run_cli() -> dict:
    out = subprocess.check_output(
        [sys.executable, str(SCRIPT), "--format", "json"],
        cwd=str(REPO_ROOT),
    )
    return json.loads(out.decode("utf-8"))


# --------------------------------------------------------------------------- #
# Script smoke
# --------------------------------------------------------------------------- #


def test_telescope_script_returns_ten_factors():
    snapshot = _run_cli()
    assert set(snapshot["factors"].keys()) == FACTOR_KEYS, (
        f"expected 10 factors, got {sorted(snapshot['factors'].keys())}"
    )


def test_telescope_script_has_timestamp():
    snapshot = _run_cli()
    assert "timestamp" in snapshot
    assert isinstance(snapshot["timestamp"], float)


# --------------------------------------------------------------------------- #
# Each factor has the expected shape
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "factor",
    sorted(FACTOR_KEYS),
)
def test_factor_shape(factor, snapshot):
    payload = snapshot[factor]
    assert "value" in payload, f"{factor}: missing 'value'"
    assert "healthy_range" in payload, f"{factor}: missing 'healthy_range'"
    assert "tag" in payload, f"{factor}: missing 'tag'"
    lo, hi = payload["healthy_range"]
    assert lo <= hi, f"{factor}: invalid healthy_range {payload['healthy_range']}"
    assert payload["tag"].startswith("cognitive_factor:"), (
        f"{factor}: tag must begin with 'cognitive_factor:'"
    )


@pytest.mark.parametrize(
    "factor",
    sorted(FACTOR_KEYS),
)
def test_factor_value_is_numeric(factor, snapshot):
    payload = snapshot[factor]
    assert isinstance(payload["value"], (int, float)), (
        f"{factor}: value must be numeric, got {type(payload['value']).__name__}"
    )


# --------------------------------------------------------------------------- #
# Each factor names its (real) producing module
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "factor, expected_substring",
    [
        ("wm", "subgrid_attention_working_memory"),
        ("speed", "cognitive_cost_model"),
        ("pattern", "concept_graph"),
        ("knowledge", "semantic_memory_store"),
        ("abstraction", "hierarchical_concept_abstraction_layer"),
        ("relational", "temporal_causal_reasoning_layer"),
        ("metacognition", "metacognitive_monitor"),
        ("attention", "thalamic_relay_engine"),
        ("motivation", "autonomous_drives"),
        ("flexibility", "mmapr_council"),
    ],
)
def test_factor_module_path_is_real(factor, expected_substring, snapshot):
    payload = snapshot[factor]
    assert expected_substring in payload.get("module", ""), (
        f"{factor}: module path does not contain '{expected_substring}', "
        f"got {payload.get('module')!r}"
    )


# --------------------------------------------------------------------------- #
# The motivation probe is the only one that has live data at smoke time.
# --------------------------------------------------------------------------- #


def test_motivation_value_loaded_from_yaml(snapshot):
    motivation = snapshot["motivation"]
    # The autonomous_drives.yaml has 7 drives with setpoints in [0,1].
    assert "setpoints" in motivation
    assert len(motivation["setpoints"]) == 7
    for name, sp in motivation["setpoints"].items():
        assert 0.0 <= sp <= 1.0, f"{name}: setpoint out of range"


# --------------------------------------------------------------------------- #
# The script must be runnable repeatedly without state leaks.
# --------------------------------------------------------------------------- #


def test_repeatable_run():
    snap1 = _run_cli()
    snap2 = _run_cli()
    # The 10 factor values are deterministic (no live organism), only the
    # timestamp changes.
    for f in FACTOR_KEYS:
        assert snap1["factors"][f]["value"] == snap2["factors"][f]["value"], (
            f"{f}: non-deterministic between runs"
        )