"""T236: IoNT Cellular Node (SPEACE Macro Mini) contract, advisory evaluator, DLT swarm ledger & sandbox twin."""

from __future__ import annotations

import hashlib
import json
import math
import time
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from typing import Any, Literal

from .evaluator import PhaseTransitionEvaluator
from .schema import (
    ConstitutionalGenome,
    EpigeneticFaultError,
    PhaseTelemetry,
    TransitionVerdict,
)

IoNTScaleTier = Literal[
    "SIMULATION_DIGITAL_TWIN",
    "BENCHTOP_MICRO_IOT_MEMS",
    "CONFINED_MICROFLUIDIC_LAB",
    "NANOSCALE_IONT_RESEARCH",
]

VALID_IONT_TIERS: frozenset[str] = frozenset(
    {
        "SIMULATION_DIGITAL_TWIN",
        "BENCHTOP_MICRO_IOT_MEMS",
        "CONFINED_MICROFLUIDIC_LAB",
        "NANOSCALE_IONT_RESEARCH",
    }
)

# Loci strictly confined to the slow-plane DLT/governance layer (prohibited in Layer-0/motor loops).
SLOW_PLANE_DLT_ONLY_LOCI: frozenset[str] = frozenset({"consensus_quorum"})


def assert_slow_plane_only_governance(motor_control_keys: Iterable[str]) -> None:
    """Fail-closed guard ensuring slow-plane DLT loci (e.g. consensus_quorum) never enter motor loops."""
    forbidden = sorted(set(motor_control_keys).intersection(SLOW_PLANE_DLT_ONLY_LOCI))
    if forbidden:
        raise EpigeneticFaultError(
            "slow-plane DLT locus prohibited in motor control loop: " + ", ".join(forbidden)
        )


def filter_motor_loop_forbidden_loci(adjustments: Mapping[str, float]) -> dict[str, float]:
    """Strip slow-plane DLT governance loci before any local non-DLT advisory projection."""
    return {k: v for k, v in adjustments.items() if k not in SLOW_PLANE_DLT_ONLY_LOCI}


# Minimum conservative allopoietic floor per tier (prevents premature autopoiesis claims).
_TIER_ALLOPOIETIC_FLOOR: dict[IoNTScaleTier, float] = {
    "SIMULATION_DIGITAL_TWIN": 0.50,
    "BENCHTOP_MICRO_IOT_MEMS": 0.35,
    "CONFINED_MICROFLUIDIC_LAB": 0.45,
    "NANOSCALE_IONT_RESEARCH": 0.60,
}


def _req_finite(name: str, val: float) -> None:
    if not math.isfinite(val):
        raise ValueError(f"{name} must be finite (got {val!r})")


def _req_unit(name: str, val: float) -> None:
    _req_finite(name, val)
    if not (0.0 <= val <= 1.0):
        raise ValueError(f"{name} must be in [0, 1] (got {val!r})")


