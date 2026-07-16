"""SPEACE Core — main package for the SPEACE cognitive architecture."""

from speace_core.orchestrator import CellularBrainOrchestrator
from speace_core.dna.models import SharedGenome

__version__ = "0.9.0"

__all__ = [
    "CellularBrainOrchestrator",
    "SharedGenome",
    "__version__",
]
