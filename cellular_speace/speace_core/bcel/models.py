"""Data models for the Biological-Cybernetic Equivalence Layer."""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional


class ConstraintKind(Enum):
    """Classification of a biological constraint."""

    ACCIDENTAL = auto()  # limit of the carbon substrate; removable in silicon
    FUNCTIONAL = auto()  # emergent stabilizer; must be kept as a math rule
    UNKNOWN = auto()  # not yet classified


@dataclass
class FunctionalConstraint:
    """A biological restriction that is kept because it stabilizes the system.

    Attributes:
        name: human-readable identifier.
        invariant: which informational invariant it protects.
        biological_form: how nature implements it.
        mathematical_form: the digital rule that preserves the same property.
        parameters: tunable parameters for the rule.
        stability_test: metric that proves the rule is needed.
    """

    name: str
    invariant: str
    biological_form: str
    mathematical_form: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    stability_test: str = ""


@dataclass
class CyberneticEquivalent:
    """Result of translating a biological component into the digital domain."""

    component_name: str
    preserved_function: str
    removed_constraints: List[str] = field(default_factory=list)
    kept_constraints: List[FunctionalConstraint] = field(default_factory=list)
    digital_implementation: str = ""
    configuration: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BiologicalComponent:
    """A biological construct under BCEL analysis."""

    name: str
    function: str
    biological_constraints: List[str] = field(default_factory=list)
    known_equivalent: Optional[CyberneticEquivalent] = None
