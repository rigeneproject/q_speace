"""Integration test: load the default genome and check TFTpsp integration."""

import pytest

from speace_core.dna.parser import load_genome


@pytest.fixture(scope="module")
def genome():
    return load_genome("speace_core/dna/genome/default_genome.yaml")


def test_genome_loads_with_tftpsp_genes(genome):
    assert genome.tftpsp_genes is not None
    assert genome.tftpsp_genes.enabled is True
    assert len(genome.tftpsp_genes.genes) == 33


def test_genes_have_unique_ids(genome):
    ids = [g.gene_id for g in genome.tftpsp_genes.genes]
    assert len(set(ids)) == 33


def test_genes_have_unique_tft_index(genome):
    indices = [g.tft_index for g in genome.tftpsp_genes.genes]
    assert sorted(indices) == list(range(1, 34))


def test_emergency_gene_is_locked(genome):
    emergency = genome.tftpsp_genes.emergency_genes()
    assert len(emergency) == 1
    epshcpe = emergency[0]
    assert epshcpe.gene_id == "tftpsp_023_epshcpe"
    assert epshcpe.mutation_policy.allowed is False
    assert epshcpe.mutation_policy.max_priority_delta_per_cycle <= 0.05


def test_dna_tft_gene_has_highest_priority(genome):
    top = genome.tftpsp_genes.by_tft_index(8)
    assert top is not None
    assert top.short_label == "DNA-TFT"
    # DNA-TFT should be in the top-5 by priority
    by_priority = sorted(
        genome.tftpsp_genes.genes, key=lambda g: g.priority, reverse=True
    )[:5]
    assert top in by_priority


def test_bcel_references_resolve(genome):
    """BCEL-mapped genes must reference a known CyberneticEquivalent name.

    The exact resolution check is enforced by the BCEL auditor in
    T173.8; this test only checks that the references are syntactically
    well-formed.
    """
    for g in genome.tftpsp_genes.genes:
        if g.bcel_equivalent is not None:
            assert isinstance(g.bcel_equivalent, str)
            assert g.bcel_equivalent.strip()
            # The convention from the catalogue is: "BCEL name (catalog key)"
            assert "(" in g.bcel_equivalent
            assert g.bcel_equivalent.endswith(")")


def test_all_genes_immutable_by_default(genome):
    """Mutation policy is read-only by default for every TFTpsp gene."""
    for g in genome.tftpsp_genes.genes:
        assert g.mutation_policy.allowed is False
        assert g.mutation_policy.requires_governance is True


def test_genome_blocks_unchanged_after_tftpsp_integration(genome):
    """Sanity: adding TFTpsp didn't perturb any other genome block."""
    # These are blocks we did NOT modify; they should still have their
    # expected keys.
    assert genome.connectome_genes is not None
    assert genome.periodic_table_genes is not None
    assert genome.cor_genes is not None
    assert genome.quantum_genes is not None
    assert genome.functional_activation is not None


def test_default_genome_yaml_structure_intact():
    """The YAML file should still parse after our additions."""
    import yaml
    from pathlib import Path
    data = yaml.safe_load(
        Path("speace_core/dna/genome/default_genome.yaml").read_text(encoding="utf-8")
    )
    assert "tftpsp_genes" in data
    assert data["tftpsp_genes"]["enabled"] is True
    assert "catalog_path" in data["tftpsp_genes"]