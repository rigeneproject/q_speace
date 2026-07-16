"""Functional constraint laws for the neural-synaptic periodic table.

These laws encode the *mathematical* properties of biological stabilizers
(rate limiting, gain control, low-pass filtering) as tunable rules attached
to synaptic bonds or neural elements.
"""

from dataclasses import dataclass, field
from typing import Any, Dict

from pydantic import BaseModel, ConfigDict


class FunctionalConstraintLaw(BaseModel):
    """A digital rule that preserves a functional biological property.

    Example: a synaptic delay is not simulated as a timer; instead, a
    FunctionalConstraintLaw applies a leaky-integrator time constant and a
    maximum firing rate to the bond.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    invariant: str
    biological_form: str
    target: str = "synaptic_bond"  # or "neural_element" / "circuit"
    parameters: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True

    def apply_to_bond(self, bond: Any) -> None:
        """Apply this law's parameters to a SynapticBond-like object."""
        if not self.enabled or self.target != "synaptic_bond":
            return
        # Parameters are attached to the bond as metadata; the bond's own
        # update logic can read them. We do not silently change existing
        # numeric attributes to avoid breaking tested behavior.
        if hasattr(bond, "metadata"):
            bond.metadata[self.name] = dict(self.parameters)
        else:
            try:
                bond.metadata = {self.name: dict(self.parameters)}
            except Exception:
                pass

    def apply_to_element(self, element: Any) -> None:
        """Apply this law to a NeuralElement-like object."""
        if not self.enabled or self.target != "neural_element":
            return
        if hasattr(element, "metadata"):
            element.metadata[self.name] = dict(self.parameters)
        else:
            try:
                element.metadata = {self.name: dict(self.parameters)}
            except Exception:
                pass


@dataclass
class FunctionalConstraintRegistry:
    """Collection of functional constraint laws."""

    laws: Dict[str, FunctionalConstraintLaw] = field(default_factory=dict)

    def register(self, law: FunctionalConstraintLaw) -> None:
        self.laws[law.name] = law

    def get(self, name: str) -> FunctionalConstraintLaw | None:
        return self.laws.get(name)

    def default_registry() -> "FunctionalConstraintRegistry":
        reg = FunctionalConstraintRegistry()
        reg.register(
            FunctionalConstraintLaw(
                name="synaptic_delay_lowpass",
                invariant="coherence_preservation",
                biological_form="1-2 ms chemical synaptic delay",
                target="synaptic_bond",
                parameters={"leaky_tau_ms": 5.0, "max_rate_hz": 100.0},
            )
        )
        reg.register(
            FunctionalConstraintLaw(
                name="short_term_depression",
                invariant="destructive_entropy_reduction",
                biological_form="vesicle depletion reduces repeated gain",
                target="synaptic_bond",
                parameters={"decay_per_spike": 0.05, "recovery_tau": 10.0},
            )
        )
        reg.register(
            FunctionalConstraintLaw(
                name="statistical_memory_gate",
                invariant="destructive_entropy_reduction",
                biological_form="slow consolidation filters noise",
                target="neural_element",
                parameters={"recurrence_threshold": 3, "observation_window": 100},
            )
        )
        return reg
