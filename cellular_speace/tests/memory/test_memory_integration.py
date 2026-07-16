import asyncio
import random

from speace_core.cellular_brain.memory.morphological_memory import MorphologicalMemory
from speace_core.cellular_brain.memory.morphology_events import MorphologyEventType
from speace_core.cellular_brain.circuits.neural_circuit import NeuralCircuit
from speace_core.cellular_brain.cells.digital_microglia import DigitalMicroglia
from speace_core.cellular_brain.cells.digital_neuron import DigitalNeuron
from speace_core.cellular_brain.cells.digital_synapse import DigitalSynapse
from speace_core.dna.parser import load_genome
from speace_core.orchestrator import CellularBrainOrchestrator


def test_feedback_records_events():
    genome = load_genome("speace_core/dna/genome/default_genome.yaml")
    mem = MorphologicalMemory()
    neuron = DigitalNeuron(cell_id="n1", role="digital_neuron")
    syn = DigitalSynapse(cell_id="s1", role="digital_synapse", source="n1", target="n2", weight=0.5, trust=0.5)
    circuit = NeuralCircuit(
        circuit_id="test",
        input_neurons=[neuron],
        synapses=[syn],
        memory=mem,
    )
    circuit.apply_feedback(1.0)
    assert mem.count_events(MorphologyEventType.SYNAPSE_REINFORCED) == 1
    assert mem.events[0].metadata["old_weight"] == 0.5


def test_immune_records_pruning():
    genome = load_genome("speace_core/dna/genome/default_genome.yaml")
    mem = MorphologicalMemory()
    syn = DigitalSynapse(cell_id="s1", role="digital_synapse", source="n1", target="n2", trust=0.05, use_count=2)
    mg = DigitalMicroglia(cell_id="m1", role="digital_microglia")
    circuit = NeuralCircuit(
        circuit_id="test",
        synapses=[syn],
        microglia=[mg],
        memory=mem,
    )
    circuit.run_immune()
    assert mem.count_events(MorphologyEventType.SYNAPSE_PRUNED) == 1


def test_orchestrator_records_snapshots():
    random.seed(42)
    genome = load_genome("speace_core/dna/genome/default_genome.yaml")
    orch = CellularBrainOrchestrator.build_mvp(genome)

    async def _run():
        for _ in range(5):
            await orch._tick()

    asyncio.run(_run())
    assert len(orch.memory.snapshots) == 5
    assert orch.memory.latest_phi() is not None
    assert orch.memory.phi_trend() is not None
