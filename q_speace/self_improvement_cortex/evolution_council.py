"""EvolutionCouncil — agent collective that proposes and votes on mutations (T33)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentProposal:
    agent_name: str
    level: int
    target: str
    reason: str
    confidence: float = 0.0
    expected_impact: float = 0.0
    risk: float = 0.0
    payload: dict = field(default_factory=dict)


class BaseAgent:
    name: str = "base"

    def propose(self, context: dict) -> list[AgentProposal]:
        raise NotImplementedError

    def confidence_in(self, proposal: AgentProposal) -> float:
        return proposal.confidence


class NeuroscienceAgent(BaseAgent):
    name = "neuroscience"

    def propose(self, context: dict) -> list[AgentProposal]:
        proposals = []
        plasticity = context.get("plasticity_index", 0.0)
        if plasticity < 0.3:
            proposals.append(AgentProposal(
                agent_name=self.name, level=4, target="agent_roles",
                reason="low plasticity suggests suboptimal role distribution",
                confidence=0.6, expected_impact=0.3, risk=0.2,
            ))
        coherence = context.get("coherence_phi", 1.0)
        if coherence < 0.3:
            proposals.append(AgentProposal(
                agent_name=self.name, level=6, target="world_model",
                reason="low coherence indicates world model drift",
                confidence=0.7, expected_impact=0.5, risk=0.3,
            ))
        return proposals


class SoftwareArchitect(BaseAgent):
    name = "software_architect"

    def propose(self, context: dict) -> list[AgentProposal]:
        proposals = []
        error_rate = context.get("prediction_error", 0.0)
        if error_rate > 0.2:
            proposals.append(AgentProposal(
                agent_name=self.name, level=2, target="workflow_pipeline",
                reason="high prediction error suggests workflow inefficiency",
                confidence=0.65, expected_impact=0.4, risk=0.15,
            ))
        return proposals


class RLAgent(BaseAgent):
    name = "rl_agent"

    def propose(self, context: dict) -> list[AgentProposal]:
        proposals = []
        goal = context.get("goal_completion", 1.0)
        if goal < 0.5:
            proposals.append(AgentProposal(
                agent_name=self.name, level=8, target="policy_weights",
                reason="low goal completion rate, LoRA update indicated",
                confidence=0.55, expected_impact=0.6, risk=0.4,
            ))
        return proposals


class MemoryAgent(BaseAgent):
    name = "memory_agent"

    def propose(self, context: dict) -> list[AgentProposal]:
        proposals = []
        mem_compression = context.get("memory_compression", 0.0)
        if mem_compression < 0.3:
            proposals.append(AgentProposal(
                agent_name=self.name, level=5, target="memory_consolidation",
                reason="low memory compression, consolidation needed",
                confidence=0.7, expected_impact=0.35, risk=0.1,
            ))
        return proposals


class SafetyAgent(BaseAgent):
    name = "safety_agent"

    def propose(self, context: dict) -> list[AgentProposal]:
        proposals = []
        resilience = context.get("resilience", 1.0)
        if resilience < 0.4:
            proposals.append(AgentProposal(
                agent_name=self.name, level=3, target="safety_tools",
                reason="low resilience, safety tools need reinforcement",
                confidence=0.9, expected_impact=0.5, risk=0.05,
            ))
        return proposals

    def confidence_in(self, proposal: AgentProposal) -> float:
        return min(1.0, proposal.confidence + 0.2)


class DigitalDNAAgent(BaseAgent):
    name = "dna_agent"

    def propose(self, context: dict) -> list[AgentProposal]:
        proposals = []
        dna_stability = context.get("dna_stability", 1.0)
        mutation_rate = context.get("mutation_success_rate", 0.5)
        if dna_stability > 0.8 and mutation_rate < 0.3:
            proposals.append(AgentProposal(
                agent_name=self.name, level=7, target="genome_parameters",
                reason="stable DNA with low mutation success, tune genome",
                confidence=0.6, expected_impact=0.3, risk=0.2,
            ))
        return proposals


class ILFAgent(BaseAgent):
    name = "ilf_agent"

    def propose(self, context: dict) -> list[AgentProposal]:
        proposals = []
        ilf_coh = context.get("ilf_coherence", 1.0)
        if ilf_coh < 0.5:
            proposals.append(AgentProposal(
                agent_name=self.name, level=6, target="ilf_field",
                reason="ILF coherence degraded, field recalibration needed",
                confidence=0.8, expected_impact=0.45, risk=0.15,
            ))
        return proposals


class MutationAgent(BaseAgent):
    name = "mutation_agent"

    def propose(self, context: dict) -> list[AgentProposal]:
        proposals = []
        novelty = context.get("novelty", 0.0)
        if novelty < 0.2:
            proposals.append(AgentProposal(
                agent_name=self.name, level=1, target="prompt_strategy",
                reason="low novelty, mutate prompt strategy for exploration",
                confidence=0.5, expected_impact=0.2, risk=0.1,
            ))
        return proposals


_AGENT_CLASSES = [
    NeuroscienceAgent, SoftwareArchitect, RLAgent, MemoryAgent,
    SafetyAgent, DigitalDNAAgent, ILFAgent, MutationAgent,
]


@dataclass
class EvolutionCouncil:
    agents: list[BaseAgent] = field(default_factory=lambda: [cls() for cls in _AGENT_CLASSES])
    orchestrator: EvolutionOrchestrator = field(default_factory=lambda: EvolutionOrchestrator())

    def gather_proposals(self, context: dict) -> list[AgentProposal]:
        all_proposals = []
        for agent in self.agents:
            try:
                proposals = agent.propose(context)
                all_proposals.extend(proposals)
            except Exception:
                continue
        return all_proposals

    def decide(self, proposals: list[AgentProposal], context: dict) -> list[AgentProposal]:
        return self.orchestrator.select(proposals, context)


@dataclass
class EvolutionOrchestrator:
    min_confidence: float = 0.4
    max_proposals_per_tick: int = 3

    def select(self, proposals: list[AgentProposal], context: dict) -> list[AgentProposal]:
        scored = []
        for p in proposals:
            score = p.confidence * (1.0 - p.risk) * p.expected_impact
            scored.append((score, p))
        scored.sort(key=lambda x: x[0], reverse=True)
        selected = []
        for _score, proposal in scored:
            if proposal.confidence < self.min_confidence:
                continue
            if len(selected) >= self.max_proposals_per_tick:
                break
            selected.append(proposal)
        return selected