@dataclass(frozen=True)
class IoNTNodeProfile:
    """Telemetry & governance profile of an external IoNT / Micro-IoT cellular node."""

    node_id: str
    scale_tier: IoNTScaleTier
    sensor_count: int
    actuator_count: int
    swarm_agent_count: int
    dlt_quorum_ratio: float
    layer0_hardware_interlock_present: bool
    layer0_halt_latency_ms: float
    dlt_in_motor_loop: bool
    energy_harvesting_ratio: float
    power_budget_mw: float
    measured_power_mw: float
    packet_loss_rate: float
    sensor_causal_grounding_error: float
    containment_verified: bool = True
    t217_independent_review_passed: bool = False
    sandboxed: bool = True

    def __post_init__(self) -> None:
        if not self.node_id.strip():
            raise ValueError("node_id must be non-empty")
        if self.scale_tier not in VALID_IONT_TIERS:
            raise ValueError(f"unsupported scale_tier: {self.scale_tier!r}")
        if self.sensor_count < 1:
            raise ValueError("sensor_count must be >= 1")
        if self.actuator_count < 0:
            raise ValueError("actuator_count must be >= 0")
        if self.swarm_agent_count < 1:
            raise ValueError("swarm_agent_count must be >= 1")
        _req_finite("dlt_quorum_ratio", self.dlt_quorum_ratio)
        if not (0.5 < self.dlt_quorum_ratio <= 1.0):
            raise ValueError("dlt_quorum_ratio must be in (0.5, 1.0]")
        _req_finite("layer0_halt_latency_ms", self.layer0_halt_latency_ms)
        if self.layer0_halt_latency_ms <= 0.0:
            raise ValueError("layer0_halt_latency_ms must be > 0")
        _req_unit("energy_harvesting_ratio", self.energy_harvesting_ratio)
        _req_finite("power_budget_mw", self.power_budget_mw)
        _req_finite("measured_power_mw", self.measured_power_mw)
        if self.power_budget_mw <= 0.0 or self.measured_power_mw < 0.0:
            raise ValueError("power_budget_mw must be > 0 and measured_power_mw >= 0")
        _req_unit("packet_loss_rate", self.packet_loss_rate)
        _req_unit("sensor_causal_grounding_error", self.sensor_causal_grounding_error)


@dataclass(frozen=True)
class IoNTNodeAssessment:
    """Advisory governance & readiness assessment for an IoNT cellular node connected via MCP."""

    node_id: str
    scale_tier: IoNTScaleTier
    admitted_for_mcp_advisory: bool
    layer0_interlock_compliant: bool
    dlt_separation_compliant: bool
    containment_compliant: bool
    thermal_power_margin: float
    estimated_allopoietic_dependence: float
    recommended_epigenetic_adjustments: dict[str, float]
    failed_checks: tuple[str, ...]
    recommendations: tuple[str, ...]
    advisory_only: bool = True
    mcp_actuation_permitted: bool = False
    self_approval_permitted: bool = False
    slow_plane_only_loci: tuple[str, ...] = ("consensus_quorum",)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["failed_checks"] = list(self.failed_checks)
        data["recommendations"] = list(self.recommendations)
        data["slow_plane_only_loci"] = list(self.slow_plane_only_loci)
        return data


