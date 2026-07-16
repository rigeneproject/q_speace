"""Adapter: Digital RNA → Neural-Synaptic Periodic Table.

The functional constraints carried by the transcriptome become dynamic laws
in the periodic table, not hard-coded patches.
"""

from typing import Any, Dict, List

from speace_core.digital_rna.models import Transcriptome


try:
    from speace_core.cellular_brain.neuroperiodic.periodic_law import PeriodicLaw
except Exception:  # pragma: no cover
    PeriodicLaw = None  # type: ignore[misc,assignment]


class PeriodicTableAdapter:
    """Apply a transcriptome to a PeriodicLaw instance."""

    def __init__(self, law: "PeriodicLaw") -> None:
        self.law = law

    def apply(self, transcriptome: Transcriptome) -> Dict[str, Any]:
        """Push functional constraints from the transcriptome into the law."""
        applied: List[str] = []
        for fc in transcriptome.functional_constraints:
            name = fc.get("name", "unknown")
            if hasattr(self.law, "add_functional_constraint"):
                self.law.add_functional_constraint(fc)
                applied.append(name)

        return {
            "applied_constraints": applied,
            "law_functional_constraints": len(
                getattr(self.law, "functional_constraints", [])
            ),
        }
