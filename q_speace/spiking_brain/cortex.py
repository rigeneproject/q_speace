"""SpikingBrainCortex — integration layer with Q-SPEACE (task T205).

Owns one backend (stub or HTTP), costs each think call via the
:class:`QuantumCostModel`, gates it through the
:class:`ILFRegulator` (Sevo + coherence check), and exposes:

- :meth:`think` — high-level call: builds the prompt, runs the backend,
  returns a :class:`ThinkResult`.
- :meth:`apply_to_ilf` — converts the result into an ILF belief update
  for a given agent id.
- :meth:`tick` — one cognitive step: sense ILF → think → apply → return a
  short report (used by :class:`SelfImprovementCortex`).

The cortex is **not** an LLM wrapper. It is the binding layer between
language-model output and the SPEACE-native representational stack
(belief vector + spike pattern + plasticity coefficients).
"""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, cast

import numpy as np

from ..edd_cvt.ilf import InformationalLogicalField
from ..metabolism.cognitive_cost_model import QuantumCostModel, QuantumOperation
from .stub import StubSpikingBrain
from .types import ThinkResult


@dataclass
class CortexReport:
    """Outcome of one ``SpikingBrainCortex.tick`` call."""

    backend: str
    confidence: float
    sevo: float
    energy_w: float
    approved: bool
    reason: str
    result: ThinkResult | None = None
    latency_s: float = 0.0
    metadata: dict = field(default_factory=dict)


