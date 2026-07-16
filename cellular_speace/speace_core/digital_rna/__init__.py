"""Digital RNA — volatile working copy between Digital DNA and execution.

The Digital RNA protects the immutable genome by exposing only the
context-dependent expression profile to the cognitive workspace and the
neural-synaptic periodic table.
"""

from speace_core.digital_rna.models import RNAExpressionProfile, Transcriptome
from speace_core.digital_rna.engine import RNAExpressionEngine
from speace_core.digital_rna.workspace_adapter import WorkspaceAdapter
from speace_core.digital_rna.periodic_table_adapter import PeriodicTableAdapter

__all__ = [
    "RNAExpressionProfile",
    "Transcriptome",
    "RNAExpressionEngine",
    "WorkspaceAdapter",
    "PeriodicTableAdapter",
]
