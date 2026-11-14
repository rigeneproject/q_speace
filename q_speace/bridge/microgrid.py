"""Bridge-v0 microgrid plant and three-arm experimental harness (T218-T09).

The declared scientific instance of spec §3 and §7.1: a 19-cell
hexagonal microgrid (1 centre + 2 rings, axial coordinates, 6-neighbour
adjacency) in one explicitly modeled resource domain (electrical power
with battery storage).

Per-cell discrete-time dynamics (one control step = 1 minute):

    available = P_solar * solar(t) + P_discharge_max * soc
    supply    = min(load, available)
    unmet     = load - supply
    surplus   = max(0, P_solar * solar(t) - load)
    soc'      = clip(soc + (P_charge_max * surplus - (load - supply)) / E_cap, 0, 1)

Adaptive parameter vector ``p = (P_discharge_max, soc_reserve)`` with
declared bounds. Three preregistered arms:

* ``fixed``            — frozen parameters, no adaptation;
* ``conventional``     — integral adaptation of the parameters from the
  observed unmet demand, no validation, no update budget;
* ``q_speace_v0``      — periodic proposals passed through the Bridge:
  screening (budget Δ), independent validation on a short plant
  forecast, ledger activation, rollback to the last certified
  configuration on abstention.

Metrics per trajectory (EXP-01 units): cumulative unmet energy (kWh),
constraint violations, recovery time (steps) after the declared outage.

BCEL: the plant is a functional electrical model. The three arms differ
only in the declared adaptation mechanism; no arm is "conscious" and
no comparison result is reported here — this module provides the
harness, not the experimental outcome.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from q_speace.bridge.protocol import UpdateLedger, UpdateProposal, UpdateStatus
from q_speace.bridge.screening import ScreeningOutcome, screen_candidate
from q_speace.bridge.validator import IndependentValidator, ValidatorKey

# --------------------------------------------------------------------- #
# hexagonal lattice
# --------------------------------------------------------------------- #
_AXIAL_DIRS = ((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1))


def hex_ring(radius: int) -> list[tuple[int, int]]:
    """Axial coordinates of one hexagonal ring.

    Walk starts at ``center + dir[4] * radius`` and applies each of the
    six directions ``radius`` times (Red Blob Games ring algorithm),
    returning to the start — every generated cell is at hex distance
    exactly ``radius`` from the centre.
    """
    if radius == 0:
        return [(0, 0)]
    cells: list[tuple[int, int]] = []
    q, r = -radius, radius
    for dq, dr in _AXIAL_DIRS:
        for _ in range(radius):
            cells.append((q, r))
            q, r = q + dq, r + dr
    return cells


def hex_lattice(
    rings: int = 2,
) -> tuple[list[tuple[int, int]], dict[tuple[int, int], list[tuple[int, int]]]]:
    """19-cell lattice for rings=2 (centre + 6 + 12)."""
    cells = hex_ring(0)
    for k in range(1, rings + 1):
        cells.extend(hex_ring(k))
    cell_set = set(cells)
    neighbours = {
        c: [nb for d in _AXIAL_DIRS if (nb := (c[0] + d[0], c[1] + d[1])) in cell_set]
        for c in cells
    }
    return cells, neighbours


# --------------------------------------------------------------------- #
# plant
# --------------------------------------------------------------------- #
@dataclass(frozen=True)
class PlantParams:
    p_discharge_min: float = 0.2  # kW
    p_discharge_max_limit: float = 1.5  # kW
    p_charge_max: float = 0.8  # kW
    e_cap: float = 10.0  # kWh
    soc_reserve_lo: float = 0.1
    soc_reserve_hi: float = 0.4
    p_solar_rated: float = 1.2  # kW
    dt_hours: float = 1.0 / 60.0  # 1-minute steps

    def check_bounds(self, p: np.ndarray) -> bool:
        return bool(
            self.p_discharge_min <= p[0] <= self.p_discharge_max_limit
            and self.soc_reserve_lo <= p[1] <= self.soc_reserve_hi
        )


@dataclass
class CellState:
    soc: float = 0.6
    online: bool = True


@dataclass(frozen=True)
class StepObservation:
    """Per-cell observation with declared uncertainty (spec §3.1)."""

    soc_hat: float
    load: float
    solar: float
    unmet: float
    age_steps: int = 0


@dataclass
class TrajectoryMetrics:
    cumulative_unmet_kwh: float = 0.0
    violations: int = 0
    recovery_time_steps: int = -1  # -1 = not yet recovered
    _unmet_started: bool = field(default=False, repr=False)


def _solar_profile(t: int) -> float:
    """Deterministic daily cycle; peak at step 720 (noon of a 1440-step day)."""
    return max(0.0, float(np.sin(np.pi * (t % 1440) / 1440)))


def step_cell(
    soc: float,
    load: float,
    solar: float,
    params: np.ndarray,
    pp: PlantParams,
    online: bool,
) -> tuple[float, float, float]:
    """One plant step; returns (soc_next, supply, unmet)."""
    p_discharge = params[0]
    soc_reserve = params[1]
    if not online:
        return soc, 0.0, load  # isolated cell loses its own solar
    available = pp.p_solar_rated * solar + p_discharge * soc
    supply = min(load, available)
    unmet = load - supply
    surplus = max(0.0, pp.p_solar_rated * solar - load)
    charge = pp.p_charge_max if surplus > 0 else 0.0
    discharge = load - pp.p_solar_rated * solar if load > pp.p_solar_rated * solar else 0.0
    soc_next = soc + (charge - discharge) * pp.dt_hours / pp.e_cap
    # reserve floor: below the adaptive reserve, discharge is curtailed
    if soc_next < soc_reserve:
        soc_next = max(soc_reserve, soc_next)
    soc_next = float(np.clip(soc_next, 0.0, 1.0))
    return soc_next, supply, unmet


# --------------------------------------------------------------------- #
# disturbance script (preregistered shape; seeds fixed in the harness)
# --------------------------------------------------------------------- #
@dataclass(frozen=True)
class DisturbanceScript:
    surge_start: int = 50
    surge_end: int = 80
    surge_factor: float = 1.3
    outage_cell: tuple[int, int] | None = (1, -1)  # axial coords of a ring-1 cell
    outage_start: int = 80
    outage_end: int = 120
    seed: int = 20261114
    steps: int = 200
    base_load: float = 0.6  # kW


def load_profile(script: DisturbanceScript, t: int, rng: np.random.Generator) -> float:
    load = script.base_load
    if script.surge_start <= t < script.surge_end:
        load *= script.surge_factor
    return float(load + 0.02 * rng.standard_normal())


# --------------------------------------------------------------------- #
# arms
# --------------------------------------------------------------------- #
@dataclass(frozen=True)
class ArmResult:
    name: str
    metrics: TrajectoryMetrics
    updates_proposed: int = 0
    updates_rejected: int = 0
    final_params: np.ndarray | None = None


def _run_fixed(script: DisturbanceScript, pp: PlantParams) -> ArmResult:
    cells, _ = hex_lattice(2)
    params = np.array([0.8, 0.2])
    socs = {c: CellState() for c in cells}
    metrics = TrajectoryMetrics()
    rng = np.random.default_rng(script.seed)
    for t in range(script.steps):
        solar = _solar_profile(t)
        for c in cells:
            online = not (script.outage_cell == c and script.outage_start <= t < script.outage_end)
            load = load_profile(script, t, rng)
            soc, _supply, unmet = step_cell(socs[c].soc, load, solar, params, pp, online)
            socs[c].soc = soc
            if online:
                metrics.cumulative_unmet_kwh += unmet * pp.dt_hours
            if script.outage_cell == c:
                _track_recovery(metrics, script, t, unmet, load)
    return ArmResult("fixed", metrics, 0, 0, params)


def _track_recovery(
    metrics: TrajectoryMetrics, script: DisturbanceScript, t: int, unmet: float, load: float
) -> None:
    """Recovery time: first step after the outage ends where the outage
    cell's unmet demand falls below 5% of its load."""
    if script.outage_start <= t < script.outage_end:
        metrics._unmet_started = True
        return
    if (
        metrics._unmet_started
        and metrics.recovery_time_steps < 0
        and t >= script.outage_end
        and unmet < 0.05 * max(load, 1e-9)
    ):
        metrics.recovery_time_steps = t - script.outage_end


