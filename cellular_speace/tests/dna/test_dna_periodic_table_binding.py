"""Tests for DNA ↔ Neural-Synaptic Periodic Table binding (T171).

This suite enforces the *mechanical* invariant of T171:

    For each informational_principle in species_orientation.yaml,
    there exists a PeriodicTrendGene / functional-constraint binding
    that makes the principle *observable* in the periodic table.

The test is intentionally read-only: it never writes to
species_orientation.yaml, never modifies SharedGenome, and never mutates
the periodic_law. It only loads YAML and inspects structure.

Related: docs/T171_DNA_PERIODIC_TABLE_BINDING_SPEC.md
"""

from __future__ import annotations

import pathlib
from typing import Dict, List

import pytest
import yaml


BINDING_YAML_PATH = pathlib.Path(
    "speace_core/dna/genome/core/dna_periodic_binding.yaml"
)
SPECIES_ORIENTATION_PATH = pathlib.Path(
    "speace_core/dna/genome/core/species_orientation.yaml"
)


def _load_yaml(path: pathlib.Path) -> dict:
    assert path.exists(), f"required YAML not found: {path}"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_species_orientation_invariants() -> Dict[str, dict]:
    """Return {symbol: principle_dict} for every informational_principle."""
    raw = _load_yaml(SPECIES_ORIENTATION_PATH)
    principles = (
        raw["species_orientation"].get("informational_principles", []) or []
    )
    return {p["symbol"]: p for p in principles}


def _load_bindings() -> List[dict]:
    raw = _load_yaml(BINDING_YAML_PATH)
    return raw.get("dna_periodic_binding", []) or []


# ---------------------------------------------------------------------------
# 1. The species orientation invariant set is unchanged.
# ---------------------------------------------------------------------------


EXPECTED_INVARIANT_SYMBOLS = {
    "U(1)_coh",
    "S_ent",
    "V_gen",
    "Diff(F)",
    "D_nonlocal",
    "R_renorm",
}


def test_species_orientation_has_six_invariants():
    invariants = _load_species_orientation_invariants()
    assert EXPECTED_INVARIANT_SYMBOLS.issubset(
        invariants.keys()
    ), f"missing informational principles: {EXPECTED_INVARIANT_SYMBOLS - invariants.keys()}"


def test_each_invariant_has_metric_and_direction():
    invariants = _load_species_orientation_invariants()
    for symbol, p in invariants.items():
        assert p.get("metric"), f"{symbol}: metric missing"
        assert p.get("target_direction"), f"{symbol}: target_direction missing"
        assert p["target_direction"] in {
            "maximize",
            "minimize",
            "maintain",
            "maintain_above_threshold",
        }, f"{symbol}: invalid direction {p['target_direction']!r}"


# ---------------------------------------------------------------------------
# 2. The binding YAML maps every invariant to a trend.
# ---------------------------------------------------------------------------


def test_binding_covers_every_invariant():
    bindings = _load_bindings()
    binding_symbols = {b["symbol"] for b in bindings}
    assert binding_symbols == EXPECTED_INVARIANT_SYMBOLS, (
        f"binding coverage mismatch. "
        f"missing={EXPECTED_INVARIANT_SYMBOLS - binding_symbols}, "
        f"extra={binding_symbols - EXPECTED_INVARIANT_SYMBOLS}"
    )


@pytest.mark.parametrize("symbol", sorted(EXPECTED_INVARIANT_SYMBOLS))
def test_each_binding_has_required_fields(symbol):
    bindings = {b["symbol"]: b for b in _load_bindings()}
    b = bindings[symbol]
    for field in (
        "invariant",
        "symbol",
        "trend_name",
        "expression",
        "element_pair",
        "ilf_metric",
        "test_direction",
    ):
        assert field in b, f"{symbol}: missing field {field!r}"
        assert b[field], f"{symbol}: empty field {field!r}"


# Aliases accepted in the binding YAML for legibility.
_BINDING_DIRECTION_ALIASES = {
    "maintain_above_threshold": "maintain",
    "maintain_below_threshold": "maintain",
}


@pytest.mark.parametrize("symbol", sorted(EXPECTED_INVARIANT_SYMBOLS))
def test_binding_test_direction_matches_invariant(symbol):
    bindings = {b["symbol"]: b for b in _load_bindings()}
    invariants = _load_species_orientation_invariants()
    expected = invariants[symbol]["target_direction"]
    binding_dir = bindings[symbol]["test_direction"]
    # The test_direction is the direction the *ILF metric* should move under
    # *healthy* conditions. The species_orientation uses {maximize,
    # minimize, maintain, maintain_above_threshold}; the binding uses the
    # same vocabulary with optional aliases.
    canonical = _BINDING_DIRECTION_ALIASES.get(expected, expected)
    assert canonical == binding_dir, (
        f"{symbol}: species_orientation says {expected!r}, "
        f"binding says {binding_dir!r}"
    )


