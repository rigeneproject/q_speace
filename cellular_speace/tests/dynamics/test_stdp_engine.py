"""Tests for the STDP engine and its integration with DigitalSynapse / NeuralCircuit."""
from __future__ import annotations

import asyncio

import pytest

from speace_core.cellular_brain.cells.digital_neuron import DigitalNeuron
from speace_core.cellular_brain.cells.digital_synapse import DigitalSynapse
from speace_core.cellular_brain.circuits.neural_circuit import NeuralCircuit
from speace_core.cellular_brain.dynamics.stdp_engine import STDPEngine


def test_ltp_increases_weight():
    engine = STDPEngine(tau_plus=10.0, a_plus=0.1)
    syn = DigitalSynapse(cell_id="s", role="digital_synapse", source="a", target="b", weight=0.5, trust=0.5)
    syn.last_pre_spike_tick = 0
    syn.last_post_spike_tick = 5
    engine.apply_updates([syn], dopamine=0.0, base_plasticity=1.0)
    assert syn.weight > 0.5
    assert syn.trust > 0.5


def test_ltd_decreases_weight():
    engine = STDPEngine(tau_minus=10.0, a_minus=0.1)
    syn = DigitalSynapse(cell_id="s", role="digital_synapse", source="a", target="b", weight=0.5, trust=0.5)
    syn.last_pre_spike_tick = 5
    syn.last_post_spike_tick = 0
    engine.apply_updates([syn], dopamine=0.0, base_plasticity=1.0)
    assert syn.weight < 0.5
    assert syn.trust < 0.5


def test_dopamine_amplifies_ltp():
    engine = STDPEngine(tau_plus=10.0, a_plus=0.1, dopamine_gain=2.0)
    syn_low = DigitalSynapse(cell_id="s1", role="digital_synapse", source="a", target="b", weight=0.5, trust=0.5)
    syn_high = DigitalSynapse(cell_id="s2", role="digital_synapse", source="a", target="b", weight=0.5, trust=0.5)
    syn_low.last_pre_spike_tick = 0
    syn_low.last_post_spike_tick = 5
    syn_high.last_pre_spike_tick = 0
    syn_high.last_post_spike_tick = 5

    engine.apply_updates([syn_low], dopamine=0.0, base_plasticity=1.0)
    engine.apply_updates([syn_high], dopamine=0.5, base_plasticity=1.0)

    assert syn_high.weight > syn_low.weight


def test_neural_circuit_records_spike_timing():
    pre = DigitalNeuron(cell_id="pre", role="digital_neuron", threshold=0.5, activation=0.0)
    post = DigitalNeuron(cell_id="post", role="digital_neuron", threshold=0.5, activation=0.0)
    pre.targets = ["post"]
    syn = DigitalSynapse(cell_id="s", role="digital_synapse", source="pre", target="post", weight=1.0, trust=1.0)
    circuit = NeuralCircuit(
        circuit_id="test",
        input_neurons=[],
        hidden_neurons=[pre, post],
        output_neurons=[],
        synapses=[syn],
    )

    pre.activation = 1.0
    asyncio.run(circuit.tick())
    assert circuit.current_tick == 1
    assert syn.last_pre_spike_tick == 1
    assert syn.last_post_spike_tick is None

    # Next tick: post receives activation from pre and fires
    asyncio.run(circuit.tick())
    assert syn.last_post_spike_tick == 2


def test_apply_feedback_runs_stdp_and_clears_timing():
    pre = DigitalNeuron(cell_id="pre", role="digital_neuron", threshold=0.5, activation=0.0)
    post = DigitalNeuron(cell_id="post", role="digital_neuron", threshold=0.5, activation=0.0)
    pre.targets = ["post"]
    syn = DigitalSynapse(cell_id="s", role="digital_synapse", source="pre", target="post", weight=0.5, trust=0.5)
    circuit = NeuralCircuit(
        circuit_id="test",
        input_neurons=[],
        hidden_neurons=[pre, post],
        output_neurons=[],
        synapses=[syn],
    )

    pre.activation = 1.0
    asyncio.run(circuit.tick())  # pre fires, post receives subthreshold? weight=0.5 -> 0.5, not enough
    # Force post timing manually to simulate delayed post spike
    syn.last_post_spike_tick = circuit.current_tick + 1

    old_weight = syn.weight
    circuit.apply_feedback(1.0)
    assert syn.weight != old_weight
    assert syn.last_pre_spike_tick is None
    assert syn.last_post_spike_tick is None
