"""Bridge-v0 — Transduction Bridge contract (T218).

Modules
-------
``protocol``  update state machine, journal, fencing, coupled commit.
``screening`` two-stage parameter screening on the admissible set.
``validator`` independent validation with attestations (T218-T03).
``safety_contract`` observation-latency-aware safety contract (T218-T04).

BCEL: all Bridge primitives are *functional* — finite automata, set
projections and signed records. No biological or quantum vocabulary is
load-bearing here.
"""

from .dual_speed import (
    DualSpeedCognitiveLoop,
    DualSpeedTurnRecord,
    MaintenanceReport,
    RoutingTier,
    TurnGroundingStatus,
)
from .grounding import (
    CandidateEdge,
    CandidateEdgeStatus,
    GroundedPayload,
    GroundingRejection,
    GroundingStatus,
    SymbolicGroundingAdapter,
    SymbolRegistry,
)
from .protocol import (
    CoupledCommit,
    CrashAtomicCoupledCommit,
    ExpiryError,
    FencingError,
    IdempotencyError,
    JournalRecord,
    ProtocolError,
    SimulatedCrashError,
    StateError,
    UpdateLedger,
    UpdateProposal,
    UpdateStatus,
    canonical_param_hash,
    recover_coupled_wal,
)
from .simulated_sensor import (
    VALID_RUNTIME_MODES,
    SimulatedSensorAdapter,
    SimulatedSensorReading,
    run_coro_isolated,
)
from .validator import ProcessIsolatedValidator, ValidatorKey

__all__ = [
    "CandidateEdge",
    "CandidateEdgeStatus",
    "CoupledCommit",
    "CrashAtomicCoupledCommit",
    "DualSpeedCognitiveLoop",
    "DualSpeedTurnRecord",
    "ExpiryError",
    "FencingError",
    "GroundedPayload",
    "GroundingRejection",
    "GroundingStatus",
    "IdempotencyError",
    "JournalRecord",
    "MaintenanceReport",
    "ProcessIsolatedValidator",
    "ProtocolError",
    "RoutingTier",
    "SimulatedCrashError",
    "SimulatedSensorAdapter",
    "SimulatedSensorReading",
    "StateError",
    "SymbolRegistry",
    "SymbolicGroundingAdapter",
    "TurnGroundingStatus",
    "UpdateLedger",
    "UpdateProposal",
    "UpdateStatus",
    "VALID_RUNTIME_MODES",
    "ValidatorKey",
    "canonical_param_hash",
    "recover_coupled_wal",
    "run_coro_isolated",
]
