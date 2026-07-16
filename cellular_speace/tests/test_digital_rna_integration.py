"""Integration test: Digital RNA wired into the orchestrator."""

import asyncio
import pathlib

import pytest

from speace_core.orchestrator import CellularBrainOrchestrator
from speace_core.dna.parser import load_genome


def _default_genome():
    root = pathlib.Path(__file__).resolve().parent.parent
    return load_genome(root / "speace_core" / "dna" / "genome" / "default_genome.yaml")


def test_build_mvp_enables_digital_rna_by_default():
    genome = _default_genome()
    orch = CellularBrainOrchestrator.build_mvp(genome)
    assert orch.digital_rna_enabled is True
    assert orch._digital_transcriptor is None


def test_tick_generates_transcriptome():
    genome = _default_genome()
    orch = CellularBrainOrchestrator.build_mvp(genome)
    asyncio.run(orch.run_ticks(3))
    assert orch._digital_transcriptor is not None
    assert orch._transcriptome is not None
    assert 0.0 <= orch._transcriptome.lambda_coherence_entropy <= 1.0
