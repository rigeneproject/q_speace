import asyncio

from speace_core.cellular_brain.memory.morphology_events import MorphologyEventType
from speace_core.dna.parser import load_genome
from speace_core.orchestrator import CellularBrainOrchestrator


def test_orchestrator_differentiation_specializes_neurons():
    genome = load_genome("speace_core/dna/genome/default_genome.yaml")
    orch = CellularBrainOrchestrator.build_mvp(genome)

    # Set a hidden neuron region for differentiation
    target = orch.circuit.hidden_neurons[0]
    target.region = "hippocampus"
    target.differentiation_state = "undifferentiated"

    orch.run_differentiation()
    assert target.cell_type == "hippocampal_neuron"
    assert target.differentiation_state == "differentiated"


def test_orchestrator_neurogenesis_creates_differentiated_neuron():
    genome = load_genome("speace_core/dna/genome/default_genome.yaml")
    orch = CellularBrainOrchestrator.build_mvp(genome)

    # Force neurogenesis conditions
    orch.negative_feedback_count = 5
    for n in orch.circuit.hidden_neurons:
        n.energy = 1.0

    async def _run():
        for _ in range(5):
            await orch._tick()
        orch.run_neurogenesis()

    asyncio.run(_run())
    created_events = [
        e for e in orch.memory.events
        if e.event_type == MorphologyEventType.NEURON_CREATED
    ]
    assert len(created_events) >= 1
    # New neuron should have been differentiated (default generic_neuron or other)
    last_event = created_events[-1]
    assert "neuron_type" in last_event.metadata
