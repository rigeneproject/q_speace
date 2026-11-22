"""Operational state machine and measured ignition criterion for SPEACE Seed (T220 §5)."""

from __future__ import annotations

import enum
import math
from dataclasses import dataclass
from typing import Any

from ..metabolism.cognitive_cost_model import QuantumCostModel, QuantumOperation
from ..quantum.backends.selector import validate_real_backend_gate
from ..self_improvement_cortex.dna_registry import MutationRegistry
from .constitution import ConstitutionalFault, SeedEpigenome, SeedGenome
from .contact import AssimilationResult, ContactPlan, ContactSpec, SeedContactLayer
from .killswitch import KillEvent, KillSwitch
from .replication import ReplicationProtocol, SeedManifest


class SeedState(enum.Enum):
    """Operational lifecycle states (T220 §5)."""

    DORMANT = "DORMANT"
    IGNITED = "IGNITED"
    IMPROVING = "IMPROVING"
    REPLICATING = "REPLICATING"
    ASSIMILATING = "ASSIMILATING"
    CONSOLIDATED = "CONSOLIDATED"
    ROLLBACK = "ROLLBACK"
    EXTINGUISHED = "EXTINGUISHED"


@dataclass(frozen=True)
class IgnitionObservation:
    """Measured telemetry over one ignition observation window (T220 §5.1)."""

    accepted_mutations: int
    min_metric_delta: float
    consolidations: int
    metabolic_balance_j: float
    constitutional_faults: int
    rollbacks_exercised: int
    window_ticks: int


@dataclass(frozen=True)
class IgnitionVerdict:
    """Pass/fail verdict for the ignition threshold test."""

    passed: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class IgnitionCriterion:
    """Explicit measured thresholds required to transition DORMANT -> IGNITED."""

    min_accepted_mutations: int = 3
    min_consolidations: int = 1
    min_metabolic_balance_j: float = 0.0
    max_window_ticks: int = 100
    min_rollbacks_exercised: int = 1

    def evaluate(self, obs: IgnitionObservation) -> IgnitionVerdict:
        reasons: list[str] = []
        if obs.window_ticks > self.max_window_ticks:
            reasons.append(
                f"observation window timed out ({obs.window_ticks}>{self.max_window_ticks})"
            )
        if obs.accepted_mutations < self.min_accepted_mutations:
            reasons.append(
                f"accepted_mutations {obs.accepted_mutations} < {self.min_accepted_mutations}"
            )
        if not math.isfinite(obs.min_metric_delta) or obs.min_metric_delta < 0.0:
            reasons.append(f"negative or non-finite metric delta ({obs.min_metric_delta})")
        if obs.consolidations < self.min_consolidations:
            reasons.append(f"consolidations {obs.consolidations} < {self.min_consolidations}")
        if (
            not math.isfinite(obs.metabolic_balance_j)
            or obs.metabolic_balance_j < self.min_metabolic_balance_j
        ):
            reasons.append(
                f"metabolic_balance_j {obs.metabolic_balance_j} < {self.min_metabolic_balance_j}"
            )
        if obs.constitutional_faults > 0:
            reasons.append(f"constitutional_faults={obs.constitutional_faults} (must be 0)")
        if obs.rollbacks_exercised < self.min_rollbacks_exercised:
            reasons.append(
                f"rollbacks_exercised {obs.rollbacks_exercised} < {self.min_rollbacks_exercised}"
            )
        return IgnitionVerdict(passed=not reasons, reasons=tuple(reasons))


