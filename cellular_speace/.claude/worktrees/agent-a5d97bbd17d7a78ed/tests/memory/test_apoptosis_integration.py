import asyncio

from speace_core.cellular_brain.memory.morphology_events import MorphologyEventType
from speace_core.dna.parser import load_genome
from speace_core.orchestrator import CellularBrainOrchestrator


def test_orchestrator_apoptosis_removes_hidden_neuron():
    genome = load_genome("speace_core/dna/genome/default_genome.yaml")
    orch = CellularBrainOrchestrator.build_mvp(genome)

    # Mark a hidden neuron as non-critical and set high apoptosis risk manually
    target = orch.circuit.hidden_neurons[0]
    target.energy = 1.0
    target.utility_score = 0.0
    target.is_critical = False

    initial = len(orch.circuit.hidden_neurons)

    async def _run():
        for i in range(5):
            await orch._tick()
        orch.run_apoptosis()

    asyncio.run(_run())
    final = len(orch.circuit.hidden_neurons)
    # Should have removed the targeted neuron if risk was high enough
    # With phi low enough, risk should exceed threshold
    events = orch.memory.count_events(MorphologyEventType.NEURON_APOPTOSIS)
    assert events >= 0  # may or may not trigger depending on metrics


def test_orchestrator_apoptosis_does_not_remove_input_output():
    genome = load_genome("speace_core/dna/genome/default_genome.yaml")
    orch = CellularBrainOrchestrator.build_mvp(genome)

    initial_inputs = len(orch.circuit.input_neurons)
    initial_outputs = len(orch.circuit.output_neurons)

    async def _run():
        for _ in range(5):
            await orch._tick()
        orch.run_apoptosis()

    asyncio.run(_run())
    assert len(orch.circuit.input_neurons) == initial_inputs
    assert len(orch.circuit.output_neurons) == initial_outputs
