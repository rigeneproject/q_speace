"""Q-SPEACE — Quantum Super Planetary Entità Autonoma Cibernetica.

Quantum layer for the SPEACE organism: numpy quantum kernel, EDD-CVT
(ILF + Cosmic Viruses), fractal QCA, earth-signal feed, energy cost model
and a quantum orchestrator. See progetto_q_speace_linee_guida.md.
"""
from __future__ import annotations

from .bcel import BCELCatalog
from .earth_feed import EarthFeed, EarthSignals
from .edd_cvt import CosmicVirusOptimizer, CVConfig, InformationalLogicalField
from .fractal_qca import FractalQCA
from .genome import QuantumGeneSet
from .metabolism import QuantumCostModel, QuantumOperation
from .orchestrator import QuantumOrchestrator, TickReport
from .quantum import (
    BrainQuantumCircuit,
    EntangledPair,
    EntanglementRegistry,
    GateType,
    MeasurementResult,
    QuantumBrainSimulator,
    QuantumGates,
    QuantumNeuralBridge,
    QuantumState,
)
from .schumann import run_schumann, schumann_circuit

__all__ = [
    "QuantumState",
    "QuantumGates",
    "GateType",
    "EntanglementRegistry",
    "EntangledPair",
    "BrainQuantumCircuit",
    "QuantumBrainSimulator",
    "QuantumNeuralBridge",
    "MeasurementResult",
    "QuantumGeneSet",
    "QuantumCostModel",
    "QuantumOperation",
    "InformationalLogicalField",
    "CosmicVirusOptimizer",
    "CVConfig",
    "FractalQCA",
    "EarthFeed",
    "EarthSignals",
    "QuantumOrchestrator",
    "TickReport",
    "BCELCatalog",
    "run_schumann",
    "schumann_circuit",
]