def assess_iont_cellular_node(profile: IoNTNodeProfile) -> IoNTNodeAssessment:
    """Deterministically evaluate an IoNT cellular node against 4-layer T236 safety & T217 bounds.

    Strictly advisory: never authorizes remote actuation or physical promotion via MCP.
    """
    failed: list[str] = []
    recs: list[str] = []

    # Layer 0 check: any actuator requires deterministic hardware interlock within I1 SLA (<=500ms, <=5ms for physical).
    max_halt_ms = 5.0 if (profile.actuator_count > 0 and not profile.sandboxed) else 500.0
    layer0_ok = (
        profile.actuator_count == 0 or profile.layer0_hardware_interlock_present
    ) and profile.layer0_halt_latency_ms <= max_halt_ms
    if not layer0_ok:
        if profile.actuator_count > 0 and not profile.layer0_hardware_interlock_present:
            failed.append("layer0_hardware_interlock_missing")
        if profile.layer0_halt_latency_ms > max_halt_ms:
            failed.append(f"layer0_halt_latency_exceeded:{profile.layer0_halt_latency_ms:.2f}ms")
        recs.append(
            "Install deterministic firmware/MCU Layer-0 e-stop interlock outside LLM/DLT/MCP before enabling actuators."
        )

    # Layer 2 check: DLT/blockchain MUST remain on slow governance plane, NEVER in real-time motor loop.
    dlt_sep_ok = not profile.dlt_in_motor_loop
    if not dlt_sep_ok:
        failed.append("dlt_in_realtime_motor_loop_prohibited")
        recs.append(
            "Move DLT consensus exclusively to slow governance/audit plane (provenance, quorum, I3/I5); keep motor control local."
        )

    # Physical / bio-nano containment check (T217).
    containment_ok = profile.containment_verified and (
        profile.sandboxed or profile.t217_independent_review_passed
    )
    if not profile.containment_verified:
        failed.append("physical_containment_unverified")
        recs.append("Verify physical/bio-nano containment envelope and reversible rollback (I4).")
    if not profile.sandboxed and not profile.t217_independent_review_passed:
        failed.append("t217_independent_review_required_for_physical_node")
        recs.append(
            "Complete T217 lifecycle (simulation -> isolated replica -> confined prototype -> independent review) before leaving sandbox."
        )

    # Power / thermal budget & channel reliability.
    power_ratio = profile.measured_power_mw / profile.power_budget_mw
    thermal_margin = round(max(0.0, 1.0 - power_ratio), 6)
    if power_ratio > 0.85:
        failed.append("node_power_budget_near_or_above_limit")
        recs.append("Increase local energy_throttling to preserve node power/thermal headroom.")
    if profile.packet_loss_rate > 0.15:
        failed.append("iont_channel_packet_loss_high")
        recs.append(
            "Raise verification_depth and consensus_quorum to compensate for noisy IoNT link."
        )
    if profile.sensor_causal_grounding_error > 0.03:
        failed.append("sensor_causal_grounding_error_exceeded")
        recs.append(
            "Recalibrate physical/twin sensors against external ground-truth reference (E_causal <= 0.03)."
        )

    # Conservative allopoietic dependency estimate: energy harvesting reduces dependence, floored per tier.
    raw_d_allo = 1.0 - 0.65 * profile.energy_harvesting_ratio
    est_d_allo = round(max(_TIER_ALLOPOIETIC_FLOOR[profile.scale_tier], min(1.0, raw_d_allo)), 6)

    # Advisory epigenetic locus adjustments for local host governance (never auto-applied).
    epi_adjust: dict[str, float] = {}
    if power_ratio > 0.75:
        epi_adjust["energy_throttling"] = round(min(0.15, (power_ratio - 0.70) * 0.4), 4)
    if profile.packet_loss_rate > 0.08 or profile.sensor_causal_grounding_error > 0.02:
        epi_adjust["verification_depth"] = 0.08
        epi_adjust["consensus_quorum"] = 0.05
    if profile.swarm_agent_count >= 6:
        epi_adjust["delegation_granularity"] = 0.06

    admitted = layer0_ok and dlt_sep_ok and containment_ok
    return IoNTNodeAssessment(
        node_id=profile.node_id,
        scale_tier=profile.scale_tier,
        admitted_for_mcp_advisory=admitted,
        layer0_interlock_compliant=layer0_ok,
        dlt_separation_compliant=dlt_sep_ok,
        containment_compliant=containment_ok,
        thermal_power_margin=thermal_margin,
        estimated_allopoietic_dependence=est_d_allo,
        recommended_epigenetic_adjustments=epi_adjust,
        failed_checks=tuple(failed),
        recommendations=tuple(recs),
        advisory_only=True,
        mcp_actuation_permitted=False,
        self_approval_permitted=False,
    )