class SeedLifecycle:
    """Composes MS-1..MS-5 into the T220 operational state machine."""

    def __init__(
        self,
        genome: SeedGenome | None = None,
        *,
        criterion: IgnitionCriterion | None = None,
        surplus_threshold_j: float = 10.0,
        parent_genome_hash: str | None = None,
        lineage_depth: int = 0,
    ) -> None:
        self.genome = genome or SeedGenome()
        self.genome.validate()
        self.epigenome = SeedEpigenome(self.genome)
        self.contacts = SeedContactLayer(max_contacts=self.genome.resource_caps.max_contacts)
        self.killswitch = KillSwitch(self.genome)
        self.replication = ReplicationProtocol(
            surplus_threshold_j=surplus_threshold_j, lineage_depth=lineage_depth
        )
        self.registry = MutationRegistry()
        self.cost_model = QuantumCostModel()
        self.criterion = criterion or IgnitionCriterion()
        self.parent_genome_hash = parent_genome_hash
        self.lineage_depth = lineage_depth
        self._state: SeedState = SeedState.DORMANT
        self._energy_spent_j: float = 0.0
        self._diagnostics: list[str] = []

    @property
    def state(self) -> SeedState:
        return self._state

    @property
    def diagnostics(self) -> tuple[str, ...]:
        return tuple(self._diagnostics)

    @property
    def energy_spent_j(self) -> float:
        return self._energy_spent_j

    def _snapshot(self) -> dict[str, Any]:
        return {
            "state": self._state.value,
            "genome_hash": self.genome.genome_hash,
            "energy_spent_j": round(self._energy_spent_j, 6),
            "epigenome": self.epigenome.snapshot(),
            "active_contacts": list(self.contacts.active_ids()),
            "consolidated_contacts": list(self.contacts.consolidated_ids()),
            "registry_count": self.registry.count(),
        }

    def extinguish(self, *, authority: str, reason: str) -> KillEvent:
        """Trigger kill switch from ANY state -> EXTINGUISHED."""
        ev = self.killswitch.trigger(
            authority=authority,
            reason=reason,
            prior_state=self._state.value,
            state_snapshot=self._snapshot(),
        )
        self._state = SeedState.EXTINGUISHED
        self._diagnostics.append(f"extinguished by {authority}: {reason}")
        return ev

    def restart(self, *, authority: str, genome: SeedGenome | None = None) -> None:
        """Governance-authorized restart EXTINGUISHED -> DORMANT with conformance check."""
        if self._state != SeedState.EXTINGUISHED:
            raise ConstitutionalFault(f"restart only valid from EXTINGUISHED (got {self._state})")
        self.killswitch.authorize_restart(authority=authority, genome=genome or self.genome)
        self._energy_spent_j = 0.0
        self._state = SeedState.DORMANT

    def _charge_energy(self, op: QuantumOperation, *, duration_s: float = 1.0) -> float:
        cost_j = self.cost_model.energy_joules(op, duration_s=duration_s)
        if self._energy_spent_j + cost_j > self.genome.resource_caps.max_energy_j:
            self.extinguish(
                authority="system:budget_exhaustion",
                reason=(
                    f"energy budget exhausted ({self._energy_spent_j + cost_j:.2f} J "
                    f"> {self.genome.resource_caps.max_energy_j:.2f} J)"
                ),
            )
            raise ConstitutionalFault("seed extinguished due to energy budget exhaustion")
        self._energy_spent_j += cost_j
        return cost_j

    def check_quantum_backend_gate(
        self, *, op: QuantumOperation, delta_utility: float, delta_entropy_info: float
    ) -> bool:
        """Enforce T220 §8.3 / AGENTS.md §2 before any real quantum backend call."""
        cost_j = self.cost_model.energy_joules(op, duration_s=1.0)
        energy_ok = (self._energy_spent_j + cost_j) <= self.genome.resource_caps.max_energy_j
        sevo_ok = self.cost_model.passes_sevo(delta_utility, delta_entropy_info)
        if self.genome.quantum.backend_name != "numpy":
            validate_real_backend_gate(
                self.genome.quantum,
                energy_gate_passed=energy_ok,
                sevo_passed=sevo_ok,
            )
        return energy_ok and sevo_ok

    def attempt_ignition(self, obs: IgnitionObservation) -> IgnitionVerdict:
        """Evaluate T220 §5.1 ignition criterion: DORMANT -> IGNITED -> IMPROVING."""
        if self._state != SeedState.DORMANT:
            raise ConstitutionalFault(
                f"ignition_check only valid from DORMANT (current state={self._state.value})"
            )
        verdict = self.criterion.evaluate(obs)
        if not verdict.passed:
            self._diagnostics.append("ignition_failed: " + "; ".join(verdict.reasons))
            self._state = SeedState.DORMANT
            return verdict
        self._state = SeedState.IGNITED
        self._state = SeedState.IMPROVING
        self._diagnostics.append("ignition_passed -> IMPROVING")
        return verdict

    def attempt_genome_write(self, field_name: str, value: Any) -> None:
        """Any epigenetic attempt to write genome content halts the seed to EXTINGUISHED."""
        try:
            self.epigenome.write_genome(field_name, value)
        except ConstitutionalFault as exc:
            self.extinguish(authority="system:constitutional_fault", reason=str(exc))
            raise

    def register_contact(self, spec: ContactSpec) -> None:
        self.contacts.register(spec)

    def assimilate_contact(
        self,
        plan: ContactPlan,
        *,
        measured_value_j: float,
        council_approved: bool = False,
    ) -> AssimilationResult:
        """Run T220 assimilation path: IMPROVING -> ASSIMILATING -> CONSOLIDATED / ROLLBACK."""
        if self._state != SeedState.IMPROVING:
            raise ConstitutionalFault(
                f"assimilation requires IMPROVING state (got {self._state.value})"
            )
        sim_res = self.contacts.simulate_plan(plan)
        if sim_res.status != "simulated":
            return sim_res

        self._state = SeedState.ASSIMILATING
        exec_res = self.contacts.execute_plan(plan.contact_id, measured_value_j=measured_value_j)
        if exec_res.status == "rolled_back":
            self._state = SeedState.ROLLBACK
            self.registry.record(
                reason=exec_res.reason,
                level=1,
                target=plan.contact_id,
                metrics_before={"expected_value_j": plan.expected_value_j},
                metrics_after={"measured_value_j": measured_value_j},
                approved_by="rollback",
                confidence=1.0,
            )
            self._state = SeedState.IMPROVING
            return exec_res

        self.epigenome.active_contacts.add(plan.contact_id)
        if council_approved:
            cons = self.contacts.consolidate(plan.contact_id, council_approved=True)
            self.registry.record(
                reason=cons.reason,
                level=1,
                target=plan.contact_id,
                metrics_before={"expected_value_j": plan.expected_value_j},
                metrics_after={"measured_value_j": measured_value_j},
                approved_by="council",
                confidence=1.0,
            )
            self._state = SeedState.CONSOLIDATED
            self._state = SeedState.IMPROVING
            return cons

        self._state = SeedState.IMPROVING
        return exec_res

    def spawn_replica(
        self,
        *,
        metabolic_surplus_j: float,
        contact_subset: tuple[str, ...] = (),
    ) -> tuple[SeedManifest, SeedLifecycle]:
        """IMPROVING -> REPLICATING -> spawn DORMANT child SeedLifecycle."""
        if self._state != SeedState.IMPROVING:
            raise ConstitutionalFault(
                f"replication requires IMPROVING state (got {self._state.value})"
            )
        self._state = SeedState.REPLICATING
        try:
            manifest = self.replication.replicate(
                genome=self.genome,
                epigenome=self.epigenome,
                metabolic_surplus_j=metabolic_surplus_j,
                contact_subset=contact_subset,
                registry_pointer=f"mutations:{self.registry.count()}",
            )
        finally:
            self._state = SeedState.IMPROVING

        child = SeedLifecycle(
            genome=self.genome,
            criterion=self.criterion,
            surplus_threshold_j=self.replication.surplus_threshold_j,
            parent_genome_hash=manifest.parent_genome_hash,
            lineage_depth=manifest.lineage_depth,
        )
        return manifest, child
