"""Minimal deterministic circuit for BCEL stress testing.

The full MVP orchestrator includes many noisy subsystems. For stress testing a
functional constraint we want a small, controlled circuit where relaxing the
constraint has a visible effect. This module builds such a circuit on demand.
"""

from dataclasses import dataclass
from typing import Any, List, Tuple

from speace_core.cellular_brain.cells.digital_neuron import DigitalNeuron
from speace_core.cellular_brain.cells.digital_synapse import DigitalSynapse
from speace_core.cellular_brain.circuits.neural_circuit import NeuralCircuit


def build_minimal_loop_circuit(
    excitatory_self_loop: bool = True,
) -> NeuralCircuit:
    """Build a tiny excitable circuit: one input, one hidden, one output.

    If excitatory_self_loop is True, the hidden neuron has a strong self-loop
    that can sustain or amplify activity. This makes the circuit sensitive to
    gain-control constraints.
    """
    input_neuron = DigitalNeuron(
        cell_id="in_0", role="digital_neuron", threshold=0.3, energy=1.0
    )
    hidden_neuron = DigitalNeuron(
        cell_id="hid_0", role="digital_neuron", threshold=0.3, energy=1.0
    )
    output_neuron = DigitalNeuron(
        cell_id="out_0", role="digital_neuron", threshold=0.3, energy=1.0
    )

    synapses: List[DigitalSynapse] = []

    # Input -> hidden
    synapses.append(
        DigitalSynapse(
            cell_id="in_hid",
            role="digital_synapse",
            source="in_0",
            target="hid_0",
            weight=0.8,
            trust=0.8,
        )
    )
    input_neuron.targets.append("hid_0")

    # Hidden -> output
    synapses.append(
        DigitalSynapse(
            cell_id="hid_out",
            role="digital_synapse",
            source="hid_0",
            target="out_0",
            weight=0.8,
            trust=0.8,
        )
    )
    hidden_neuron.targets.append("out_0")

    if excitatory_self_loop:
        # Self-loop: hidden feeds itself strongly.
        synapses.append(
            DigitalSynapse(
                cell_id="hid_hid",
                role="digital_synapse",
                source="hid_0",
                target="hid_0",
                weight=0.95,
                trust=0.95,
            )
        )
        hidden_neuron.targets.append("hid_0")

    return NeuralCircuit(
        circuit_id="stress_circuit",
        input_neurons=[input_neuron],
        hidden_neurons=[hidden_neuron],
        output_neurons=[output_neuron],
        synapses=synapses,
    )


def build_refractory_circuit() -> NeuralCircuit:
    """Circuit where refractory period is the only thing preventing runaway."""
    input_neuron = DigitalNeuron(
        cell_id="in_0", role="digital_neuron", threshold=0.3, energy=1.0
    )
    hidden_neuron = DigitalNeuron(
        cell_id="hid_0",
        role="digital_neuron",
        threshold=0.2,
        energy=1.0,
        refractory_period=2,
    )

    synapses = [
        DigitalSynapse(
            cell_id="in_hid",
            role="digital_synapse",
            source="in_0",
            target="hid_0",
            weight=0.9,
            trust=0.9,
        ),
    ]
    input_neuron.targets.append("hid_0")

    return NeuralCircuit(
        circuit_id="refractory_circuit",
        input_neurons=[input_neuron],
        hidden_neurons=[hidden_neuron],
        output_neurons=[],
        synapses=synapses,
    )



@dataclass
class CircuitTickMetrics:
    """Metrics recorded after each tick of a minimal stress circuit."""
    tick: int
    coherence_phi: float
    mean_energy: float
    spike_count: int
    max_activation: float
    active_neurons: int = 0
    pruned_synapses: int = 0


class MinimalCircuitOrchestrator:
    """Thin shim that turns a NeuralCircuit into a deterministic test target.

    The full MVP orchestrator includes noisy subsystems that can mask the
    effect of a single functional constraint.  This wrapper exposes only the
    small circuit under test and records per-tick metrics so that relaxing a
    protective constraint produces a measurable jump in instability.
    """

    def __init__(self, circuit: NeuralCircuit) -> None:
        self.circuit = circuit
        self.metrics_log: list[CircuitTickMetrics] = []
        self.latest_metrics: Any = None

    def inject(self, pattern: list[float]) -> None:
        """Inject a pattern into the circuit's input neurons."""
        self.circuit.inject_input(pattern)

    async def run_ticks(self, n: int) -> None:
        """Run the circuit for ``n`` ticks and record per-tick metrics."""
        for _ in range(n):
            neurons = self.circuit.all_neurons
            pre_activations = [n.activation for n in neurons]
            pre_max = max(pre_activations) if pre_activations else 0.0
            outbound = await self.circuit.tick()
            post_activations = [n.activation for n in neurons]
            post_energies = [n.energy for n in neurons]
            self._record_metrics(pre_max, len(outbound), post_activations, post_energies)

    def _record_metrics(
        self,
        pre_max_activation: float,
        spike_count: int,
        activations: list[float],
        energies: list[float],
    ) -> None:
        mean_act = sum(activations) / len(activations) if activations else 0.0
        if len(activations) > 1:
            variance = sum((a - mean_act) ** 2 for a in activations) / len(activations)
            coherence = max(0.0, 1.0 - variance * 4.0)
        else:
            coherence = 1.0 if activations else 0.0
        mean_energy = sum(energies) / len(energies) if energies else 0.0
        active = sum(1 for a in activations if a > 0.5)
        metrics = CircuitTickMetrics(
            tick=self.circuit.current_tick,
            coherence_phi=coherence,
            mean_energy=mean_energy,
            spike_count=spike_count,
            max_activation=pre_max_activation,
            active_neurons=active,
        )
        self.metrics_log.append(metrics)
        self.latest_metrics = metrics


def make_minimal_builder(constraint_name: str):
    """Return a builder that produces a minimal deterministic circuit for a constraint.

    ``rate_limiter`` uses the refractory circuit; gain-control/low-pass
    constraints use the excitatory self-loop circuit.
    """

    def builder() -> MinimalCircuitOrchestrator:
        if constraint_name == "rate_limiter":
            circuit = build_refractory_circuit()
        else:
            circuit = build_minimal_loop_circuit()
        return MinimalCircuitOrchestrator(circuit)

    return builder
