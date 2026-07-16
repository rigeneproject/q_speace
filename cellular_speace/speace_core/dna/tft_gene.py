"""Pydantic schemas for TFTpsp-as-DNA.

Each TFTpsp (TFT Problem-Solving Parameter) is encoded as a digital gene
following the schema defined in ``docs/T173_TFTPSP_GENOMIC_ENCODING_SPEC.md``.

The schema mirrors the conventions used in ``speace_core/dna/models.py``
(``CORGeneSet``, ``PeriodicTableGeneSet``, ``ConnectomeGeneSet``):

* flat Pydantic v2 ``BaseModel``
* ``Field(default_factory=...)`` for mutable defaults
* ``Field(ge=..., le=...)`` for bounded numerics
* no behavioral methods — pure data; behavior lives in the consumers
  (``tftpsp_library``, the Digital RNA engine, the Omni-RAG collector).

The schema is intentionally NOT mutated by the runtime; it is the
executable form of the constitutional DNA described by the source
document ``docs/List of the 33 TFT problem solving.txt``.
"""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Constraint / interaction primitive types
# ---------------------------------------------------------------------------

INFORMATIONAL_INVARIANTS = (
    "coherence_preservation",
    "destructive_entropy_reduction",
    "generative_variability_preservation",
    "interconnection_efficiency",
    "nonlocal_decoherence_tolerance",
    "identity_preservation_through_change",
)


RelationType = Literal[
    "depends_on",
    "gates",
    "inhibits",
    "supports",
    "contradicts",
]


EpigeneticEffect = Literal["boost", "suppress", "silence", "lock_open"]

EpigeneticScope = Literal["global", "context_local"]


TargetDirection = Literal[
    "maximize",
    "minimize",
    "maintain_above_threshold",
]


class ActivationCondition(BaseModel):
    """Promoter/enhancer analog: a context-tag that boosts this gene."""

    trigger_tag: str
    min_signal: float = 0.0
    boost: float = 1.0


class GeneInteraction(BaseModel):
    """Typed edge to another TFTpsp gene in the regulatory network."""

    target_gene_id: str
    relation: RelationType = "supports"
    weight: float = 0.5


class FunctionalGeneConstraint(BaseModel):
    """A functional invariant that this gene helps preserve.

    Mirrors :class:`speace_core.bcel.models.FunctionalConstraint` but is
    trimmed to the DNA-level shape (no mathematical form / parameters —
    those live in the BCEL catalog entry referenced by ``bcel_equivalent``).
    """

    name: str
    invariant: str
    description: str = ""


class EpigeneticRule(BaseModel):
    """Tag-driven modulator for this gene.

    * ``boost``     — multiplicative scaling
    * ``suppress``  — multiplicative reduction (modifier < 1.0)
    * ``silence``   — forced expression → 0
    * ``lock_open`` — bypass normal suppression (used by emergency genes
      that must be reachable under explicit crisis governance).
    """

    tag: str
    effect: EpigeneticEffect = "boost"
    modifier: float = 1.0
    scope: EpigeneticScope = "context_local"


class MutationPolicy(BaseModel):
    """How a TFTpsp gene may evolve.

    By default TFTpsp genes are **immutable** — mutations require explicit
    human governance, mirroring ``AGENTS.md §7``. The ``changeable_fields``
    list declares which sub-fields may move within the
    ``max_priority_delta_per_cycle`` budget.
    """

    allowed: bool = False
    requires_governance: bool = True
    max_priority_delta_per_cycle: float = 0.05
    changeable_fields: List[str] = Field(default_factory=list)


class EfficacyMetric(BaseModel):
    """Observable signature of whether this gene is doing its job."""

    metric_name: str
    target_direction: TargetDirection = "maintain_above_threshold"
    threshold: Optional[float] = None
    observation_window_ticks: int = 100


# ---------------------------------------------------------------------------
# The gene record itself
# ---------------------------------------------------------------------------


class TFTGene(BaseModel):
    """A single TFTpsp gene.

    ``gene_id`` is the stable symbol (e.g. ``"tftpsp_001_tft"``).
    ``tft_index`` is the original 1..33 number from the Rigene catalogue.
    """

    gene_id: str
    tft_index: int = Field(ge=1, le=33)
    name: str
    short_label: str
    function: str
    domain_tags: List[str] = Field(default_factory=list)

    activation_conditions: List[ActivationCondition] = Field(default_factory=list)
    interactions: List[GeneInteraction] = Field(default_factory=list)

    priority: float = Field(ge=0.0, le=1.0, default=0.5)

    constraints: List[FunctionalGeneConstraint] = Field(default_factory=list)

    epigenetic_mechanisms: List[EpigeneticRule] = Field(default_factory=list)

    mutation_policy: MutationPolicy = Field(default_factory=MutationPolicy)

    efficacy_metric: EfficacyMetric = Field(
        default_factory=lambda: EfficacyMetric(metric_name="expression_ratio")
    )

    # Optional pointer to a CyberneticEquivalent in the BCEL catalog.
    # Descriptive-only genes (TFT-1, TFT-2, TFT-3, …) leave this None.
    bcel_equivalent: Optional[str] = None


# ---------------------------------------------------------------------------
# Container for the whole genome set
# ---------------------------------------------------------------------------


class TFTPspGeneSet(BaseModel):
    """The complete TFTpsp Digital-DNA block.

    Mirrors ``CORGeneSet`` / ``PeriodicTableGeneSet``. The
    ``enabled`` flag keeps TFTpsp expressive by default but allows a
    stage-0 (local embryo) organism to disable the whole block until
    the constitutional substrate is in place.
    """

    enabled: bool = True
    genes: List[TFTGene] = Field(default_factory=list)

    def get(self, gene_id: str) -> Optional[TFTGene]:
        for g in self.genes:
            if g.gene_id == gene_id:
                return g
        return None

    def by_tft_index(self, tft_index: int) -> Optional[TFTGene]:
        for g in self.genes:
            if g.tft_index == tft_index:
                return g
        return None

    def by_short_label(self, short_label: str) -> Optional[TFTGene]:
        for g in self.genes:
            if g.short_label == short_label:
                return g
        return None

    def by_domain_tag(self, tag: str) -> List[TFTGene]:
        return [g for g in self.genes if tag in g.domain_tags]

    def emergency_genes(self) -> List[TFTGene]:
        """Genes whose ``epigenetic_mechanisms`` include ``lock_open``.

        Used by the audit / governance layer to enumerate the
        emergency-style TFTpsp genes that require explicit crisis-tag
        activation.
        """
        return [
            g
            for g in self.genes
            if any(rule.effect == "lock_open" for rule in g.epigenetic_mechanisms)
        ]
