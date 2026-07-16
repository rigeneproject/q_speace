"""Tests for CognitiveObjectiveReduction (COR)."""
import math
from dataclasses import dataclass, field
from typing import Dict, List

import pytest

from speace_core.cellular_brain.cells.digital_neuron import DigitalNeuron
from speace_core.cellular_brain.dynamics.cognitive_objective_reduction import (
    CognitiveObjectiveReduction,
    CORHypothesis,
    CORResult,
)


@dataclass
class FakeCircuit:
    input_neurons: List[DigitalNeuron] = field(default_factory=list)
    hidden_neurons: List[DigitalNeuron] = field(default_factory=list)
    output_neurons: List[DigitalNeuron] = field(default_factory=list)
    synapses: List[object] = field(default_factory=list)


@dataclass
class FakeSynapse:
    source: str = ""
    target: str = ""
    weight: float = 0.5


def make_neuron(cell_id: str, latent: Dict[str, float] | None = None, pressure: float = 0.0) -> DigitalNeuron:
    n = DigitalNeuron(cell_id=cell_id, role="excitatory")
    if latent is not None:
        n.update_latent_states(latent)
    n.cor_pressure = pressure
    return n


def test_cor_entropy_with_latent_states():
    circuit = FakeCircuit(
        hidden_neurons=[
            make_neuron("n1", {"A": 0.3, "B": 0.7}),
            make_neuron("n2", {"A": 0.6, "B": 0.4}),
        ]
    )
    cor = CognitiveObjectiveReduction(circuit=circuit)
    h = cor._compute_entropy()
    assert 0.0 <= h <= 1.0
    assert h > 0.0  # two distinct distributions give non-zero entropy


def test_cor_no_latent_states_falls_back_to_activation():
    circuit = FakeCircuit(
        hidden_neurons=[
            make_neuron("n1"),
            make_neuron("n2"),
        ]
    )
    circuit.hidden_neurons[0].activation = 0.9
    circuit.hidden_neurons[1].activation = 0.1
    cor = CognitiveObjectiveReduction(circuit=circuit)
    h = cor._compute_entropy()
    assert 0.0 <= h <= 1.0


def test_cor_collapse_condition_met():
    circuit = FakeCircuit(
        hidden_neurons=[
            make_neuron("n1", {"A": 0.2, "B": 0.8}),
            make_neuron("n2", {"A": 0.1, "B": 0.9}),
            make_neuron("n3", {"A": 0.7, "B": 0.3}),
        ]
    )
    for n in circuit.hidden_neurons:
        n.cor_pressure = 0.5
    cor = CognitiveObjectiveReduction(
        circuit=circuit,
        phi_threshold_factor=0.1,  # low threshold to force collapse
        collapse_refractory_ticks=0,
    )
    result = cor.tick(tick=1)
    assert isinstance(result, CORResult)
    assert result.collapsed is True
    assert result.dominant_hypothesis is not None
    assert result.dominant_hypothesis.label == "B"
    assert result.neurons_collapsed >= 2


def test_cor_collapse_condition_not_met():
    circuit = FakeCircuit(
        hidden_neurons=[
            make_neuron("n1", {"A": 0.5, "B": 0.5}),
        ]
    )
    cor = CognitiveObjectiveReduction(
        circuit=circuit,
        phi_threshold_factor=2.0,  # high threshold prevents collapse
    )
    result = cor.tick(tick=1)
    assert result.collapsed is False
    assert result.dominant_hypothesis is None


def test_cor_refractory_period():
    circuit = FakeCircuit(
        hidden_neurons=[
            make_neuron("n1", {"A": 0.1, "B": 0.9}),
            make_neuron("n2", {"A": 0.1, "B": 0.9}),
        ]
    )
    for n in circuit.hidden_neurons:
        n.cor_pressure = 0.5
    cor = CognitiveObjectiveReduction(
        circuit=circuit,
        phi_threshold_factor=0.1,
        collapse_refractory_ticks=5,
    )
    first = cor.tick(tick=1)
    assert first.collapsed is True
    second = cor.tick(tick=2)
    assert second.collapsed is False  # refractory


