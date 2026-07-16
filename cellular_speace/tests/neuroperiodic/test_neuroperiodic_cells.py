"""Tests for Neural Periodic Table integration with DigitalNeuron and DigitalSynapse."""
from __future__ import annotations

import pytest

from speace_core.cellular_brain.cells.digital_neuron import DigitalNeuron
from speace_core.cellular_brain.cells.digital_synapse import DigitalSynapse
from speace_core.environment.environment_adapter import EnvironmentAdapter


def test_digital_neuron_periodic_identity_from_cell_type():
    n = DigitalNeuron(cell_id="n1", role="digital_neuron", cell_type="input")
    element = n.get_periodic_element()
    assert element is not None
    assert element.symbol == "Ph"


def test_digital_synapse_periodic_identity():
    syn = DigitalSynapse(
        cell_id="s1",
        role="digital_synapse",
        source="a",
        target="b",
        source_periodic_element_id=1,
        target_periodic_element_id=17,
    )
    assert syn.source_periodic_element_id == 1
    assert syn.target_periodic_element_id == 17
    bond = syn.predict_bond_properties()
    assert bond["source"] == "Ph"
    assert bond["target"] == "Mo"
    assert "bond_type" in bond
    assert "strength" in bond


def test_mvp_orchestrator_assigns_periodic_identities():
    adapter = EnvironmentAdapter()
    orch = adapter.orchestrator
    input_neuron = orch.circuit.input_neurons[0]
    output_neuron = orch.circuit.output_neurons[0]

    assert input_neuron.cell_type == "input"
    assert input_neuron.periodic_element_id == 1
    assert output_neuron.cell_type == "output"
    assert output_neuron.periodic_element_id == 17

    # At least some synapses should carry source/target periodic IDs.
    synapses_with_ids = [
        s for s in orch.circuit.synapses
        if s.source_periodic_element_id is not None and s.target_periodic_element_id is not None
    ]
    assert len(synapses_with_ids) > 0


def test_hidden_neurons_have_varied_periodic_elements():
    adapter = EnvironmentAdapter()
    orch = adapter.orchestrator
    ids = {n.periodic_element_id for n in orch.circuit.hidden_neurons}
    assert len(ids) >= 2


def test_neuron_periodic_classification():
    n = DigitalNeuron(cell_id="n1", role="digital_neuron", cell_type="output")
    classification = n.periodic_classification()
    assert classification["classified"] is True
    assert classification["symbol"] == "Mo"
