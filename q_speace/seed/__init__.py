"""SPEACE Seed minimal ignition package (T220 / T221 Track B)."""

from __future__ import annotations

from .constitution import (
    ChangeBudgetEngine,
    ConstitutionalFault,
    ResourceCaps,
    SCCInvariants,
    SeedConstitution,
    SeedEpigenome,
    SeedGenome,
)
from .contact import AssimilationResult, ContactPlan, ContactSpec, SeedContactLayer
from .killswitch import KillEvent, KillSwitch
from .replication import ReplicationProtocol, SeedManifest
from .state_machine import (
    IgnitionCriterion,
    IgnitionObservation,
    IgnitionVerdict,
    SeedLifecycle,
    SeedState,
)

__all__ = [
    "AssimilationResult",
    "ChangeBudgetEngine",
    "ConstitutionalFault",
    "ContactPlan",
    "ContactSpec",
    "IgnitionCriterion",
    "IgnitionObservation",
    "IgnitionVerdict",
    "KillEvent",
    "KillSwitch",
    "ReplicationProtocol",
    "ResourceCaps",
    "SCCInvariants",
    "SeedConstitution",
    "SeedContactLayer",
    "SeedEpigenome",
    "SeedGenome",
    "SeedLifecycle",
    "SeedManifest",
    "SeedState",
]
