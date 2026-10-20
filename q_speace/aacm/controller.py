"""AACMController — the runtime that wires AACM dynamics into SPEACE.

The controller is the executable form of the strategic 4-act plan:

  Atto 1 — ACQUISIZIONE  (regole 1-3)
  Atto 2 — CONVERSIONE   (regole 4-6)
  Atto 3 — STABILIZZAZIONE (regole 7-8)
  Atto 4 — RESILIENZA    (regole 9-10)

It is a *pure* state machine: each call to :meth:`step` returns a
:class:`StepDecision` and updates the internal state. The state is
serialized via the checkpoint module. The controller does not perform
I/O of its own beyond the explicit checkpoint path.

BCEL: the controller is a *deterministic state machine*. The "strategy"
it returns is a tag for downstream observability, not a command to a
mind. The model remains a control layer.
"""

from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field
from typing import Any

from .constants import (
    CENTRALITY_HIT_THRESHOLD,
    CHECKPOINT_INTERVAL_STEPS,
    DECAY_HALF_LIFE_S,
    FAIL_FAST_WINDOW,
    OMEGA_MIN,
)
from .primitives import (
    CentralityGraph,
    FractureMap,
    LegitimationChannel,
    LegitimationChannelRegistry,
    ResilienceManifest,
)
from .topology import betweenness_centrality, node_failure_streak


class AACMStrategy(enum.Enum):
    """Strategy tag for a single step (regola 1-3)."""

    DEFAULT = "default"
    CENTRAL_HIT = "central_hit"
    FAIL_FAST = "fail_fast"
    LEVERAGE_FRACTURE = "leverage_fracture"


@dataclass(frozen=True)
class StepDecision:
    """Decision returned by :meth:`AACMController.step`."""

    strategy: AACMStrategy
    central_node: str | None
    aacm_omega: float
    recommended_redirect: str | None
    notes: dict[str, Any] = field(default_factory=dict)


