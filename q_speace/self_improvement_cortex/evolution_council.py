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
            proposals.append(
                AgentProposal(
                    agent_name=self.name,
                    level=4,
                    target="agent_roles",
                    reason="low plasticity suggests suboptimal role distribution",
                    confidence=0.6,
                    expected_impact=0.3,
                    risk=0.2,
                )
            )
        coherence = context.get("coherence_phi", 1.0)
        if coherence < 0.3:
            proposals.append(
                AgentProposal(
                    agent_name=self.name,
                    level=6,
                    target="world_model",
                    reason="low coherence indicates world model drift",
                    confidence=0.7,
                    expected_impact=0.5,
                    risk=0.3,
                )
            )
        return proposals


class SoftwareArchitect(BaseAgent):
    name = "software_architect"

    def propose(self, context: dict) -> list[AgentProposal]:
        proposals = []
        error_rate = context.get("prediction_error", 0.0)
        if error_rate > 0.2:
            proposals.append(
                AgentProposal(
                    agent_name=self.name,
                    level=2,
                    target="workflow_pipeline",
                    reason="high prediction error suggests workflow inefficiency",
                    confidence=0.65,
                    expected_impact=0.4,
                    risk=0.15,
                )
            )
        return proposals


class RLAgent(BaseAgent):
    name = "rl_agent"

    def propose(self, context: dict) -> list[AgentProposal]:
        proposals = []
        goal = context.get("goal_completion", 1.0)
        if goal < 0.5:
            proposals.append(
                AgentProposal(
                    agent_name=self.name,
                    level=8,
                    target="policy_weights",
                    reason="low goal completion rate, LoRA update indicated",
                    confidence=0.55,
                    expected_impact=0.6,
                    risk=0.4,
                )
            )
        return proposals


class MemoryAgent(BaseAgent):
    name = "memory_agent"

    def propose(self, context: dict) -> list[AgentProposal]:
        proposals = []
        mem_compression = context.get("memory_compression", 0.0)
        if mem_compression < 0.3:
            proposals.append(
                AgentProposal(
                    agent_name=self.name,
                    level=5,
                    target="memory_consolidation",
                    reason="low memory compression, consolidation needed",
                    confidence=0.7,
                    expected_impact=0.35,
                    risk=0.1,
                )
            )
        return proposals


class SafetyAgent(BaseAgent):
    name = "safety_agent"

    def propose(self, context: dict) -> list[AgentProposal]:
        proposals = []
        resilience = context.get("resilience", 1.0)
        if resilience < 0.4:
            proposals.append(
                AgentProposal(
                    agent_name=self.name,
                    level=3,
                    target="safety_tools",
                    reason="low resilience, safety tools need reinforcement",
                    confidence=0.9,
                    expected_impact=0.5,
                    risk=0.05,
                )
            )
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
            proposals.append(
                AgentProposal(
                    agent_name=self.name,
                    level=7,
                    target="genome_parameters",
                    reason="stable DNA with low mutation success, tune genome",
                    confidence=0.6,
                    expected_impact=0.3,
                    risk=0.2,
                )
            )
        return proposals


class ILFAgent(BaseAgent):
    name = "ilf_agent"

    def propose(self, context: dict) -> list[AgentProposal]:
        proposals = []
        ilf_coh = context.get("ilf_coherence", 1.0)
        if ilf_coh < 0.5:
            proposals.append(
                AgentProposal(
                    agent_name=self.name,
                    level=6,
                    target="ilf_field",
                    reason="ILF coherence degraded, field recalibration needed",
                    confidence=0.8,
                    expected_impact=0.45,
                    risk=0.15,
                )
            )
        return proposals


class MutationAgent(BaseAgent):
    name = "mutation_agent"

    def propose(self, context: dict) -> list[AgentProposal]:
        proposals = []
        novelty = context.get("novelty", 0.0)
        if novelty < 0.2:
            proposals.append(
                AgentProposal(
                    agent_name=self.name,
                    level=1,
                    target="prompt_strategy",
                    reason="low novelty, mutate prompt strategy for exploration",
                    confidence=0.5,
                    expected_impact=0.2,
                    risk=0.1,
                )
            )
        return proposals


_AGENT_CLASSES = [
    NeuroscienceAgent,
    SoftwareArchitect,
    RLAgent,
    MemoryAgent,
    SafetyAgent,
    DigitalDNAAgent,
    ILFAgent,
    MutationAgent,
]


