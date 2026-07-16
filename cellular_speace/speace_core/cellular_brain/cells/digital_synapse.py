from typing import List, Optional

from pydantic import Field

from speace_core.cellular_brain.base.digital_cell import DigitalCell
from speace_core.cellular_brain.base.digital_signal import DigitalSignal


class DigitalSynapse(DigitalCell):
    source: str = ""
    target: str = ""
    weight: float = 0.5
    use_count: int = 0
    trust: float = 0.5
    decay: float = 0.001
    consolidated: bool = False
    stability: float = 0.0
    recurrence_count: int = 0

    # T-STDP — spike timing records for plasticity
    last_pre_spike_tick: Optional[int] = None
    last_post_spike_tick: Optional[int] = None

    # T-NPT — Neural Periodic Table identity
    periodic_element_id: Optional[int] = None
    periodic_symbol: Optional[str] = None
    source_periodic_element_id: Optional[int] = None
    target_periodic_element_id: Optional[int] = None

    # T-DNA — DNA-driven connectome initialization
    periodic_plasticity: float = 0.5
    periodic_bond_type: Optional[str] = None
    periodic_bond_order: Optional[int] = None
    dna_driven_init: bool = False

    async def receive(self, signal: DigitalSignal) -> None:
        pass

    async def tick(self) -> List[DigitalSignal]:
        return []

    def transmit(self, signal: DigitalSignal) -> DigitalSignal:
        self.use_count += 1
        signal.strength *= self.weight * self.trust
        return signal

    def reinforce(self, success_score: float) -> None:
        self.weight += 0.02 * success_score
        self.trust += 0.01 * success_score
        self.weight = max(0.0, min(1.0, self.weight))
        self.trust = max(0.0, min(1.0, self.trust))

    def weaken(self, error_score: float) -> None:
        self.weight -= 0.02 * error_score
        self.trust -= 0.01 * error_score
        self.weight = max(0.0, min(1.0, self.weight))
        self.trust = max(0.0, min(1.0, self.trust))

    def get_periodic_element(self):
        """Get the NeuralElement assigned to this synapse, if any."""
        from speace_core.cellular_brain.neuroperiodic.neural_element import (
            build_element,
        )
        if self.periodic_element_id is not None:
            return build_element(self.periodic_element_id)
        return None

    def get_source_periodic_element(self):
        """Get the NeuralElement for the source neuron, if known."""
        from speace_core.cellular_brain.neuroperiodic.neural_element import (
            build_element,
        )
        if self.source_periodic_element_id is not None:
            return build_element(self.source_periodic_element_id)
        return None

    def get_target_periodic_element(self):
        """Get the NeuralElement for the target neuron, if known."""
        from speace_core.cellular_brain.neuroperiodic.neural_element import (
            build_element,
        )
        if self.target_periodic_element_id is not None:
            return build_element(self.target_periodic_element_id)
        return None

    def predict_bond_properties(self, integrator=None) -> dict:
        """Predict synaptic bond properties from source/target periodic elements."""
        from speace_core.cellular_brain.neuroperiodic.neuroperiodic_integrator import (
            NeuroPeriodicIntegrator,
        )
        src = self.get_source_periodic_element()
        tgt = self.get_target_periodic_element()
        if src is None or tgt is None:
            return {}
        integrator = integrator or NeuroPeriodicIntegrator()
        return integrator.predict_synapse_by_elements(src, tgt)

    def apply_periodic_prediction(self, integrator=None) -> None:
        """Initialize synaptic parameters from Neural Periodic Table bond physics.

        Uses the source/target NeuralElements to derive:
          - weight from bond strength
          - trust from compatibility
          - periodic_plasticity from bond plasticity
          - decay from metabolic energy cost
          - bond type/order metadata

        This realizes DNA-driven connectome weights: the Digital DNA shapes
        the periodic laws, which in turn shape the initial connectome.
        """
        props = self.predict_bond_properties(integrator)
        if not props:
            return

        strength = float(props.get("strength", 0.5))
        compatibility = float(props.get("compatibility", 0.5))
        plasticity = float(props.get("plasticity", 0.5))
        energy_cost = float(props.get("energy_cost", 0.05))

        # Map bond strength to initial weight: strong bonds start stronger.
        # Centered mapping keeps the majority of weights in [0.1, 0.9].
        self.weight = max(0.1, min(0.9, strength * 0.6 + 0.25))
        # Trust reflects how well the two elements get along.
        self.trust = max(0.1, min(0.9, compatibility * 0.7 + 0.2))
        # Plasticity is inherited from the periodic law prediction.
        self.periodic_plasticity = max(0.1, min(0.9, plasticity))
        # Decay is proportional to metabolic maintenance cost.
        self.decay = max(0.0001, min(0.01, energy_cost * 0.01))

        self.periodic_bond_type = props.get("bond_type")
        self.periodic_bond_order = props.get("bond_order")
        self.dna_driven_init = True
