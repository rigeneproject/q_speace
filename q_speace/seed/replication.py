"""MS-4: Gated replication protocol and SeedManifest (T220 §4 MS-4 & §6)."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Any

from .constitution import ConstitutionalFault, SeedEpigenome, SeedGenome


@dataclass(frozen=True)
class SeedManifest:
    """Replication and audit artifact carrying immutable genome hash and full invariant checklist."""

    genome_hash: str
    parent_genome_hash: str | None
    lineage_depth: int
    epigenome_snapshot: dict[str, Any]
    contact_subset: tuple[str, ...]
    registry_pointer: str
    invariant_checklist: dict[str, bool]
    initial_state: str = "DORMANT"

    def __post_init__(self) -> None:
        if not self.genome_hash:
            raise ConstitutionalFault("SeedManifest requires non-empty genome_hash")
        if self.lineage_depth < 0:
            raise ValueError("lineage_depth must be >= 0")
        if not self.invariant_checklist or not all(self.invariant_checklist.values()):
            raise ConstitutionalFault("SeedManifest invariant_checklist must have all entries True")
        if self.initial_state != "DORMANT":
            raise ConstitutionalFault(
                f"replicated child must start in DORMANT state (got {self.initial_state!r})"
            )

    def digest(self) -> str:
        encoded = json.dumps(asdict(self), sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class ReplicationProtocol:
    """Enforces metabolic surplus, replica caps, full invariant inheritance, and DORMANT spawn."""

    def __init__(self, *, surplus_threshold_j: float = 10.0, lineage_depth: int = 0) -> None:
        if not math.isfinite(surplus_threshold_j) or surplus_threshold_j < 0.0:
            raise ValueError("surplus_threshold_j must be finite and >= 0")
        if lineage_depth < 0:
            raise ValueError("lineage_depth must be >= 0")
        self.surplus_threshold_j = float(surplus_threshold_j)
        self.lineage_depth = int(lineage_depth)
        self._lineage: list[SeedManifest] = []

    @property
    def lineage(self) -> tuple[SeedManifest, ...]:
        return tuple(self._lineage)

    def replicate(
        self,
        *,
        genome: SeedGenome,
        epigenome: SeedEpigenome,
        metabolic_surplus_j: float,
        contact_subset: tuple[str, ...] = (),
        registry_pointer: str = "in-memory",
    ) -> SeedManifest:
        genome.validate()
        if not math.isfinite(metabolic_surplus_j):
            raise ValueError("metabolic_surplus_j must be finite")
        if metabolic_surplus_j < self.surplus_threshold_j:
            raise ConstitutionalFault(
                f"replication blocked: metabolic surplus {metabolic_surplus_j:.2f} J "
                f"< threshold {self.surplus_threshold_j:.2f} J"
            )
        if epigenome.replicas_remaining <= 0:
            raise ConstitutionalFault(
                f"replication blocked: replica budget exhausted (cap={genome.resource_caps.max_replicas})"
            )
        checklist = genome.invariants.checklist()
        if not all(checklist.values()):
            raise ConstitutionalFault("replication blocked: parent invariants not all True")

        epigenome.replicas_remaining -= 1
        manifest = SeedManifest(
            genome_hash=genome.genome_hash,
            parent_genome_hash=genome.genome_hash,
            lineage_depth=self.lineage_depth + 1,
            epigenome_snapshot=epigenome.snapshot(),
            contact_subset=tuple(contact_subset),
            registry_pointer=registry_pointer,
            invariant_checklist=checklist,
            initial_state="DORMANT",
        )
        self._lineage.append(manifest)
        return manifest