@dataclass
class EvolutionCouncil:
    agents: list[BaseAgent] = field(default_factory=lambda: [cls() for cls in _AGENT_CLASSES])
    orchestrator: EvolutionOrchestrator = field(default_factory=lambda: EvolutionOrchestrator())
    # Optional SpikingBrain cortex used as a *consultative* signal re-weighter.
    # When set, ``deliberate_with_brain`` (and any call that opts in)
    # invokes a ``think`` per proposal cluster and uses the returned
    # ``confidence`` to bias the per-proposal confidence before the
    # orchestrator's selection step. The brain NEVER votes directly —
    # it only re-weights existing proposals (BCEL gate: functional
    # data path, not decisional agency).
    brain: object | None = None  # SpikingBrainCortex | None — type hint at use site
    # AACM extension (T-AACM-SPEC §4.2): an optional controller that
    # applies the AACM gate (B: opposition→capacity, C: legitimation
    # stratification) to proposals. ``None`` means no AACM gating —
    # the existing behaviour is preserved.
    aacm_controller: object | None = None
    aacm_min_evidence_kinds: int = 2  # K ≥ 2 for stratification (regola 7)

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

    def aacm_filter(self, proposals: list[AgentProposal], context: dict) -> list[AgentProposal]:
        """Apply AACM Fase B+C gates to a list of proposals.

        Without a controller attached, returns the input unchanged
        (BCEL: do not modify behaviour unless AACM is active).

        With a controller, a proposal is admitted only if its
        ``payload["evidence_kinds"]`` lists at least
        ``aacm_min_evidence_kinds`` distinct kinds (regola 7). The
        controller's ``register_legitimation`` is then called for each
        admitted proposal, converting the proposal into a
        stratification channel (Fase C).
        """
        if self.aacm_controller is None:
            return list(proposals)
        # Local import to keep the cortex importable without AACM.
        from ..aacm import LegitimationChannel

        admitted: list[AgentProposal] = []
        for prop in proposals:
            kinds = prop.payload.get("evidence_kinds", [])
            if not isinstance(kinds, (list, tuple)):
                continue
            unique_kinds = tuple(sorted({str(k) for k in kinds}))
            if len(unique_kinds) < self.aacm_min_evidence_kinds:
                continue
            admitted.append(prop)
            # Convert opposition into capacity: each admitted
            # proposal adds ONE new legitimation channel per
            # distinct evidence kind to the controller's
            # stratification registry (Fase C, regola 7).
            for kind in unique_kinds:
                ch_id = f"leg:{prop.agent_name}:{prop.target}:{kind}"
                ch_path = str(prop.payload.get("artifact_paths", {}).get(kind, "(unset)"))
                # Deduplicate: if a channel with the same id and
                # evidence_kind already exists, do not re-add it.
                # (The registry itself rejects duplicate
                # evidence_kind across channels; we add at most
                # one channel per kind per proposal.)
                existing = {
                    (c.evidence_kind,) for c in self.aacm_controller.legitimation.channels  # type: ignore[union-attr]
                }
                if (kind,) in existing:
                    continue
                self.aacm_controller.register_legitimation(  # type: ignore[union-attr]
                    LegitimationChannel(
                        channel_id=ch_id,
                        evidence_kind=kind,
                        artifact_path=ch_path,
                        verified=bool(prop.payload.get("verified", False)),
                        verified_at=(
                            float(prop.payload["verified_at"])
                            if prop.payload.get("verified_at") is not None
                            else None
                        ),
                    )
                )
        return admitted

    async def deliberate_with_brain(
        self,
        context: dict,
        prompt: str | None = None,
    ) -> list[AgentProposal]:
        """Gather proposals, optionally re-weight via the brain, then select.

        The brain is consulted **once** on a synthetic prompt summarising
        the current context + proposal list. The returned confidence is
        mapped to a multiplicative re-weighting of each proposal:

            weight = 1 + (brain_confidence - 0.5)

        i.e. confidence 0.5 → neutral, 1.0 → x1.5, 0.0 → x0.5. The brain
        is purely consultative: it never inserts, deletes, or re-orders
        proposals, and its output is clamped to [0.0, 1.0] before being
        applied.

        Returns the list of proposals the orchestrator selected AFTER
        re-weighting. If the brain is unavailable or raises, this falls
        back to the synchronous ``decide`` path with no re-weighting.
        """
        proposals = self.gather_proposals(context)

        if self.brain is None or not proposals:
            return self.decide(proposals, context)

        try:
            import asyncio

            from ..spiking_brain import SpikingBrainCortex

            cortex: SpikingBrainCortex = self.brain  # type: ignore[assignment]
            summary_prompt = prompt or (
                "Evaluate the following organism proposals. "
                "Reply with a single confidence score in [0,1]."
            )
            if asyncio.iscoroutinefunction(getattr(cortex, "think", None)):
                result = await cortex.think(summary_prompt)
            else:
                # sync path (used when the brain backend exposes a sync
                # ``think``, e.g. the stub in tests).
                result = cortex.think_sync(summary_prompt)
            brain_conf = max(0.0, min(1.0, float(result.confidence)))
        except Exception:
            return self.decide(proposals, context)

        weight = 1.0 + (brain_conf - 0.5) * 1.0  # x0.5..x1.5
        for p in proposals:
            new_conf = max(0.0, min(1.0, p.confidence * weight))
            p.confidence = new_conf
        return self.decide(proposals, context)


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
