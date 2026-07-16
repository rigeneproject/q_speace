"""High-level transcriptor: genome → transcriptome in one call."""

from typing import Any, Dict

from speace_core.digital_rna.engine import RNAExpressionEngine
from speace_core.digital_rna.models import Transcriptome
from speace_core.epigenetics.epigenetic_tags import EpigeneticTagsManager


try:
    from speace_core.dna.models import SharedGenome
except Exception:  # pragma: no cover
    SharedGenome = None  # type: ignore[misc,assignment]


class DigitalTranscriptor:
    """Convenience wrapper around the RNA expression engine."""

    def __init__(
        self,
        genome: "SharedGenome",
        tags_manager: EpigeneticTagsManager | None = None,
    ) -> None:
        self.engine = RNAExpressionEngine(genome, tags_manager)

    def transcribe(
        self,
        context_key: str = "default",
        context_state: Dict[str, float] | None = None,
    ) -> Transcriptome:
        """Create a fresh transcriptome for the given context."""
        return self.engine.build_transcriptome(context_key, context_state)
