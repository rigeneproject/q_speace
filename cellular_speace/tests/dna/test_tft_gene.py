"""Unit tests for the TFTpsp Pydantic schema."""

import pytest
from pydantic import ValidationError

from speace_core.dna.tft_gene import (
    ActivationCondition,
    EfficacyMetric,
    EpigeneticRule,
    FunctionalGeneConstraint,
    GeneInteraction,
    MutationPolicy,
    TFTPspGeneSet,
    TFTGene,
)


def test_minimal_gene_roundtrip():
    g = TFTGene(
        gene_id="tftpsp_001_tft",
        tft_index=1,
        name="Technological Fields Theory",
        short_label="TFT",
        function="Reference map of major technological fields.",
    )
    assert g.gene_id == "tftpsp_001_tft"
    assert g.tft_index == 1
    assert g.priority == 0.5
    assert g.mutation_policy.allowed is False
    assert g.mutation_policy.max_priority_delta_per_cycle == 0.05
    assert g.efficacy_metric.metric_name == "expression_ratio"


def test_gene_index_bounds():
    with pytest.raises(ValidationError):
        TFTGene(
            gene_id="bad",
            tft_index=0,
            name="x",
            short_label="x",
            function="x",
        )
    with pytest.raises(ValidationError):
        TFTGene(
            gene_id="bad",
            tft_index=34,
            name="x",
            short_label="x",
            function="x",
        )


def test_priority_bounds():
    base = dict(gene_id="g", tft_index=1, name="n", short_label="s", function="f")
    with pytest.raises(ValidationError):
        TFTGene(**base, priority=-0.01)
    with pytest.raises(ValidationError):
        TFTGene(**base, priority=1.01)


def test_activation_condition_boost_field():
    ac = ActivationCondition(trigger_tag="crisis", min_signal=0.2, boost=1.5)
    assert ac.trigger_tag == "crisis"
    assert ac.boost == 1.5


def test_gene_interaction_relation_typed():
    gi = GeneInteraction(target_gene_id="tftpsp_005_tftof", relation="supports", weight=0.7)
    assert gi.relation == "supports"
    assert gi.weight == 0.7


def test_functional_constraint_invariant_accepted():
    c = FunctionalGeneConstraint(
        name="coherence_anchor",
        invariant="coherence_preservation",
        description="keeps the field aligned",
    )
    assert c.invariant == "coherence_preservation"


def test_epigenetic_lock_open_for_emergency_genes():
    rule = EpigeneticRule(tag="crisis", effect="lock_open")
    assert rule.effect == "lock_open"


def test_mutation_policy_default_readonly():
    mp = MutationPolicy()
    assert mp.allowed is False
    assert mp.requires_governance is True
    assert mp.changeable_fields == []


def test_mutation_policy_explicit_changeable_fields():
    mp = MutationPolicy(allowed=True, changeable_fields=["priority", "function"])
    assert mp.allowed is True
    assert mp.changeable_fields == ["priority", "function"]


def test_efficacy_metric_with_threshold():
    em = EfficacyMetric(
        metric_name="expression_ratio",
        target_direction="maintain_above_threshold",
        threshold=0.3,
        observation_window_ticks=100,
    )
    assert em.threshold == 0.3
    assert em.target_direction == "maintain_above_threshold"


def test_geneset_lookup_helpers():
    g1 = TFTGene(
        gene_id="tftpsp_001_tft",
        tft_index=1,
        name="A",
        short_label="TFT",
        function="x",
        domain_tags=["technology"],
    )
    g2 = TFTGene(
        gene_id="tftpsp_018_5pc",
        tft_index=18,
        name="B",
        short_label="5PC",
        function="y",
        domain_tags=["crisis", "environment"],
        epigenetic_mechanisms=[EpigeneticRule(tag="crisis", effect="lock_open")],
    )
    gs = TFTPspGeneSet(genes=[g1, g2])

    assert gs.get("tftpsp_001_tft") is g1
    assert gs.by_tft_index(18) is g2
    assert gs.by_short_label("5PC") is g2
    assert gs.by_domain_tag("environment") == [g2]
    assert gs.by_domain_tag("nonexistent") == []
    assert gs.emergency_genes() == [g2]
    assert gs.get("missing") is None
    assert gs.by_tft_index(99) is None


def test_geneset_disabled():
    gs = TFTPspGeneSet(enabled=False, genes=[])
    assert gs.enabled is False
    assert gs.genes == []
    assert gs.emergency_genes() == []
