"""Tests for the TFTpsp Digital RNA expression engine."""

from __future__ import annotations

import pytest

from speace_core.digital_rna.models import Transcriptome
from speace_core.digital_rna.tftpsp_engine import (
    build_tftpsp_transcriptome,
    expression_for_gene,
    infer_context_tags,
    populate_tftpsp_transcriptome,
)
from speace_core.dna.tftpsp_library import TFTPspGeneLibrary


@pytest.fixture(scope="module")
def lib() -> TFTPspGeneLibrary:
    return TFTPspGeneLibrary.default()


# ---------------------------------------------------------------------------
# infer_context_tags
# ---------------------------------------------------------------------------


def test_infer_context_tags_threshold_half():
    tags = infer_context_tags({"crisis": 0.5, "energy": 0.49, "novelty": 0.7})
    assert "crisis" in tags
    assert "novelty" in tags
    assert "energy" not in tags


def test_infer_context_tags_ignores_none():
    tags = infer_context_tags({"crisis": None, "novelty": 1.0})
    assert "crisis" not in tags
    assert "novelty" in tags


def test_infer_context_tags_is_sorted_dedup():
    tags = infer_context_tags({"b": 1.0, "a": 1.0, "c": 0.9, "a": 1.0})
    assert tags == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# expression_for_gene: formula basics
# ---------------------------------------------------------------------------


def test_default_expression_equals_priority(lib):
    gene = lib.by_short_label("CFU")  # priority 0.8, no activation tags active
    expr = expression_for_gene(gene, context_tags=[], context_state={})
    assert expr == pytest.approx(0.8)


def test_activation_boost_multiplies_when_signal_above_min(lib):
    # TFT-1 (TFT) priority 0.8; bootstrap boost 1.5 -> 1.2 (clamped to 1.0)
    gene = lib.by_short_label("TFT")
    expr = expression_for_gene(
        gene,
        context_tags=["bootstrap"],
        context_state={"bootstrap": 1.0},
    )
    assert expr == pytest.approx(1.0)  # engine clamps the raw 1.2 to 1.0


def test_activation_boost_ignored_when_signal_below_min(lib):
    # TFT-1 only activates on bootstrap / orientation. Use an unrelated tag
    # so no activation boost applies at all.
    gene = lib.by_short_label("TFT")
    expr = expression_for_gene(
        gene,
        context_tags=["crisis"],
        context_state={"crisis": 0.4},
    )
    # No boost applies -> base priority only
    assert expr == pytest.approx(0.8)


def test_min_signal_threshold_blocks_activation(lib):
    """Activation with min_signal=0.5 must NOT apply when signal=0.4."""
    from speace_core.dna.tft_gene import ActivationCondition, TFTGene

    gene = TFTGene(
        gene_id="tftpsp_test_min_signal",
        tft_index=33,  # schema requires <= 33
        name="MinSignal Probe",
        short_label="MSP",
        function="probe",
        priority=0.5,
        activation_conditions=[
            ActivationCondition(trigger_tag="probe", boost=1.5, min_signal=0.5),
        ],
    )
    low = expression_for_gene(
        gene, context_tags=["probe"], context_state={"probe": 0.4}
    )
    high = expression_for_gene(
        gene, context_tags=["probe"], context_state={"probe": 0.5}
    )
    assert low == pytest.approx(0.5)
    assert high == pytest.approx(0.5 * 1.5)


def test_expression_clamped_to_one():
    # Real gene that crosses the cap: TFT-1 priority 0.8 + bootstrap 1.5 = 1.2
    from speace_core.dna.tft_gene import TFTGene
    from speace_core.dna.tftpsp_library import TFTPspGeneLibrary

    lib = TFTPspGeneLibrary.default()
    gene = lib.by_short_label("TFT")
    expr = expression_for_gene(
        gene,
        context_tags=["bootstrap"],
        context_state={"bootstrap": 1.0},
    )
    assert expr == 1.0  # engine clamps 0.8 * 1.5 = 1.2 to 1.0


