"""Digital RNA expression engine.

Builds the Transcriptome from the immutable SharedGenome and the current
epigenetic context. The Transcriptome is the volatile working copy passed to
the cognitive workspace and the neural-synaptic periodic table.
"""

from typing import Any, Dict, List, Set

from speace_core.digital_rna.models import RNAExpressionProfile, Transcriptome
from speace_core.digital_rna.tftpsp_engine import populate_tftpsp_transcriptome
from speace_core.epigenetics.epigenetic_tags import EpigeneticTagsManager


try:
    from speace_core.dna.models import SharedGenome
except Exception:  # pragma: no cover
    SharedGenome = None  # type: ignore[misc,assignment]


class RNAExpressionEngine:
    """Produce a context-dependent transcriptome without mutating the genome."""

    def __init__(
        self,
        genome: "SharedGenome",
        tags_manager: EpigeneticTagsManager | None = None,
    ) -> None:
        self.genome = genome
        self.tags = tags_manager or EpigeneticTagsManager()

    def build_transcriptome(
        self,
        context_key: str = "default",
        context_state: Dict[str, float] | None = None,
    ) -> Transcriptome:
        """Build a fresh transcriptome from DNA + epigenetic context.

        After the cell-type expression rules are evaluated, the
        :class:`TFTPspGeneSet` carried by the genome is transcribed via
        :func:`speace_core.digital_rna.tftpsp_engine.populate_tftpsp_transcriptome`.
        This is purely additive: existing expression profiles are not
        overwritten.
        """
        transcriptome = Transcriptome(context_key=context_key)
        state = context_state or {}

        # 1. Seed expression profiles from genome rules.
        for rule_name, rule in self._iter_expression_rules():
            base = 1.0
            if context_key in (getattr(rule, "regions", None) or []):
                base = 1.2
            transcriptome.set_expression(
                rule_name, base, source="genome", tags=[context_key]
            )

        # 2. Ensure any tagged gene has a profile so epigenetic modulation
        #    is visible even if the gene has no explicit expression rule.
        for tag in self.tags.get_active_tags():
            if tag.gene_name not in transcriptome.expression_profiles:
                transcriptome.set_expression(
                    tag.gene_name, 1.0, source="genome", tags=[context_key]
                )

        # 3. Modulate by epigenetic tags.
        for profile in list(transcriptome.expression_profiles.values()):
            modifier = self.tags.get_expression_modifier(
                profile.gene_name, state
            )
            new_expr = profile.expression * modifier
            transcriptome.set_expression(
                profile.gene_name,
                new_expr,
                source="epigenetics",
                tags=profile.context_tags + ["epigenetic_modulation"],
            )

        # 4. Set the coherence/entropy lambda from context.
        transcriptome.lambda_coherence_entropy = self._derive_lambda(state)

        # 5. T173 — Transcribe the TFTpsp block if present in the genome.
        tftpsp_set = getattr(self.genome, "tftpsp_genes", None)
        if tftpsp_set is not None:
            populate_tftpsp_transcriptome(transcriptome, tftpsp_set, state)

        transcriptome.metadata = {
            "genome_version": getattr(self.genome, "__version__", "unknown"),
            "context_state": state,
            "tagged_genes": len(self.tags.get_active_tags()),
            "tftpsp_genes_applied": transcriptome.metadata.get(
                "tftpsp_genes_applied", 0
            ),
            "tftpsp_context_tags": transcriptome.metadata.get(
                "tftpsp_context_tags", []
            ),
        }
        return transcriptome

    def _iter_expression_rules(self) -> List[tuple[str, Any]]:
        """Yield genome expression rules in a stable format."""
        rules: Dict[str, Any] = {}
        if self.genome is not None:
            rules.update(getattr(self.genome, "expression_rules", {}) or {})
        return list(rules.items())

    def _derive_lambda(self, context_state: Dict[str, float]) -> float:
        """Return the coherence-vs-entropy balance parameter λ.

        Low λ = exploratory / creative regime.
        High λ = deterministic / executive regime.
        """
        stress = context_state.get("stress", 0.5)
        energy = context_state.get("energy", 0.5)
        # High stress or low energy pushes toward executive/deterministic regime.
        lam = 0.3 + 0.5 * stress - 0.2 * (energy - 0.5)
        return max(0.1, min(0.9, lam))