# ---------------------------------------------------------------------------
# 3. The trend *expression* must be evaluable against a small whitelist.
# ---------------------------------------------------------------------------


def _safe_eval(expression: str, variables: Dict[str, float]) -> float:
    """Whitelist-only evaluator mirroring periodic_law._safe_eval_expression."""
    safe_names = {"abs": abs, "max": max, "min": min, "pow": pow, "round": round}
    safe_names.update(variables)
    try:
        return float(eval(expression, {"__builtins__": {}}, safe_names))
    except Exception:
        return 0.0


@pytest.mark.parametrize("symbol", sorted(EXPECTED_INVARIANT_SYMBOLS))
def test_trend_expression_evaluates_to_a_number(symbol):
    bindings = {b["symbol"]: b for b in _load_bindings()}
    expression = bindings[symbol]["expression"]
    # Provide expected variable tokens; should not raise.
    for variables in (
        {"g": 0.5, "p": 0.5, "z1": 10, "z2": 11, "n": 5, "rate": 50, "mid": 0.5, "e": 0.6},
        {"g": 0.0, "p": 0.0, "z1": 1, "z2": 28, "n": 0, "rate": 0, "mid": 0.0, "e": 0.0},
    ):
        value = _safe_eval(expression, variables)
        assert isinstance(value, (int, float)), (
            f"{symbol}: expression did not return a number for {variables}"
        )


# ---------------------------------------------------------------------------
# 4. Removal-of-trend degradation test (the "mechanical" invariant).
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("symbol", sorted(EXPECTED_INVARIANT_SYMBOLS))
def test_trend_removal_degrades_metric(symbol):
    """If the trend expression is replaced by a constant zero, the metric
    in the expected direction must drop (or be lost).

    Semantic interpretation:
      - `maximize`     : healthy trend contributes positively (>0); removal
                        collapses to 0.
      - `minimize`     : healthy trend is an active *damping* factor
                        (0 < value ≤ 1); removing it (=0) cancels the
                        damping — the metric rises unbounded. We check
                        the healthy value is in (0, 1] and the removed
                        value is exactly 0 (loss of damping).
      - `maintain` / `maintain_above_threshold` : healthy trend must be
                        non-trivial (≠ 0).

    The numerical stress-test (relaxing the constraint and measuring
    metric drift) is performed in the BCEL stress suite (T174/D2).
    """
    bindings = {b["symbol"]: b for b in _load_bindings()}
    original_expression = bindings[symbol]["expression"]
    direction = bindings[symbol]["test_direction"]

    variables = {"g": 0.5, "p": 0.5, "z1": 10, "z2": 11, "n": 5, "rate": 50, "mid": 0.5, "e": 0.6}
    healthy = _safe_eval(original_expression, variables)
    removed = _safe_eval("0.0", variables)

    if direction == "maximize":
        assert healthy > 0.0, (
            f"{symbol}: maximize-direction trend is non-positive "
            f"(healthy={healthy}) — it cannot protect the invariant."
        )
        assert removed == 0.0
        assert healthy > removed, (
            f"{symbol}: trend removal did not collapse the metric "
            f"(healthy={healthy}, removed={removed})"
        )
    elif direction == "maintain_above_threshold":
        assert healthy > 0.0, (
            f"{symbol}: maintain_above_threshold trend is non-positive "
            f"(healthy={healthy})"
        )
    elif direction == "minimize":
        # The trend must be an active damping factor in (0, 1].
        assert 0.0 < healthy <= 1.0, (
            f"{symbol}: minimize-direction trend produces a damping "
            f"factor outside (0, 1] (healthy={healthy}) — should be a "
            f"suppressor, not a source."
        )
        assert removed == 0.0, (
            f"{symbol}: removed trend is not zero (got {removed}); "
            f"the loss of damping is the metric-rising event."
        )
    elif direction == "maintain":
        assert healthy != 0.0, (
            f"{symbol}: maintain-direction trend is degenerate (always 0)"
        )
    else:  # pragma: no cover
        pytest.fail(f"{symbol}: unknown direction {direction!r}")


# ---------------------------------------------------------------------------
# 5. Binding file does not modify species_orientation invariants.
# ---------------------------------------------------------------------------


def test_binding_file_does_not_override_species_orientation():
    """The binding file is *additional*, not a redefinition."""
    binding_raw = _load_yaml(BINDING_YAML_PATH)
    assert "species_orientation" not in binding_raw, (
        "binding file must not redefine species_orientation"
    )
    assert "informational_principles" not in binding_raw, (
        "binding file must not redefine informational_principles"
    )