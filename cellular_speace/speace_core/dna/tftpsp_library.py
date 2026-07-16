"""TFTPspGeneLibrary — load and query the TFTpsp Digital-DNA catalogue.

This module exposes a single :class:`TFTPspGeneLibrary` that:

* lazily loads ``speace_core/dna/genome/tftpsp/00_tftpsp_genome.yaml``
* validates the catalogue against the ``TFTPspGeneSet`` schema
* provides convenient indexes: by gene_id, by tft_index, by short_label,
  by domain_tag, by priority, by emergency status
* exposes a ``with_bcel()`` filter that returns the subset of genes that
  have a non-null ``bcel_equivalent`` (i.e. that the BCEL can attach a
  cybernetic constraint to)

The library is **read-only**: it never mutates the genome. Mutations go
through the existing counterfactual-sandbox → safe-patch → audit →
human-approval governance flow (see ``docs/T173_TFTPSP_GENOMIC_ENCODING_SPEC.md``
section 10).
"""

from __future__ import annotations

import pathlib
from functools import lru_cache
from typing import Iterable, List, Optional

import yaml

from speace_core.dna.tft_gene import TFTPspGeneSet, TFTGene


_DEFAULT_CATALOG_PATH = (
    pathlib.Path(__file__).resolve().parent / "genome" / "tftpsp" / "00_tftpsp_genome.yaml"
)


class TFTPspGeneLibrary:
    """In-memory index over the 33 TFTpsp genes."""

    def __init__(self, gene_set: TFTPspGeneSet, source_path: pathlib.Path) -> None:
        self._gene_set = gene_set
        self._source_path = source_path

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    @classmethod
    def from_file(cls, path: Optional[pathlib.Path] = None) -> "TFTPspGeneLibrary":
        """Load and validate the catalogue from a YAML file."""
        p = path or _DEFAULT_CATALOG_PATH
        if not p.exists():
            raise FileNotFoundError(f"TFTpsp catalogue not found: {p}")
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
        if data is None:
            raise ValueError(f"Empty TFTpsp catalogue: {p}")
        # The catalogue nests the set under a top-level ``tftpsp:`` key.
        if "tftpsp" in data:
            payload = data["tftpsp"]
        else:
            payload = data
        gene_set = TFTPspGeneSet.model_validate(payload)
        return cls(gene_set, p)

    @classmethod
    def default(cls) -> "TFTPspGeneLibrary":
        """Cached default instance (the on-disk catalogue)."""
        return _default_library()


    # ------------------------------------------------------------------
    # Query surface
    # ------------------------------------------------------------------
    @property
    def enabled(self) -> bool:
        return self._gene_set.enabled

    @property
    def source_path(self) -> pathlib.Path:
        return self._source_path

    def all(self) -> List[TFTGene]:
        return list(self._gene_set.genes)

    def __len__(self) -> int:
        return len(self._gene_set.genes)

    def __iter__(self):
        return iter(self._gene_set.genes)

    def get(self, gene_id: str) -> Optional[TFTGene]:
        return self._gene_set.get(gene_id)

    def by_tft_index(self, tft_index: int) -> Optional[TFTGene]:
        return self._gene_set.by_tft_index(tft_index)

    def by_short_label(self, short_label: str) -> Optional[TFTGene]:
        return self._gene_set.by_short_label(short_label)

    def by_domain_tag(self, tag: str) -> List[TFTGene]:
        return self._gene_set.by_domain_tag(tag)

    def emergency_genes(self) -> List[TFTGene]:
        return self._gene_set.emergency_genes()

    def with_bcel(self) -> List[TFTGene]:
        """Genes that have a non-null BCEL equivalent reference."""
        return [g for g in self._gene_set.genes if g.bcel_equivalent]

    def without_bcel(self) -> List[TFTGene]:
        """Genes that are purely descriptive (no BCEL equivalent)."""
        return [g for g in self._gene_set.genes if not g.bcel_equivalent]

    def by_priority(self, descending: bool = True) -> List[TFTGene]:
        return sorted(
            self._gene_set.genes,
            key=lambda g: g.priority,
            reverse=descending,
        )

    def filter(self, **criteria) -> List[TFTGene]:
        """Naive AND-filter over the most common fields.

        Supported: ``priority_ge``, ``priority_le``, ``has_bcel``,
        ``domain_tag``, ``trigger_tag``, ``relation`` (in interactions).
        """
        results: Iterable[TFTGene] = self._gene_set.genes
        if "priority_ge" in criteria:
            v = criteria["priority_ge"]
            results = (g for g in results if g.priority >= v)
        if "priority_le" in criteria:
            v = criteria["priority_le"]
            results = (g for g in results if g.priority <= v)
        if criteria.get("has_bcel"):
            results = (g for g in results if g.bcel_equivalent)
        if "domain_tag" in criteria:
            v = criteria["domain_tag"]
            results = (g for g in results if v in g.domain_tags)
        if "trigger_tag" in criteria:
            v = criteria["trigger_tag"]
            results = (
                g
                for g in results
                if any(ac.trigger_tag == v for ac in g.activation_conditions)
                or any(r.tag == v for r in g.epigenetic_mechanisms)
            )
        if "relation" in criteria:
            v = criteria["relation"]
            results = (
                g for g in results if any(i.relation == v for i in g.interactions)
            )
        return list(results)

    # ------------------------------------------------------------------
    # BCEL integration helpers
    # ------------------------------------------------------------------
    def bcel_resolvable(self) -> List[tuple[TFTGene, str]]:
        """Return (gene, bcel_equivalent_name) for every BCEL-mappable gene.

        The names follow the convention used in
        ``speace_core/bcel/catalog.py``. This list is consumed by the
        BCEL auditor in T173.8 to verify that every referenced
        equivalence actually exists in the catalog.
        """
        out: List[tuple[TFTGene, str]] = []
        for g in self.with_bcel():
            assert g.bcel_equivalent is not None  # narrowing for type checkers
            out.append((g, g.bcel_equivalent))
        return out


# ---------------------------------------------------------------------------
# Process-wide cached default
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _default_library() -> TFTPspGeneLibrary:
    return TFTPspGeneLibrary.from_file()