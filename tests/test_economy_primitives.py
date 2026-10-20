"""Tests for the q_speace_economy primitives module (T6.2)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from jsonschema import Draft202012Validator

from q_speace.economy.primitives import CME, J_c, V

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "q_speace" / "economy" / "schemas"


# ---------------------------------------------------------------------------
# J_c
# ---------------------------------------------------------------------------


def test_jc_constructor_accepts_canonical() -> None:
    j = J_c(J=10.0, delta_S=-0.5, delta_I_c=4.0, R_b=0.6, delta_C=0.1, confidence=0.9)
    assert j.J == 10.0
    assert j.confidence == 0.9


@pytest.mark.parametrize(
    "kw",
    [
        {"J": -1.0},
        {"delta_S": 0.1},
        {"delta_I_c": -0.1},
        {"R_b": 1.5},
        {"delta_C": 1.5},
        {"confidence": -0.1},
    ],
)
def test_jc_rejects_out_of_range(kw: dict[str, float]) -> None:
    base = {
        "J": 1.0,
        "delta_S": -0.1,
        "delta_I_c": 1.0,
        "R_b": 0.5,
        "delta_C": 0.0,
        "confidence": 0.5,
    }
    base.update(kw)
    with pytest.raises(ValueError):
        J_c(**base)


def test_jc_from_telemetry_computes_confidence() -> None:
    j = J_c.from_telemetry(
        J=5.0,
        delta_S=-0.2,
        delta_I_c=2.0,
        R_b=0.4,
        delta_C=0.0,
        measured_components=3,
        total_components=5,
    )
    assert j.confidence == pytest.approx(0.6)
    assert j.metadata == {}


def test_jc_to_dict_matches_schema() -> None:
    j = J_c.from_telemetry(
        J=2.0, delta_S=-0.1, delta_I_c=1.0, R_b=0.3, delta_C=0.05, measured_components=5
    )
    with (SCHEMA_DIR / "j_c.schema.json").open(encoding="utf-8") as f:
        validator = Draft202012Validator(json.load(f))
    assert not list(validator.iter_errors(j.to_dict()))


# ---------------------------------------------------------------------------
# V
# ---------------------------------------------------------------------------


def test_v_constructor_4_components() -> None:
    v = V(E_x=1.0, S_gen=0.2, I_c=0.5, R_b=0.7)
    assert v.n_components == 4
    np.testing.assert_array_equal(v.as_array(), [1.0, 0.2, 0.5, 0.7])


def test_v_constructor_5_components() -> None:
    v = V(E_x=1.0, S_gen=0.2, I_c=0.5, R_b=0.7, coherence_phi=0.9)
    assert v.n_components == 5


@pytest.mark.parametrize("kw", [{"E_x": -0.1}, {"S_gen": -0.1}, {"R_b": 1.1}])
def test_v_rejects_invalid(kw: dict[str, float]) -> None:
    base = {"E_x": 1.0, "S_gen": 0.2, "I_c": 0.5, "R_b": 0.7}
    base.update(kw)
    with pytest.raises(ValueError):
        V(**base)


def test_v_to_dict_matches_schema() -> None:
    v = V(E_x=1.0, S_gen=0.2, I_c=0.5, R_b=0.7, coherence_phi=0.9)
    with (SCHEMA_DIR / "v.schema.json").open(encoding="utf-8") as f:
        validator = Draft202012Validator(json.load(f))
    assert not list(validator.iter_errors(v.to_dict()))


# ---------------------------------------------------------------------------
# CME
# ---------------------------------------------------------------------------


def test_cme_canonical() -> None:
    c = CME(
        energy=0.5,
        matter=0.5,
        information=0.5,
        time=0.5,
        ecology=0.5,
        resilience=0.5,
        wellbeing=0.5,
        innovation=0.5,
        reversibility=0.5,
        distribution=0.5,
        coherence=0.5,
        regeneration=0.5,
    )
    assert c.as_array().shape == (12,)
    assert all(0.0 <= x <= 1.0 for x in c.as_array())


def test_cme_rejects_out_of_range() -> None:
    base = {
        "energy": 0.5,
        "matter": 0.5,
        "information": 0.5,
        "time": 0.5,
        "ecology": 0.5,
        "resilience": 0.5,
        "wellbeing": 0.5,
        "innovation": 0.5,
        "reversibility": 0.5,
        "distribution": 0.5,
        "coherence": 0.5,
        "regeneration": 0.5,
    }
    base["energy"] = 1.5
    with pytest.raises(ValueError):
        CME(**base)


def test_cme_weak_axes() -> None:
    c = CME(
        energy=0.1,
        matter=0.9,
        information=0.15,
        time=0.5,
        ecology=0.5,
        resilience=0.5,
        wellbeing=0.5,
        innovation=0.5,
        reversibility=0.5,
        distribution=0.5,
        coherence=0.5,
        regeneration=0.5,
    )
    weak = c.weak_axes(threshold=0.2)
    assert set(weak) == {"energy", "information"}


def test_cme_to_dict_matches_schema() -> None:
    c = CME(
        energy=0.5,
        matter=0.5,
        information=0.5,
        time=0.5,
        ecology=0.5,
        resilience=0.5,
        wellbeing=0.5,
        innovation=0.5,
        reversibility=0.5,
        distribution=0.5,
        coherence=0.5,
        regeneration=0.5,
    )
    with (SCHEMA_DIR / "cme.schema.json").open(encoding="utf-8") as f:
        validator = Draft202012Validator(json.load(f))
    assert not list(validator.iter_errors(c.to_dict()))
