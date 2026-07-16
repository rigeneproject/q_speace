"""Tests for DNA-driven Neural Periodic Table laws."""
from typing import Any

import pytest

from speace_core.dna.models import (
    SharedGenome,
    PeriodicTableGeneSet,
    PeriodicTrendGene,
    ValenceRuleGene,
    ReactionRuleGene,
)
from speace_core.cellular_brain.neuroperiodic.periodic_law import PeriodicLaw
from speace_core.cellular_brain.neuroperiodic.neuroperiodic_integrator import (
    NeuroPeriodicIntegrator,
)
from speace_core.cellular_brain.neuroperiodic.neural_element import (
    ElementGroup,
    ElementPeriod,
)


def make_genome_with_periodic_genes() -> SharedGenome:
    """Build a minimal genome whose periodic-table genes override defaults."""
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
            "ionization_energy": PeriodicTrendGene(
                name="IonizationEnergy",
                description="Test trend",
                across_period="g",
                down_group="1.0 - p",
                noise_amplitude=0.0,
            ),
        },
        valence_rules=[
            ValenceRuleGene(
                name="TestFeedforward",
                description="Lower period to higher period",
                condition="source.period.value < target.period.value",
                result={"polarity": "forward", "direction_boost": 0.25},
            ),
        ],
        reaction_rules=[
            ReactionRuleGene(
                name="TestReaction",
                description="A + B → C",
                reactants=["Ph", "Sc"],
                products=["Cc"],
                energy_barrier=0.2,
                rate_constant=0.5,
            ),
        ],
    )
    return SharedGenome(periodic_table_genes=genes)


def test_periodic_law_loads_from_genome():
    genome = make_genome_with_periodic_genes()
    law = PeriodicLaw.from_genome(genome)
    assert "electronegativity" in law.trends
    assert len(law.valence_rules) == 1
    assert law.valence_rules[0].name == "TestFeedforward"
    assert len(law.reaction_rules) == 1
    assert law.reaction_rules[0].name == "TestReaction"


def test_dna_trend_evaluation():
    genome = make_genome_with_periodic_genes()
    law = PeriodicLaw.from_genome(genome)
    en = law.trends["electronegativity"].predict(
        period=ElementPeriod.SENSORY_TRANSDUCTION,
        group=ElementGroup.SENSORY_VISUAL,
    )
    # g=0, p=0 → (0.1 + 0 + 0.9) / 2 = 0.5
    assert 0.49 <= en <= 0.51


def test_dna_trend_evaluation_high_group():
    genome = make_genome_with_periodic_genes()
    law = PeriodicLaw.from_genome(genome)
    en = law.trends["electronegativity"].predict(
        period=ElementPeriod.EXECUTIVE,
        group=ElementGroup.EXECUTIVE_PFC,
    )
    # g=(9-1)/17≈0.47, p=(5-1)/6≈0.67
    # across ≈ 0.1 + 0.47*0.5 ≈ 0.335
    # down ≈ 0.9 - 0.67*0.4 ≈ 0.632
    # avg ≈ 0.483
    assert 0.4 <= en <= 0.6


def test_neuro_periodic_integrator_from_genome():
    genome = make_genome_with_periodic_genes()
    integrator = NeuroPeriodicIntegrator.from_genome(genome)
    assert integrator.laws is not None
    assert "TestFeedforward" in [r.name for r in integrator.laws.valence_rules]


def test_periodic_law_falls_back_when_genome_has_no_genes():
    genome = SharedGenome()
    law = PeriodicLaw.from_genome(genome)
    # Defaults should be present
    assert "electronegativity" in law.trends
    assert any(r.name == "Octet Rule" for r in law.valence_rules)


def test_periodic_law_disabled_genes_fall_back():
    genes = PeriodicTableGeneSet(enabled=False)
    genome = SharedGenome(periodic_table_genes=genes)
    law = PeriodicLaw.from_genome(genome)
    assert any(r.name == "Octet Rule" for r in law.valence_rules)


def test_valence_rule_from_dna_evaluates():
    genome = make_genome_with_periodic_genes()
    law = PeriodicLaw.from_genome(genome)
    rule = law.valence_rules[0]
    from speace_core.cellular_brain.neuroperiodic.neural_element import build_element
    src = build_element(1)  # Ph, period 1
    tgt = build_element(14)  # Pf, period 5
    assert rule.check(src, tgt) is True
