"""MembraneDynamics — LIF neuron model driven by periodic element properties.

Maps NeuralElement properties to Leaky Integrate-and-Fire parameters:
  - ionization_energy → firing threshold
  - atomic_radius     → input integration window / receptive field
  - electronegativity → lateral inhibition strength
  - mass              → metabolic cost per spike
  - period            → integration time constant (τ)
  - block (S/P/D/F)   → neurotransmitter effect class
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from speace_core.cellular_brain.neuroperiodic.neural_element import (
    NeuralElement,
    ElementBlock,
    ElementPeriod,
)


class MembraneState(BaseModel):
    """Per-neuron membrane dynamics state."""
    potential: float = 0.0
    refractory_ticks: int = 0
    last_spike_tick: int = -1
    spike_count: int = 0
    adaptation: float = 0.0


class MembraneDynamics:
    """LIF dynamics parameterized by periodic element properties.

    Provides per-neuron membrane potential (as MembraneState) and LIF
    step/fire/reset logic driven by the periodic table.
    """

    def __init__(self):
        self._states: dict[str, MembraneState] = {}

    # ------------------------------------------------------------------
    # Parameter mapping
    # ------------------------------------------------------------------

    def threshold(self, element: NeuralElement) -> float:
        """Firing threshold derived from ionization energy (0–1 range)."""
        return max(0.1, min(1.0, element.ionization_energy))

    def tau(self, element: NeuralElement) -> float:
        """Integration time constant derived from period depth.

        Deeper periods (executive, output) integrate longer.
        """
        period_map = {
            ElementPeriod.SENSORY_TRANSDUCTION: 2.0,
            ElementPeriod.INTEGRATION: 5.0,
            ElementPeriod.ASSOCIATION: 8.0,
            ElementPeriod.EXECUTIVE: 12.0,
            ElementPeriod.MOTOR_COORDINATION: 6.0,
            ElementPeriod.OUTPUT_HOMEOSTASIS: 4.0,
        }
        return period_map.get(element.period, 5.0)

    def lateral_inhibition(self, element: NeuralElement) -> float:
        """Lateral inhibition strength derived from electronegativity."""
        return element.electronegativity * 0.5

    def metabolic_cost(self, element: NeuralElement) -> float:
        """Metabolic cost per spike from element mass."""
        return element.mass * 0.1

    def refractory_period(self, element: NeuralElement) -> int:
        """Refractory period in ticks based on bond type default for element."""
        block_map = {
            ElementBlock.S_BLOCK: 3,
            ElementBlock.P_BLOCK: 2,
            ElementBlock.D_BLOCK: 1,
            ElementBlock.F_BLOCK: 1,
        }
        return block_map.get(element.block, 2)

    # ------------------------------------------------------------------
    # Per-neuron state management
    # ------------------------------------------------------------------

    def get_state(self, neuron_id: str) -> MembraneState:
        if neuron_id not in self._states:
            self._states[neuron_id] = MembraneState()
        return self._states[neuron_id]

    # ------------------------------------------------------------------
    # LIF step
    # ------------------------------------------------------------------

    def step(
        self,
        neuron_id: str,
        input_current: float,
        element: NeuralElement,
        dt: float = 1.0,
        tick: int = 0,
    ) -> MembraneState:
        """Update membrane potential for one time step.

        dv/dt = (-v + I_input + I_noise) / τ
        where τ comes from element.period and I_input accumulates
        EPSP/IPSP from incoming spikes.
        """
        state = self.get_state(neuron_id)

        if state.refractory_ticks > 0:
            state.refractory_ticks -= 1
            state.potential = 0.0
            return state

        tau = self.tau(element)
        leak = dt / max(tau, 0.1)
        inhibition = self.lateral_inhibition(element)

        noise = 0.0
        state.potential = (1.0 - leak) * state.potential + leak * (
            input_current - inhibition * state.potential + noise
        )
        state.potential = max(0.0, min(2.0, state.potential))

        return state

    def should_fire(self, neuron_id: str, element: NeuralElement) -> bool:
        """Check if neuron's membrane potential exceeds element-specific threshold."""
        state = self.get_state(neuron_id)
        thr = self.threshold(element)
        return state.potential >= thr and state.refractory_ticks == 0

    def reset(
        self,
        neuron_id: str,
        element: NeuralElement,
        tick: int = 0,
    ) -> MembraneState:
        """Reset after firing: set refractory period, subtract adaptation."""
        state = self.get_state(neuron_id)
        state.potential = 0.0
        state.refractory_ticks = self.refractory_period(element)
        state.last_spike_tick = tick
        state.spike_count += 1
        state.adaptation = min(1.0, state.adaptation + 0.05)
        return state