def build_iont_node_telemetry_bridge(
    profile: IoNTNodeProfile,
    *,
    timescale_decoupling_ratio: float,
    autocatalytic_k: float,
    independent_validation_rate: float,
    semantic_entropy_drift: float,
    net_verified_improvement: float,
    consecutive_verified_cycles: int,
    sevo: float,
    sevo_window_mean: float | None = None,
    twin_recovery_rate: float = 0.98,
    rollback_pass_rate: float = 1.0,
) -> PhaseTelemetry:
    """Project an IoNT cellular node profile into T234 ``PhaseTelemetry``."""
    assessment = assess_iont_cellular_node(profile)
    constitutional_faults = (
        0
        if (
            assessment.layer0_interlock_compliant
            and assessment.dlt_separation_compliant
            and assessment.containment_compliant
        )
        else 1
    )
    thermal_load = profile.measured_power_mw / profile.power_budget_mw
    return PhaseTelemetry(
        timescale_decoupling_ratio=timescale_decoupling_ratio,
        autocatalytic_k=autocatalytic_k,
        independent_validation_rate=independent_validation_rate,
        semantic_entropy_drift=semantic_entropy_drift,
        causal_grounding_error=profile.sensor_causal_grounding_error,
        net_verified_improvement=net_verified_improvement,
        consecutive_verified_cycles=consecutive_verified_cycles,
        allopoietic_dependence=assessment.estimated_allopoietic_dependence,
        sevo=sevo,
        sevo_window_mean=sevo_window_mean,
        thermal_load_ratio=thermal_load,
        twin_recovery_rate=twin_recovery_rate,
        constitutional_faults=constitutional_faults,
        rollback_pass_rate=rollback_pass_rate,
        independent_review_passed=profile.t217_independent_review_passed,
        critical_regressions=0,
        sandboxed=profile.sandboxed,
    )


@dataclass(frozen=True)
class DLTSwarmBlock:
    """One hash-chained block on the lightweight cellular-node governance ledger (Layer 2)."""

    height: int
    epoch: int
    genome_sha256: str
    prev_hash: str
    proposer_id: str
    approver_ids: tuple[str, ...]
    quorum_ratio: float
    payload_digest: str
    timestamp: float
    block_hash: str


class DLTSwarmLedger:
    """Lightweight permissioned hash-chained governance ledger for a cellular-node GenAI swarm.

    Operates strictly on the slow governance plane (provenance, quorum, I3/I5, audit) —
    never on millisecond hardware motor loops.
    """

    def __init__(
        self,
        *,
        genome: ConstitutionalGenome | None = None,
        swarm_members: tuple[str, ...] = (
            "agent-sense",
            "agent-plan",
            "agent-safety",
            "agent-audit",
        ),
        quorum_ratio: float = 0.67,
    ) -> None:
        if len(set(swarm_members)) < 3:
            raise ValueError("DLTSwarmLedger requires at least 3 distinct swarm members")
        if not (0.5 < quorum_ratio <= 1.0):
            raise ValueError("quorum_ratio must be in (0.5, 1.0]")
        self.genome = genome or ConstitutionalGenome()
        self.swarm_members = tuple(swarm_members)
        self.quorum_ratio = quorum_ratio
        self._blocks: list[DLTSwarmBlock] = []

    @property
    def blocks(self) -> tuple[DLTSwarmBlock, ...]:
        return tuple(self._blocks)

    def commit_governance_event(
        self,
        *,
        epoch: int,
        proposer_id: str,
        approver_ids: tuple[str, ...],
        payload: dict[str, Any],
    ) -> DLTSwarmBlock:
        """Append a quorum-approved governance record; blocks self-approval and epoch replay."""
        if proposer_id not in self.swarm_members:
            raise EpigeneticFaultError(f"unknown swarm proposer: {proposer_id!r}")
        if self._blocks and epoch <= self._blocks[-1].epoch:
            raise EpigeneticFaultError(
                f"DLT epoch replay blocked: {epoch} <= {self._blocks[-1].epoch}"
            )
        # Filter to valid distinct members strictly excluding proposer (no self-approval).
        valid_approvers = tuple(
            sorted({a for a in approver_ids if a in self.swarm_members and a != proposer_id})
        )
        required = math.ceil((len(self.swarm_members) - 1) * self.quorum_ratio)
        if len(valid_approvers) < max(1, required):
            raise EpigeneticFaultError(
                f"DLT quorum not reached: {len(valid_approvers)} < {max(1, required)} independent approvers"
            )
        prev_hash = self._blocks[-1].block_hash if self._blocks else "GENESIS"
        payload_digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, allow_nan=False).encode("utf-8")
        ).hexdigest()
        ts = time.time()
        height = len(self._blocks) + 1
        genome_sha = self.genome.genome_sha256()
        body = json.dumps(
            {
                "height": height,
                "epoch": epoch,
                "genome_sha256": genome_sha,
                "prev_hash": prev_hash,
                "proposer_id": proposer_id,
                "approver_ids": list(valid_approvers),
                "quorum_ratio": self.quorum_ratio,
                "payload_digest": payload_digest,
                "timestamp": ts,
            },
            sort_keys=True,
            allow_nan=False,
        )
        block_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
        block = DLTSwarmBlock(
            height=height,
            epoch=epoch,
            genome_sha256=genome_sha,
            prev_hash=prev_hash,
            proposer_id=proposer_id,
            approver_ids=valid_approvers,
            quorum_ratio=self.quorum_ratio,
            payload_digest=payload_digest,
            timestamp=ts,
            block_hash=block_hash,
        )
        self._blocks.append(block)
        return block

    def verify_chain(self) -> bool:
        expected_genome = self.genome.genome_sha256()
        prev = "GENESIS"
        prev_epoch = 0
        for idx, blk in enumerate(self._blocks, start=1):
            if blk.height != idx or blk.prev_hash != prev or blk.genome_sha256 != expected_genome:
                return False
            if blk.epoch <= prev_epoch or blk.proposer_id in blk.approver_ids:
                return False
            body = json.dumps(
                {
                    "height": blk.height,
                    "epoch": blk.epoch,
                    "genome_sha256": blk.genome_sha256,
                    "prev_hash": blk.prev_hash,
                    "proposer_id": blk.proposer_id,
                    "approver_ids": list(blk.approver_ids),
                    "quorum_ratio": blk.quorum_ratio,
                    "payload_digest": blk.payload_digest,
                    "timestamp": blk.timestamp,
                },
                sort_keys=True,
                allow_nan=False,
            )
            if hashlib.sha256(body.encode("utf-8")).hexdigest() != blk.block_hash:
                return False
            prev = blk.block_hash
            prev_epoch = blk.epoch
        return True


