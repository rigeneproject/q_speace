"""Tests for conservative COR consolidation via STDP."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

import pytest

from speace_core.cellular_brain.cells.digital_neuron import DigitalNeuron
from speace_core.cellular_brain.cells.digital_synapse import DigitalSynapse
from speace_core.cellular_brain.dynamics.cognitive_objective_reduction import (
    CognitiveObjectiveReduction,
    CORHypothesis,
)
from speace_core.cellular_brain.dynamics.stdp_engine import STDPEngine


@dataclass
class FakeCircuit:
    input_neurons: List[DigitalNeuron] = field(default_factory=list)
    hidden_neurons: List[DigitalNeuron] = field(default_factory=list)
    output_neurons: List[DigitalNeuron] = field(default_factory=list)
    synapses: List[DigitalSynapse] = field(default_factory=list)


def make_neuron(cell_id: str, latent: Dict[str, float] | None = None, pressure: float = 0.0) -> DigitalNeuron:
    n = DigitalNeuron(cell_id=cell_id, role="excitatory")
    if latent is not None:
        n.update_latent_states(latent)
    n.cor_pressure = pressure
    return n


def test_cor_stdpi_reinforces_active_synapses():
    """COR with STDP should reinforce only synapses with pre/post timing evidence."""
    n1 = make_neuron("n1", {"A": 0.2, "B": 0.8}, pressure=0.5)
    n2 = make_neuron("n2", {"A": 0.1, "B": 0.9}, pressure=0.5)

    # Active synapse: recent pre and post spike timing.
    active_syn = DigitalSynapse(
        cell_id="s_active",
        role="digital_synapse",
        source="n1",
        target="n2",
        weight=0.5,
        last_pre_spike_tick=5,
        last_post_spike_tick=6,
    )
    # Inactive synapse: no timing evidence.
    inactive_syn = DigitalSynapse(
        cell_id="s_inactive",
        role="digital_synapse",
        source="n1",
        target="n2",
        weight=0.5,
    )

    circuit = FakeCircuit(hidden_neurons=[n1, n2], synapses=[active_syn, inactive_syn])
    cor = CognitiveObjectiveReduction(
        circuit=circuit,
        phi_threshold_factor=0.1,
        collapse_refractory_ticks=0,
    )
    cor.stdp_engine = STDPEngine()

    result = cor.tick(tick=1)
    assert result.collapsed is True
    assert result.dominant_hypothesis.label == "B"

    # Active synapse should be reinforced; inactive gets only tiny direct boost.
    assert active_syn.weight > 0.5
    assert inactive_syn.weight >= 0.5
    # Active synapse should be reinforced via STDP; inactive only direct.
    assert active_syn.weight > 0.5
    assert active_syn.trust > 0.5


def test_cor_falls_back_to_direct_boost_without_stdp():
    """Without STDP engine, COR still applies a bounded direct weight boost."""
    n1 = make_neuron("n1", {"A": 0.2, "B": 0.8}, pressure=0.5)
    n2 = make_neuron("n2", {"A": 0.1, "B": 0.9}, pressure=0.5)
    syn = DigitalSynapse(
        cell_id="s1",
        role="digital_synapse",
        source="n1",
        target="n2",
        weight=0.5,
    )

    circuit = FakeCircuit(hidden_neurons=[n1, n2], synapses=[syn])
    cor = CognitiveObjectiveReduction(
        circuit=circuit,
        phi_threshold_factor=0.1,
        collapse_refractory_ticks=0,
    )
    # stdp_engine intentionally left as None

    result = cor.tick(tick=1)
    assert result.collapsed is True
    assert syn.weight > 0.5
    assert syn.weight <= 0.6  # bounded direct boost


def test_cor_conservative_reinforcement_respects_weight_ceiling():
    """Direct weight boost must never exceed 1.0."""
    n1 = make_neuron("n1", {"B": 1.0}, pressure=0.5)
    n2 = make_neuron("n2", {"B": 1.0}, pressure=0.5)
    syn = DigitalSynapse(
        cell_id="s1",
        role="digital_synapse",
        source="n1",
        target="n2",
        weight=0.98,
    )

    circuit = FakeCircuit(hidden_neurons=[n1, n2], synapses=[syn])
    cor = CognitiveObjectiveReduction(
        circuit=circuit,
        phi_threshold_factor=0.1,
        collapse_refractory_ticks=0,
    )
    cor.tick(tick=1)
    assert syn.weight <= 1.0


def test_cor_summary_reports_stdpi_and_direct_changes():
    n1 = make_neuron("n1", {"B": 0.8}, pressure=0.5)
    n2 = make_neuron("n2", {"B": 0.9}, pressure=0.5)
    active = DigitalSynapse(
        cell_id="s_active",
        role="digital_synapse",
        source="n1",
        target="n2",
        weight=0.5,
        last_pre_spike_tick=1,
        last_post_spike_tick=2,
    )
    inactive = DigitalSynapse(
        cell_id="s_inactive",
        role="digital_synapse",
        source="n1",
        target="n2",
        weight=0.5,
    )

    circuit = FakeCircuit(hidden_neurons=[n1, n2], synapses=[active, inactive])
    cor = CognitiveObjectiveReduction(
        circuit=circuit,
        phi_threshold_factor=0.1,
        collapse_refractory_ticks=0,
    )
    cor.stdp_engine = STDPEngine()

    result = cor.tick(tick=1)
    summary = result.reconfiguration_summary
    assert summary.get("stdp_reinforced", 0) >= 1
    assert summary.get("direct_reinforced", 0) >= 1
    assert summary["synapses_strengthened"] >= 2
