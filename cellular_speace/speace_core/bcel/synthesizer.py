"""Generate cybernetic equivalents from classified biological constraints."""

from typing import Any, Dict, List

from speace_core.bcel.catalog import BCELCatalog
from speace_core.bcel.classifier import ConstraintClassifier
from speace_core.bcel.models import (
    BiologicalComponent,
    ConstraintKind,
    CyberneticEquivalent,
    FunctionalConstraint,
)


class CyberneticSynthesizer:
    """Produce a digital equivalent for a biological component.

    Steps:
        1. Look up the component in the catalog.
        2. Classify any new constraints.
        3. Drop accidental constraints.
        4. Convert functional constraints into digital rules.
        5. Return a CyberneticEquivalent ready for implementation.
    """

    def __init__(
        self,
        catalog: BCELCatalog | None = None,
        classifier: ConstraintClassifier | None = None,
    ) -> None:
        self.catalog = catalog or BCELCatalog()
        self.classifier = classifier or ConstraintClassifier()

    def synthesize(self, component: BiologicalComponent) -> CyberneticEquivalent:
        """Synthesize the digital equivalent for a biological component."""
        base = self.catalog.evaluate_component(component)

        removed: List[str] = list(base.removed_constraints)
        kept: List[FunctionalConstraint] = list(base.kept_constraints)

        for constraint in component.biological_constraints:
            kind = self.classifier.classify(component, constraint)
            if kind is ConstraintKind.ACCIDENTAL:
                if constraint not in removed:
                    removed.append(constraint)
            elif kind is ConstraintKind.FUNCTIONAL:
                if not any(fc.biological_form == constraint for fc in kept):
                    kept.append(
                        self.classifier.propose_functional_constraint(
                            component, constraint
                        )
                    )

        return CyberneticEquivalent(
            component_name=component.name,
            preserved_function=component.function or base.preserved_function,
            removed_constraints=removed,
            kept_constraints=kept,
            digital_implementation=base.digital_implementation,
            configuration=base.configuration,
        )

    def synthesize_all(
        self, components: List[BiologicalComponent]
    ) -> Dict[str, CyberneticEquivalent]:
        """Synthesize equivalents for many components."""
        return {c.name: self.synthesize(c) for c in components}
