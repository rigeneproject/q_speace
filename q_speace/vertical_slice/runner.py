"""Decision-trace runner wiring EventRouter -> SpikingBrainCortex -> GatePolicy."""

from __future__ import annotations

import asyncio
import math
import time
import uuid

from ..metabolism.cognitive_cost_model import QuantumCostModel, QuantumOperation
from ..routing import Event, EventRouter
from ..spiking_brain import SpikingBrainCortex, StubSpikingBrain, ThinkResult
from .contracts import (
    DecisionRecord,
    ExperimentManifest,
    OutcomeRecord,
    OutcomeStatus,
    RequestRecord,
    TraceRecord,
    capture_git_state,
    runtime_environment,
    sha256_text,
    utc_now_iso,
)
from .dataset import BenchmarkCase, BenchmarkDataset
from .policies import PolicyConfig, evaluate_policy


class VerticalSliceRunner:
    """Executes the T208 reference vertical slice with full decision traces.

    Generated text is treated as untrusted output: it cannot directly mutate
    Q-SPEACE state. ILF belief updates occur only when ``decision.gate_open``
    is True and the cortex's own Sevo/coherence invariants are satisfied.
    """

    def __init__(
        self,
        *,
        cortex: SpikingBrainCortex | None = None,
        router: EventRouter | None = None,
        policy: PolicyConfig | None = None,
        timeout_s: float = 10.0,
        include_raw_text: bool = False,
        seed: int = 0,
    ) -> None:
        if not math.isfinite(timeout_s) or timeout_s <= 0.0:
            raise ValueError(f"timeout_s must be finite and > 0 (got {timeout_s!r})")
        self.cortex = cortex or SpikingBrainCortex(backend=StubSpikingBrain(seed=seed))
        self.router = router or EventRouter()
        self.policy = policy or PolicyConfig(policy_id="t209-always_answer", kind="always_answer")
        self.timeout_s = float(timeout_s)
        self.include_raw_text = bool(include_raw_text)
        self.seed = int(seed)

    def _predict_energy_j(self, n_tokens: int, confidence_est: float = 0.5) -> float:
        op = QuantumOperation(
            num_qubits=self.cortex.BRAIN_NUM_QUBITS,
            num_gates=max(int(n_tokens), 0) * self.cortex.BRAIN_NUM_GATES_PER_TOKEN,
            entanglement_depth=self.cortex.BRAIN_ENTANGLEMENT_DEPTH,
            decoherence_budget=max(1.0 - confidence_est, 0.0),
        )
        return self.cortex.cost.energy_joules(op, duration_s=1.0)

    async def execute_case(
        self,
        case: BenchmarkCase,
        *,
        run_id: str,
        request_id: str | None = None,
    ) -> TraceRecord:
        req_id = request_id or f"{run_id}-{case.case_id}"
        started_at = utc_now_iso()
        request = RequestRecord(
            run_id=run_id,
            request_id=req_id,
            model_id=self.cortex.backend_name,
            model_revision=self.policy.model_revision,
            policy_id=self.policy.policy_id,
            prompt_hash=sha256_text(case.prompt),
            started_at=started_at,
            prompt_text=case.prompt if self.include_raw_text else None,
        )

        event = Event(kind="text_input", text=case.prompt)
        route = self.router.route(event).area
        predicted_energy_j = self._predict_energy_j(case.n_tokens)
        t0 = time.perf_counter()

        # Non-language routes are rejected before invoking the backend.
        if route != "language":
            decision = evaluate_policy(
                self.policy,
                route=route,
                predicted_energy_j=predicted_energy_j,
                confidence=None,
                sevo=None,
                coherence_phi=float(self.cortex.ilf.coherence_phi),
            )
            status: OutcomeStatus = (
                "fallback" if self.policy.fallback_mode == "fallback" else "refused"
            )
            outcome = OutcomeRecord(
                status=status,
                latency_s=time.perf_counter() - t0,
                tokens_in=0,
                tokens_out=0,
                measured_energy_j=0.0,
                response_hash=None,
            )
            return TraceRecord(
                case_id=case.case_id, request=request, decision=decision, outcome=outcome
            )

        # Pre-dispatch energy gate: avoid spending backend work if budget is already exceeded.
        if (
            self.policy.enabled
            and self.policy.kind in ("energy_gate", "combined_gate")
            and predicted_energy_j > self.policy.max_energy_j
        ):
            decision = DecisionRecord(
                route=route,
                gate_open=False,
                decision_reason="energy_gate_exceeded",
                predicted_energy_j=predicted_energy_j,
                confidence=None,
                thresholds=self.policy.thresholds_dict(),
            )
            status = "fallback" if self.policy.fallback_mode == "fallback" else "refused"
            outcome = OutcomeRecord(
                status=status,
                latency_s=time.perf_counter() - t0,
                tokens_in=len(case.prompt.split()),
                tokens_out=0,
                measured_energy_j=0.0,
                response_hash=None,
            )
            return TraceRecord(
                case_id=case.case_id, request=request, decision=decision, outcome=outcome
            )

        # Invoke backend with explicit timeout and malformed-response protection.
        try:
            result = await asyncio.wait_for(
                self.cortex.think(case.prompt, n_tokens=case.n_tokens),
                timeout=self.timeout_s,
            )
            if not isinstance(result, ThinkResult):
                raise ValueError(f"malformed backend result type: {type(result).__name__}")
            if not math.isfinite(result.confidence) or not (0.0 <= result.confidence <= 1.0):
                raise ValueError(f"non-finite or out-of-range confidence: {result.confidence!r}")
        except TimeoutError:
            decision = DecisionRecord(
                route=route,
                gate_open=False,
                decision_reason="backend_timeout",
                predicted_energy_j=predicted_energy_j,
                confidence=None,
                thresholds=self.policy.thresholds_dict(),
            )
            outcome = OutcomeRecord(
                status="failed",
                latency_s=time.perf_counter() - t0,
                tokens_in=len(case.prompt.split()),
                tokens_out=0,
                measured_energy_j=None,
                response_hash=None,
            )
            return TraceRecord(
                case_id=case.case_id, request=request, decision=decision, outcome=outcome
            )
        except Exception as exc:  # noqa: BLE001 — surface malformed/backend failures cleanly
            decision = DecisionRecord(
                route=route,
                gate_open=False,
                decision_reason=f"backend_error:{type(exc).__name__}",
                predicted_energy_j=predicted_energy_j,
                confidence=None,
                thresholds=self.policy.thresholds_dict(),
            )
            outcome = OutcomeRecord(
                status="failed",
                latency_s=time.perf_counter() - t0,
                tokens_in=len(case.prompt.split()),
                tokens_out=0,
                measured_energy_j=None,
                response_hash=None,
            )
            return TraceRecord(
                case_id=case.case_id, request=request, decision=decision, outcome=outcome
            )

        elapsed_s = time.perf_counter() - t0
        actual_energy_j = self._predict_energy_j(
            max(result.n_tokens, case.n_tokens),
            confidence_est=float(result.confidence),
        )
        delta_entropy = max(1.0 - float(result.confidence), 1e-3)
        sevo = QuantumCostModel.sevo(float(result.confidence), delta_entropy)
        coherence_phi = float(self.cortex.ilf.coherence_phi)

        decision = evaluate_policy(
            self.policy,
            route=route,
            predicted_energy_j=actual_energy_j,
            confidence=float(result.confidence),
            sevo=sevo,
            coherence_phi=coherence_phi,
        )

        if decision.gate_open:
            # Apply belief only when the deterministic gate opened.
            self.cortex.apply_to_ilf(
                result,
                agent_id="vertical_slice",
                prompt=case.prompt,
                sevo=sevo,
                energy_w=actual_energy_j,
                approved=True,
                reason=decision.decision_reason,
            )
            outcome = OutcomeRecord(
                status="answered",
                latency_s=elapsed_s,
                tokens_in=int(result.metadata.get("n_tokens_in", len(case.prompt.split()))),
                tokens_out=int(result.n_tokens),
                measured_energy_j=actual_energy_j,
                response_hash=sha256_text(result.text),
                response_text=result.text if self.include_raw_text else None,
            )
        else:
            status = "fallback" if self.policy.fallback_mode == "fallback" else "refused"
            outcome = OutcomeRecord(
                status=status,
                latency_s=elapsed_s,
                tokens_in=int(result.metadata.get("n_tokens_in", len(case.prompt.split()))),
                tokens_out=0,
                measured_energy_j=actual_energy_j,
                response_hash=None,
            )

        return TraceRecord(
            case_id=case.case_id, request=request, decision=decision, outcome=outcome
        )

    async def run_dataset_async(
        self,
        dataset: BenchmarkDataset,
        *,
        run_id: str | None = None,
    ) -> tuple[list[TraceRecord], ExperimentManifest]:
        rid = run_id or f"vs-{uuid.uuid4().hex[:12]}"
        traces = [await self.execute_case(case, run_id=rid) for case in dataset.cases]
        git_commit, git_dirty = capture_git_state()
        py_ver, plat = runtime_environment()
        manifest = ExperimentManifest(
            manifest_version="1.0.0",
            run_id=rid,
            created_at=utc_now_iso(),
            git_commit=git_commit,
            git_dirty=git_dirty,
            python_version=py_ver,
            platform=plat,
            model_id=self.cortex.backend_name,
            model_revision=self.policy.model_revision,
            dataset_id=dataset.dataset_id,
            dataset_sha256=dataset.sha256(),
            dataset_size=len(dataset.cases),
            policy_id=self.policy.policy_id,
            policy_config=self.policy.to_dict(),
            seed=self.seed,
            include_raw_text=self.include_raw_text,
            summary={
                "answered": sum(1 for t in traces if t.outcome.status == "answered"),
                "refused": sum(1 for t in traces if t.outcome.status == "refused"),
                "fallback": sum(1 for t in traces if t.outcome.status == "fallback"),
                "failed": sum(1 for t in traces if t.outcome.status == "failed"),
            },
        )
        return traces, manifest

    def run_dataset(
        self,
        dataset: BenchmarkDataset,
        *,
        run_id: str | None = None,
    ) -> tuple[list[TraceRecord], ExperimentManifest]:
        return asyncio.run(self.run_dataset_async(dataset, run_id=run_id))
