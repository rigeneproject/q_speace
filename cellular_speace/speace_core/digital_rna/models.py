"""Data models for the Digital RNA layer."""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class RNAExpressionProfile:
    """Expression levels for a set of genes in the current context.

    Attributes:
        gene_name: gene identifier.
        expression: 0..1 activation level.
        source: system, epigenetics, experience, bcel.
    """

    gene_name: str
    expression: float = 1.0
    source: str = "system"
    context_tags: List[str] = field(default_factory=list)


@dataclass
class Transcriptome:
    """Volatile working copy of the genome for the current operational context.

    This is the Digital RNA: it carries what the organism is "expressing"
    right now without modifying the underlying Digital DNA.
    """

    context_key: str = "default"
    expression_profiles: Dict[str, RNAExpressionProfile] = field(default_factory=dict)
    functional_constraints: List[Dict[str, Any]] = field(default_factory=list)
    lambda_coherence_entropy: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_expression(self, gene_name: str) -> float:
        profile = self.expression_profiles.get(gene_name)
        if profile is None:
            return 1.0
        return max(0.0, min(1.0, profile.expression))

    def set_expression(
        self,
        gene_name: str,
        expression: float,
        source: str = "system",
        tags: List[str] | None = None,
    ) -> None:
        self.expression_profiles[gene_name] = RNAExpressionProfile(
            gene_name=gene_name,
            expression=max(0.0, min(1.0, expression)),
            source=source,
            context_tags=tags or [],
        )

    def add_functional_constraint(self, constraint: Dict[str, Any]) -> None:
        self.functional_constraints.append(constraint)
