"""Enteroception — digital gut-brain axis for SPEACE.

This package provides the digital equivalent of the biological gut-brain
axis, including a digital microbiome (MicrobiomeModulator) and a vagus-
nerve analog (EntericSignalBus).
"""

from speace_core.cellular_brain.enteroception.enteric_signal_bus import (
    ENTERCEPTION_CHANNELS,
    EntericSignalBus,
    EnteroceptiveSnapshot,
)
from speace_core.cellular_brain.enteroception.microbiome_modulator import (
    MicrobiomeModulator,
)
from speace_core.cellular_brain.enteroception.strain_definitions import (
    DEFAULT_STRAINS,
    MicrobialStrain,
)

__all__ = [
    "DEFAULT_STRAINS",
    "EntericSignalBus",
    "EnteroceptiveSnapshot",
    "ENTERCEPTION_CHANNELS",
    "MicrobialStrain",
    "MicrobiomeModulator",
]
