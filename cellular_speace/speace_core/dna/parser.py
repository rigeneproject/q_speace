import pathlib
from typing import Union

import yaml

from speace_core.dna.models import SharedGenome
from speace_core.dna.tft_gene import TFTPspGeneSet
from speace_core.dna.tftpsp_library import TFTPspGeneLibrary


def load_genome(
    path: Union[str, pathlib.Path],
    load_tftpsp_catalog: bool = True,
) -> SharedGenome:
    """Load a YAML genome file into a :class:`SharedGenome`.

    When ``load_tftpsp_catalog`` is true (default) and the genome declares
    a ``tftpsp_genes`` block with a non-empty ``inline`` list, the
    inline entries are used as the catalogue. Otherwise the parser
    resolves ``tftpsp_genes.catalog_path`` (relative to the genome file
    or absolute) and merges the on-disk catalogue into the genome's
    ``tftpsp_genes.genes`` list.

    The TFTpsp catalogue is **immutable DNA** — like every other genome
    block, it is loaded once at construction and never mutated by the
    runtime.
    """
    p = pathlib.Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Genome file not found: {p}")
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    if data is None:
        data = {}

    if load_tftpsp_catalog:
        _merge_tftpsp_catalog(p, data)

    return SharedGenome.model_validate(data)


def _merge_tftpsp_catalog(genome_path: pathlib.Path, data: dict) -> None:
    """Populate ``data['tftpsp_genes']`` from the catalogue file."""
    block = data.get("tftpsp_genes")
    if not isinstance(block, dict):
        return

    inline = block.get("inline") or []
    catalog_path_raw = block.get("catalog_path")

    if inline:
        # Validate the inline copy directly.
        block["genes"] = list(inline)
        block.pop("inline", None)
        # Validate via the schema.
        validated = TFTPspGeneSet.model_validate(
            {"enabled": block.get("enabled", True), "genes": block["genes"]}
        )
        block["genes"] = [g.model_dump() for g in validated.genes]
        return

    if not catalog_path_raw:
        # No inline, no catalog path → leave the genes field empty.
        block.setdefault("genes", [])
        return

    catalog_path = pathlib.Path(catalog_path_raw)
    if not catalog_path.is_absolute():
        # The catalog path in the genome YAML is project-relative
        # (e.g. ``speace_core/dna/genome/tftpsp/00_tftpsp_genome.yaml``).
        # Try a few reasonable bases before giving up.
        candidates = [
            pathlib.Path.cwd() / catalog_path,
            (genome_path.parent / catalog_path).resolve(),
        ]
        # Also try the genome's parent's parent (the speace_core/dna/
        # directory) joined with the catalog path.
        try:
            candidates.append(
                (genome_path.parent.parent / catalog_path).resolve()
            )
        except Exception:
            pass
        for c in candidates:
            if c.exists():
                catalog_path = c
                break

    lib = TFTPspGeneLibrary.from_file(catalog_path)
    block["enabled"] = block.get("enabled", lib.enabled)
    block["genes"] = [g.model_dump() for g in lib.all()]