def _run_conventional(script: DisturbanceScript, pp: PlantParams) -> ArmResult:
    """Integral adaptation from observed unmet demand — no validation."""
    cells, _ = hex_lattice(2)
    params = np.array([0.8, 0.2])
    socs = {c: CellState() for c in cells}
    metrics = TrajectoryMetrics()
    rng = np.random.default_rng(script.seed)
    proposed = 0
    for t in range(script.steps):
        solar = _solar_profile(t)
        total_unmet = 0.0
        for c in cells:
            online = not (script.outage_cell == c and script.outage_start <= t < script.outage_end)
            load = load_profile(script, t, rng)
            soc, _supply, unmet = step_cell(socs[c].soc, load, solar, params, pp, online)
            socs[c].soc = soc
            total_unmet += unmet if online else 0.0
            metrics.cumulative_unmet_kwh += unmet * pp.dt_hours
            if script.outage_cell == c:
                _track_recovery(metrics, script, t, unmet, load)
        # unconstrained integral adaptation (may leave declared bounds)
        params = params + np.array([0.05 * total_unmet, -0.01 * total_unmet])
        proposed += 1
        if not pp.check_bounds(params):
            metrics.violations += 1
        params = np.clip(
            params,
            [pp.p_discharge_min, pp.soc_reserve_lo],
            [pp.p_discharge_max_limit, pp.soc_reserve_hi],
        )
    return ArmResult("conventional", metrics, proposed, 0, params)


