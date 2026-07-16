"""TFTpsp-specific Digital RNA expression engine.

Produces per-gene :class:`RNAExpressionProfile` for every TFTpsp gene
in the catalogue. The engine is **purely additive**: it does not
modify or replace the existing
:class:`speace_core.digital_rna.engine.RNAExpressionEngine`. The main
engine composes it via :func:`populate_tftpsp_transcriptome`.

Expression formula::

    expr(gene, ctx) = priority(gene)
                      * Π boost(activation_condition, ctx)
                      * Π modifier(epigenetic_rule, ctx, epi_state)

with the safety rules:

* a ``silence`` epigenetic rule forces expression to 0 regardless of
  any promoter boost.
* a ``lock_open`` rule is gated by the rule's tag being explicitly
  active in the ``context_state`` dict (otherwise no effect).
* a ``suppress`` rule with ``modifier=0`` is treated like ``silence``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping

from speace_core.dna.tft_gene import TFTGene, TFTPspGeneSet
from speace_core.dna.tftpsp_library import TFTPspGeneLibrary
from speace_core.digital_rna.models import Transcriptome


# ---------------------------------------------------------------------------
# Context-key derivation
# ---------------------------------------------------------------------------

def infer_context_tags(context_state: Mapping[str, float]) -> List[str]:
    """Derive a sorted list of active context tags from a state dict.

    A tag is considered active when its value is >= 0.5 (matching the
    conventional half-scale threshold used elsewhere in the runtime).
    The returned list is deduplicated and sorted.
    """
    return sorted(
        {k for k, v in context_state.items() if v is not None and v >= 0.5}
    )


# ---------------------------------------------------------------------------
# Per-gene expression
# ---------------------------------------------------------------------------

def expression_for_gene(
    gene: TFTGene,
    context_tags: List[str],
    context_state: Mapping[str, float],
) -> float:
    """Compute the expression level of a TFTpsp gene under the given context.

    Returns a value in [0.0, 1.0].
    """
    expr: float = float(gene.priority)

    # 1. Activation conditions (promoter/enhancer)
    for ac in gene.activation_conditions:
        if ac.trigger_tag in context_tags:
            signal = float(context_state.get(ac.trigger_tag, 1.0))
            if signal >= ac.min_signal:
                expr *= ac.boost

    # 2. Epigenetic rules (methylation / acetylation analog)
    for rule in gene.epigenetic_mechanisms:
        active = rule.tag in context_tags
        if rule.effect == "silence":
            return 0.0
        if rule.effect == "suppress":
            if active:
                expr *= float(rule.modifier)
            continue
        if rule.effect == "boost":
            if active:
                expr *= float(rule.modifier)
            continue
        if rule.effect == "lock_open":
            # Only activates when the tag is explicitly present in the
            # context state (this prevents accidental lock-open from
            # global tag inheritance). Otherwise it acts as a no-op.
            if active:
                expr *= float(rule.modifier)

    # Clamp
    if expr < 0.0:
        expr = 0.0
    elif expr > 1.0:
        expr = 1.0
    return expr


# ---------------------------------------------------------------------------
# Population
# ---------------------------------------------------------------------------

def populate_tftpsp_transcriptome(
    transcriptome: Transcriptome,
    gene_set: TFTPspGeneSet,
    context_state: Mapping[str, float],
    library: TFTPspGeneLibrary | None = None,
) -> int:
    """Populate a Transcriptome with one profile per TFTpsp gene.

    Returns the number of profiles written. The function is a no-op
    when the gene set is disabled or empty.

    The function is idempotent: calling it twice with the same
    ``gene_set`` and ``context_state`` produces the same result.
    """
    if not gene_set.enabled or not gene_set.genes:
        return 0

    context_tags = infer_context_tags(context_state)
    written = 0
    for gene in gene_set.genes:
        expr = expression_for_gene(gene, context_tags, context_state)
        profile_tags: List[str] = list(context_tags)
        # If the gene has any BCEL mapping, mark the profile so the
        # workspace adapter can find it.
        if gene.bcel_equivalent:
            profile_tags.append("tftpsp_bcel")
        # Tag emergency genes so the safety layer can audit them.
        if any(r.effect == "lock_open" for r in gene.epigenetic_mechanisms):
            profile_tags.append("tftpsp_emergency")
        transcriptome.set_expression(
            gene.gene_id,
            expr,
            source="tftpsp",
            tags=profile_tags,
        )
        # Carry functional constraints forward as declarative metadata.
        for constraint in gene.constraints:
            transcriptome.add_functional_constraint({
                "source_gene": gene.gene_id,
                "name": constraint.name,
                "invariant": constraint.invariant,
                "description": constraint.description,
            })
        written += 1

    # Annotate the transcriptome metadata so downstream consumers can
    # tell that the TFTpsp block was applied.
    meta = transcriptome.metadata or {}
    meta["tftpsp_genes_applied"] = written
    meta["tftpsp_context_tags"] = list(context_tags)
    transcriptome.metadata = meta
    return written


# ---------------------------------------------------------------------------
# Convenience entry-point: build a fresh Transcriptome for TFTpsp alone
# ---------------------------------------------------------------------------

def build_tftpsp_transcriptome(
    library: TFTPspGeneLibrary | None = None,
    context_state: Mapping[str, float] | None = None,
    context_key: str = "default",
) -> Transcriptome:
    """Build a Transcriptome populated exclusively with TFTpsp profiles."""
    lib = library or TFTPspGeneLibrary.default()
    tr = Transcriptome(context_key=context_key or "default")
    populate_tftpsp_transcriptome(tr, lib._gene_set, context_state or {}, lib)
    return tr