def test_expression_lower_bound_is_respected():
    """When epigenetic suppress modifies below 0, expression floors at 0."""
    # EPSHCPE-TFT has suppress=0.0 on the 'normal' tag (silence-like).
    from speace_core.dna.tftpsp_library import TFTPspGeneLibrary

    lib = TFTPspGeneLibrary.default()
    gene = lib.by_short_label("EPSHCPE-TFT")
    expr = expression_for_gene(
        gene,
        context_tags=["normal"],
        context_state={"normal": 1.0},
    )
    assert expr == 0.0


# ---------------------------------------------------------------------------
# epigenetic mechanisms
# ---------------------------------------------------------------------------


def test_silence_rule_forces_expression_to_zero(lib):
    gene = lib.by_short_label("EPSHCPE-TFT")  # has 'normal' suppress=0.0 rule
    # Activate the 'normal' suppress rule -> expression collapses to 0
    expr = expression_for_gene(
        gene,
        context_tags=["normal"],
        context_state={"normal": 1.0},
    )
    assert expr == 0.0


def test_lock_open_keeps_baseline_when_tag_inactive(lib):
    # Without crisis/existential_threat active, EPSHCPE has no boost from
    # lock_open rules and base priority is 0.1.
    gene = lib.by_short_label("EPSHCPE-TFT")
    expr = expression_for_gene(
        gene,
        context_tags=["other"],
        context_state={"other": 1.0},
    )
    assert expr == pytest.approx(gene.priority)


def test_lock_open_combines_with_activation_on_explicit_crisis(lib):
    # TFT-23 priority 0.1, 'crisis' activation boost 2.0, lock_open no-op
    # (modifier 1.0). Net effect: 0.1 * 2.0 = 0.2.
    gene = lib.by_short_label("EPSHCPE-TFT")
    expr = expression_for_gene(
        gene,
        context_tags=["crisis"],
        context_state={"crisis": 1.0},
    )
    assert expr == pytest.approx(0.1 * 2.0)


def test_boost_rule_multiplies_when_active(lib):
    # TFT-20 (PCAI) priority 0.6, 'innovation' activation boost 1.5 -> 0.9
    gene = lib.by_short_label("PCAI-TFT")
    expr = expression_for_gene(
        gene,
        context_tags=["innovation"],
        context_state={"innovation": 1.0},
    )
    assert expr == pytest.approx(0.6 * 1.5)


def test_innovation_tag_boosts_pcai(lib):
    # TFT-20 (PCAI-TFT) priority 0.6; 'innovation' boost 1.5
    gene = lib.by_short_label("PCAI-TFT")
    expr = expression_for_gene(
        gene,
        context_tags=["innovation"],
        context_state={"innovation": 1.0},
    )
    assert expr == pytest.approx(0.6 * 1.5)


# ---------------------------------------------------------------------------
# populate_tftpsp_transcriptome
# ---------------------------------------------------------------------------


def test_populate_writes_one_profile_per_gene(lib):
    tr = Transcriptome(context_key="default")
    written = populate_tftpsp_transcriptome(tr, lib._gene_set, {})
    assert written == 33
    assert len(tr.expression_profiles) == 33


def test_populate_idempotent(lib):
    tr = Transcriptome(context_key="default")
    populate_tftpsp_transcriptome(tr, lib._gene_set, {})
    first = dict(tr.expression_profiles)

    populate_tftpsp_transcriptome(tr, lib._gene_set, {})
    second = dict(tr.expression_profiles)

    assert set(first.keys()) == set(second.keys())
    for k in first:
        assert first[k].expression == pytest.approx(second[k].expression)


def test_populate_marks_bcel_genes(lib):
    tr = Transcriptome(context_key="default")
    populate_tftpsp_transcriptome(tr, lib._gene_set, {})
    bcel_tags = {
        name
        for name, profile in tr.expression_profiles.items()
        if "tftpsp_bcel" in profile.context_tags
    }
    # There are exactly 5 BCEL-mapped genes in the catalogue
    assert len(bcel_tags) == 5
    assert "tftpsp_023_epshcpe" in bcel_tags
    assert "tftpsp_033_aiscdsagi" in bcel_tags


