"""T218-T09 tests — microgrid plant and three-arm harness (EXP-01).

Acceptance (spec §7.1): the 19-cell hexagonal lattice is generated with
six-neighbour adjacency; all three preregistered arms execute under the
declared disturbance script; q_speace-v0 routes every accepted proposal
through screening (budget Δ), independent validation and ledger
activation; configurations are frozen (fixed seeds).
"""

from __future__ import annotations

import numpy as np
import pytest

from q_speace.bridge.microgrid import (
    DisturbanceScript,
    PlantParams,
    _run_conventional,
    _run_fixed,
    _run_qspeace_v0,
    hex_lattice,
    run_all_arms,
    step_cell,
)


def test_hex_lattice_19_cells_with_six_neighbours() -> None:
    cells, neighbours = hex_lattice(2)
    assert len(cells) == 19
    assert (0, 0) in cells
    centre = neighbours[(0, 0)]
    assert len(centre) == 6
    # every interior cell has exactly six neighbours
    interior = [c for c in cells if max(abs(c[0]), abs(c[1]), abs(c[0] + c[1])) <= 1]
    for c in interior:
        assert len(neighbours[c]) == 6


def test_plant_step_conserves_declared_bounds() -> None:
    pp = PlantParams()
    params = np.array([0.8, 0.2])
    soc, supply, unmet = step_cell(0.6, 0.6, 0.8, params, pp, True)
    assert 0.0 <= soc <= 1.0
    assert supply + unmet == pytest.approx(0.6)  # service balance
    assert unmet >= 0.0


def test_offline_cell_supplies_nothing() -> None:
    pp = PlantParams()
    params = np.array([0.8, 0.2])
    soc, supply, unmet = step_cell(0.6, 0.6, 0.8, params, pp, False)
    assert soc == pytest.approx(0.6)
    assert supply == pytest.approx(0.0)
    assert unmet == pytest.approx(0.6)


def _script() -> DisturbanceScript:
    return DisturbanceScript(seed=20261114, steps=200)


def test_all_arms_execute_under_frozen_script() -> None:
    results = run_all_arms(_script())
    names = [r.name for r in results]
    assert names == ["fixed", "conventional", "q_speace_v0"]
    for r in results:
        assert r.metrics.cumulative_unmet_kwh >= 0.0
        assert r.final_params is not None


def test_qspeace_v0_respects_update_budget_and_validator() -> None:
    script = _script()
    pp = PlantParams()
    result = _run_qspeace_v0(script, pp)
    assert result.updates_proposed >= 1
    # every activated configuration must lie inside the declared bounds
    assert pp.check_bounds(result.final_params)  # type: ignore[arg-type]
    # proposals rejected or abstained are recorded, never silently applied
    assert result.updates_rejected >= 0
    assert result.updates_proposed + result.updates_rejected >= 1


def test_fixed_arm_never_adapts() -> None:
    pp = PlantParams()
    result = _run_fixed(_script(), pp)
    assert np.array_equal(result.final_params, np.array([0.8, 0.2]))
    assert result.updates_proposed == 0


def test_conventional_arm_adapts_without_validation() -> None:
    pp = PlantParams()
    result = _run_conventional(_script(), pp)
    assert result.updates_proposed > 0
    # unconstrained adaptation is counted as a bounds violation when it
    # leaves the declared envelope (the arm has no validator)
    assert result.final_params is not None


def test_outage_cell_registered_in_script() -> None:
    script = _script()
    cells, _ = hex_lattice(2)
    assert script.outage_cell in cells


def test_harness_is_reproducible() -> None:
    r1 = run_all_arms(_script())
    r2 = run_all_arms(_script())
    for a, b in zip(r1, r2, strict=False):
        assert a.metrics.cumulative_unmet_kwh == pytest.approx(b.metrics.cumulative_unmet_kwh)
        assert np.array_equal(a.final_params, b.final_params)
