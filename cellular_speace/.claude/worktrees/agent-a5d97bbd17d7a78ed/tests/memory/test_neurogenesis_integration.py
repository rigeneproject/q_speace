import asyncio
import random

from speace_core.cellular_brain.memory.morphological_memory import MorphologicalMemory
from speace_core.cellular_brain.memory.morphology_events import MorphologyEventType
from speace_core.dna.parser import load_genome
from speace_core.orchestrator import CellularBrainOrchestrator


def test_orchestrator_triggers_neurogenesis():
    random.seed(42)
    genome = load_genome("speace_core/dna/genome/default_genome.yaml")
    orch = CellularBrainOrchestrator.build_mvp(genome)

    async def _run():
        for i in range(10):
            await orch._tick()
            orch.feedback(-1.0)
        orch.run_neurogenesis()

    asyncio.run(_run())
    assert orch.memory.count_events(MorphologyEventType.NEURON_CREATED) >= 1


def test_orchestrator_neurogenesis_increases_neurons():
    random.seed(42)
    genome = load_genome("speace_core/dna/genome/default_genome.yaml")
    orch = CellularBrainOrchestrator.build_mvp(genome)
    initial = len(
        orch.circuit.input_neurons
        + orch.circuit.hidden_neurons
        + orch.circuit.output_neurons
    )

    async def _run():
        for i in range(10):
            await orch._tick()
            orch.feedback(-1.0)
        orch.run_neurogenesis()

    asyncio.run(_run())
    final = len(
        orch.circuit.input_neurons
        + orch.circuit.hidden_neurons
        + orch.circuit.output_neurons
    )
    assert final > initial
