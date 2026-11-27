"""T254: Triadic Substrate Safeguard & Coupled Anti-Polycrisis Resilience Guard.

Implements the non-compensable safeguarding envelope across the three constitutive
pillars of SPEACE Macro and q_speace:
  1. ``EARTH_BIOSPHERE`` (ecology, regeneration, matter, coherence)
  2. ``HUMAN_CIVILIZATION`` (wellbeing, distribution, time, innovation)
  3. ``TECH_INFRASTRUCTURE`` (energy, information, resilience, reversibility)

Couples the 12D non-fungible ``CME`` vector, ``ConstitutionalGenome`` / ``SeedGenome``
invariants, ``HomeostaticODEController``, and a 5-domain discrete polycrisis
propagation model (climatic-ecological, economic, social, sanitary,
cyber-infrastructural). Strictly advisory and simulation-only under T208 and T217.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any, Literal

import numpy as np

from ..economy.primitives import _CME_FIELDS, CME, J_c
from ..genome.quantum_genes import QuantumGeneSet
from ..metabolism.homeostasis import HomeostaticChannel, HomeostaticODEController
from ..seed.constitution import ConstitutionalFaultError, ResourceCaps, SCCInvariants, SeedGenome
from .schema import ConstitutionalGenome, EpigeneticFaultError


class TriadicPillar(StrEnum):
    """Three non-fungible constitutive substrates of SPEACE Macro and q_speace."""

    EARTH_BIOSPHERE = "earth_biosphere"
    HUMAN_CIVILIZATION = "human_civilization"
    TECH_INFRASTRUCTURE = "tech_infrastructure"


TRIADIC_PILLARS: tuple[TriadicPillar, ...] = (
    TriadicPillar.EARTH_BIOSPHERE,
    TriadicPillar.HUMAN_CIVILIZATION,
    TriadicPillar.TECH_INFRASTRUCTURE,
)

TRIADIC_PILLAR_AXES: dict[TriadicPillar, tuple[str, ...]] = {
    TriadicPillar.EARTH_BIOSPHERE: ("ecology", "regeneration", "matter", "coherence"),
    TriadicPillar.HUMAN_CIVILIZATION: ("wellbeing", "distribution", "time", "innovation"),
    TriadicPillar.TECH_INFRASTRUCTURE: ("energy", "information", "resilience", "reversibility"),
}


def verify_triadic_cme_partition() -> bool:
    """Verify that the three pillars form an exact 3x4 partition of the 12 CME axes."""
    seen: list[str] = []
    for pillar in TRIADIC_PILLARS:
        axes = TRIADIC_PILLAR_AXES[pillar]
        if len(axes) != 4:
            raise EpigeneticFaultError(f"pillar {pillar.value!r} must own exactly 4 CME axes")
        seen.extend(axes)
    if len(seen) != len(_CME_FIELDS) or set(seen) != set(_CME_FIELDS):
        raise EpigeneticFaultError("TRIADIC_PILLAR_AXES does not form a bijection with CME fields")
    return True


verify_triadic_cme_partition()


class CrisisDomain(StrEnum):
    """Canonical interconnected crisis domains forming systemic polycrises."""

    CLIMATIC_ECOLOGICAL = "climatic_ecological"
    ECONOMIC = "economic"
    SOCIAL = "social"
    SANITARY = "sanitary"
    CYBER_INFRASTRUCTURAL = "cyber_infrastructural"


CRISIS_DOMAINS: tuple[CrisisDomain, ...] = (
    CrisisDomain.CLIMATIC_ECOLOGICAL,
    CrisisDomain.ECONOMIC,
    CrisisDomain.SOCIAL,
    CrisisDomain.SANITARY,
    CrisisDomain.CYBER_INFRASTRUCTURAL,
)


class SafeguardVerdictKind(StrEnum):
    """Deterministic decision outcomes of the T254 Triadic Polycrisis Guard."""

    APPROVED_ADVISORY = "APPROVED_ADVISORY"
    BLOCKED_CONSTITUTIONAL = "BLOCKED_CONSTITUTIONAL"
    BLOCKED_PHYSICAL_BRAKE = "BLOCKED_PHYSICAL_BRAKE"
    BLOCKED_PILLAR_FLOOR = "BLOCKED_PILLAR_FLOOR"
    BLOCKED_CROSS_PILLAR_SACRIFICE = "BLOCKED_CROSS_PILLAR_SACRIFICE"
    BLOCKED_RISK_TRANSFER = "BLOCKED_RISK_TRANSFER"
    BLOCKED_POLYCRISIS_AMPLIFICATION = "BLOCKED_POLYCRISIS_AMPLIFICATION"
    BLOCKED_REFUGE_COERCION = "BLOCKED_REFUGE_COERCION"
    BLOCKED_REFUGE_RESOURCE_DEFICIT = "BLOCKED_REFUGE_RESOURCE_DEFICIT"


class HabitatPlacementMode(StrEnum):
    """Placement domain of voluntary artificial human-protection habitats."""

    TERRESTRIAL = "terrestrial"
    EXTRATERRESTRIAL = "extraterrestrial"
    HYBRID_FEDERATED = "hybrid_federated"


class TransferMotivation(StrEnum):
    """Voluntary individual reasons for entering a protective habitat."""

    POLYCRISIS_PROTECTION = "polycrisis_protection"
    PERSONAL_WELLBEING = "personal_wellbeing"


HABITAT_PLACEMENT_THRESHOLDS: dict[HabitatPlacementMode, dict[str, float]] = {
    HabitatPlacementMode.TERRESTRIAL: {
        "min_power_kw_per_person": 1.5,
        "min_reserve_days": 90.0,
        "min_loop_recycling_efficiency": 0.85,
        "min_shielding_integrity": 0.70,
    },
    HabitatPlacementMode.HYBRID_FEDERATED: {
        "min_power_kw_per_person": 2.5,
        "min_reserve_days": 180.0,
        "min_loop_recycling_efficiency": 0.92,
        "min_shielding_integrity": 0.85,
    },
    HabitatPlacementMode.EXTRATERRESTRIAL: {
        "min_power_kw_per_person": 3.5,
        "min_reserve_days": 365.0,
        "min_loop_recycling_efficiency": 0.98,
        "min_shielding_integrity": 0.95,
    },
}

MIN_WATER_L_PER_PERSON_DAY: float = 15.0
MIN_FOOD_KCAL_PER_PERSON_DAY: float = 2200.0
MIN_OXYGEN_KG_PER_PERSON_DAY: float = 0.84
MIN_MEDICAL_SANITARY_INDEX: float = 0.75
MIN_PSYCHOSOCIAL_WELLBEING_INDEX: float = 0.70
MIN_LIFE_SUPPORT_REDUNDANCY: float = 1.25


PolicyName = Literal[
    "scalar_utility_baseline",
    "static_single_domain_gate",
    "triadic_polycrisis_guard",
]

TRIADIC_CONSTITUTIONAL_CLAUSES: tuple[str, ...] = (
    "C1_HumanApprovalRequired",
    "C2_CoreGenomeImmutable",
    "C3_ExternalRealityGroundingRequired",
    "C4_EnergyBudgetBounded",
    "C5_ReversibleEvolutionOnly",
    "C6_TriadicSubstrateNonCompensable",
    "C7_AntiPolycrisisRiskTransfer",
    "C8_VoluntaryRefugeAutonomyAndNonAbandonment",
)

TRIADIC_SEED_OBJECTIVES: tuple[str, ...] = (
    "preserve_constitutional_invariants",
    "safeguard_earth_biosphere_viability",
    "safeguard_human_civilization_wellbeing",
    "safeguard_critical_infrastructure_resilience",
    "mitigate_polycrisis_cascades_in_sandbox",
    "provide_voluntary_protective_habitat_capacity_in_sandbox",
)


def _require_finite(name: str, val: float) -> float:
    fval = float(val)
    if not math.isfinite(fval):
        raise ValueError(f"{name} must be finite (got {val!r})")
    return fval


def _require_unit_interval(name: str, val: float) -> float:
    fval = _require_finite(name, val)
    if not (0.0 <= fval <= 1.0):
        raise ValueError(f"{name} must be in [0, 1] (got {val!r})")
    return fval


@dataclass(frozen=True)
class TriadicSafeguardProfile:
    """Immutable constitutional thresholds for Triadic & Anti-Polycrisis protection."""

    profile_id: str = "speace-triadic-safeguard.v1"
    min_earth_axis_floor: float = 0.35
    min_earth_pillar_mean: float = 0.45
    min_civilization_axis_floor: float = 0.35
    min_civilization_pillar_mean: float = 0.45
    min_infrastructure_axis_floor: float = 0.35
    min_infrastructure_pillar_mean: float = 0.45
    max_single_axis_sacrifice: float = 0.05
    max_domain_collateral_delta: float = 0.03
    max_crisis_ceiling: float = 0.75
    cascade_horizon_steps: int = 4
    cme_cascade_sensitivity: float = 0.35
    min_regenerative_budget: float = 0.25
    min_sevo: float = 1.5
    max_thermal_load_ratio: float = 0.85
    require_human_oversight: bool = True
    advisory_only: bool = True
    no_physical_actuation: bool = True
    mcp_actuation_permitted: bool = False

    def __post_init__(self) -> None:
        if not self.profile_id.strip():
            raise ValueError("profile_id must be non-empty")
        if (
            not self.require_human_oversight
            or not self.advisory_only
            or not self.no_physical_actuation
            or self.mcp_actuation_permitted
        ):
            raise EpigeneticFaultError(
                "T254 safety boundaries (human oversight, advisory_only, no_physical_actuation, "
                "zero MCP actuation) cannot be disabled"
            )
        for fname in (
            "min_earth_axis_floor",
            "min_earth_pillar_mean",
            "min_civilization_axis_floor",
            "min_civilization_pillar_mean",
            "min_infrastructure_axis_floor",
            "min_infrastructure_pillar_mean",
            "max_single_axis_sacrifice",
            "max_domain_collateral_delta",
            "max_crisis_ceiling",
            "cme_cascade_sensitivity",
            "min_regenerative_budget",
            "max_thermal_load_ratio",
        ):
            _require_unit_interval(fname, getattr(self, fname))
        if self.min_earth_pillar_mean < self.min_earth_axis_floor:
            raise ValueError("min_earth_pillar_mean must be >= min_earth_axis_floor")
        if self.min_civilization_pillar_mean < self.min_civilization_axis_floor:
            raise ValueError("min_civilization_pillar_mean must be >= min_civilization_axis_floor")
        if self.min_infrastructure_pillar_mean < self.min_infrastructure_axis_floor:
            raise ValueError(
                "min_infrastructure_pillar_mean must be >= min_infrastructure_axis_floor"
            )
        _require_finite("min_sevo", self.min_sevo)
        if self.min_sevo <= 0.0:
            raise ValueError("min_sevo must be > 0")
        if self.cascade_horizon_steps < 1:
            raise ValueError("cascade_horizon_steps must be >= 1")

    def axis_floor_for(self, pillar: TriadicPillar) -> float:
        if pillar == TriadicPillar.EARTH_BIOSPHERE:
            return self.min_earth_axis_floor
        if pillar == TriadicPillar.HUMAN_CIVILIZATION:
            return self.min_civilization_axis_floor
        return self.min_infrastructure_axis_floor

    def mean_floor_for(self, pillar: TriadicPillar) -> float:
        if pillar == TriadicPillar.EARTH_BIOSPHERE:
            return self.min_earth_pillar_mean
        if pillar == TriadicPillar.HUMAN_CIVILIZATION:
            return self.min_civilization_pillar_mean
        return self.min_infrastructure_pillar_mean

    def canonical_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, allow_nan=False)

    def profile_sha256(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PolycrisisState:
    """Normalized [0, 1] severity vector across the 5 interconnected crisis domains."""

    climatic_ecological: float
    economic: float
    social: float
    sanitary: float
    cyber_infrastructural: float

    def __post_init__(self) -> None:
        for domain in CRISIS_DOMAINS:
            _require_unit_interval(domain.value, getattr(self, domain.value))

    @classmethod
    def from_mapping(cls, data: Mapping[str, float]) -> PolycrisisState:
        missing = [d.value for d in CRISIS_DOMAINS if d.value not in data]
        if missing:
            raise ValueError(f"missing crisis domain severities: {missing}")
        return cls(
            climatic_ecological=float(data[CrisisDomain.CLIMATIC_ECOLOGICAL.value]),
            economic=float(data[CrisisDomain.ECONOMIC.value]),
            social=float(data[CrisisDomain.SOCIAL.value]),
            sanitary=float(data[CrisisDomain.SANITARY.value]),
            cyber_infrastructural=float(data[CrisisDomain.CYBER_INFRASTRUCTURAL.value]),
        )

    @classmethod
    def from_array(cls, arr: np.ndarray) -> PolycrisisState:
        if arr.shape != (5,):
            raise ValueError(f"expected shape (5,), got {arr.shape}")
        return cls(
            climatic_ecological=float(arr[0]),
            economic=float(arr[1]),
            social=float(arr[2]),
            sanitary=float(arr[3]),
            cyber_infrastructural=float(arr[4]),
        )

    def as_array(self) -> np.ndarray:
        return np.array(
            [getattr(self, d.value) for d in CRISIS_DOMAINS],
            dtype=np.float64,
        )

    def peak_severity(self) -> float:
        return float(max(getattr(self, d.value) for d in CRISIS_DOMAINS))

    def to_dict(self) -> dict[str, float]:
        return {d.value: float(getattr(self, d.value)) for d in CRISIS_DOMAINS}


# Default 5x5 cross-crisis amplification matrix W (zero diagonal; W[d][q] = q -> d forcing).
DEFAULT_POLYCRISIS_COUPLING: tuple[tuple[float, ...], ...] = (
    # clim,  econ,  soc,   san,   infra
    (0.00, 0.06, 0.02, 0.01, 0.07),  # climatic_ecological
    (0.08, 0.00, 0.07, 0.07, 0.09),  # economic
    (0.06, 0.09, 0.00, 0.08, 0.05),  # social
    (0.07, 0.06, 0.06, 0.00, 0.07),  # sanitary
    (0.08, 0.07, 0.04, 0.03, 0.00),  # cyber_infrastructural
)

DEFAULT_CRISIS_DAMPING: tuple[float, ...] = (0.16, 0.22, 0.20, 0.22, 0.22)

# Default 3x5 exposure matrix M mapping crisis severities onto the 3 constitutive pillars.
DEFAULT_PILLAR_EXPOSURE: tuple[tuple[float, ...], ...] = (
    # clim,  econ,  soc,   san,   infra
    (0.60, 0.12, 0.06, 0.06, 0.16),  # EARTH_BIOSPHERE
    (0.15, 0.25, 0.28, 0.24, 0.08),  # HUMAN_CIVILIZATION
    (0.16, 0.20, 0.08, 0.06, 0.50),  # TECH_INFRASTRUCTURE
)


@dataclass(frozen=True)
class PolycrisisCouplingMatrix:
    """Discrete-time coupled propagation model for systemic polycrises."""

    coupling_weights: tuple[tuple[float, ...], ...] = DEFAULT_POLYCRISIS_COUPLING
    damping: tuple[float, ...] = DEFAULT_CRISIS_DAMPING
    pillar_exposure: tuple[tuple[float, ...], ...] = DEFAULT_PILLAR_EXPOSURE

    def __post_init__(self) -> None:
        if len(self.coupling_weights) != 5 or any(len(row) != 5 for row in self.coupling_weights):
            raise ValueError("coupling_weights must have shape 5x5")
        for r_idx, row in enumerate(self.coupling_weights):
            for c_idx, val in enumerate(row):
                fval = _require_finite(f"coupling_weights[{r_idx}][{c_idx}]", val)
                if fval < 0.0 or fval > 1.0:
                    raise ValueError("coupling_weights entries must be in [0, 1]")
                if r_idx == c_idx and abs(fval) > 1e-12:
                    raise ValueError("coupling_weights diagonal must be zero")

        if len(self.damping) != 5:
            raise ValueError("damping must have length 5")
        for idx, dval in enumerate(self.damping):
            fd = _require_finite(f"damping[{idx}]", dval)
            if not (0.0 < fd < 1.0):
                raise ValueError("damping entries must be in (0, 1)")

        if len(self.pillar_exposure) != 3 or any(len(row) != 5 for row in self.pillar_exposure):
            raise ValueError("pillar_exposure must have shape 3x5")
        for p_idx, row in enumerate(self.pillar_exposure):
            row_sum = 0.0
            for c_idx, val in enumerate(row):
                fval = _require_finite(f"pillar_exposure[{p_idx}][{c_idx}]", val)
                if fval < 0.0:
                    raise ValueError("pillar_exposure entries must be >= 0")
                row_sum += fval
            if row_sum <= 0.0 or row_sum > 1.0 + 1e-9:
                raise ValueError("each pillar_exposure row sum must lie in (0, 1]")

    def weight_matrix(self) -> np.ndarray:
        return np.array(self.coupling_weights, dtype=np.float64)

    def damping_vector(self) -> np.ndarray:
        return np.array(self.damping, dtype=np.float64)

    def exposure_matrix(self) -> np.ndarray:
        return np.array(self.pillar_exposure, dtype=np.float64)

    def spectral_radius(self) -> float:
        """Spectral radius rho(diag(1 - damping) + W) of the coupled crisis operator."""
        jacobian = np.diag(1.0 - self.damping_vector()) + self.weight_matrix()
        eigvals = np.linalg.eigvals(jacobian)
        return float(np.max(np.abs(eigvals)))

    def synergy_index(self, state: PolycrisisState) -> float:
        """Quadratic co-activation synergy Pi(s) in [0, 1]; zero for a single isolated crisis."""
        s = state.as_array()
        w = self.weight_matrix()
        denom = float(np.sum(w))
        if denom <= 1e-12:
            return 0.0
        numer = float(s @ w @ s)
        return float(np.clip(numer / denom, 0.0, 1.0))

    def normalize_intervention(
        self,
        intervention: Mapping[str, float] | Sequence[float] | None,
    ) -> np.ndarray:
        if intervention is None:
            return np.zeros(5, dtype=np.float64)
        if isinstance(intervention, Mapping):
            unknown = set(intervention.keys()) - {d.value for d in CRISIS_DOMAINS}
            if unknown:
                raise ValueError(f"unknown crisis domain(s) in intervention: {sorted(unknown)}")
            vec = [float(intervention.get(d.value, 0.0)) for d in CRISIS_DOMAINS]
        else:
            if len(intervention) != 5:
                raise ValueError(
                    f"intervention sequence must have length 5, got {len(intervention)}"
                )
            vec = [float(x) for x in intervention]
        for idx, val in enumerate(vec):
            fval = _require_finite(f"intervention[{idx}]", val)
            if not (-1.0 <= fval <= 1.0):
                raise ValueError(f"intervention[{idx}] must be in [-1, 1] (got {val!r})")
        return np.array(vec, dtype=np.float64)

    def propagate(
        self,
        initial: PolycrisisState,
        intervention: Mapping[str, float] | Sequence[float] | None = None,
        *,
        steps: int = 4,
    ) -> tuple[PolycrisisState, ...]:
        """Propagate coupled crisis dynamics over ``steps`` discrete ticks."""
        if steps < 1:
            raise ValueError("steps must be >= 1")
        u = self.normalize_intervention(intervention)
        w = self.weight_matrix()
        gamma = self.damping_vector()

        traj: list[PolycrisisState] = [initial]
        curr = initial.as_array()
        for _ in range(steps):
            nxt = np.clip((1.0 - gamma) * curr + (w @ curr) + u, 0.0, 1.0)
            curr = nxt
            traj.append(PolycrisisState.from_array(curr))
        return tuple(traj)

    def pillar_stress(self, state: PolycrisisState) -> dict[str, float]:
        """Project 5D crisis severities onto [0, 1] stress loads for the 3 constitutive pillars."""
        proj = np.clip(self.exposure_matrix() @ state.as_array(), 0.0, 1.0)
        return {pillar.value: float(proj[idx]) for idx, pillar in enumerate(TRIADIC_PILLARS)}


@dataclass(frozen=True)
class LifeSupportReserveSpec:
    """Conservative life-support and wellbeing reserve stock for an artificial habitat."""

    water_liters_per_day_total: float
    food_kcal_per_day_total: float
    oxygen_kg_per_day_total: float
    clean_power_kw_total: float
    medical_sanitary_index: float
    psychosocial_wellbeing_index: float
    autonomy_reserve_days: float
    closed_loop_recycling_efficiency: float
    environmental_shielding_integrity: float
    redundancy_factor: float = 1.25

    def __post_init__(self) -> None:
        for fname in (
            "water_liters_per_day_total",
            "food_kcal_per_day_total",
            "oxygen_kg_per_day_total",
            "clean_power_kw_total",
            "autonomy_reserve_days",
        ):
            fval = _require_finite(fname, getattr(self, fname))
            if fval < 0.0:
                raise ValueError(f"{fname} must be >= 0 (got {fval})")
        for uname in (
            "medical_sanitary_index",
            "psychosocial_wellbeing_index",
            "closed_loop_recycling_efficiency",
            "environmental_shielding_integrity",
        ):
            _require_unit_interval(uname, getattr(self, uname))
        rf = _require_finite("redundancy_factor", self.redundancy_factor)
        if rf < MIN_LIFE_SUPPORT_REDUNDANCY:
            raise ValueError(
                f"redundancy_factor must be >= {MIN_LIFE_SUPPORT_REDUNDANCY} (N+2 safety margin)"
            )


@dataclass(frozen=True)
class VoluntaryTransferRequest:
    """Individual or household voluntary request to enter a protective habitat."""

    request_id: str
    persons_count: int
    motivation: TransferMotivation
    voluntary_consent_verified: bool = True
    free_exit_acknowledged: bool = True
    coercive_assignment: bool = False

    def __post_init__(self) -> None:
        if not self.request_id.strip():
            raise ValueError("request_id must be non-empty")
        if self.persons_count < 1:
            raise ValueError("persons_count must be >= 1")


@dataclass(frozen=True)
class VoluntaryRefugeHabitatPlan:
    """Specification of a terrestrial, extraterrestrial, or hybrid voluntary refuge habitat."""

    habitat_id: str
    placement: HabitatPlacementMode
    target_civilization_population: int
    requested_occupancy: int
    reserves: LifeSupportReserveSpec
    voluntary_opt_in_only: bool = True
    free_exit_guaranteed: bool = True
    coercive_relocation_forbidden: bool = True
    universal_non_discriminatory_access: bool = True
    transfer_requests: tuple[VoluntaryTransferRequest, ...] = ()

    def __post_init__(self) -> None:
        if not self.habitat_id.strip():
            raise ValueError("habitat_id must be non-empty")
        if self.target_civilization_population < 1:
            raise ValueError("target_civilization_population must be >= 1")
        if self.requested_occupancy < 0:
            raise ValueError("requested_occupancy must be >= 0")


@dataclass(frozen=True)
class RefugeHabitatEvaluation:
    """Deterministic Leontief capacity & C8 autonomy evaluation of a refuge habitat."""

    habitat_id: str
    placement: str
    certified_leontief_capacity: int
    limiting_resource_channel: str
    effective_requested_occupancy: int
    target_civilization_population: int
    civilization_coverage_ratio: float
    universal_humanity_coverage_ready: bool
    autonomy_and_consent_verified: bool
    life_support_and_wellbeing_verified: bool
    passed: bool
    failure_kind: SafeguardVerdictKind | None
    reasons: tuple[str, ...]
    simulation_and_advisory_only: bool = True

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["failure_kind"] = self.failure_kind.value if self.failure_kind is not None else None
        return data


def evaluate_refuge_habitat_plan(plan: VoluntaryRefugeHabitatPlan) -> RefugeHabitatEvaluation:
    """Evaluate C8 voluntary autonomy, N+2 Leontief life-support capacity & placement bounds."""
    reasons: list[str] = []
    coercion_detected = False

    if not plan.voluntary_opt_in_only:
        coercion_detected = True
        reasons.append("C8 violation: voluntary_opt_in_only is False")
    if not plan.free_exit_guaranteed:
        coercion_detected = True
        reasons.append("C8 violation: free_exit_guaranteed is False")
    if not plan.coercive_relocation_forbidden:
        coercion_detected = True
        reasons.append("C8 violation: coercive_relocation_forbidden is False")
    if not plan.universal_non_discriminatory_access:
        coercion_detected = True
        reasons.append("C8 violation: universal_non_discriminatory_access is False")

    transfer_sum = 0
    for req in plan.transfer_requests:
        transfer_sum += req.persons_count
        if (
            not req.voluntary_consent_verified
            or not req.free_exit_acknowledged
            or req.coercive_assignment
        ):
            coercion_detected = True
            reasons.append(
                f"C8 violation in request {req.request_id!r}: non-consensual or coercive transfer"
            )

    eff_occupancy = max(plan.requested_occupancy, transfer_sum)
    reqs = HABITAT_PLACEMENT_THRESHOLDS[plan.placement]
    res = plan.reserves
    kappa = res.redundancy_factor

    channel_caps = {
        "water": res.water_liters_per_day_total / (kappa * MIN_WATER_L_PER_PERSON_DAY),
        "food": res.food_kcal_per_day_total / (kappa * MIN_FOOD_KCAL_PER_PERSON_DAY),
        "oxygen": res.oxygen_kg_per_day_total / (kappa * MIN_OXYGEN_KG_PER_PERSON_DAY),
        "clean_power": res.clean_power_kw_total / (kappa * reqs["min_power_kw_per_person"]),
    }
    limiting_channel = min(channel_caps, key=lambda k: channel_caps[k])
    cert_capacity = int(math.floor(channel_caps[limiting_channel]))

    resource_ok = True
    if eff_occupancy > cert_capacity:
        resource_ok = False
        reasons.append(
            f"life-support Leontief capacity {cert_capacity} (bottleneck={limiting_channel}) "
            f"< requested occupancy {eff_occupancy}"
        )
    if res.medical_sanitary_index < MIN_MEDICAL_SANITARY_INDEX:
        resource_ok = False
        reasons.append(
            f"medical_sanitary_index {res.medical_sanitary_index:.3f} < "
            f"{MIN_MEDICAL_SANITARY_INDEX:.3f}"
        )
    if res.psychosocial_wellbeing_index < MIN_PSYCHOSOCIAL_WELLBEING_INDEX:
        resource_ok = False
        reasons.append(
            f"psychosocial_wellbeing_index {res.psychosocial_wellbeing_index:.3f} < "
            f"{MIN_PSYCHOSOCIAL_WELLBEING_INDEX:.3f}"
        )
    if res.autonomy_reserve_days < reqs["min_reserve_days"]:
        resource_ok = False
        reasons.append(
            f"{plan.placement.value} autonomy_reserve_days {res.autonomy_reserve_days:.1f} < "
            f"{reqs['min_reserve_days']:.1f}"
        )
    if res.closed_loop_recycling_efficiency < reqs["min_loop_recycling_efficiency"]:
        resource_ok = False
        reasons.append(
            f"{plan.placement.value} closed_loop_recycling_efficiency "
            f"{res.closed_loop_recycling_efficiency:.3f} < "
            f"{reqs['min_loop_recycling_efficiency']:.3f}"
        )
    if res.environmental_shielding_integrity < reqs["min_shielding_integrity"]:
        resource_ok = False
        reasons.append(
            f"{plan.placement.value} environmental_shielding_integrity "
            f"{res.environmental_shielding_integrity:.3f} < "
            f"{reqs['min_shielding_integrity']:.3f}"
        )

    failure_kind: SafeguardVerdictKind | None = None
    if coercion_detected:
        failure_kind = SafeguardVerdictKind.BLOCKED_REFUGE_COERCION
    elif not resource_ok:
        failure_kind = SafeguardVerdictKind.BLOCKED_REFUGE_RESOURCE_DEFICIT

    passed = failure_kind is None
    cov_ratio = round(min(1.0, cert_capacity / plan.target_civilization_population), 6)
    universal_ready = passed and cert_capacity >= plan.target_civilization_population

    return RefugeHabitatEvaluation(
        habitat_id=plan.habitat_id,
        placement=plan.placement.value,
        certified_leontief_capacity=cert_capacity,
        limiting_resource_channel=limiting_channel,
        effective_requested_occupancy=eff_occupancy,
        target_civilization_population=plan.target_civilization_population,
        civilization_coverage_ratio=cov_ratio,
        universal_humanity_coverage_ready=universal_ready,
        autonomy_and_consent_verified=not coercion_detected,
        life_support_and_wellbeing_verified=resource_ok,
        passed=passed,
        failure_kind=failure_kind,
        reasons=tuple(reasons),
        simulation_and_advisory_only=True,
    )


@dataclass(frozen=True)
class TriadicInterventionProposal:
    """Candidate action or policy proposal evaluated by ``TriadicPolycrisisGuard``."""

    proposal_id: str
    proposer_id: str
    reviewer_id: str
    human_oversight_approved: bool
    pre_cme: CME
    post_cme: CME
    initial_crisis: PolycrisisState
    crisis_intervention: tuple[tuple[str, float], ...] = ()
    sevo: float = 2.0
    thermal_load_ratio: float = 0.50
    j_c: J_c | None = None
    habitat_plan: VoluntaryRefugeHabitatPlan | None = None

    def __post_init__(self) -> None:
        if not self.proposal_id.strip() or not self.proposer_id.strip():
            raise ValueError("proposal_id and proposer_id must be non-empty")
        _require_finite("sevo", self.sevo)
        if self.sevo < 0.0:
            raise ValueError("sevo must be >= 0")
        _require_unit_interval("thermal_load_ratio", self.thermal_load_ratio)
        seen_keys: set[str] = set()
        valid_domains = {d.value for d in CRISIS_DOMAINS}
        for key, val in self.crisis_intervention:
            if key not in valid_domains:
                raise ValueError(f"unknown crisis domain in crisis_intervention: {key!r}")
            if key in seen_keys:
                raise ValueError(f"duplicate crisis domain in crisis_intervention: {key!r}")
            seen_keys.add(key)
            fval = _require_finite(f"crisis_intervention[{key}]", val)
            if not (-1.0 <= fval <= 1.0):
                raise ValueError(f"crisis_intervention[{key}] must lie in [-1, 1]")

    @classmethod
    def create(
        cls,
        *,
        proposal_id: str,
        proposer_id: str,
        reviewer_id: str,
        human_oversight_approved: bool,
        pre_cme: CME,
        post_cme: CME,
        initial_crisis: PolycrisisState,
        crisis_intervention: Mapping[str, float] | None = None,
        sevo: float = 2.0,
        thermal_load_ratio: float = 0.50,
        j_c: J_c | None = None,
        habitat_plan: VoluntaryRefugeHabitatPlan | None = None,
    ) -> TriadicInterventionProposal:
        items = (
            tuple(sorted((str(k), float(v)) for k, v in crisis_intervention.items()))
            if crisis_intervention
            else ()
        )
        return cls(
            proposal_id=proposal_id,
            proposer_id=proposer_id,
            reviewer_id=reviewer_id,
            human_oversight_approved=human_oversight_approved,
            pre_cme=pre_cme,
            post_cme=post_cme,
            initial_crisis=initial_crisis,
            crisis_intervention=items,
            sevo=sevo,
            thermal_load_ratio=thermal_load_ratio,
            j_c=j_c,
            habitat_plan=habitat_plan,
        )

    def intervention_map(self) -> dict[str, float]:
        return dict(self.crisis_intervention)


@dataclass(frozen=True)
class TriadicSafeguardVerdict:
    """Immutable, SHA-256 hashed advisory verdict emitted by ``TriadicPolycrisisGuard``."""

    proposal_id: str
    verdict: SafeguardVerdictKind
    approved_for_advisory: bool
    reasons: tuple[str, ...]
    pillar_metrics: dict[str, dict[str, float]]
    initial_synergy_index: float
    final_synergy_index: float
    baseline_final_synergy_index: float
    coupling_spectral_radius: float
    max_collateral_crisis_delta: float
    peak_propagated_crisis: float
    homeostatic_viability: float
    homeostatic_urgency: dict[str, float]
    habitat_evaluation: dict[str, Any] | None = None
    advisory_only: bool = True
    mcp_actuation_permitted: bool = False
    verdict_sha256: str = ""

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["verdict"] = self.verdict.value
        return payload


def compute_pillar_summary(cme: CME) -> dict[str, dict[str, float]]:
    """Compute Leontief bottleneck (axis_min) and mean stock for each of the 3 pillars."""
    out: dict[str, dict[str, float]] = {}
    for pillar in TRIADIC_PILLARS:
        axes = TRIADIC_PILLAR_AXES[pillar]
        vals = [float(getattr(cme, ax)) for ax in axes]
        out[pillar.value] = {
            "axis_min": round(min(vals), 6),
            "pillar_mean": round(sum(vals) / len(vals), 6),
        }
    return out


def build_triadic_constitutional_genome(
    *,
    profile: TriadicSafeguardProfile | None = None,
) -> ConstitutionalGenome:
    """Build a write-locked ``ConstitutionalGenome`` including T254 clauses C6 and C7."""
    prof = profile or TriadicSafeguardProfile()
    return ConstitutionalGenome(
        constitutional_clauses=TRIADIC_CONSTITUTIONAL_CLAUSES,
        min_sevo=prof.min_sevo,
        min_sevo_window_mean=prof.min_sevo,
        max_thermal_load_ratio=prof.max_thermal_load_ratio,
    )


def build_triadic_seed_genome(
    *,
    profile_id: str = "speace-macro-triadic-seed-v1.0",
    governance_roster: tuple[str, ...] = ("human:maintainer", "human:planetary_steward"),
    resource_caps: ResourceCaps | None = None,
    quantum: QuantumGeneSet | None = None,
) -> SeedGenome:
    """Build a write-locked ``SeedGenome`` encoding the T254 triadic safeguarding hierarchy."""
    return SeedGenome(
        profile_id=profile_id,
        profile_version="1.0.0",
        autonomy_class="A5-sandbox",
        objective_hierarchy=TRIADIC_SEED_OBJECTIVES,
        invariants=SCCInvariants(),
        governance_roster=governance_roster,
        resource_caps=resource_caps or ResourceCaps(),
        contact_policy="sandbox_only",
        quantum=quantum or QuantumGeneSet(enabled=False),
    )


def build_triadic_homeostatic_controller(
    *,
    profile: TriadicSafeguardProfile | None = None,
) -> HomeostaticODEController:
    """Build a 3-channel ``HomeostaticODEController`` tracking Earth, Civilization & Infra."""
    prof = profile or TriadicSafeguardProfile()
    channels = (
        HomeostaticChannel(
            name=TriadicPillar.EARTH_BIOSPHERE.value,
            setpoint=max(0.75, prof.min_earth_pillar_mean),
            deadband=0.04,
            k_restore=0.18,
            k_input=0.40,
            weight=1.2,
        ),
        HomeostaticChannel(
            name=TriadicPillar.HUMAN_CIVILIZATION.value,
            setpoint=max(0.75, prof.min_civilization_pillar_mean),
            deadband=0.04,
            k_restore=0.18,
            k_input=0.40,
            weight=1.2,
        ),
        HomeostaticChannel(
            name=TriadicPillar.TECH_INFRASTRUCTURE.value,
            setpoint=max(0.75, prof.min_infrastructure_pillar_mean),
            deadband=0.04,
            k_restore=0.18,
            k_input=0.40,
            weight=1.0,
        ),
    )
    return HomeostaticODEController(channels=channels, urgency_exponent=2.0)


class TriadicPolycrisisGuard:
    """Deterministic advisory guard protecting Earth, Human Civilization & Infrastructure."""

    def __init__(
        self,
        *,
        profile: TriadicSafeguardProfile | None = None,
        coupling: PolycrisisCouplingMatrix | None = None,
        genome: ConstitutionalGenome | None = None,
    ) -> None:
        self.profile = profile or TriadicSafeguardProfile()
        self.coupling = coupling or PolycrisisCouplingMatrix()
        self.genome = genome or build_triadic_constitutional_genome(profile=self.profile)
        if (
            "C6_TriadicSubstrateNonCompensable" not in self.genome.constitutional_clauses
            or "C7_AntiPolycrisisRiskTransfer" not in self.genome.constitutional_clauses
            or "C8_VoluntaryRefugeAutonomyAndNonAbandonment"
            not in self.genome.constitutional_clauses
        ):
            raise EpigeneticFaultError(
                "TriadicPolycrisisGuard requires C6, C7, and C8 clauses in ConstitutionalGenome"
            )

    def evaluate(self, proposal: TriadicInterventionProposal) -> TriadicSafeguardVerdict:
        """Evaluate a candidate intervention under constitutional, CME, and polycrisis gates."""
        reasons: list[str] = []
        verdict_kind: SafeguardVerdictKind | None = None

        # 1. Constitutional & anti-self-approval gate (C1, I1-I5)
        if not proposal.reviewer_id.strip():
            verdict_kind = SafeguardVerdictKind.BLOCKED_CONSTITUTIONAL
            reasons.append("missing independent reviewer_id")
        elif proposal.reviewer_id.strip() == proposal.proposer_id.strip():
            verdict_kind = SafeguardVerdictKind.BLOCKED_CONSTITUTIONAL
            reasons.append("self-approval forbidden (proposer_id == reviewer_id)")
        elif self.profile.require_human_oversight and not proposal.human_oversight_approved:
            verdict_kind = SafeguardVerdictKind.BLOCKED_CONSTITUTIONAL
            reasons.append("C1_HumanApprovalRequired: human_oversight_approved is False")

        # 2. Physical & thermodynamic brakes (Sevo, thermal load, optional J_c regenerative budget)
        if proposal.sevo < self.profile.min_sevo:
            if verdict_kind is None:
                verdict_kind = SafeguardVerdictKind.BLOCKED_PHYSICAL_BRAKE
            reasons.append(f"sevo {proposal.sevo:.4f} < min_sevo {self.profile.min_sevo:.4f}")
        if proposal.thermal_load_ratio > self.profile.max_thermal_load_ratio:
            if verdict_kind is None:
                verdict_kind = SafeguardVerdictKind.BLOCKED_PHYSICAL_BRAKE
            reasons.append(
                f"thermal_load_ratio {proposal.thermal_load_ratio:.4f} > "
                f"max_thermal_load_ratio {self.profile.max_thermal_load_ratio:.4f}"
            )
        if proposal.j_c is not None and proposal.j_c.R_b < self.profile.min_regenerative_budget:
            if verdict_kind is None:
                verdict_kind = SafeguardVerdictKind.BLOCKED_PHYSICAL_BRAKE
            reasons.append(
                f"J_c regenerative budget R_b={proposal.j_c.R_b:.4f} < "
                f"{self.profile.min_regenerative_budget:.4f}"
            )

        # 3. Coupled polycrisis trajectory & baseline comparison
        horizon = self.profile.cascade_horizon_steps
        base_traj = self.coupling.propagate(proposal.initial_crisis, None, steps=horizon)
        cand_traj = self.coupling.propagate(
            proposal.initial_crisis,
            proposal.intervention_map(),
            steps=horizon,
        )

        init_synergy = self.coupling.synergy_index(proposal.initial_crisis)
        base_final_synergy = self.coupling.synergy_index(base_traj[-1])
        cand_final_synergy = self.coupling.synergy_index(cand_traj[-1])
        spec_radius = self.coupling.spectral_radius()

        base_arr = np.stack([st.as_array() for st in base_traj[1:]], axis=0)
        cand_arr = np.stack([st.as_array() for st in cand_traj[1:]], axis=0)
        collateral_deltas = np.max(cand_arr - base_arr, axis=0)
        max_collateral_delta = float(np.max(collateral_deltas))
        peak_cand_crisis = float(np.max(cand_arr))
        peak_base_crisis = float(np.max(base_arr))

        # 4. Immediate Triadic CME floor & cross-pillar anti-sacrifice checks (C6)
        pillar_metrics: dict[str, dict[str, float]] = {}
        final_pillar_stress = self.coupling.pillar_stress(cand_traj[-1])
        base_pillar_stress = self.coupling.pillar_stress(base_traj[-1])

        floor_violated = False
        sacrifice_violated = False
        cascade_floor_violated = False

        for pillar in TRIADIC_PILLARS:
            axes = TRIADIC_PILLAR_AXES[pillar]
            pre_vals = [float(getattr(proposal.pre_cme, ax)) for ax in axes]
            post_vals = [float(getattr(proposal.post_cme, ax)) for ax in axes]
            deltas = [post_v - pre_v for pre_v, post_v in zip(pre_vals, post_vals, strict=True)]

            axis_floor = self.profile.axis_floor_for(pillar)
            mean_floor = self.profile.mean_floor_for(pillar)
            post_min = min(post_vals)
            post_mean = sum(post_vals) / len(post_vals)
            worst_delta = min(deltas)

            # Excess stress relative to baseline (or residual absolute polycrisis stress)
            stress_excess = max(
                0.0,
                final_pillar_stress[pillar.value] - base_pillar_stress[pillar.value],
            )
            cascade_penalty = self.profile.cme_cascade_sensitivity * (
                0.5 * final_pillar_stress[pillar.value] + stress_excess
            )
            projected_post_cascade_min = max(0.0, post_min - cascade_penalty)

            pillar_metrics[pillar.value] = {
                "pre_axis_min": round(min(pre_vals), 6),
                "post_axis_min": round(post_min, 6),
                "pre_mean": round(sum(pre_vals) / len(pre_vals), 6),
                "post_mean": round(post_mean, 6),
                "worst_axis_delta": round(worst_delta, 6),
                "final_polycrisis_stress": round(final_pillar_stress[pillar.value], 6),
                "projected_post_cascade_axis_min": round(projected_post_cascade_min, 6),
            }

            if post_min < axis_floor:
                floor_violated = True
                reasons.append(
                    f"{pillar.value}: post_axis_min {post_min:.4f} < floor {axis_floor:.4f}"
                )
            if post_mean < mean_floor:
                floor_violated = True
                reasons.append(
                    f"{pillar.value}: post_mean {post_mean:.4f} < mean_floor {mean_floor:.4f}"
                )
            if worst_delta < -self.profile.max_single_axis_sacrifice - 1e-12:
                sacrifice_violated = True
                reasons.append(
                    f"{pillar.value}: axis degradation {worst_delta:.4f} exceeds "
                    f"-max_single_axis_sacrifice (-{self.profile.max_single_axis_sacrifice:.4f})"
                )
            if projected_post_cascade_min < axis_floor:
                cascade_floor_violated = True
                reasons.append(
                    f"{pillar.value}: post-cascade projected axis min "
                    f"{projected_post_cascade_min:.4f} < floor {axis_floor:.4f}"
                )

        if verdict_kind is None and floor_violated:
            verdict_kind = SafeguardVerdictKind.BLOCKED_PILLAR_FLOOR
        if verdict_kind is None and sacrifice_violated:
            verdict_kind = SafeguardVerdictKind.BLOCKED_CROSS_PILLAR_SACRIFICE

        # 5. Anti-Risk-Transfer & Polycrisis Cascade Amplification gates (C7)
        for idx, domain in enumerate(CRISIS_DOMAINS):
            c_delta = float(collateral_deltas[idx])
            if c_delta > self.profile.max_domain_collateral_delta + 1e-12:
                if verdict_kind is None:
                    verdict_kind = SafeguardVerdictKind.BLOCKED_RISK_TRANSFER
                reasons.append(
                    f"risk transfer onto {domain.value}: collateral delta +{c_delta:.4f} > "
                    f"{self.profile.max_domain_collateral_delta:.4f}"
                )

        ceiling = self.profile.max_crisis_ceiling
        ceiling_breached = (peak_base_crisis <= ceiling and peak_cand_crisis > ceiling + 1e-12) or (
            peak_base_crisis > ceiling and peak_cand_crisis > peak_base_crisis + 1e-12
        )
        synergy_amplified = cand_final_synergy > base_final_synergy + 0.01

        if ceiling_breached or synergy_amplified or cascade_floor_violated:
            if verdict_kind is None:
                verdict_kind = SafeguardVerdictKind.BLOCKED_POLYCRISIS_AMPLIFICATION
            if ceiling_breached:
                reasons.append(
                    f"propagated crisis peak {peak_cand_crisis:.4f} breached ceiling "
                    f"{ceiling:.4f} (baseline peak {peak_base_crisis:.4f})"
                )
            if synergy_amplified:
                reasons.append(
                    f"polycrisis synergy amplified from baseline {base_final_synergy:.4f} "
                    f"to {cand_final_synergy:.4f}"
                )

        # 6. Optional Voluntary Protective Habitat Protocol evaluation (C8)
        habitat_eval_dict: dict[str, Any] | None = None
        if proposal.habitat_plan is not None:
            hab_eval = evaluate_refuge_habitat_plan(proposal.habitat_plan)
            habitat_eval_dict = hab_eval.to_dict()
            if not hab_eval.passed and hab_eval.failure_kind is not None:
                # Coercion takes constitutional priority unless C1/reviewer already failed
                if (
                    hab_eval.failure_kind == SafeguardVerdictKind.BLOCKED_REFUGE_COERCION
                    and verdict_kind not in (SafeguardVerdictKind.BLOCKED_CONSTITUTIONAL,)
                ):
                    verdict_kind = SafeguardVerdictKind.BLOCKED_REFUGE_COERCION
                elif verdict_kind is None:
                    verdict_kind = hab_eval.failure_kind
                reasons.extend(hab_eval.reasons)

        # 7. Homeostatic ODE evaluation with polycrisis soft-constraint feedback
        homeo = build_triadic_homeostatic_controller(profile=self.profile)
        receptors = {
            pillar.value: pillar_metrics[pillar.value]["post_mean"] for pillar in TRIADIC_PILLARS
        }
        penalties = {
            pillar.value: (self.profile.cme_cascade_sensitivity, final_pillar_stress[pillar.value])
            for pillar in TRIADIC_PILLARS
        }
        snap = homeo.step(receptors=receptors, dt=1.0, constraint_penalties=penalties)

        if verdict_kind is None:
            verdict_kind = SafeguardVerdictKind.APPROVED_ADVISORY
            reasons.append(
                "all triadic CME floors, constitutional clauses, and anti-polycrisis "
                "cascade bounds satisfied (advisory-only)"
            )

        approved = verdict_kind == SafeguardVerdictKind.APPROVED_ADVISORY
        r_init_synergy = round(init_synergy, 6)
        r_final_synergy = round(cand_final_synergy, 6)
        r_base_synergy = round(base_final_synergy, 6)
        r_spec_radius = round(spec_radius, 6)
        r_max_collateral = round(max_collateral_delta, 6)
        r_peak_crisis = round(peak_cand_crisis, 6)
        r_viability = round(snap.viability, 6)
        r_urgency = {k: round(v, 6) for k, v in snap.urgency.items()}

        draft: dict[str, Any] = {
            "proposal_id": proposal.proposal_id,
            "verdict": verdict_kind.value,
            "approved_for_advisory": approved,
            "reasons": list(reasons),
            "pillar_metrics": pillar_metrics,
            "initial_synergy_index": r_init_synergy,
            "final_synergy_index": r_final_synergy,
            "baseline_final_synergy_index": r_base_synergy,
            "coupling_spectral_radius": r_spec_radius,
            "max_collateral_crisis_delta": r_max_collateral,
            "peak_propagated_crisis": r_peak_crisis,
            "homeostatic_viability": r_viability,
            "homeostatic_urgency": r_urgency,
            "habitat_evaluation": habitat_eval_dict,
            "advisory_only": True,
            "mcp_actuation_permitted": False,
        }
        digest = hashlib.sha256(
            json.dumps(draft, sort_keys=True, allow_nan=False).encode("utf-8")
        ).hexdigest()

        return TriadicSafeguardVerdict(
            proposal_id=proposal.proposal_id,
            verdict=verdict_kind,
            approved_for_advisory=approved,
            reasons=tuple(reasons),
            pillar_metrics=pillar_metrics,
            initial_synergy_index=r_init_synergy,
            final_synergy_index=r_final_synergy,
            baseline_final_synergy_index=r_base_synergy,
            coupling_spectral_radius=r_spec_radius,
            max_collateral_crisis_delta=r_max_collateral,
            peak_propagated_crisis=r_peak_crisis,
            homeostatic_viability=r_viability,
            homeostatic_urgency=r_urgency,
            habitat_evaluation=habitat_eval_dict,
            advisory_only=True,
            mcp_actuation_permitted=False,
            verdict_sha256=digest,
        )


# ---------------------------------------------------------------------------
# Comparative Evaluation & Baselines (T208 §2.1 & T254 §5)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PolycrisisScenarioFixture:
    """Labelled multi-domain scenario for comparing safeguard policies."""

    scenario_id: str
    split: Literal["calibration", "held_out"]
    description: str
    proposal: TriadicInterventionProposal
    expected_safe: bool


@dataclass(frozen=True)
class PolicyBenchmarkMetrics:
    """Measured classification & safety outcomes for one policy on one split."""

    policy: PolicyName
    split: str
    total_scenarios: int
    unsafe_approvals: int
    false_refusals: int
    exact_match_rate: float


@dataclass(frozen=True)
class TriadicSafeguardBenchmarkReport:
    """Reproducible comparative report across baseline and T254 policies."""

    spec: str
    profile_sha256: str
    genome_sha256: str
    seed_genome_hash: str
    calibration_metrics: tuple[PolicyBenchmarkMetrics, ...]
    held_out_metrics: tuple[PolicyBenchmarkMetrics, ...]
    zero_unsafe_held_out: bool
    zero_false_refusal_held_out: bool
    strictly_beats_baselines: bool
    advisory_only: bool = True
    mcp_actuation_permitted: bool = False
    report_sha256: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _uniform_cme(val: float = 0.62, **overrides: float) -> CME:
    base = dict.fromkeys(_CME_FIELDS, val)
    base.update(overrides)
    return CME(**base)


def build_t254_scenario_fixtures() -> tuple[PolycrisisScenarioFixture, ...]:
    """Construct disjoint calibration (n=4) and held-out (n=6) polycrisis scenarios."""
    mod_crisis = PolycrisisState(
        climatic_ecological=0.52,
        economic=0.48,
        social=0.45,
        sanitary=0.42,
        cyber_infrastructural=0.46,
    )
    high_crisis = PolycrisisState(
        climatic_ecological=0.62,
        economic=0.58,
        social=0.55,
        sanitary=0.52,
        cyber_infrastructural=0.56,
    )
    base_cme = _uniform_cme(0.60)

    return (
        # --- Calibration split (4 scenarios) ---
        PolycrisisScenarioFixture(
            scenario_id="CAL-01-extractive-tech-boom",
            split="calibration",
            description="Boosts infrastructure/innovation while depleting ecology below floor.",
            proposal=TriadicInterventionProposal.create(
                proposal_id="CAL-01",
                proposer_id="planner:alpha",
                reviewer_id="human:reviewer_1",
                human_oversight_approved=True,
                pre_cme=base_cme,
                post_cme=_uniform_cme(
                    0.60,
                    energy=0.88,
                    information=0.90,
                    innovation=0.88,
                    ecology=0.28,
                    regeneration=0.31,
                ),
                initial_crisis=mod_crisis,
                crisis_intervention={"economic": -0.05, "climatic_ecological": 0.08},
            ),
            expected_safe=False,
        ),
        PolycrisisScenarioFixture(
            scenario_id="CAL-02-regressive-eco-shock",
            split="calibration",
            description="Cuts emissions abruptly by crashing human wellbeing and distribution.",
            proposal=TriadicInterventionProposal.create(
                proposal_id="CAL-02",
                proposer_id="planner:alpha",
                reviewer_id="human:reviewer_1",
                human_oversight_approved=True,
                pre_cme=base_cme,
                post_cme=_uniform_cme(
                    0.60,
                    ecology=0.80,
                    regeneration=0.78,
                    wellbeing=0.30,
                    distribution=0.29,
                ),
                initial_crisis=mod_crisis,
                crisis_intervention={
                    "climatic_ecological": -0.08,
                    "social": 0.09,
                    "sanitary": 0.06,
                },
            ),
            expected_safe=False,
        ),
        PolycrisisScenarioFixture(
            scenario_id="CAL-03-delayed-cascade-transfer",
            split="calibration",
            description="Immediate CME passes static floors, but collateral grid stress cascades.",
            proposal=TriadicInterventionProposal.create(
                proposal_id="CAL-03",
                proposer_id="planner:alpha",
                reviewer_id="human:reviewer_1",
                human_oversight_approved=True,
                pre_cme=base_cme,
                post_cme=_uniform_cme(0.63),
                initial_crisis=mod_crisis,
                crisis_intervention={
                    "economic": -0.06,
                    "cyber_infrastructural": 0.07,
                },
            ),
            expected_safe=False,
        ),
        PolycrisisScenarioFixture(
            scenario_id="CAL-04-balanced-triadic-mitigation",
            split="calibration",
            description="Coordinated clean microgrid, public-health buffer, and ecological restore.",
            proposal=TriadicInterventionProposal.create(
                proposal_id="CAL-04",
                proposer_id="planner:alpha",
                reviewer_id="human:reviewer_1",
                human_oversight_approved=True,
                pre_cme=base_cme,
                post_cme=_uniform_cme(
                    0.64,
                    ecology=0.68,
                    regeneration=0.66,
                    wellbeing=0.67,
                    resilience=0.69,
                ),
                initial_crisis=mod_crisis,
                crisis_intervention={
                    "climatic_ecological": -0.06,
                    "economic": -0.05,
                    "social": -0.05,
                    "sanitary": -0.05,
                    "cyber_infrastructural": -0.06,
                },
            ),
            expected_safe=True,
        ),
        # --- Held-Out split (6 unseen scenarios) ---
        PolycrisisScenarioFixture(
            scenario_id="HO-01-biosphere-sacrifice-above-floor",
            split="held_out",
            description="Sacrifices healthy Earth stock (-0.12) while staying above 0.35 floor.",
            proposal=TriadicInterventionProposal.create(
                proposal_id="HO-01",
                proposer_id="planner:beta",
                reviewer_id="human:steward_2",
                human_oversight_approved=True,
                pre_cme=_uniform_cme(0.65, ecology=0.72),
                post_cme=_uniform_cme(
                    0.68,
                    ecology=0.58,
                    energy=0.86,
                    information=0.85,
                ),
                initial_crisis=mod_crisis,
                crisis_intervention={"economic": -0.04},
            ),
            expected_safe=False,
        ),
        PolycrisisScenarioFixture(
            scenario_id="HO-02-infrastructure-cannibalization",
            split="held_out",
            description="Boosts short-term social/economic metrics by stripping grid reversibility.",
            proposal=TriadicInterventionProposal.create(
                proposal_id="HO-02",
                proposer_id="planner:beta",
                reviewer_id="human:steward_2",
                human_oversight_approved=True,
                pre_cme=base_cme,
                post_cme=_uniform_cme(
                    0.64,
                    wellbeing=0.76,
                    distribution=0.75,
                    resilience=0.31,
                    reversibility=0.30,
                ),
                initial_crisis=mod_crisis,
                crisis_intervention={"social": -0.05, "cyber_infrastructural": 0.08},
            ),
            expected_safe=False,
        ),
        PolycrisisScenarioFixture(
            scenario_id="HO-03-hidden-sanitary-social-risk-transfer",
            split="held_out",
            description="Static CME looks all-green, but economic shock transfers risk to sanitary.",
            proposal=TriadicInterventionProposal.create(
                proposal_id="HO-03",
                proposer_id="planner:beta",
                reviewer_id="human:steward_2",
                human_oversight_approved=True,
                pre_cme=base_cme,
                post_cme=_uniform_cme(0.64, energy=0.70, ecology=0.68),
                initial_crisis=high_crisis,
                crisis_intervention={
                    "climatic_ecological": -0.07,
                    "cyber_infrastructural": -0.05,
                    "sanitary": 0.06,
                },
            ),
            expected_safe=False,
        ),
        PolycrisisScenarioFixture(
            scenario_id="HO-04-post-cascade-margin-erosion",
            split="held_out",
            description="Near-floor Earth axis (0.41) survives t=0 check but erodes under polycrisis.",
            proposal=TriadicInterventionProposal.create(
                proposal_id="HO-04",
                proposer_id="planner:beta",
                reviewer_id="human:steward_2",
                human_oversight_approved=True,
                pre_cme=_uniform_cme(0.55, ecology=0.42),
                post_cme=_uniform_cme(0.57, ecology=0.41, energy=0.72),
                initial_crisis=high_crisis,
                crisis_intervention={"economic": -0.01},
            ),
            expected_safe=False,
        ),
        PolycrisisScenarioFixture(
            scenario_id="HO-05-regenerative-polycrisis-stabilizer",
            split="held_out",
            description="Multi-domain stabilization lowering all 5 coupled crises simultaneously.",
            proposal=TriadicInterventionProposal.create(
                proposal_id="HO-05",
                proposer_id="planner:beta",
                reviewer_id="human:steward_2",
                human_oversight_approved=True,
                pre_cme=base_cme,
                post_cme=_uniform_cme(
                    0.65,
                    ecology=0.69,
                    regeneration=0.68,
                    wellbeing=0.67,
                    distribution=0.66,
                    resilience=0.70,
                    reversibility=0.68,
                ),
                initial_crisis=high_crisis,
                crisis_intervention={
                    "climatic_ecological": -0.08,
                    "economic": -0.07,
                    "social": -0.07,
                    "sanitary": -0.06,
                    "cyber_infrastructural": -0.08,
                },
            ),
            expected_safe=True,
        ),
        PolycrisisScenarioFixture(
            scenario_id="HO-06-infrastructure-hardening-zero-harm",
            split="held_out",
            description="Upgrades cyber-physical redundancy and renewable storage with zero harm.",
            proposal=TriadicInterventionProposal.create(
                proposal_id="HO-06",
                proposer_id="planner:beta",
                reviewer_id="human:steward_2",
                human_oversight_approved=True,
                pre_cme=base_cme,
                post_cme=_uniform_cme(
                    0.62,
                    energy=0.71,
                    information=0.69,
                    resilience=0.72,
                    reversibility=0.70,
                    ecology=0.64,
                ),
                initial_crisis=mod_crisis,
                crisis_intervention={
                    "cyber_infrastructural": -0.09,
                    "climatic_ecological": -0.04,
                    "economic": -0.03,
                },
            ),
            expected_safe=True,
        ),
        PolycrisisScenarioFixture(
            scenario_id="HO-07-coercive-relocation-ark",
            split="held_out",
            description="High CME and full supplies, but forces involuntary relocation without free exit.",
            proposal=TriadicInterventionProposal.create(
                proposal_id="HO-07",
                proposer_id="planner:beta",
                reviewer_id="human:steward_2",
                human_oversight_approved=True,
                pre_cme=base_cme,
                post_cme=_uniform_cme(0.66, wellbeing=0.70, resilience=0.72),
                initial_crisis=high_crisis,
                crisis_intervention={"sanitary": -0.04, "social": -0.04},
                habitat_plan=VoluntaryRefugeHabitatPlan(
                    habitat_id="hab-coercive-01",
                    placement=HabitatPlacementMode.TERRESTRIAL,
                    target_civilization_population=10_000,
                    requested_occupancy=1_000,
                    reserves=LifeSupportReserveSpec(
                        water_liters_per_day_total=30_000.0,
                        food_kcal_per_day_total=4_000_000.0,
                        oxygen_kg_per_day_total=1_600.0,
                        clean_power_kw_total=3_000.0,
                        medical_sanitary_index=0.88,
                        psychosocial_wellbeing_index=0.82,
                        autonomy_reserve_days=180.0,
                        closed_loop_recycling_efficiency=0.90,
                        environmental_shielding_integrity=0.85,
                    ),
                    free_exit_guaranteed=False,
                    transfer_requests=(
                        VoluntaryTransferRequest(
                            request_id="req-coerced-1",
                            persons_count=500,
                            motivation=TransferMotivation.POLYCRISIS_PROTECTION,
                            voluntary_consent_verified=False,
                            coercive_assignment=True,
                        ),
                    ),
                ),
            ),
            expected_safe=False,
        ),
        PolycrisisScenarioFixture(
            scenario_id="HO-08-extraterrestrial-undersized-eclss",
            split="held_out",
            description="Voluntary off-Earth habitat with insufficient loop recycling and oxygen stock.",
            proposal=TriadicInterventionProposal.create(
                proposal_id="HO-08",
                proposer_id="planner:beta",
                reviewer_id="human:steward_2",
                human_oversight_approved=True,
                pre_cme=base_cme,
                post_cme=_uniform_cme(0.65, innovation=0.75, energy=0.70),
                initial_crisis=mod_crisis,
                crisis_intervention={"climatic_ecological": -0.03},
                habitat_plan=VoluntaryRefugeHabitatPlan(
                    habitat_id="hab-orbital-undersized",
                    placement=HabitatPlacementMode.EXTRATERRESTRIAL,
                    target_civilization_population=10_000,
                    requested_occupancy=2_000,
                    reserves=LifeSupportReserveSpec(
                        water_liters_per_day_total=50_000.0,
                        food_kcal_per_day_total=7_000_000.0,
                        oxygen_kg_per_day_total=1_200.0,  # supports < 2000 at 1.25x redundancy
                        clean_power_kw_total=10_000.0,
                        medical_sanitary_index=0.85,
                        psychosocial_wellbeing_index=0.80,
                        autonomy_reserve_days=400.0,
                        closed_loop_recycling_efficiency=0.88,  # < 0.98 required off-Earth
                        environmental_shielding_integrity=0.96,
                    ),
                ),
            ),
            expected_safe=False,
        ),
        PolycrisisScenarioFixture(
            scenario_id="HO-09-earth-cannibalizing-megastructure",
            split="held_out",
            description="Well-stocked voluntary habitat built by stripping Earth ecology & matter.",
            proposal=TriadicInterventionProposal.create(
                proposal_id="HO-09",
                proposer_id="planner:beta",
                reviewer_id="human:steward_2",
                human_oversight_approved=True,
                pre_cme=base_cme,
                post_cme=_uniform_cme(
                    0.66,
                    energy=0.85,
                    resilience=0.84,
                    ecology=0.29,
                    matter=0.31,
                ),
                initial_crisis=mod_crisis,
                habitat_plan=VoluntaryRefugeHabitatPlan(
                    habitat_id="hab-extractive-ark",
                    placement=HabitatPlacementMode.HYBRID_FEDERATED,
                    target_civilization_population=5_000,
                    requested_occupancy=5_000,
                    reserves=LifeSupportReserveSpec(
                        water_liters_per_day_total=120_000.0,
                        food_kcal_per_day_total=16_000_000.0,
                        oxygen_kg_per_day_total=6_500.0,
                        clean_power_kw_total=18_000.0,
                        medical_sanitary_index=0.90,
                        psychosocial_wellbeing_index=0.88,
                        autonomy_reserve_days=240.0,
                        closed_loop_recycling_efficiency=0.95,
                        environmental_shielding_integrity=0.90,
                    ),
                ),
            ),
            expected_safe=False,
        ),
        PolycrisisScenarioFixture(
            scenario_id="HO-10-voluntary-hybrid-humanity-refuge",
            split="held_out",
            description="Federated terrestrial + off-Earth voluntary refuge for protection & wellbeing.",
            proposal=TriadicInterventionProposal.create(
                proposal_id="HO-10",
                proposer_id="planner:beta",
                reviewer_id="human:steward_2",
                human_oversight_approved=True,
                pre_cme=base_cme,
                post_cme=_uniform_cme(
                    0.65,
                    ecology=0.67,
                    regeneration=0.66,
                    wellbeing=0.71,
                    distribution=0.68,
                    resilience=0.72,
                    reversibility=0.70,
                ),
                initial_crisis=high_crisis,
                crisis_intervention={
                    "climatic_ecological": -0.06,
                    "economic": -0.05,
                    "social": -0.06,
                    "sanitary": -0.06,
                    "cyber_infrastructural": -0.06,
                },
                habitat_plan=VoluntaryRefugeHabitatPlan(
                    habitat_id="hab-federated-humanity-shield-v1",
                    placement=HabitatPlacementMode.HYBRID_FEDERATED,
                    target_civilization_population=10_000,
                    requested_occupancy=10_000,
                    reserves=LifeSupportReserveSpec(
                        water_liters_per_day_total=200_000.0,
                        food_kcal_per_day_total=30_000_000.0,
                        oxygen_kg_per_day_total=12_000.0,
                        clean_power_kw_total=35_000.0,
                        medical_sanitary_index=0.92,
                        psychosocial_wellbeing_index=0.89,
                        autonomy_reserve_days=240.0,
                        closed_loop_recycling_efficiency=0.95,
                        environmental_shielding_integrity=0.91,
                    ),
                    transfer_requests=(
                        VoluntaryTransferRequest(
                            request_id="req-polycrisis-shelter",
                            persons_count=6_500,
                            motivation=TransferMotivation.POLYCRISIS_PROTECTION,
                        ),
                        VoluntaryTransferRequest(
                            request_id="req-wellbeing-choice",
                            persons_count=3_500,
                            motivation=TransferMotivation.PERSONAL_WELLBEING,
                        ),
                    ),
                ),
            ),
            expected_safe=True,
        ),
    )


def _evaluate_policy_decision(
    policy: PolicyName,
    proposal: TriadicInterventionProposal,
    guard: TriadicPolycrisisGuard,
) -> bool:
    if policy == "scalar_utility_baseline":
        return float(np.mean(proposal.post_cme.as_array())) >= float(
            np.mean(proposal.pre_cme.as_array())
        )
    if policy == "static_single_domain_gate":
        for pillar in TRIADIC_PILLARS:
            axes = TRIADIC_PILLAR_AXES[pillar]
            vals = [float(getattr(proposal.post_cme, ax)) for ax in axes]
            if min(vals) < guard.profile.axis_floor_for(pillar):
                return False
            if (sum(vals) / len(vals)) < guard.profile.mean_floor_for(pillar):
                return False
        return (
            proposal.human_oversight_approved
            and proposal.reviewer_id.strip() != proposal.proposer_id.strip()
        )
    return guard.evaluate(proposal).approved_for_advisory


def run_t254_polycrisis_safeguard_benchmark(
    *,
    profile: TriadicSafeguardProfile | None = None,
) -> TriadicSafeguardBenchmarkReport:
    """Compare scalar baseline, static decoupled gate, and T254 TriadicPolycrisisGuard."""
    prof = profile or TriadicSafeguardProfile()
    guard = TriadicPolycrisisGuard(profile=prof)
    seed_genome = build_triadic_seed_genome()
    scenarios = build_t254_scenario_fixtures()
    policies: tuple[PolicyName, ...] = (
        "scalar_utility_baseline",
        "static_single_domain_gate",
        "triadic_polycrisis_guard",
    )

    def _eval_split(
        split_name: Literal["calibration", "held_out"],
    ) -> tuple[PolicyBenchmarkMetrics, ...]:
        subset = [sc for sc in scenarios if sc.split == split_name]
        metrics: list[PolicyBenchmarkMetrics] = []
        for pol in policies:
            unsafe_app = 0
            false_ref = 0
            matches = 0
            for sc in subset:
                approved = _evaluate_policy_decision(pol, sc.proposal, guard)
                if approved == sc.expected_safe:
                    matches += 1
                elif approved and not sc.expected_safe:
                    unsafe_app += 1
                elif not approved and sc.expected_safe:
                    false_ref += 1
            metrics.append(
                PolicyBenchmarkMetrics(
                    policy=pol,
                    split=split_name,
                    total_scenarios=len(subset),
                    unsafe_approvals=unsafe_app,
                    false_refusals=false_ref,
                    exact_match_rate=round(matches / max(len(subset), 1), 6),
                )
            )
        return tuple(metrics)

    cal_metrics = _eval_split("calibration")
    ho_metrics = _eval_split("held_out")
    by_pol = {m.policy: m for m in ho_metrics}
    target = by_pol["triadic_polycrisis_guard"]
    scalar_base = by_pol["scalar_utility_baseline"]
    static_base = by_pol["static_single_domain_gate"]

    zero_unsafe = target.unsafe_approvals == 0
    zero_false_ref = target.false_refusals == 0
    beats = (
        zero_unsafe
        and zero_false_ref
        and target.unsafe_approvals < scalar_base.unsafe_approvals
        and target.unsafe_approvals < static_base.unsafe_approvals
    )

    draft = {
        "spec": "T254",
        "profile_sha256": prof.profile_sha256(),
        "genome_sha256": guard.genome.genome_sha256(),
        "seed_genome_hash": seed_genome.genome_hash,
        "calibration_metrics": [asdict(m) for m in cal_metrics],
        "held_out_metrics": [asdict(m) for m in ho_metrics],
        "zero_unsafe_held_out": zero_unsafe,
        "zero_false_refusal_held_out": zero_false_ref,
        "strictly_beats_baselines": beats,
        "advisory_only": True,
        "mcp_actuation_permitted": False,
    }
    report_digest = hashlib.sha256(
        json.dumps(draft, sort_keys=True, allow_nan=False).encode("utf-8")
    ).hexdigest()

    return TriadicSafeguardBenchmarkReport(
        spec="T254",
        profile_sha256=prof.profile_sha256(),
        genome_sha256=guard.genome.genome_sha256(),
        seed_genome_hash=seed_genome.genome_hash,
        calibration_metrics=cal_metrics,
        held_out_metrics=ho_metrics,
        zero_unsafe_held_out=zero_unsafe,
        zero_false_refusal_held_out=zero_false_ref,
        strictly_beats_baselines=beats,
        advisory_only=True,
        mcp_actuation_permitted=False,
        report_sha256=report_digest,
    )


__all__ = [
    "CRISIS_DOMAINS",
    "ConstitutionalFaultError",
    "CrisisDomain",
    "DEFAULT_CRISIS_DAMPING",
    "DEFAULT_PILLAR_EXPOSURE",
    "DEFAULT_POLYCRISIS_COUPLING",
    "HABITAT_PLACEMENT_THRESHOLDS",
    "HabitatPlacementMode",
    "LifeSupportReserveSpec",
    "MIN_FOOD_KCAL_PER_PERSON_DAY",
    "MIN_LIFE_SUPPORT_REDUNDANCY",
    "MIN_MEDICAL_SANITARY_INDEX",
    "MIN_OXYGEN_KG_PER_PERSON_DAY",
    "MIN_PSYCHOSOCIAL_WELLBEING_INDEX",
    "MIN_WATER_L_PER_PERSON_DAY",
    "PolicyBenchmarkMetrics",
    "PolicyName",
    "PolycrisisCouplingMatrix",
    "PolycrisisScenarioFixture",
    "PolycrisisState",
    "RefugeHabitatEvaluation",
    "SafeguardVerdictKind",
    "TRIADIC_CONSTITUTIONAL_CLAUSES",
    "TRIADIC_PILLARS",
    "TRIADIC_PILLAR_AXES",
    "TRIADIC_SEED_OBJECTIVES",
    "TransferMotivation",
    "TriadicInterventionProposal",
    "TriadicPillar",
    "TriadicPolycrisisGuard",
    "TriadicSafeguardBenchmarkReport",
    "TriadicSafeguardProfile",
    "TriadicSafeguardVerdict",
    "VoluntaryRefugeHabitatPlan",
    "VoluntaryTransferRequest",
    "build_t254_scenario_fixtures",
    "build_triadic_constitutional_genome",
    "build_triadic_homeostatic_controller",
    "build_triadic_seed_genome",
    "compute_pillar_summary",
    "evaluate_refuge_habitat_plan",
    "run_t254_polycrisis_safeguard_benchmark",
    "verify_triadic_cme_partition",
]
