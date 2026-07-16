"""Tests for DNA-driven connectome weights derived from the Neural Periodic Table."""
from __future__ import annotations

import pytest

from speace_core.cellular_brain.cells.digital_neuron import DigitalNeuron
from speace_core.cellular_brain.cells.digital_synapse import DigitalSynapse
from speace_core.cellular_brain.neuroperiodic.neural_element import build_element
from speace_core.cellular_brain.neuroperiodic.neuroperiodic_integrator import (
    NeuroPeriodicIntegrator,
)
from speace_core.dna.models import SharedGenome, PeriodicTableGeneSet, PeriodicTrendGene
from speace_core.environment.environment_adapter import EnvironmentAdapter


def test_mvp_synapse_dna_driven_init():
    adapter = EnvironmentAdapter()
    synapses = adapter.orchestrator.circuit.synapses
    assert len(synapses) > 0
    driven = [s for s in synapses if s.dna_driven_init]
    assert len(driven) == len(synapses)


def test_mvp_synapse_weight_in_range():
    adapter = EnvironmentAdapter()
    for syn in adapter.orchestrator.circuit.synapses:
        assert 0.1 <= syn.weight <= 0.9
        assert 0.1 <= syn.trust <= 0.9
        assert 0.1 <= syn.periodic_plasticity <= 0.9


def test_mvp_synapse_bond_metadata_set():
    adapter = EnvironmentAdapter()
    synapses = adapter.orchestrator.circuit.synapses
    with_metadata = [
        s for s in synapses
        if s.periodic_bond_type is not None and s.periodic_bond_order is not None
    ]
    assert len(with_metadata) == len(synapses)


def test_apply_periodic_prediction_updates_synapse():
    src = DigitalNeuron(cell_id="src", role="digital_neuron", cell_type="input")
    tgt = DigitalNeuron(cell_id="tgt", role="digital_neuron", cell_type="output")
    syn = DigitalSynapse(
        cell_id="s1",
        role="digital_synapse",
        source=src.cell_id,
        target=tgt.cell_id,
        source_periodic_element_id=src.get_periodic_element().atomic_number,
        target_periodic_element_id=tgt.get_periodic_element().atomic_number,
    )
    baseline_weight = syn.weight
    syn.apply_periodic_prediction()
    assert syn.dna_driven_init is True
    assert syn.weight != pytest.approx(baseline_weight, abs=1e-6)
    assert syn.periodic_bond_type is not None
    assert syn.periodic_bond_order is not None


def test_periodic_connectome_weight_pattern():
    """Synapses between more compatible periodic elements get stronger weights."""
    integrator = NeuroPeriodicIntegrator()
    ph = build_element(1)
    mo = build_element(17)

    ph_to_mo = DigitalSynapse(
        cell_id="ph_mo",
        role="digital_synapse",
        source="a",
        target="b",
        source_periodic_element_id=ph.atomic_number,
        target_periodic_element_id=mo.atomic_number,
    )
    ph_to_ph = DigitalSynapse(
        cell_id="ph_ph",
        role="digital_synapse",
        source="a",
        target="c",
        source_periodic_element_id=ph.atomic_number,
        target_periodic_element_id=ph.atomic_number,
    )

    ph_to_mo.apply_periodic_prediction(integrator)
    ph_to_ph.apply_periodic_prediction(integrator)

    # Photoreceptor -> motor output is a strong feedforward pathway.
    assert ph_to_mo.weight >= ph_to_ph.weight


def test_dna_genome_influences_periodic_integrator():
    """A genome with periodic-table genes should be loaded by the integrator."""
    genes = PeriodicTableGeneSet(
        enabled=True,
        trends={
            "electronegativity": PeriodicTrendGene(
                name="Electronegativity",
                description="Test trend",
                across_period="0.1 + g * 0.5",
                down_group="0.9 - p * 0.4",
                noise_amplitude=0.0,
            ),
        },
    )
    genome = SharedGenome(periodic_table_genes=genes)
    integrator = NeuroPeriodicIntegrator.from_genome(genome)
    assert "electronegativity" in integrator.laws.trends


def test_mvp_uses_genome_integrator_for_synapse_weights():
    """build_mvp should derive weights through a genome-aware periodic integrator."""
    from speace_core.orchestrator import CellularBrainOrchestrator

    genome = SharedGenome()
    orch = CellularBrainOrchestrator.build_mvp(genome)
    assert any(s.dna_driven_init for s in orch.circuit.synapses)
    # At least one synapse should reflect non-default initialization
    assert any(s.periodic_plasticity != 0.5 for s in orch.circuit.synapses)
