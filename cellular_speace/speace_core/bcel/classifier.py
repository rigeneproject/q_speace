"""Classify biological constraints as accidental or functional."""

from typing import Dict, List

from speace_core.bcel.models import BiologicalComponent, ConstraintKind, FunctionalConstraint


class ConstraintClassifier:
    """Heuristic + stress-test driven classifier for biological constraints.

    The classifier does not rely on a fixed list. For each constraint it
    proposes a classification and records the test that would validate it.
    """

    def __init__(self, known_accidental_keywords: List[str] | None = None) -> None:
        # Keywords strongly associated with physical limits of carbon chemistry.
        self._accidental_keywords = set(known_accidental_keywords or [
            "thermal",
            "diffusion",
            "chemical",
            "macromolecular",
            "ion channel",
            "vesicle",
            "wet",
            "aqueous",
            "temperature",
        ])
        # Keywords strongly associated with systemic stabilizers.
        self._functional_keywords = {
            "filter",
            "stabilizer",
            "oscillation",
            "gain control",
            "threshold",
            "sampling",
            "rate limit",
            "depression",
            "refractory",
            "homeostasis",
        }

    def classify(
        self, component: BiologicalComponent, constraint: str
    ) -> ConstraintKind:
        """Return a heuristic classification for a constraint string."""
        low = constraint.lower()
        accidental_hits = sum(1 for kw in self._accidental_keywords if kw in low)
        functional_hits = sum(1 for kw in self._functional_keywords if kw in low)
        if functional_hits > accidental_hits:
            return ConstraintKind.FUNCTIONAL
        if accidental_hits > functional_hits:
            return ConstraintKind.ACCIDENTAL
        return ConstraintKind.UNKNOWN

    def classify_all(
        self, component: BiologicalComponent
    ) -> Dict[str, ConstraintKind]:
        """Classify every biological constraint of a component."""
        return {
            constraint: self.classify(component, constraint)
            for constraint in component.biological_constraints
        }

    def propose_functional_constraint(
        self,
        component: BiologicalComponent,
        constraint: str,
        invariant: str = "coherence_preservation",
    ) -> FunctionalConstraint:
        """Propose a placeholder functional constraint for a stabilizer."""
        return FunctionalConstraint(
            name=f"{component.name}_{constraint}",
            invariant=invariant,
            biological_form=constraint,
            mathematical_form="to_be_defined_by_stress_test",
            parameters={},
            stability_test=f"stress_test_{component.name}_{constraint}",
        )