class SpikingBrainCortex:
    """Top-level integration layer for the SpikingBrain satellite."""

    # Cost model parameters for a single "think" call. These are tuned
    # to make a 32-token generation cost roughly the same energy as a
    # 4-qubit quantum step, so the Sevo gate is meaningful.
    BRAIN_NUM_QUBITS = 4
    BRAIN_NUM_GATES_PER_TOKEN = 3
    BRAIN_ENTANGLEMENT_DEPTH = 2
    SEVO_THRESHOLD = 1.5

    def __init__(
        self,
        backend: StubSpikingBrain | object | None = None,
        ilf: InformationalLogicalField | None = None,
        cost: QuantumCostModel | None = None,
        sevo_threshold: float = SEVO_THRESHOLD,
        min_coherence_phi: float = 0.05,
        min_confidence: float = 0.05,
    ) -> None:
        if backend is None:
            from .factory import make_spiking_brain

            backend = make_spiking_brain()
        self.backend = backend
        self.ilf = ilf or InformationalLogicalField(coherence_phi=1.0)
        self.cost = cost or QuantumCostModel()
        self.sevo_threshold = sevo_threshold
        self.min_coherence_phi = min_coherence_phi
        self.min_confidence = min_confidence
        self._history: list[ThinkResult] = []
        self._reports: list[CortexReport] = []

    @property
    def backend_name(self) -> str:
        return getattr(self.backend, "backend", type(self.backend).__name__)

    # --- async / sync shim ---

    async def _think_async(
        self,
        prompt: str,
        coherence_phi: float,
        n_tokens: int,
        history: Sequence[ThinkResult] | None,
    ) -> ThinkResult:
        backend_think = getattr(self.backend, "think", None)
        if backend_think is None:
            raise RuntimeError("backend has no think() method")
        out = backend_think(prompt, coherence_phi, n_tokens, history)
        if inspect.isawaitable(out):
            out = await out
        return cast(ThinkResult, out)

    # --- public API ---

    async def think(
        self,
        prompt: str,
        n_tokens: int = 32,
        history: Sequence[ThinkResult] | None = None,
    ) -> ThinkResult:
        """Run a single think call, updating the local history."""
        coherence_phi = float(self.ilf.coherence_phi)
        result = await self._think_async(prompt, coherence_phi, n_tokens, history)
        self._history.append(result)
        if len(self._history) > 64:
            self._history = self._history[-64:]
        return result

    def think_sync(
        self,
        prompt: str,
        n_tokens: int = 32,
        history: Sequence[ThinkResult] | None = None,
    ) -> ThinkResult:
        """Convenience synchronous wrapper. Returns the coroutine's result.

        Raises ``RuntimeError`` if called from inside an event loop.
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass
        else:
            raise RuntimeError("think_sync() called inside a running event loop; use await think()")
        return asyncio.run(self.think(prompt, n_tokens=n_tokens, history=history))

    async def tick(
        self,
        prompt: str,
        n_tokens: int = 32,
        agent_id: str = "spiking_brain",
        history: Sequence[ThinkResult] | None = None,
    ) -> CortexReport:
        """Full sense-decide-act step: think, cost, gate, apply to ILF."""
        coherence_phi = float(self.ilf.coherence_phi)

        # 1. Think (the only network/disk cost).
        try:
            result = await self.think(prompt, n_tokens=n_tokens, history=history)
        except Exception as exc:  # noqa: BLE001 — surface to caller via report
            return CortexReport(
                backend=self.backend_name,
                confidence=0.0,
                sevo=float("-inf"),
                energy_w=0.0,
                approved=False,
                reason=f"backend error: {exc.__class__.__name__}: {exc}",
            )

        # 2. Cost the call (no quantum ops — pure classical; treat as one
        #    quantum step sized by token count).
        op = QuantumOperation(
            num_qubits=self.BRAIN_NUM_QUBITS,
            num_gates=n_tokens * self.BRAIN_NUM_GATES_PER_TOKEN,
            entanglement_depth=self.BRAIN_ENTANGLEMENT_DEPTH,
            decoherence_budget=max(1.0 - result.confidence, 0.0),
        )
        energy = self.cost.energy_watts(op)

        # 3. Sevo gate: high entropy vs. low utility.
        delta_utility = result.confidence
        delta_entropy = float(max(1.0 - result.confidence, 1e-3))
        sevo = self.cost.sevo(delta_utility, delta_entropy)
        sevo_ok = sevo > self.sevo_threshold

        # 4. Coherence gate.
        coherence_ok = coherence_phi >= self.min_coherence_phi
        confidence_ok = result.confidence >= self.min_confidence

        approved = sevo_ok and coherence_ok and confidence_ok
        if not approved:
            reasons = []
            if not sevo_ok:
                reasons.append(f"sevo {sevo:.2f}<={self.sevo_threshold}")
            if not coherence_ok:
                reasons.append(f"coherence_phi {coherence_phi:.3f}<{self.min_coherence_phi}")
            if not confidence_ok:
                reasons.append(f"confidence {result.confidence:.3f}<{self.min_confidence}")
            reason = "; ".join(reasons)
        else:
            reason = "approved"

        if approved:
            self.apply_to_ilf(result, agent_id=agent_id)

        report = CortexReport(
            backend=self.backend_name,
            confidence=result.confidence,
            sevo=sevo,
            energy_w=energy,
            approved=approved,
            reason=reason,
            result=result if approved else None,
            latency_s=result.latency_s,
            metadata=result.metadata,
        )
        self._reports.append(report)
        if len(self._reports) > 64:
            self._reports = self._reports[-64:]
        return report

    def apply_to_ilf(self, result: ThinkResult, agent_id: str = "spiking_brain") -> None:
        """Inject the ThinkResult into the ILF as an agent belief.

        The plasticity coefficients scale the agent weight (recent,
        confident thoughts have more influence).
        """
        weight = float(np.mean(result.plasticity)) if result.plasticity.size else 1.0
        weight = max(weight, 0.01)
        # Ensure the agent is registered.
        self.ilf.register_agent(agent_id, weight=weight)
        self.ilf.set_belief(agent_id, np.asarray(result.belief, dtype=float))
        self.ilf.set_weight(agent_id, weight)
        # Recompute q_star so coherence_phi reflects the new belief.
        self.ilf.compute_q_star()

    async def health(self) -> dict[str, Any]:
        backend_health = getattr(self.backend, "health", None)
        if backend_health is None:
            return {"backend": self.backend_name, "ready": True}
        out = backend_health()
        if inspect.isawaitable(out):
            out = await out
        return cast(dict[str, Any], out)

    def report(self) -> dict[str, object]:
        """Aggregate statistics over the recent history."""
        if not self._reports:
            return {"ticks": 0, "approved": 0, "approval_rate": 0.0}
        approved = sum(1 for r in self._reports if r.approved)
        mean_energy = float(np.mean([r.energy_w for r in self._reports]))
        mean_sevo = float(
            np.mean([r.sevo for r in self._reports if r.sevo != float("-inf")]) or 0.0
        )
        return {
            "ticks": len(self._reports),
            "approved": approved,
            "approval_rate": approved / len(self._reports),
            "mean_energy_w": mean_energy,
            "mean_sevo": mean_sevo,
            "backend": self.backend_name,
        }

    async def aclose(self) -> None:
        aclose = getattr(self.backend, "aclose", None)
        if aclose is not None:
            out = aclose()
            if inspect.isawaitable(out):
                await out
