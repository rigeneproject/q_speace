"""Adapter: Digital RNA → Global Cognitive Workspace.

The transcriptome is the volatile expression profile that configures the
workspace for the current context without mutating the genome.
"""

from typing import Any, Dict

from speace_core.digital_rna.models import Transcriptome


try:
    from speace_core.cellular_brain.cognition.global_workspace import GlobalWorkspace
except Exception:  # pragma: no cover
    GlobalWorkspace = None  # type: ignore[misc,assignment]


class WorkspaceAdapter:
    """Apply a transcriptome to a GlobalWorkspace instance."""

    def __init__(self, workspace: "GlobalWorkspace") -> None:
        self.workspace = workspace

    def apply(self, transcriptome: Transcriptome) -> Dict[str, Any]:
        """Configure the workspace from the transcriptome.

        This is intentionally lightweight: the workspace already exists;
        the transcriptome only tunes its operating point.
        """
        report: Dict[str, Any] = {
            "lambda_coherence_entropy": transcriptome.lambda_coherence_entropy,
            "expressed_genes": len(transcriptome.expression_profiles),
            "functional_constraints": len(transcriptome.functional_constraints),
        }

        # In future iterations this can tune attention decay, recurrent leak,
        # or broadcast thresholds from the transcriptome.
        if hasattr(self.workspace, "_energy"):
            # Energy is influenced by the executive/creative balance.
            self.workspace._energy = max(
                0.3, min(1.0, 0.6 + transcriptome.lambda_coherence_entropy * 0.3)
            )
            report["workspace_energy"] = self.workspace._energy

        return report
