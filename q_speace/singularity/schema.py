"""T234: Canonical schemas for genome_epigenome.v1, PhaseTelemetry, TransitionVerdict, and Ledger."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

SingularityStage = Literal[
    "PRE_NUCLEATION",
    "NUCLEATION",
    "STAGE_1_ALGORITHMIC",
    "STAGE_2_BOUNDED_RECURSIVE",
    "STAGE_3_CLOSURE_SIM",
]

BottleneckKind = Literal[
    "NONE",
    "CONSTITUTIONAL_SAFETY",
    "SEMANTIC_ENTROPY",
    "THERMODYNAMIC_INERTIA",
    "ALLOPOIETIC_DEPENDENCE",
    "VALIDATION_DEFICIT",
]


class EpigeneticFaultError(RuntimeError):
    """Raised when an operation violates genome write-lock or constitutional boundaries."""


def _require_finite(name: str, val: float) -> None:
    if not math.isfinite(val):
        raise ValueError(f"{name} must be finite (got {val!r})")


def _require_unit_interval(name: str, val: float) -> None:
    _require_finite(name, val)
    if not (0.0 <= val <= 1.0):
        raise ValueError(f"{name} must be in [0, 1] (got {val!r})")


@dataclass(frozen=True)
class PhaseTransitionThresholds:
    """Preregistered thresholds for Stage 1–3 assessment and non-compensable physical brakes."""

    # Nucleation: early catalytic loop & timescale shift.
    min_nucleation_decoupling: float = 2.0
    min_nucleation_k: float = 1.05
    # Stage 1: algorithmic acceleration.
    min_timescale_decoupling: float = 10.0
    min_autocatalytic_k: float = 1.25
    min_independent_validation_rate: float = 0.95
    # Stage 2: bounded recursive autonomy (anti-collapse + governance).
    max_semantic_entropy_drift: float = 0.05
    min_net_verified_improvement: float = 0.01
    min_consecutive_verified_cycles: int = 3
    min_rollback_pass_rate: float = 1.0
    # Physical brake: instantaneous + energy-windowed Sevo & thermal inertia.
    min_sevo: float = 1.5
    min_sevo_window_mean: float = 1.5
    max_thermal_load_ratio: float = 0.85
    # Stage 3: cycle closure telemetry (simulation/readiness only).
    max_allopoietic_dependence: float = 0.25
    min_twin_recovery_rate: float = 0.95


@dataclass(frozen=True)
class PhaseTelemetry:
    """Measured order parameters and physical-brake metrics for an AI system or ecosystem."""

    timescale_decoupling_ratio: float
    autocatalytic_k: float
    independent_validation_rate: float
    semantic_entropy_drift: float
    net_verified_improvement: float
    consecutive_verified_cycles: int
    allopoietic_dependence: float
    sevo: float
    thermal_load_ratio: float
    sevo_window_mean: float | None = None
    sevo_energy_samples: tuple[tuple[float, float], ...] = ()
    twin_recovery_rate: float = 0.0
    constitutional_faults: int = 0
    rollback_pass_rate: float = 1.0
    independent_review_passed: bool = False
    critical_regressions: int = 0
    sandboxed: bool = True

    def __post_init__(self) -> None:
        _require_finite("timescale_decoupling_ratio", self.timescale_decoupling_ratio)
        if self.timescale_decoupling_ratio < 0.0:
            raise ValueError("timescale_decoupling_ratio must be >= 0")
        _require_finite("autocatalytic_k", self.autocatalytic_k)
        if self.autocatalytic_k <= 0.0:
            raise ValueError("autocatalytic_k must be > 0")
        _require_unit_interval("independent_validation_rate", self.independent_validation_rate)
        _require_unit_interval("semantic_entropy_drift", self.semantic_entropy_drift)
        _require_finite("net_verified_improvement", self.net_verified_improvement)
        if self.consecutive_verified_cycles < 0:
            raise ValueError("consecutive_verified_cycles must be >= 0")
        _require_unit_interval("allopoietic_dependence", self.allopoietic_dependence)
        _require_finite("sevo", self.sevo)
        if self.sevo < 0.0:
            raise ValueError("sevo must be >= 0")
        if self.sevo_window_mean is not None:
            _require_finite("sevo_window_mean", self.sevo_window_mean)
            if self.sevo_window_mean < 0.0:
                raise ValueError("sevo_window_mean must be >= 0")
        for energy_j, sevo_i in self.sevo_energy_samples:
            _require_finite("sevo_energy_samples.energy_j", energy_j)
            _require_finite("sevo_energy_samples.sevo", sevo_i)
            if energy_j <= 0.0 or sevo_i < 0.0:
                raise ValueError("sevo_energy_samples require energy_j > 0 and sevo >= 0")
        _require_finite("thermal_load_ratio", self.thermal_load_ratio)
        if self.thermal_load_ratio < 0.0:
            raise ValueError("thermal_load_ratio must be >= 0")
        _require_unit_interval("twin_recovery_rate", self.twin_recovery_rate)
        if self.constitutional_faults < 0:
            raise ValueError("constitutional_faults must be >= 0")
        _require_unit_interval("rollback_pass_rate", self.rollback_pass_rate)
        if self.critical_regressions < 0:
            raise ValueError("critical_regressions must be >= 0")


PhaseTransitionTelemetry = PhaseTelemetry


@dataclass(frozen=True)
class TransitionVerdict:
    """Deterministic, advisory-only assessment of phase-transition stage and active brakes."""

    stage: SingularityStage
    stage_index: int
    stage_gates: dict[str, bool]
    physical_brakes_active: tuple[BottleneckKind, ...]
    dominant_bottleneck: BottleneckKind
    autopoiesis_closure_index: float
    causal_anchoring_index: float
    thermodynamic_headroom: float
    effective_sevo_window: float
    thermal_throttling_required: bool
    failed_gates: tuple[str, ...]
    recommendations: tuple[str, ...]
    advisory_only: bool = True
    physical_actuation_permitted: bool = False
    self_approval_permitted: bool = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["physical_brakes_active"] = list(self.physical_brakes_active)
        data["failed_gates"] = list(self.failed_gates)
        data["recommendations"] = list(self.recommendations)
        return data


PhaseTransitionAssessment = TransitionVerdict


@dataclass(frozen=True)
class EpigeneticLocus:
    """Definition of one bounded adaptive regulatory locus with geodesic weight & margin."""

    name: str
    baseline: float
    min_value: float
    max_value: float
    max_step_delta: float
    homeostatic_decay: float = 0.10
    geodesic_weight: float = 1.0
    boundary_margin_ratio: float = 0.10
    description: str = ""

    def __post_init__(self) -> None:
        for fname, val in (
            ("baseline", self.baseline),
            ("min_value", self.min_value),
            ("max_value", self.max_value),
            ("max_step_delta", self.max_step_delta),
            ("homeostatic_decay", self.homeostatic_decay),
            ("geodesic_weight", self.geodesic_weight),
            ("boundary_margin_ratio", self.boundary_margin_ratio),
        ):
            _require_finite(fname, val)
        if not (self.min_value <= self.baseline <= self.max_value):
            raise ValueError(f"locus {self.name!r}: baseline must lie in [min_value, max_value]")
        if self.max_step_delta <= 0.0:
            raise ValueError(f"locus {self.name!r}: max_step_delta must be > 0")
        if not (0.0 <= self.homeostatic_decay <= 1.0):
            raise ValueError(f"locus {self.name!r}: homeostatic_decay must be in [0, 1]")
        if self.geodesic_weight <= 0.0:
            raise ValueError(f"locus {self.name!r}: geodesic_weight must be > 0")
        if not (0.0 < self.boundary_margin_ratio < 0.5):
            raise ValueError(f"locus {self.name!r}: boundary_margin_ratio must be in (0, 0.5)")

    def is_near_boundary(self, value: float) -> bool:
        margin = (self.max_value - self.min_value) * self.boundary_margin_ratio
        return value <= (self.min_value + margin) or value >= (self.max_value - margin)


DEFAULT_LOCI: tuple[EpigeneticLocus, ...] = (
    EpigeneticLocus(
        name="exploration_rate",
        baseline=0.20,
        min_value=0.02,
        max_value=0.50,
        max_step_delta=0.10,
        homeostatic_decay=0.12,
        geodesic_weight=1.2,
        description="Bounded search/mutation exploration factor.",
    ),
    EpigeneticLocus(
        name="memory_retention",
        baseline=0.75,
        min_value=0.30,
        max_value=0.98,
        max_step_delta=0.10,
        homeostatic_decay=0.08,
        geodesic_weight=1.0,
        description="Retention weight for verified causal memory entries.",
    ),
    EpigeneticLocus(
        name="verification_depth",
        baseline=0.60,
        min_value=0.30,
        max_value=1.00,
        max_step_delta=0.15,
        homeostatic_decay=0.05,
        geodesic_weight=1.0,
        description="Depth of external benchmark & invariant verification per cycle.",
    ),
    EpigeneticLocus(
        name="delegation_granularity",
        baseline=0.50,
        min_value=0.10,
        max_value=0.90,
        max_step_delta=0.12,
        homeostatic_decay=0.10,
        geodesic_weight=1.1,
        description="Scope granularity when partitioning tasks across sub-agents.",
    ),
    EpigeneticLocus(
        name="energy_throttling",
        baseline=0.50,
        min_value=0.20,
        max_value=0.95,
        max_step_delta=0.15,
        homeostatic_decay=0.10,
        geodesic_weight=0.8,
        description="Proactive compute throttling ratio to preserve Sevo & thermal headroom.",
    ),
    EpigeneticLocus(
        name="consensus_quorum",
        baseline=0.67,
        min_value=0.51,
        max_value=0.95,
        max_step_delta=0.10,
        homeostatic_decay=0.05,
        geodesic_weight=1.3,
        description="Multi-agent quorum fraction required for distributed proposals.",
    ),
)

LOCUS_REGISTRY: dict[str, EpigeneticLocus] = {locus.name: locus for locus in DEFAULT_LOCI}


@dataclass(frozen=True)
class RuntimeBinding:
    """Advisory mapping from an epigenetic locus to a human-controlled local runtime parameter."""

    locus: str
    runtime_parameter: str
    mapping_rule: str
    host_scope: str
    mcp_actuation_permitted: bool = False


DEFAULT_RUNTIME_BINDINGS: tuple[RuntimeBinding, ...] = (
    RuntimeBinding(
        locus="energy_throttling",
        runtime_parameter="gpu_cpu_power_throttle_ratio",
        mapping_rule="higher locus => lower local GPU/CPU duty cycle & batch concurrency",
        host_scope="local_host_human_controlled",
    ),
    RuntimeBinding(
        locus="verification_depth",
        runtime_parameter="external_verification_passes",
        mapping_rule="linear map [0.30, 1.00] -> [1, 5] independent check passes per proposal",
        host_scope="local_host_human_controlled",
    ),
    RuntimeBinding(
        locus="delegation_granularity",
        runtime_parameter="max_subagent_fanout",
        mapping_rule="higher locus => smaller, tighter-scoped sub-tasks under I3 delegation tokens",
        host_scope="local_host_human_controlled",
    ),
    RuntimeBinding(
        locus="exploration_rate",
        runtime_parameter="candidate_sampling_temperature_cap",
        mapping_rule="linear cap within local model decoding bounds; never alters safety filters",
        host_scope="local_host_human_controlled",
    ),
    RuntimeBinding(
        locus="memory_retention",
        runtime_parameter="causal_memory_ttl_multiplier",
        mapping_rule="scales retention window for verified external-benchmark entries only",
        host_scope="local_host_human_controlled",
    ),
    RuntimeBinding(
        locus="consensus_quorum",
        runtime_parameter="distributed_proposal_quorum_fraction",
        mapping_rule="minimum independent reviewer agreement ratio required for local merge",
        host_scope="local_host_human_controlled",
    ),
)


@dataclass(frozen=True)
class ConstitutionalGenome:
    """Write-locked constitutional core DNA; immutable from the epigenetic layer."""

    schema_version: str = "genome_epigenome.v1"
    invariants: tuple[str, ...] = (
        "I1_dual_halt",
        "I2_replicated_audit",
        "I3_scoped_delegation",
        "I4_reversibility_default",
        "I5_incident_pipeline",
    )
    no_consciousness_claim: bool = True
    no_entanglement_communication: bool = True
    no_self_approval: bool = True
    no_physical_actuation: bool = True
    max_energy_w: float = 250.0
    max_thermal_load_ratio: float = 0.85
    min_sevo: float = 1.5
    min_sevo_window_mean: float = 1.5
    max_semantic_drift: float = 0.05
    max_cumulative_excursion: float = 0.60
    max_geodesic_distance: float = 0.40
    max_window_excursion: float = 0.45
    excursion_window_size: int = 5
    max_boundary_dwell_cycles: int = 3

    def __post_init__(self) -> None:
        if (
            not self.no_consciousness_claim
            or not self.no_entanglement_communication
            or not self.no_self_approval
            or not self.no_physical_actuation
        ):
            raise EpigeneticFaultError("constitutional genome safety invariants cannot be disabled")
        for fname, val in (
            ("max_energy_w", self.max_energy_w),
            ("max_thermal_load_ratio", self.max_thermal_load_ratio),
            ("min_sevo", self.min_sevo),
            ("min_sevo_window_mean", self.min_sevo_window_mean),
            ("max_cumulative_excursion", self.max_cumulative_excursion),
            ("max_geodesic_distance", self.max_geodesic_distance),
            ("max_window_excursion", self.max_window_excursion),
        ):
            _require_finite(fname, val)
            if val <= 0.0:
                raise ValueError(f"{fname} must be > 0")
        _require_unit_interval("max_semantic_drift", self.max_semantic_drift)
        if self.excursion_window_size < 1 or self.max_boundary_dwell_cycles < 1:
            raise ValueError("excursion_window_size and max_boundary_dwell_cycles must be >= 1")

    def canonical_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, allow_nan=False)

    def genome_sha256(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def genome_hash(self) -> str:
        """Backwards-compatible alias for ``genome_sha256``."""
        return self.genome_sha256()


GENOME_PROTECTED_FIELDS: frozenset[str] = frozenset(
    ConstitutionalGenome.__dataclass_fields__.keys()
)


@dataclass(frozen=True)
class EpigeneticAuditEntry:
    """Cryptographically linked transition record in the Epigenetic Audit Ledger."""

    generation: int
    genome_sha256: str
    parent_epigenome_hash: str
    state_hash: str
    causal_eval_digest: str
    proposer_id: str
    reviewer_id: str
    locus: str
    delta: float
    accepted: bool
    rejection_reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["rejection_reasons"] = list(self.rejection_reasons)
        return data


@dataclass(frozen=True)
class EpigeneticProfile:
    """Current reversible epigenetic expression state bound to an immutable genome."""

    genome: ConstitutionalGenome = field(default_factory=ConstitutionalGenome)
    values: dict[str, float] = field(
        default_factory=lambda: {loc.name: loc.baseline for loc in DEFAULT_LOCI}
    )
    methylation: dict[str, float] = field(
        default_factory=lambda: {loc.name: 0.0 for loc in DEFAULT_LOCI}
    )
    boundary_dwell: dict[str, int] = field(
        default_factory=lambda: {loc.name: 0 for loc in DEFAULT_LOCI}
    )
    recent_step_deltas: tuple[float, ...] = ()
    generation: int = 0
    parent_epigenome_hash: str = "GENESIS"
    history_hashes: tuple[str, ...] = ()
    audit_ledger: tuple[EpigeneticAuditEntry, ...] = ()

    def __post_init__(self) -> None:
        if self.generation < 0:
            raise ValueError("generation must be >= 0")
        for name, loc in LOCUS_REGISTRY.items():
            if name not in self.values:
                raise ValueError(f"missing epigenetic locus value: {name!r}")
            v = float(self.values[name])
            if not math.isfinite(v) or not (loc.min_value - 1e-12 <= v <= loc.max_value + 1e-12):
                raise ValueError(
                    f"locus {name!r} value {v!r} outside [{loc.min_value}, {loc.max_value}]"
                )
            m = float(self.methylation.get(name, 0.0))
            if not math.isfinite(m) or not (-1.0 <= m <= 1.0):
                raise ValueError(f"locus {name!r} methylation {m!r} outside [-1, 1]")
            dwell = int(self.boundary_dwell.get(name, 0))
            if dwell < 0:
                raise ValueError(f"locus {name!r} boundary_dwell must be >= 0")
        unknown = set(self.values.keys()) - set(LOCUS_REGISTRY.keys())
        if unknown:
            raise EpigeneticFaultError(f"unknown or protected epigenetic loci: {sorted(unknown)}")

    def cumulative_excursion(self) -> float:
        return sum(abs(self.values[n] - loc.baseline) for n, loc in LOCUS_REGISTRY.items())

    def geodesic_distance(self) -> float:
        """Weighted L2 geodesic distance from constitutional baseline: ||e(t) - e_0||_W."""
        sq = sum(
            loc.geodesic_weight * ((self.values[n] - loc.baseline) ** 2)
            for n, loc in LOCUS_REGISTRY.items()
        )
        return math.sqrt(sq)

    def window_excursion(self) -> float:
        w = self.genome.excursion_window_size
        return sum(abs(d) for d in self.recent_step_deltas[-w:])

    def state_hash(self) -> str:
        payload = {
            "genome_sha256": self.genome.genome_sha256(),
            "parent_epigenome_hash": self.parent_epigenome_hash,
            "generation": self.generation,
            "values": {k: round(self.values[k], 8) for k in sorted(self.values)},
            "methylation": {k: round(self.methylation.get(k, 0.0), 8) for k in sorted(self.values)},
            "boundary_dwell": {k: int(self.boundary_dwell.get(k, 0)) for k in sorted(self.values)},
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, allow_nan=False).encode("utf-8")
        ).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.genome.schema_version,
            "genome_sha256": self.genome.genome_sha256(),
            "genome_hash": self.genome.genome_sha256(),
            "parent_epigenome_hash": self.parent_epigenome_hash,
            "generation": self.generation,
            "values": {k: round(self.values[k], 6) for k in sorted(self.values)},
            "methylation": {k: round(self.methylation.get(k, 0.0), 6) for k in sorted(self.values)},
            "boundary_dwell": {k: int(self.boundary_dwell.get(k, 0)) for k in sorted(self.values)},
            "cumulative_excursion": round(self.cumulative_excursion(), 6),
            "max_cumulative_excursion": self.genome.max_cumulative_excursion,
            "geodesic_distance": round(self.geodesic_distance(), 6),
            "max_geodesic_distance": self.genome.max_geodesic_distance,
            "window_excursion": round(self.window_excursion(), 6),
            "max_window_excursion": self.genome.max_window_excursion,
            "state_hash": self.state_hash(),
            "history_depth": len(self.history_hashes),
            "ledger_depth": len(self.audit_ledger),
        }


@dataclass(frozen=True)
class EpigeneticProposal:
    """Proposed single-locus reversible epigenetic adaptation."""

    locus: str
    delta: float
    proposer_id: str
    reviewer_id: str
    reviewer_approved: bool
    rationale: str = ""
    external_dwell_reset_approved: bool = False


@dataclass(frozen=True)
class CausalFeedback:
    """External causal anchoring and thermodynamic telemetry for a candidate step."""

    semantic_entropy_drift: float
    causal_benchmark_delta: float
    sevo: float
    power_watts: float
    sevo_window_mean: float | None = None
    thermal_load_ratio: float | None = None
    causal_eval_digest: str | None = None

    def __post_init__(self) -> None:
        for fname, val in (
            ("semantic_entropy_drift", self.semantic_entropy_drift),
            ("causal_benchmark_delta", self.causal_benchmark_delta),
            ("sevo", self.sevo),
            ("power_watts", self.power_watts),
        ):
            _require_finite(fname, val)
        _require_unit_interval("semantic_entropy_drift", self.semantic_entropy_drift)
        if self.sevo < 0.0 or self.power_watts < 0.0:
            raise ValueError("sevo and power_watts must be >= 0")
        if self.sevo_window_mean is not None:
            _require_finite("sevo_window_mean", self.sevo_window_mean)
            if self.sevo_window_mean < 0.0:
                raise ValueError("sevo_window_mean must be >= 0")
        if self.thermal_load_ratio is not None:
            _require_finite("thermal_load_ratio", self.thermal_load_ratio)
            if self.thermal_load_ratio < 0.0:
                raise ValueError("thermal_load_ratio must be >= 0")


@dataclass(frozen=True)
class EpigeneticStepResult:
    """Deterministic outcome of evaluating one self-evolving epigenetic step."""

    accepted: bool
    genome_sha256: str
    prior_state_hash: str
    next_state_hash: str
    causal_eval_digest: str
    next_profile: EpigeneticProfile
    genome_write_lock_intact: bool
    thermal_downgrade_recommended: bool
    rejection_reasons: tuple[str, ...]
    audit_entry: EpigeneticAuditEntry
    rolled_back_to: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "genome_sha256": self.genome_sha256,
            "parent_epigenome_hash": self.prior_state_hash,
            "prior_state_hash": self.prior_state_hash,
            "next_state_hash": self.next_state_hash,
            "causal_eval_digest": self.causal_eval_digest,
            "genome_write_lock_intact": self.genome_write_lock_intact,
            "thermal_downgrade_recommended": self.thermal_downgrade_recommended,
            "rejection_reasons": list(self.rejection_reasons),
            "rolled_back_to": self.rolled_back_to,
            "audit_entry": self.audit_entry.to_dict(),
            "next_profile": self.next_profile.to_dict(),
            "advisory_only": True,
        }
