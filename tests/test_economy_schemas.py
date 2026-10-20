"""Schema validation tests for the q_speace_economy foundation (T6.1).

The 4 schemas in ``q_speace/economy/schemas/`` are JSON Schema
draft-2020-12 documents. They must:

1. parse as valid meta-schemas (Draft202012Validator.check_schema),
2. accept the canonical example payload for each primitive,
3. reject clearly malformed payloads.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "q_speace" / "economy" / "schemas"
SCHEMA_NAMES = ("j_c", "v", "cme", "dat")


@pytest.fixture(scope="module")
def validators() -> dict[str, Draft202012Validator]:
    out: dict[str, Draft202012Validator] = {}
    for name in SCHEMA_NAMES:
        path = SCHEMA_DIR / f"{name}.schema.json"
        with path.open(encoding="utf-8") as f:
            doc = json.load(f)
        out[name] = Draft202012Validator(doc)
    return out


@pytest.mark.parametrize("name", SCHEMA_NAMES)
def test_schema_is_well_formed(name: str) -> None:
    """Each schema must parse without raising SchemaError."""
    path = SCHEMA_DIR / f"{name}.schema.json"
    with path.open(encoding="utf-8") as f:
        doc = json.load(f)
    # check_schema returns None on success, raises on failure.
    Draft202012Validator.check_schema(doc)


def test_j_c_canonical_payload_accepted(validators: dict[str, Draft202012Validator]) -> None:
    payload = {
        "J": 12.5,
        "delta_S": -0.4,
        "delta_I_c": 8.0,
        "R_b": 0.7,
        "delta_C": 0.05,
        "confidence": 0.9,
    }
    errors = list(validators["j_c"].iter_errors(payload))
    assert errors == [], f"J_c canonical payload rejected: {[e.message for e in errors]}"


def test_v_canonical_payload_accepted(validators: dict[str, Draft202012Validator]) -> None:
    payload = {"E_x": 10.0, "S_gen": 0.3, "I_c": 5.0, "R_b": 0.6}
    errors = list(validators["v"].iter_errors(payload))
    assert errors == [], f"V canonical payload rejected: {[e.message for e in errors]}"


def test_cme_canonical_payload_accepted(validators: dict[str, Draft202012Validator]) -> None:
    payload = dict.fromkeys(
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
    errors = list(validators["cme"].iter_errors(payload))
    assert errors == [], f"CME canonical payload rejected: {[e.message for e in errors]}"


def test_dat_canonical_payload_accepted(validators: dict[str, Draft202012Validator]) -> None:
    payload = {
        "amount": 100.0,
        "bound_to": "positive-exergy-processes",
        "decay_half_life": 3600.0,
        "mint_time": 1.7e9,
    }
    errors = list(validators["dat"].iter_errors(payload))
    assert errors == [], f"DAT canonical payload rejected: {[e.message for e in errors]}"


def test_j_c_rejects_confidence_out_of_range(validators: dict[str, Draft202012Validator]) -> None:
    bad = {
        "J": 1.0,
        "delta_S": 0.0,
        "delta_I_c": 0.0,
        "R_b": 0.5,
        "delta_C": 0.0,
        "confidence": 1.5,
    }
    errors = list(validators["j_c"].iter_errors(bad))
    assert any(e.validator == "maximum" for e in errors), "confidence > 1 must error"


def test_cme_rejects_unknown_key(validators: dict[str, Draft202012Validator]) -> None:
    bad = dict.fromkeys(
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
    bad["unknown_capital"] = 0.1
    errors = list(validators["cme"].iter_errors(bad))
    assert any(e.validator == "additionalProperties" for e in errors)
