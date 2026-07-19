"""SelfImprovementCortex — main orchestrator of the SIA cycle (T32)."""
from __future__ import annotations

from dataclasses import dataclass

from .adaptive_levels import AdaptiveLevelRegistry
from .dna_registry import MutationRegistry
from .epigenetics import EpigeneticEngine
from .evolution_council import AgentProposal, EvolutionCouncil
from .evolutionary_memory import EvolutionaryMemory, MemoryEntry
from .ilf_regulator import ILFRegulator, MutationVerdict
from .neurogenesis import NeurogenesisPipeline, NewModuleSpec
from .organism_observer import OrganismObserver
from .quantum_engine import (
    QuantumEvolutionEngine,
)
from .rollback import RollbackManager


@dataclass
class SIAReport:
    tick: int
    proposals: int
    selected: int
    mutations_applied: int
    rollbacks: int
    neurogenesis: int
    qee_candidates: int
    verdict: MutationVerdict | None = None


class SelfImprovementCortex:
    """Main orchestrator for the SIA self-improvement cycle.

    Integrates EvolutionCouncil, OrganismObserver, adaptive levels,
    epigenetic memory, ILF regulation, neurogenesis, and the QEE.
    """

    def __init__(
        self,
        council: EvolutionCouncil | None = None,
        observer: OrganismObserver | None = None,
        level_registry: AdaptiveLevelRegistry | None = None,
        mutation_registry: MutationRegistry | None = None,
        epigenetic_engine: EpigeneticEngine | None = None,
        evolutionary_memory: EvolutionaryMemory | None = None,
        ilf_regulator: ILFRegulator | None = None,
        neurogenesis: NeurogenesisPipeline | None = None,
        rollback_manager: RollbackManager | None = None,
        quantum_engine: QuantumEvolutionEngine | None = None,
    ) -> None:
        self.council = council or EvolutionCouncil()
        self.observer = observer or OrganismObserver()
        self.levels = level_registry or AdaptiveLevelRegistry()
        self.dna = mutation_registry or MutationRegistry()
        self.epigenetics = epigenetic_engine or EpigeneticEngine()
        self.evo_memory = evolutionary_memory or EvolutionaryMemory()
        self.ilf = ilf_regulator or ILFRegulator()
        self.neurogenesis = neurogenesis or NeurogenesisPipeline()
        self.rollback = rollback_manager or RollbackManager(
            mutation_registry=self.dna,
            epigenetic_engine=self.epigenetics,
        )
        self.qee = quantum_engine or QuantumEvolutionEngine()
        self._tick = 0
        self._history: list[SIAReport] = []

    def tick(self, context: dict | None = None) -> SIAReport:
        ctx = context or {}
        profile = self.observer.latest()
        if profile:
            ctx.update(profile.to_dict())

        self._tick += 1

        proposals = self.council.gather_proposals(ctx)
        selected = self.council.decide(proposals, ctx)

        qee_candidates: list = []
        if self.qee.enabled and selected:
            strategies = [_proposal_to_dict(p) for p in selected]
            qee_results = self.qee.propose_candidates(strategies, ctx)
            qee_candidates = list(qee_results)

        mutations_applied = 0
        for proposal in selected:
            if self._should_skip_rollback(proposal):
                continue
            metrics_before = ctx.copy()
            record = self.dna.record(
                reason=proposal.reason,
                level=proposal.level,
                target=proposal.target,
                metrics_before=metrics_before,
                metrics_after={},
                approved_by=proposal.agent_name,
                confidence=proposal.confidence,
            )
            self.epigenetics.register(record.mutation_id)

            verdict = self.ilf.assess(
                performance_impact=proposal.expected_impact,
                coherence_impact=-proposal.risk * 0.3,
                resilience_impact=1.0 - proposal.risk,
                energy_impact=proposal.risk * 0.5,
            )
            if verdict.approved:
                mutations_applied += 1
                self.levels.escalate()
                self.evo_memory.store(MemoryEntry(
                    mutation_id=record.mutation_id,
                    context_signature=str(ctx.get("coherence_phi", 0)),
                    reason=proposal.reason,
                    level=proposal.level,
                    target=proposal.target,
                    metrics_before=metrics_before,
                    metrics_after={},
                    outcome=proposal.expected_impact,
                ))
            else:
                self.epigenetics.suppress(record.mutation_id, source="ilf_regulator")

        rollbacks = 0
        for record in self.dna.recent(10):
            plan = self.rollback.evaluate(record, ctx)
            if plan and self.rollback.execute(plan):
                rollbacks += 1

        neuro_modules = self._neurogenesis_step(ctx)

        report = SIAReport(
            tick=self._tick,
            proposals=len(proposals),
            selected=len(selected),
            mutations_applied=mutations_applied,
            rollbacks=rollbacks,
            neurogenesis=len(neuro_modules),
            qee_candidates=len(qee_candidates),
        )
        self._history.append(report)
        return report

    def _should_skip_rollback(self, proposal: AgentProposal) -> bool:
        sig = str(proposal.level)
        return self.evo_memory.has_failed_before(sig, proposal.target)

    def _neurogenesis_step(self, ctx: dict) -> list[NewModuleSpec]:
        activities = self.neurogenesis.detect_recurrent_activities()
        created = []
        for act, _count in activities:
            novelty = ctx.get("novelty", 0.0)
            spec = self.neurogenesis.propose_module(act, novelty=novelty)
            if spec:
                created.append(spec)
        return created

    def report(self) -> dict:
        if not self._history:
            return {}
        total_proposals = sum(r.proposals for r in self._history)
        total_selected = sum(r.selected for r in self._history)
        total_mutations = sum(r.mutations_applied for r in self._history)
        total_rollbacks = sum(r.rollbacks for r in self._history)
        return {
            "ticks": len(self._history),
            "total_proposals": total_proposals,
            "total_selected": total_selected,
            "total_mutations_applied": total_mutations,
            "total_rollbacks": total_rollbacks,
            "mutation_success_rate": (total_mutations / max(total_selected, 1)),
            "dna_records": self.dna.count(),
            "epigenetic_consolidated": len(self.epigenetics.all_consolidated()),
            "evolutionary_memory_size": self.evo_memory.count(),
            "active_neuro_modules": len(self.neurogenesis.active_modules()),
            "current_level": self.levels.level_name(),
        }


def _proposal_to_dict(p: AgentProposal) -> dict:
    return {
        "id": f"{p.agent_name}/{p.target}",
        "expected_impact": p.expected_impact,
        "risk": p.risk,
        "confidence": p.confidence,
        "energy_cost": 0.1 * p.risk,
        "novelty": 0.2,
    }