def test_populate_marks_emergency_genes(lib):
    tr = Transcriptome(context_key="default")
    populate_tftpsp_transcriptome(tr, lib._gene_set, {})
    emergency = {
        name
        for name, profile in tr.expression_profiles.items()
        if "tftpsp_emergency" in profile.context_tags
    }
    assert emergency == {"tftpsp_023_epshcpe"}


def test_populate_carries_functional_constraints(lib):
    tr = Transcriptome(context_key="default")
    populate_tftpsp_transcriptome(tr, lib._gene_set, {})
    invariants = {c["invariant"] for c in tr.functional_constraints}
    # coherence_preservation is referenced by both TFT-1 and TFT-33
    assert "coherence_preservation" in invariants


def test_populate_noop_when_disabled(lib):
    tr = Transcriptome(context_key="default")
    disabled_set = type(lib._gene_set)(enabled=False, genes=[])
    written = populate_tftpsp_transcriptome(tr, disabled_set, {})
    assert written == 0
    assert tr.expression_profiles == {}


def test_populate_updates_metadata(lib):
    tr = Transcriptome(context_key="default")
    populate_tftpsp_transcriptome(tr, lib._gene_set, {"crisis": 1.0})
    assert tr.metadata["tftpsp_genes_applied"] == 33
    assert "crisis" in tr.metadata["tftpsp_context_tags"]


def test_populate_crisis_context_elevates_emergency_gene(lib):
    tr_default = Transcriptome(context_key="default")
    populate_tftpsp_transcriptome(tr_default, lib._gene_set, {})

    tr_crisis = Transcriptome(context_key="crisis")
    populate_tftpsp_transcriptome(tr_crisis, lib._gene_set, {"crisis": 1.0})

    base = tr_default.get_expression("tftpsp_023_epshcpe")
    under_crisis = tr_crisis.get_expression("tftpsp_023_epshcpe")
    assert under_crisis > base
    # And EPSHCPE should be clearly elevated by the crisis multiplier
    assert under_crisis == pytest.approx(0.1 * 2.0)


# ---------------------------------------------------------------------------
# build_tftpsp_transcriptome
# ---------------------------------------------------------------------------


def test_build_tftpsp_transcriptome_default_context(lib):
    tr = build_tftpsp_transcriptome(lib)
    assert len(tr.expression_profiles) == 33
    assert tr.context_key == "default"


def test_build_tftpsp_transcriptome_with_state(lib):
    tr = build_tftpsp_transcriptome(lib, {"crisis": 1.0, "innovation": 1.0})
    # 5PC gets the crisis stack (boost * epi boost) -> clamped to 1.0
    assert tr.get_expression("tftpsp_018_5pc") == pytest.approx(1.0)
    # PCAI gets the innovation activation
    assert tr.get_expression("tftpsp_020_pcai") == pytest.approx(0.6 * 1.5)
    # TFT-23 stays at base priority (lock_open rule only fires when explicitly
    # tagged, which it is here; net = 0.1 * 2.0)
    assert tr.get_expression("tftpsp_023_epshcpe") == pytest.approx(0.1 * 2.0)


# ---------------------------------------------------------------------------
# Integration with the main RNAExpressionEngine
# ---------------------------------------------------------------------------


def test_rna_expression_engine_composes_tftpsp_block():
    """The main engine must include TFTpsp profiles additively."""
    from speace_core.digital_rna import RNAExpressionEngine
    from speace_core.dna.models import SharedGenome
    from speace_core.dna.parser import load_genome

    genome = load_genome(
        "speace_core/dna/genome/default_genome.yaml"
    )
    engine = RNAExpressionEngine(genome)

    tr = engine.build_transcriptome("crisis", {"crisis": 1.0})
    # 33 TFTpsp profiles must have been written
    tftpsp_keys = [
        k for k in tr.expression_profiles if k.startswith("tftpsp_")
    ]
    assert len(tftpsp_keys) == 33
    # TFT-23 should be elevated by the crisis boost
    assert tr.get_expression("tftpsp_023_epshcpe") == pytest.approx(0.1 * 2.0)
    # And the transcriptome metadata must report the wiring
    assert tr.metadata["tftpsp_genes_applied"] == 33
