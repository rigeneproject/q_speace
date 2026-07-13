"""BCEL catalog — quantum equivalences (task T15).

Implements the Biological-Cybernetic Equivalence gate for Q-SPEACE:
each biological/quantum concept is classified as *accidental* (limit of
carbon chemistry, removed in silicon) or *functional* (emergent
stabilizer, kept as a mathematical rule). Mirrors cellular speace's
``speace_core/bcel/`` catalogue.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BCELEquivalence:
    concept: str
    classification: str  # "accidental" | "functional"
    digital_rule: str


_QUANTUM_EQUIVALENCES: list[BCELEquivalence] = [
    BCELEquivalence(
        "Entanglement (cell/planet communication)",
        "accidental",
        "Replaced by explicit message-passing; entanglement is a computational "
        "binding resource only (no-communication theorem).",
    ),
    BCELEquivalence(
        "Superposition (parallel hypotheses)",
        "functional",
        "Keep: represent multiple candidate states as amplitude weights; "
        "measurement = decision/collapse.",
    ),
    BCELEquivalence(
        "Biological fractal shape",
        "accidental",
        "Removed: 2D/3D fractal morphology is carbon-specific.",
    ),
    BCELEquivalence(
        "Fractal scaling rule (w_ij ~ d^-1.8)",
        "functional",
        "Keep as a recursive, scale-free weight update law in FractalQCA.",
    ),
    BCELEquivalence(
        "Cosmic Virus perturbation",
        "functional",
        "Keep as stochastic-resonance optimizer (CV dynamics).",
    ),
    BCELEquivalence(
        "ILF coherence / entropic gravity",
        "functional",
        "Keep as coherence_phi metric and adaptive clock r(t)=10/sqrt(S_info).",
    ),
]


class BCELCatalog:
    """Queryable catalog of quantum BCEL equivalences."""

    def __init__(self) -> None:
        self._entries: dict[str, BCELEquivalence] = {
            e.concept: e for e in _QUANTUM_EQUIVALENCES
        }

    def all(self) -> list[BCELEquivalence]:
        return list(self._entries.values())

    def get(self, concept: str) -> BCELEquivalence:
        if concept not in self._entries:
            raise KeyError(concept)
        return self._entries[concept]

    def is_functional(self, concept: str) -> bool:
        return self.get(concept).classification == "functional"