def test_cor_reconfiguration_strengthens_synapses():
    n1 = make_neuron("n1", {"A": 0.2, "B": 0.8}, pressure=0.5)
    n2 = make_neuron("n2", {"A": 0.1, "B": 0.9}, pressure=0.5)
    s = FakeSynapse(source="n1", target="n2", weight=0.5)
    circuit = FakeCircuit(
        hidden_neurons=[n1, n2],
        synapses=[s],
    )
    cor = CognitiveObjectiveReduction(
        circuit=circuit,
        phi_threshold_factor=0.1,
        collapse_refractory_ticks=0,
    )
    cor.tick(tick=1)
    assert s.weight > 0.5


def test_cor_generate_meta_event_payload():
    circuit = FakeCircuit(
        hidden_neurons=[
            make_neuron("n1", {"A": 0.2, "B": 0.8}),
            make_neuron("n2", {"A": 0.1, "B": 0.9}),
        ]
    )
    for n in circuit.hidden_neurons:
        n.cor_pressure = 0.5
    cor = CognitiveObjectiveReduction(
        circuit=circuit,
        phi_threshold_factor=0.1,
        collapse_refractory_ticks=0,
    )
    cor.tick(tick=1)
    payload = cor.generate_meta_event_payload()
    assert payload["event"] == "cognitive_objective_reduction"
    assert payload["collapsed"] is True
    assert payload["dominant_label"] == "B"


def test_cor_persistence(tmp_path):
    import os
    report_dir = tmp_path / "cor"
    circuit = FakeCircuit(
        hidden_neurons=[
            make_neuron("n1", {"A": 0.2, "B": 0.8}),
            make_neuron("n2", {"A": 0.1, "B": 0.9}),
        ]
    )
    for n in circuit.hidden_neurons:
        n.cor_pressure = 0.5
    cor = CognitiveObjectiveReduction(
        circuit=circuit,
        phi_threshold_factor=0.1,
        collapse_refractory_ticks=0,
        report_dir=str(report_dir),
    )
    cor.tick(tick=1)
    report_file = report_dir / "cor_events.jsonl"
    assert report_file.exists()
    lines = report_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    import json
    record = json.loads(lines[0])
    assert record["collapsed"] is True


def test_digital_neuron_latent_helpers():
    n = DigitalNeuron(cell_id="n_test", role="excitatory")
    n.update_latent_states({"A": 0.3, "B": 0.7})
    assert abs(sum(n.latent_states.values()) - 1.0) < 1e-9
    assert n.dominant_latent_state() == "B"
    n.add_latent_state("C", 0.5)
    assert "C" in n.latent_states
    assert abs(sum(n.latent_states.values()) - 1.0) < 1e-9
    assert n.latent_entropy() >= 0.0




# ---------------------------------------------------------------------------
# Orchestrator integration smoke test
# ---------------------------------------------------------------------------

import asyncio

from speace_core.dna.models import SharedGenome
from speace_core.orchestrator import CellularBrainOrchestrator


def test_orchestrator_initializes_cor_engine():
    genome = SharedGenome()
    orch = CellularBrainOrchestrator.build_mvp(genome=genome)
    orch.cor_enabled = True
    orch.cor_phi_threshold_factor = 0.1
    orch.cor_min_latent_states = 2
    orch.cor_max_hypotheses = 4
    orch.model_post_init(None)
    assert orch._cor_engine is not None


def test_orchestrator_tick_runs_cor_and_collapses():
    genome = SharedGenome()
    orch = CellularBrainOrchestrator.build_mvp(genome=genome)
    orch.cor_enabled = True
    orch.cor_phi_threshold_factor = 0.1
    orch.cor_min_latent_states = 2
    orch.cor_max_hypotheses = 4
    orch.model_post_init(None)

    for n in orch.circuit.hidden_neurons[:3]:
        n.update_latent_states({"A": 0.2, "B": 0.8})
        n.cor_pressure = 0.5

    asyncio.run(orch._tick())
    assert orch._last_cor_result is not None
    assert orch._last_cor_result.collapsed is True
    assert orch._last_cor_result.dominant_hypothesis is not None
