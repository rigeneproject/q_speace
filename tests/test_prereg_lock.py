"""Tests for the T222 deterministic prereg section lock."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from q_speace.spiking import (
    canonical_json,
    compute_lock_sha256,
    lock_section,
    verify_lock,
)


def test_prereg_declares_the_implemented_locking_protocol() -> None:
    path = Path(__file__).resolve().parents[1] / "docs" / "T222_PREREG.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    protocol = data["locking_protocol"]
    assert protocol["algorithm"] == "sha256"
    assert protocol["encoding"] == "utf-8 without BOM"
    assert protocol["excluded_fields"] == ["lock_sha256"]
    assert protocol["excluded_scope"] == "top-level only"
    assert data["pre_calibration"]["locked"] is False
    assert data["pre_evaluation"]["locked"] is False
    assert data["heldout"]["state"] == "sealed"


def test_canonical_json_sorts_keys_and_uses_compact_separators() -> None:
    assert canonical_json({"b": 1, "a": 2}) == '{"a":2,"b":1}'


def test_canonical_json_is_utf8_friendly() -> None:
    assert canonical_json({"key": "perché"}) == '{"key":"perché"}'


def test_lock_digest_excludes_only_the_hash_field() -> None:
    first: dict[str, Any] = {"locked": True, "value": 1, "lock_sha256": "a" * 64}
    second: dict[str, Any] = {"locked": True, "value": 1, "lock_sha256": "b" * 64}
    assert compute_lock_sha256(first) == compute_lock_sha256(second)


def test_nested_fields_participate_in_the_digest() -> None:
    first = {"locked": True, "nested": {"value": 1}, "lock_sha256": None}
    second = {"locked": True, "nested": {"value": 2}, "lock_sha256": None}
    assert compute_lock_sha256(first) != compute_lock_sha256(second)


def test_lock_section_sets_flag_and_verifies() -> None:
    locked = lock_section({"value": 1, "locked": False})
    assert locked["locked"] is True
    assert isinstance(locked["lock_sha256"], str)
    assert len(locked["lock_sha256"]) == 64
    assert verify_lock(locked)


def test_lock_section_does_not_mutate_input() -> None:
    original = {"value": 1, "locked": False}
    lock_section(original)
    assert original == {"value": 1, "locked": False}


def test_tampering_is_detected() -> None:
    locked = lock_section({"value": 1, "locked": False})
    tampered = dict(locked)
    tampered["value"] = 2
    assert not verify_lock(tampered)


def test_missing_or_malformed_hash_is_not_verified() -> None:
    assert not verify_lock({"value": 1})
    assert not verify_lock({"value": 1, "lock_sha256": "too-short"})


def test_lock_is_stable_across_key_insertion_order() -> None:
    first = lock_section({"alpha": 1, "beta": {"x": 2, "y": 3}})
    second = lock_section({"beta": {"y": 3, "x": 2}, "alpha": 1})
    assert first["lock_sha256"] == second["lock_sha256"]
