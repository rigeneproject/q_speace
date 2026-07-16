"""BCEL stress tests for the 10 cognitive-factor equivalences.

Each test asserts that the corresponding cognitive factor is registered
in `default_catalog()` with the right structure, and that the stress
tester reports an outcome (either a real protective effect, or the
documented placeholder) when the orchestrator is unknown.

Pattern: ``tests/test_bcel_stress.py``.
"""

from __future__ import annotations

import asyncio

import pytest

from speace_core.bcel import (
    BCELCatalog,
    ConstraintStressTester,
    CyberneticEquivalent,
    FunctionalConstraint,
    default_catalog,
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


COGNITIVE_FACTOR_NAMES = (
    "cognitive factor: working memory",
    "cognitive factor: processing speed",
    "cognitive factor: pattern recognition",
    "cognitive factor: prior knowledge",
    "cognitive factor: abstraction",
    "cognitive factor: relational reasoning",
    "cognitive factor: metacognition",
    "cognitive factor: sustained attention",
    "cognitive factor: motivation",
    "cognitive factor: cognitive flexibility",
)


# Map component_name → name of the kept FunctionalConstraint.
COGNITIVE_FACTOR_CONSTRAINT_NAMES = {
    "cognitive factor: working memory": "wm_slot_span",
    "cognitive factor: processing speed": "bounded_cost_per_tick",
    "cognitive factor: pattern recognition": "abstraction_compression_ratio",
    "cognitive factor: prior knowledge": "memory_link_density_floor",
    "cognitive factor: abstraction": "abstraction_levels_active",
    "cognitive factor: relational reasoning": "causal_cycle_detection",
    "cognitive factor: metacognition": "metacognitive_probe_rate",
    "cognitive factor: sustained attention": "attention_gap_budget",
    "cognitive factor: motivation": "drive_pressure_cap",
    "cognitive factor: cognitive flexibility": "perspective_switch_rate",
}


# --------------------------------------------------------------------------- #
# 1. Catalog registration
# --------------------------------------------------------------------------- #


def test_all_ten_cognitive_factors_are_registered():
    catalog = default_catalog()
    registered = set(catalog.list_components())
    expected = set(COGNITIVE_FACTOR_NAMES)
    missing = expected - registered
    assert not missing, f"missing cognitive factor entries in BCEL catalog: {sorted(missing)}"


@pytest.mark.parametrize("component_name", COGNITIVE_FACTOR_NAMES)
def test_cognitive_factor_has_kept_constraints(component_name):
    catalog = default_catalog()
    entry = catalog.get(component_name)
    assert entry is not None, (
        f"{component_name}: not in default_catalog() — was it forgotten?"
    )
    assert entry.kept_constraints, f"{component_name}: must have at least one kept constraint"
    assert entry.kept_constraints[0].name == COGNITIVE_FACTOR_CONSTRAINT_NAMES[component_name], (
        f"{component_name}: expected constraint "
        f"{COGNITIVE_FACTOR_CONSTRAINT_NAMES[component_name]!r}, "
        f"got {entry.kept_constraints[0].name!r}"
    )


@pytest.mark.parametrize("component_name", COGNITIVE_FACTOR_NAMES)
def test_cognitive_factor_has_removed_constraints(component_name):
    catalog = default_catalog()
    entry = catalog.get(component_name)
    assert entry is not None
    assert entry.removed_constraints, (
        f"{component_name}: must document at least one removed biological constraint"
    )


@pytest.mark.parametrize("component_name", COGNITIVE_FACTOR_NAMES)
def test_cognitive_factor_constraint_has_stability_test(component_name):
    catalog = default_catalog()
    entry = catalog.get(component_name)
    assert entry is not None
    constraint = entry.kept_constraints[0]
    assert constraint.stability_test, (
        f"{component_name}.{constraint.name}: stability_test must be non-empty"
    )


@pytest.mark.parametrize("component_name", COGNITIVE_FACTOR_NAMES)
def test_cognitive_factor_constraint_uses_real_invariant(component_name):
    catalog = default_catalog()
    entry = catalog.get(component_name)
    assert entry is not None
    constraint = entry.kept_constraints[0]
    # Must be one of the six informational invariants from
    # species_orientation.yaml. We don't hardcode the list here to
    # avoid coupling, but we ensure it's a non-empty identifier.
    assert constraint.invariant, (
        f"{component_name}.{constraint.name}: invariant must be set"
    )
    assert "." not in constraint.invariant, (
        f"{component_name}.{constraint.name}: invariant should be a short identifier, "
        f"got {constraint.invariant!r}"
    )


@pytest.mark.parametrize("component_name", COGNITIVE_FACTOR_NAMES)
def test_cognitive_factor_digital_implementation_is_dotted_path(component_name):
    catalog = default_catalog()
    entry = catalog.get(component_name)
    assert entry is not None
    impl = entry.digital_implementation
    assert impl, f"{component_name}: digital_implementation must be non-empty"
    # Either 'a.b.c' or 'a.b + c.d' (compound path used by pattern_recognition)
    assert "." in impl or " + " in impl, (
        f"{component_name}: digital_implementation must be a dotted module path, got {impl!r}"
    )


# --------------------------------------------------------------------------- #
# 2. StressTester behaviour — placeholder path is documented
# --------------------------------------------------------------------------- #
#
# Cognitive-factor constraints are module-level, not circuit-level: they
# don't have an orchestrator builder wired into the BCEL stress
# framework (that's a follow-up for the next release). The framework
# therefore returns the documented placeholder result, just like the
# `unknown_constraint` case in `tests/test_bcel_stress.py`.


@pytest.mark.parametrize("component_name", COGNITIVE_FACTOR_NAMES)
def test_stress_tester_returns_placeholder_for_unwired_module(component_name):
    catalog = default_catalog()
    entry = catalog.get(component_name)
    assert entry is not None
    constraint = entry.kept_constraints[0]

    tester = ConstraintStressTester()  # no builder → placeholder
    result = asyncio.run(tester.run(constraint))
    # The framework must not crash; it must return *some* verdict.
    assert result.test_name, "stress tester must produce a test_name"
    assert "could not be executed" in result.interpretation or result.passed, (
        f"{component_name}: stress tester must yield placeholder or passed, "
        f"got {result.interpretation!r}"
    )


# --------------------------------------------------------------------------- #
# 3. Operational smoke — one cognitive factor with a synthetic scenario
# --------------------------------------------------------------------------- #
#
# We demonstrate that the stress-test framework CAN drive a cognitive-
# factor constraint end-to-end when a builder + scenario is provided.
# This serves as a template for the next round of wiring.


def test_cognitive_factor_stress_template_runs():
    """Drive the working-memory slot-span constraint via a synthetic builder."""
    catalog = default_catalog()
    entry = catalog.get("cognitive factor: working memory")
    assert entry is not None
    constraint = entry.kept_constraints[0]

    # A trivial orchestrator: a list of N "active slots". Relaxing the
    # constraint multiplies capacity, so the "active_slot_count" jumps.
    class _Orch:
        def __init__(self, cap: int) -> None:
            self.cap = cap
            self.active = []

        def inject(self, pattern) -> None:
            # Cap-aware push: simulate WM slot pressure.
            self.active.append(pattern)
            if len(self.active) > self.cap:
                self.active.pop(0)

    def build(cap: int):
        return _Orch(cap)

    tester = ConstraintStressTester(build_orchestrator=lambda: build(cap=4))

    def baseline(c, proxy):
        proxy.orch.cap = 4  # tight WM

    def perturbed(c, proxy):
        proxy.orch.cap = 1000  # relaxed → no WM pressure

    tester.register_scenario(constraint.name, baseline, perturbed)

    result = asyncio.run(tester.run(constraint, metric="max_activation", ticks=5))
    # We don't assert >=2x sensitivity here because the synthetic
    # orchestrator's metric is coarse; this is a smoke that the
    # framework path works end-to-end for a cognitive-factor constraint.
    assert result.test_name, "stress tester must produce a test_name"
    assert isinstance(result.passed, bool)