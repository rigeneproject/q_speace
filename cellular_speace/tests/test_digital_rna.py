"""Unit tests for the Digital RNA layer."""

import pytest

from speace_core.digital_rna import RNAExpressionEngine, Transcriptome
from speace_core.dna.models import SharedGenome
from speace_core.epigenetics.epigenetic_tags import EpigeneticTagsManager


def test_transcriptome_is_volatile_copy():
    genome = SharedGenome()
    engine = RNAExpressionEngine(genome)
    transcriptome = engine.build_transcriptome("test_context")

    assert isinstance(transcriptome, Transcriptome)
    assert transcriptome.context_key == "test_context"
    assert 0.0 <= transcriptome.lambda_coherence_entropy <= 1.0


def test_epigenetic_modulation_changes_expression():
    genome = SharedGenome()
    tags = EpigeneticTagsManager()
    tags.apply_methylation("plasticity", 0.5)

    engine = RNAExpressionEngine(genome, tags)
    transcriptome = engine.build_transcriptome("test_context", {"stress": 0.2})

    # Methylation reduces expression of the plasticity gene.
    assert transcriptome.get_expression("plasticity") < 1.0


def test_lambda_derivation():
    genome = SharedGenome()
    engine = RNAExpressionEngine(genome)

    low_stress = engine.build_transcriptome("ctx", {"stress": 0.1, "energy": 0.9})
    high_stress = engine.build_transcriptome("ctx", {"stress": 0.9, "energy": 0.2})

    assert low_stress.lambda_coherence_entropy < high_stress.lambda_coherence_entropy
