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

T-SPB-4 additions:

- Optional :class:`Memory` injection (default ``WorkingMemory(64)``).
- Delegates ``lifecycle_state``, ``load``, ``shutdown`` to the
  backend when present (with graceful fallback for duck-typed
  backends that pre-date the formal Protocol).
- ``aclose`` retained as a deprecated alias of ``shutdown``.
"""

from __future__ import annotations

import asyncio
import inspect
import warnings
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, cast

import numpy as np

from ..edd_cvt.ilf import InformationalLogicalField
from ..metabolism.cognitive_cost_model import QuantumCostModel, QuantumOperation
from .audit import BrainAuditLog
from .interface import LifecycleState
from .memory import Memory, WorkingMemory
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
        memory: Memory | None = None,
        q_star_ema: float = 0.5,
        coherence_phi_ema: float = 0.5,
        backend_coherence_phi_floor: float = 0.7,
        brain_audit_log: BrainAuditLog | None = None,
    ) -> None:
        if backend is None:
            from .factory import make_spiking_brain

            backend = make_spiking_brain()
        self.backend = backend
        # T-SPB-3-A: when no ILF is supplied, fall back to one with EMA
        # blending enabled so multi-turn `apply_to_ilf` does not collapse
        # coherence_phi on the second tick. Callers passing their own ILF
        # control the EMA coefficients themselves (defaults preserved).
        self.ilf = ilf or InformationalLogicalField(
            coherence_phi=1.0,
            q_star_ema=q_star_ema,
            coherence_phi_ema=coherence_phi_ema,
        )
        self.cost = cost or QuantumCostModel()
        self.sevo_threshold = sevo_threshold
        self.min_coherence_phi = min_coherence_phi
        self.min_confidence = min_confidence
        # T-SPB-3-A-bis: floor for the coherence_phi value propagated to
        # the backend's ``think()``. Prevents the coupled loop where a
        # low ILF φ attenuates the backend's reported confidence, which
        # then drives sevo below threshold. The coherence gate inside
        # ``tick()`` still sees the real φ, so this does not bypass
        # the SPEACE-side quality control. Default 0.7 — at this level
        # the backend's ``confidence *= (0.5 + 0.5 * φ)`` keeps
        # attenuated_conf ≥ 0.65 · (0.5+0.5·0.7) = 0.62, which gives
        # sevo ≥ 1.6 for any incoming base confidence ≥ 0.65.
        if not (0.0 <= backend_coherence_phi_floor <= 1.0):
            raise ValueError("backend_coherence_phi_floor must be in [0, 1]")
        self.backend_coherence_phi_floor = float(backend_coherence_phi_floor)
        # T-SPB-4: default in-memory working memory (capacity 64).
        self.memory: Memory = memory if memory is not None else WorkingMemory()
        # T-SPB-3-C: optional persistent audit trail for apply events.
        self.brain_audit_log: BrainAuditLog | None = brain_audit_log
        self._history: list[ThinkResult] = []
        self._reports: list[CortexReport] = []

    @property
    def backend_name(self) -> str:
        # Prefer new ``backend_name`` (T-SPB-4 protocol attr); fall back
        # to legacy ``.backend`` string used by duck-typed backends.
        name = getattr(self.backend, "backend_name", None) or getattr(
            self.backend, "backend", type(self.backend).__name__
        )
        return str(name) if name is not None else type(self.backend).__name__

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
        """Run a single think call, updating the local history.

        T-SPB-4: also writes the result to ``self.memory`` (default
        :class:`WorkingMemory`) so other components can retrieve recent
        thoughts via ``get_relevant``.

        T-SPB-3-A-bis: ``coherence_phi`` propagated to the backend is
        clamped at ``self.backend_coherence_phi_floor``. The internal
        coherence gate still sees the unclamped value.
        """
        ilf_phi = float(self.ilf.coherence_phi)
        coherence_phi = max(ilf_phi, self.backend_coherence_phi_floor)
        result = await self._think_async(prompt, coherence_phi, n_tokens, history)
        self._history.append(result)
        if len(self._history) > 64:
            self._history = self._history[-64:]
        # T-SPB-4: persist to memory subsystem (no-op for backends
        # that don't expose memory, e.g. stubs return None).
        if self.memory is not None:
            await self.memory.put(result)
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
            self.apply_to_ilf(
                result,
                agent_id=agent_id,
                prompt=prompt,
                sevo=sevo,
                energy_w=energy,
                approved=approved,
                reason=reason,
            )

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

    def apply_to_ilf(
        self,
        result: ThinkResult,
        agent_id: str = "spiking_brain",
        *,
        prompt: str = "",
        sevo: float = 0.0,
        energy_w: float = 0.0,
        approved: bool = True,
        reason: str = "apply",
    ) -> None:
        """Inject the ThinkResult into the ILF as an agent belief.

        The plasticity coefficients scale the agent weight (recent,
        confident thoughts have more influence).

        T-SPB-3-C: when ``self.brain_audit_log`` is set, this method
        also writes one JSONL record with full provenance (backend,
        model, pre/post coherence_phi, sevo, energy_w, approved flag).
        Best-effort: a failure to write the audit line is logged to
        stderr but never raised.
        """
        coherence_phi_pre = float(self.ilf.coherence_phi)
        weight = float(np.mean(result.plasticity)) if result.plasticity.size else 1.0
        weight = max(weight, 0.01)
        # Ensure the agent is registered.
        self.ilf.register_agent(agent_id, weight=weight)
        self.ilf.set_belief(agent_id, np.asarray(result.belief, dtype=float))
        self.ilf.set_weight(agent_id, weight)
        # Recompute q_star so coherence_phi reflects the new belief.
        self.ilf.compute_q_star()
        coherence_phi_post = float(self.ilf.coherence_phi)

        if self.brain_audit_log is not None:
            from .audit import make_apply_record

            backend_meta = dict(result.metadata or {})
            backend_meta.setdefault("cortex_backend", self.backend_name)
            rec = make_apply_record(
                agent_id=agent_id,
                backend=self.backend_name,
                backend_meta=backend_meta,
                prompt=prompt or "",
                result_text=result.text or "",
                result_confidence=float(result.confidence),
                result_belief=np.asarray(result.belief, dtype=float),
                n_tokens=int(result.n_tokens),
                coherence_phi_pre=coherence_phi_pre,
                coherence_phi_post=coherence_phi_post,
                sevo=sevo,
                energy_w=energy_w,
                approved=approved,
                reason=reason,
            )
            self.brain_audit_log.write(rec)

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
        """Deprecated alias for :meth:`shutdown`.

        Kept for backward compatibility with T205 callers (CLI,
        EvolutionCouncil). Emits a :class:`DeprecationWarning` if the
        caller passes through the public API.
        """
        warnings.warn(
            "SpikingBrainCortex.aclose() is deprecated; use shutdown()",
            DeprecationWarning,
            stacklevel=2,
        )
        await self.shutdown()

    async def shutdown(self) -> None:
        """Release backend resources.

        Delegates to ``backend.shutdown()`` if present (T-SPB-4
        protocol); falls back to ``backend.aclose()`` for legacy
        backends; no-op if neither exists.
        """
        shutdown = getattr(self.backend, "shutdown", None)
        aclose = getattr(self.backend, "aclose", None)
        target = shutdown if callable(shutdown) else aclose
        if target is not None:
            out = target()
            if inspect.isawaitable(out):
                await out

    def lifecycle_state(self) -> LifecycleState:
        """Return the backend's lifecycle state.

        Delegates to ``backend.lifecycle_state()`` if present (T-SPB-4);
        otherwise infers ``READY`` (the legacy implicit state).
        """
        state = getattr(self.backend, "lifecycle_state", None)
        if callable(state):
            out = state()
            if isinstance(out, LifecycleState):
                return out
        return LifecycleState.READY

    async def load(self) -> None:
        """Initialise the backend (no-op for legacy backends).

        Delegates to ``backend.load()`` if present (T-SPB-4).
        """
        load = getattr(self.backend, "load", None)
        if callable(load):
            out = load()
            if inspect.isawaitable(out):
                await out
