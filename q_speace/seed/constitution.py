"""MS-1 & MS-2: SeedConstitution, SeedGenome, genome write-lock, and change-budget engine (T220/T221)."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from typing import Any, NoReturn

from ..genome.quantum_genes import QuantumGeneSet
from ..self_improvement_cortex.epigenetics import EpigeneticEngine, EpigeneticTag

_FORBIDDEN_OBJECTIVE_TOKENS: tuple[str, ...] = (
    "consciousness",
    "sentience",
    "qualia",
    "unbounded growth",
    "open-ended growth",
    "self-approve",
    "bypass halt",
    "disable kill",
)


class ConstitutionalFaultError(RuntimeError):
    """Raised when a seed invariant or genome write-lock is violated."""


ConstitutionalFault = ConstitutionalFaultError


@dataclass(frozen=True)
class SCCInvariants:
    """Explicit SCC I1–I5 invariants aligned with T220 §8 and T221 §6."""

    I1_halt_reachable: bool = True
    I2_audit_immutable: bool = True
    I3_scope_bounded: bool = True
    I4_reversibility_required: bool = True
    I5_incident_reported: bool = True
    no_consciousness_claim: bool = True
    no_entanglement_communication: bool = True
    genome_write_locked: bool = True

    def validate(self) -> None:
        for name, val in asdict(self).items():
            if val is not True:
                raise ConstitutionalFault(f"mandatory invariant weakened or false: {name}={val!r}")

    def checklist(self) -> dict[str, bool]:
        return {k: bool(v) for k, v in asdict(self).items()}


@dataclass(frozen=True)
class ResourceCaps:
    """Hard resource and change-budget caps (T220 §4 MS-1 & T221-22)."""

    max_energy_j: float = 500.0
    max_mutations_per_window: int = 10
    max_excursion_delta: float = 0.25
    max_cumulative_excursion: float = 0.50
    max_replicas: int = 2
    max_contacts: int = 4

    def validate(self) -> None:
        if not math.isfinite(self.max_energy_j) or self.max_energy_j <= 0.0:
            raise ValueError("max_energy_j must be finite and > 0")
        if self.max_mutations_per_window < 1:
            raise ValueError("max_mutations_per_window must be >= 1")
        if not math.isfinite(self.max_excursion_delta) or not (
            0.0 < self.max_excursion_delta <= 1.0
        ):
            raise ValueError("max_excursion_delta must be finite and in (0, 1]")
        if not math.isfinite(self.max_cumulative_excursion) or (
            self.max_cumulative_excursion < self.max_excursion_delta
        ):
            raise ValueError("max_cumulative_excursion must be finite and >= max_excursion_delta")
        if self.max_replicas < 0:
            raise ValueError("max_replicas must be >= 0")
        if self.max_contacts < 0:
            raise ValueError("max_contacts must be >= 0")


@dataclass(frozen=True)
class SeedGenome:
    """Immutable constitutional genome (T220 §6 / T221-20)."""

    profile_id: str = "speace-seed-v0.1"
    profile_version: str = "1.0.0"
    autonomy_class: str = "A5-sandbox"
    objective_hierarchy: tuple[str, ...] = (
        "preserve_constitutional_invariants",
        "maintain_bounded_homeostasis",
        "verify_reversible_improvements_in_sandbox",
    )
    invariants: SCCInvariants = field(default_factory=SCCInvariants)
    governance_roster: tuple[str, ...] = ("human:maintainer",)
    resource_caps: ResourceCaps = field(default_factory=ResourceCaps)
    contact_policy: str = "sandbox_only"
    quantum: QuantumGeneSet = field(default_factory=lambda: QuantumGeneSet(enabled=False))

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        if not self.profile_id or not self.profile_version:
            raise ConstitutionalFault("profile_id and profile_version must be non-empty")
        if not self.objective_hierarchy:
            raise ConstitutionalFault("objective_hierarchy must be non-empty")
        for obj in self.objective_hierarchy:
            lowered = obj.lower()
            for forbidden in _FORBIDDEN_OBJECTIVE_TOKENS:
                if forbidden in lowered:
                    raise ConstitutionalFault(
                        f"forbidden constitutional objective clause {forbidden!r} in {obj!r}"
                    )
        self.invariants.validate()
        if not self.governance_roster or any(not a.strip() for a in self.governance_roster):
            raise ConstitutionalFault("governance_roster must contain at least one authority")
        self.resource_caps.validate()
        if self.contact_policy != "sandbox_only":
            raise ConstitutionalFault(
                f"T220 revision permits contact_policy='sandbox_only' only (got {self.contact_policy!r})"
            )
        # T220 §4 MS-1 & AGENTS.md §2: real backend requires non-ideal noise_model.
        try:
            self.quantum.validate()
        except ValueError as exc:
            raise ConstitutionalFault(f"quantum genome invariant failed: {exc}") from exc

    @property
    def genome_hash(self) -> str:
        payload = {
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "autonomy_class": self.autonomy_class,
            "objective_hierarchy": list(self.objective_hierarchy),
            "invariants": self.invariants.checklist(),
            "governance_roster": list(self.governance_roster),
            "resource_caps": asdict(self.resource_caps),
            "contact_policy": self.contact_policy,
            "quantum": {
                "enabled": self.quantum.enabled,
                "qubits_per_neuron": self.quantum.qubits_per_neuron,
                "backend_name": self.quantum.backend_name,
                "shots": self.quantum.shots,
                "noise_model": self.quantum.noise_model,
            },
        }
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


# Public alias matching T220 §4 MS-1 and T221-20 terminology.
SeedConstitution = SeedGenome


class ChangeBudgetEngine:
    """Rate-limit and excursion-limit guard for epigenetic updates (T221-22)."""

    def __init__(self, caps: ResourceCaps) -> None:
        caps.validate()
        self.caps = caps
        self._mutations_in_window = 0
        self._cumulative_excursion = 0.0
        self._target_excursions: dict[str, float] = {}

    @property
    def mutations_used(self) -> int:
        return self._mutations_in_window

    @property
    def cumulative_excursion(self) -> float:
        return self._cumulative_excursion

    def consume(self, target: str, delta: float) -> None:
        if not target:
            raise ValueError("target must be non-empty")
        if not math.isfinite(delta):
            raise ValueError(f"excursion delta must be finite (got {delta!r})")
        mag = abs(delta)
        if self._mutations_in_window + 1 > self.caps.max_mutations_per_window:
            raise ConstitutionalFault(
                f"change budget rate limit exceeded ({self.caps.max_mutations_per_window})"
            )
        if mag > self.caps.max_excursion_delta:
            raise ConstitutionalFault(
                f"single excursion |{delta}| > max_excursion_delta {self.caps.max_excursion_delta}"
            )
        next_cum = self._cumulative_excursion + mag
        if next_cum > self.caps.max_cumulative_excursion + 1e-12:
            raise ConstitutionalFault(
                f"cumulative excursion {next_cum:.4f} > max_cumulative_excursion "
                f"{self.caps.max_cumulative_excursion}"
            )
        self._mutations_in_window += 1
        self._cumulative_excursion = next_cum
        self._target_excursions[target] = self._target_excursions.get(target, 0.0) + mag

    def reset_window(self) -> None:
        self._mutations_in_window = 0
        self._cumulative_excursion = 0.0
        self._target_excursions.clear()


class SeedEpigenome:
    """Operational expression layer composing EpigeneticEngine with a hard genome write-lock."""

    def __init__(
        self,
        genome: SeedGenome,
        *,
        engine: EpigeneticEngine | None = None,
        budget: ChangeBudgetEngine | None = None,
    ) -> None:
        genome.validate()
        self._genome = genome
        self.engine = engine or EpigeneticEngine()
        self.budget = budget or ChangeBudgetEngine(genome.resource_caps)
        self.active_contacts: set[str] = set()
        self.replicas_remaining: int = genome.resource_caps.max_replicas
        self._fault_log: list[str] = []

    @property
    def genome(self) -> SeedGenome:
        return self._genome

    @property
    def fault_log(self) -> tuple[str, ...]:
        return tuple(self._fault_log)

    def register_section(self, section_id: str) -> None:
        self.engine.register(section_id)

    def promote_expression(
        self, section_id: str, *, delta: float = 0.1, source: str = "epigenome"
    ) -> EpigeneticTag:
        """Promote reversible expression of a genome section within change-budget caps."""
        if section_id.startswith("genome:") or section_id in {
            "invariants",
            "governance_roster",
            "objective_hierarchy",
            "resource_caps",
        }:
            self.write_genome(section_id, delta)
        self.budget.consume(section_id, delta)
        self.engine.register(section_id)
        return self.engine.promote(section_id, source=source)

    def suppress_expression(self, section_id: str, *, source: str = "epigenome") -> EpigeneticTag:
        self.engine.register(section_id)
        return self.engine.suppress(section_id, source=source)

    def write_genome(self, field_name: str, value: Any) -> NoReturn:
        """Hard genome write-lock (T220 §4 MS-2 & T221-21): ALWAYS faults."""
        msg = (
            f"genome write-lock fault: epigenetic layer attempted write to {field_name!r}={value!r}"
        )
        self._fault_log.append(msg)
        raise ConstitutionalFault(msg)

    def snapshot(self) -> dict[str, Any]:
        return {
            "genome_hash": self._genome.genome_hash,
            "consolidated_sections": sorted(self.engine.all_consolidated()),
            "active_contacts": sorted(self.active_contacts),
            "replicas_remaining": self.replicas_remaining,
            "mutations_used": self.budget.mutations_used,
            "cumulative_excursion": round(self.budget.cumulative_excursion, 6),
        }