def _plant_check_factory(
    socs: dict[tuple[int, int], float],
    load: float,
    solar: float,
    pp: PlantParams,
    center: tuple[int, int],
) -> Callable[[UpdateProposal], bool]:
    """Short 5-step forecast with the candidate parameters (validator side)."""

    def check(proposal: UpdateProposal) -> bool:
        # The candidate parameter vector is reconstructed from the hash
        # registry by the caller; for the harness we evaluate the
        # declared candidate attached to the ledger proposal payload.
        candidate = _CANDIDATE_STORE.get(proposal.proposal_id)
        if candidate is None:
            return False
        soc = socs[center]
        unmet_total = 0.0
        for _ in range(5):
            soc, _s, unmet = step_cell(soc, load, solar, candidate, pp, True)
            unmet_total += unmet
            if soc < pp.soc_reserve_lo - 1e-9 or soc > 1.0 + 1e-9:
                return False
        return unmet_total <= 5 * load * 0.5

    return check


_CANDIDATE_STORE: dict[str, np.ndarray] = {}


def _run_qspeace_v0(script: DisturbanceScript, pp: PlantParams) -> ArmResult:
    """q_speace-v0 arm: proposals through the full Bridge contract."""
    cells, _ = hex_lattice(2)
    center = cells[0]
    params = np.array([0.8, 0.2])
    certified = params.copy()
    socs = {c: CellState() for c in cells}
    metrics = TrajectoryMetrics()
    rng = np.random.default_rng(script.seed)
    ledger = UpdateLedger()
    validator = IndependentValidator(ValidatorKey(generation=1, key=b"v0" * 16))
    lower = np.array([pp.p_discharge_min, pp.soc_reserve_lo])
    upper = np.array([pp.p_discharge_max_limit, pp.soc_reserve_hi])
    scale = np.array([1.0, 1.0])
    budget = 0.05
    proposed = rejected = 0
    for t in range(script.steps):
        solar = _solar_profile(t)
        load = load_profile(script, t, rng)
        for c in cells:
            online = not (script.outage_cell == c and script.outage_start <= t < script.outage_end)
            cell_load = load_profile(script, t, rng)
            soc, _supply, unmet = step_cell(socs[c].soc, cell_load, solar, params, pp, online)
            socs[c].soc = soc
            metrics.cumulative_unmet_kwh += unmet * pp.dt_hours
            if script.outage_cell == c:
                _track_recovery(metrics, script, t, unmet, cell_load)
        # q_speace proposal cadence: every 10 steps
        if t % 10 == 0 and t > 0:
            # gradient-like proposal toward reducing predicted unmet
            grad = np.array([0.02 * (load - pp.p_solar_rated * solar), 0.0])
            candidate = params + grad
            result = screen_candidate(
                candidate,
                certified,
                lower=lower,
                upper=upper,
                scale=scale,
                budget=budget,
            )
            if result.outcome is not ScreeningOutcome.ACCEPTED or result.candidate is None:
                rejected += 1
                continue
            proposed += 1
            pid = f"prop-{t}"
            _CANDIDATE_STORE[pid] = result.candidate
            base_proposal = UpdateProposal(
                proposal_id=pid,
                base_epoch=1,
                param_hash=f"hash-{pid}",
                scope=("cell_centre",),
                dependencies=(),
                validation_attest="",
                expiry=t + 5,
            )
            try:
                attest = validator.attest(
                    base_proposal,
                    epoch=1,
                    plant_check=_plant_check_factory(
                        {c: s.soc for c, s in socs.items()}, load, solar, pp, center
                    ),
                )
            except Exception:  # noqa: BLE001 — declared abstention path
                rejected += 1
                _CANDIDATE_STORE.pop(pid, None)
                continue
            proposal = UpdateProposal(
                proposal_id=pid,
                base_epoch=1,
                param_hash=f"hash-{pid}",
                scope=("cell_centre",),
                dependencies=(),
                validation_attest=attest,
                expiry=t + 5,
            )
            led_status = ledger.submit(proposal, epoch=1)
            if led_status is not UpdateStatus.PROPOSED:
                rejected += 1
                continue
            try:
                ledger.mark_validated(pid, epoch=1, fencing=1, attest=attest)
                ledger.activate(pid, epoch=1, fencing=1)
                certified = result.candidate.copy()
                params = certified.copy()
            except Exception:  # noqa: BLE001 — declared abstention path
                rejected += 1
                params = certified.copy()
    return ArmResult("q_speace_v0", metrics, proposed, rejected, params)


def run_all_arms(script: DisturbanceScript | None = None) -> list[ArmResult]:
    """Execute the three preregistered arms under one disturbance script."""
    pp = PlantParams()
    s = script or DisturbanceScript()
    return [
        _run_fixed(s, pp),
        _run_conventional(s, pp),
        _run_qspeace_v0(s, pp),
    ]