class AACMController:
    """Runtime state machine for the AACM model.

    The controller is constructed with a :class:`ResilienceManifest`
    that satisfies the Vincolo D invariants. It then receives
    :class:`CentralityGraph` snapshots, :class:`FractureMap` updates,
    and an event stream of (node, success) pairs, and produces
    :class:`StepDecision` outputs.
    """

    def __init__(
        self,
        resilience: ResilienceManifest,
        *,
        decay_half_life_s: float = DECAY_HALF_LIFE_S,
        checkpoint_interval_steps: int = CHECKPOINT_INTERVAL_STEPS,
        centrality_hit_threshold: float = CENTRALITY_HIT_THRESHOLD,
        fail_fast_window: int = FAIL_FAST_WINDOW,
    ) -> None:
        # Vincolo D check is also enforced by the dataclass __post_init__,
        # but we re-check here for defence in depth and to surface a
        # clearer error early.
        if resilience.omega < OMEGA_MIN:
            raise ValueError(f"resilience.omega={resilience.omega} < OMEGA_MIN={OMEGA_MIN}")
        self._resilience = resilience
        self._decay_half_life_s = decay_half_life_s
        self._checkpoint_interval_steps = checkpoint_interval_steps
        self._centrality_hit_threshold = centrality_hit_threshold
        self._fail_fast_window = fail_fast_window

        self._step_count = 0
        self._history: list[tuple[str, bool]] = []
        self._legitimation = LegitimationChannelRegistry(channels=self._default_channels())
        self._last_central_node: str | None = None
        self._last_redirect: str | None = None

    # ------------------------------------------------------------------
    # Public state
    # ------------------------------------------------------------------

    @property
    def resilience(self) -> ResilienceManifest:
        return self._resilience

    @property
    def step_count(self) -> int:
        return self._step_count

    @property
    def history(self) -> list[tuple[str, bool]]:
        return list(self._history)

    @property
    def legitimation(self) -> LegitimationChannelRegistry:
        return self._legitimation

    # ------------------------------------------------------------------
    # Step
    # ------------------------------------------------------------------

    def step(
        self,
        graph: CentralityGraph,
        fracture_map: FractureMap,
    ) -> StepDecision:
        """Compute the AACM decision for one step.

        Returns a :class:`StepDecision` that downstream code can act on.
        The controller does not perform the action itself.
        """
        self._step_count += 1
        notes: dict[str, Any] = {}

        # --- Atto 1: ACQUISIZIONE (regole 1, 2, 3) ---
        centrality = betweenness_centrality(graph)
        notes["centrality"] = dict(centrality)
        central_node, central_score = _argmax_centrality(centrality)
        strategy = AACMStrategy.DEFAULT
        redirect: str | None = None

        # Regola 1: if a node exceeds the threshold, target it.
        if central_score >= self._centrality_hit_threshold:
            strategy = AACMStrategy.CENTRAL_HIT
            self._last_central_node = central_node
            notes["central_score"] = central_score
        else:
            # Regola 2: check failure streaks.
            failing = self._failing_node()
            if failing is not None:
                strategy = AACMStrategy.FAIL_FAST
                redirect = self._pick_redirect(graph, failing)
                self._last_redirect = redirect
                notes["failing_node"] = failing
            else:
                # Regola 3: leverage pre-existing fractures when the
                # signal quality is low (proxy: low centrality in
                # the top quartile is taken as low overall quality).
                mean_centrality = sum(centrality.values()) / len(centrality) if centrality else 0.0
                if mean_centrality < 0.2 and fracture_map.total_magnitude > 0.0:
                    strategy = AACMStrategy.LEVERAGE_FRACTURE
                    notes["fracture_total"] = fracture_map.total_magnitude

        return StepDecision(
            strategy=strategy,
            central_node=self._last_central_node,
            aacm_omega=self._resilience.omega,
            recommended_redirect=redirect or self._last_redirect,
            notes=notes,
        )

    # ------------------------------------------------------------------
    # Event ingestion
    # ------------------------------------------------------------------

    def record_event(self, node: str, success: bool) -> None:
        """Append a (node, success) event to the history.

        The history is used by the fail-fast (regola 2) logic to
        detect consecutive failures and trigger a switch.
        """
        self._history.append((node, bool(success)))

    def register_legitimation(
        self,
        channel: LegitimationChannel,
    ) -> LegitimationChannelRegistry:
        """Add a new legitimation channel.

        Returns the updated registry. Raises if the new channel breaks
        the K ≥ 2 or independence invariants.
        """
        new_channels = self._legitimation.channels + (channel,)
        self._legitimation = LegitimationChannelRegistry(channels=new_channels)
        return self._legitimation

    # ------------------------------------------------------------------
    # Checkpoint helpers
    # ------------------------------------------------------------------

    def should_checkpoint(self) -> bool:
        """True if the controller has reached the checkpoint interval."""
        if self._checkpoint_interval_steps <= 0:
            return False
        return self._step_count > 0 and self._step_count % self._checkpoint_interval_steps == 0

    def snapshot(self, agent_id: str, session_id: str) -> dict[str, Any]:
        """Build a checkpoint payload (no I/O).

        Use :func:`q_speace.aacm.checkpoint.write_checkpoint` to
        persist this payload to disk.
        """
        return {
            "schema_version": "aacm.cp.1",
            "agent_id": agent_id,
            "session_id": session_id,
            "step": self._step_count,
            "created_at": time.time(),
            "legitimation_registry": self._legitimation.to_dict(),
            "resilience_manifest": self._resilience.to_dict(),
            "decision_history": [{"node": n, "success": s} for (n, s) in self._history],
        }

    def restore_snapshot(self, payload: dict[str, Any]) -> None:
        """Restore controller state from a checkpoint payload.

        Re-applies the history; the resilience and legitimation are
        taken from the payload as-is.
        """
        from .checkpoint import check_compatibility

        check_compatibility(payload)
        self._step_count = int(payload.get("step", 0))
        history = payload.get("decision_history", [])
        self._history = [(str(d["node"]), bool(d["success"])) for d in history]
        # Resilience and legitimation are re-derived from the payload
        # to validate invariants post-resume.
        rm = payload.get("resilience_manifest", {})
        self._resilience = ResilienceManifest(
            omega=float(rm["omega"]),
            independent_nodes=tuple(rm.get("independent_nodes", ())),
            checkpoint_paths=tuple(rm.get("checkpoint_paths", ())),
            schema_version=str(rm.get("schema_version", "aacm.cp.1")),
        )
        lr = payload.get("legitimation_registry", {})
        channels_raw = lr.get("channels", [])
        channels = tuple(
            LegitimationChannel(
                channel_id=str(c["channel_id"]),
                evidence_kind=str(c["evidence_kind"]),
                artifact_path=str(c["artifact_path"]),
                verified=bool(c["verified"]),
                verified_at=(float(c["verified_at"]) if c.get("verified_at") is not None else None),
            )
            for c in channels_raw
        )
        self._legitimation = LegitimationChannelRegistry(channels=channels)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _failing_node(self) -> str | None:
        for node in {n for (n, _) in self._history}:
            if node_failure_streak(node, self._history) >= self._fail_fast_window:
                return node
        return None

    def _pick_redirect(self, graph: CentralityGraph, failing: str) -> str | None:
        # Pick the first node that is not the failing one and has
        # outgoing edges. Deterministic: order of insertion.
        for src, dst, _w in graph.edges:
            if src != failing and dst != failing:
                return src
        return next(
            (n for n in graph.nodes if n != failing),
            None,
        )

    def _default_channels(self) -> tuple[LegitimationChannel, ...]:
        # Default: one code channel + one test channel. These are
        # placeholders until the host wires in real artefacts.
        return (
            LegitimationChannel(
                channel_id="leg:code:default",
                evidence_kind="code",
                artifact_path="(unset)",
                verified=False,
                verified_at=None,
            ),
            LegitimationChannel(
                channel_id="leg:test:default",
                evidence_kind="test",
                artifact_path="(unset)",
                verified=False,
                verified_at=None,
            ),
        )


def _argmax_centrality(d: dict[str, float]) -> tuple[str | None, float]:
    if not d:
        return None, 0.0
    node, score = max(d.items(), key=lambda kv: kv[1])
    return node, score
