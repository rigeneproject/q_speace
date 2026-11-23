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
from .validator import ProcessIsolatedValidator, ValidatorKey

__all__ = [
    "CoupledCommit",
    "CrashAtomicCoupledCommit",
    "ExpiryError",
    "FencingError",
    "IdempotencyError",
    "JournalRecord",
    "ProcessIsolatedValidator",
    "ProtocolError",
    "SimulatedCrashError",
    "StateError",
    "UpdateLedger",
    "UpdateProposal",
    "UpdateStatus",
    "ValidatorKey",
    "canonical_param_hash",
    "recover_coupled_wal",
]
