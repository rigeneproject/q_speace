"""Biological-Cybernetic Equivalence Layer (BCEL).

The BCEL translates biological structures into digital principles while
preserving their informational invariants. It distinguishes accidental
constraints (limits of carbon chemistry) from functional constraints
(emergent stabilizers) and produces cybernetic equivalents for SPEACE.
"""

from speace_core.bcel.models import (
    BiologicalComponent,
    ConstraintKind,
    CyberneticEquivalent,
    FunctionalConstraint,
)
from speace_core.bcel.catalog import BCELCatalog, default_catalog
from speace_core.bcel.classifier import ConstraintClassifier
from speace_core.bcel.synthesizer import CyberneticSynthesizer
from speace_core.bcel.stress_tester import ConstraintStressTester, StressTestResult
from speace_core.bcel.stress_scenarios import (
    CircuitProxy,
    StressScenarioRegistry,
    StabilityMetrics,
)

__all__ = [
    "BiologicalComponent",
    "ConstraintKind",
    "CyberneticEquivalent",
    "FunctionalConstraint",
    "BCELCatalog",
    "default_catalog",
    "ConstraintClassifier",
    "CyberneticSynthesizer",
    "ConstraintStressTester",
    "StressTestResult",
    "CircuitProxy",
    "StressScenarioRegistry",
    "StabilityMetrics",
]