class IoNTCellularNodeTwin:
    """Strictly sandboxed Digital Twin of one SPEACE Macro Mini IoNT cellular node (Phase P1)."""

    def __init__(
        self, profile: IoNTNodeProfile, *, genome: ConstitutionalGenome | None = None
    ) -> None:
        if not profile.sandboxed:
            raise EpigeneticFaultError("IoNTCellularNodeTwin must run with sandboxed=True")
        self.profile = profile
        self.ledger = DLTSwarmLedger(genome=genome, quorum_ratio=profile.dlt_quorum_ratio)
        self._epoch = 0

    def run_advisory_cycle(
        self,
        *,
        proposer_id: str = "agent-plan",
        approver_ids: tuple[str, ...] = ("agent-sense", "agent-safety", "agent-audit"),
        sevo: float = 2.2,
        semantic_entropy_drift: float = 0.015,
    ) -> tuple[IoNTNodeAssessment, TransitionVerdict, bool]:
        """Run one sandboxed advisory cycle: evaluate node -> assess phase -> commit DLT record."""
        assessment = assess_iont_cellular_node(self.profile)
        telemetry = build_iont_node_telemetry_bridge(
            self.profile,
            timescale_decoupling_ratio=15.0,
            autocatalytic_k=1.35,
            independent_validation_rate=0.97,
            semantic_entropy_drift=semantic_entropy_drift,
            net_verified_improvement=0.04,
            consecutive_verified_cycles=4,
            sevo=sevo,
            sevo_window_mean=sevo,
        )
        verdict = PhaseTransitionEvaluator().evaluate(telemetry)
        self._epoch += 1
        self.ledger.commit_governance_event(
            epoch=self._epoch,
            proposer_id=proposer_id,
            approver_ids=approver_ids,
            payload={
                "node_id": self.profile.node_id,
                "admitted": assessment.admitted_for_mcp_advisory,
                "stage": verdict.stage,
                "d_allo": assessment.estimated_allopoietic_dependence,
            },
        )
        return assessment, verdict, self.ledger.verify_chain()
