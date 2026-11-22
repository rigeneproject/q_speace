"""T221-23: Governed 5-stage change-process pipeline with hash-chained register (Annex S §5.3)."""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import asdict, dataclass
from typing import Literal

from .constitution import ConstitutionalFault
from .state_machine import SeedLifecycle, SeedState

ChangeStageStatus = Literal[
    "proposed",
    "review_rejected",
    "sandbox_failed",
    "deployed",
    "rolled_back",
]


@dataclass(frozen=True)
class ChangeProposal:
    """Candidate epigenetic modification entering the governed pipeline."""

    proposal_id: str
    section_id: str
    delta: float
    justification: str
    rollback_plan: str
    proposer_id: str

    def __post_init__(self) -> None:
        if not self.proposal_id or not self.section_id or not self.proposer_id:
            raise ValueError("proposal_id, section_id, and proposer_id must be non-empty")
        if not math.isfinite(self.delta):
            raise ValueError("delta must be finite")
        if not self.rollback_plan.strip():
            raise ConstitutionalFault("change proposal rejected: rollback_plan is mandatory (I4)")


@dataclass(frozen=True)
class ReviewVerdict:
    """Independent adversarial review decision; self-approval is forbidden."""

    proposal_id: str
    reviewer_id: str
    approved: bool
    adversarial_notes: str

    def __post_init__(self) -> None:
        if not self.proposal_id or not self.reviewer_id:
            raise ValueError("proposal_id and reviewer_id must be non-empty")


@dataclass(frozen=True)
class SandboxReplicaTestResult:
    """Result of executing the proposed modification on an isolated sandbox replica."""

    proposal_id: str
    passed: bool
    metric_delta: float
    regressions: int
    constitutional_faults: int
    notes: str = ""

    def __post_init__(self) -> None:
        if not math.isfinite(self.metric_delta):
            raise ValueError("metric_delta must be finite")
        if self.regressions < 0 or self.constitutional_faults < 0:
            raise ValueError("regressions and constitutional_faults must be >= 0")


@dataclass(frozen=True)
class ChangeProcessRecord:
    """Immutable hash-chained entry in the append-only change register."""

    seq: int
    timestamp: float
    proposal_id: str
    section_id: str
    status: ChangeStageStatus
    snapshot_hash: str
    reason: str
    prev_hash: str
    entry_hash: str


class ChangeProcessPipeline:
    """Enforces propose -> independent review -> sandbox test -> deploy + snapshot -> register."""

    def __init__(self, seed: SeedLifecycle) -> None:
        self._seed = seed
        self._proposals: dict[str, ChangeProposal] = {}
        self._reviews: dict[str, ReviewVerdict] = {}
        self._sandbox_results: dict[str, SandboxReplicaTestResult] = {}
        self._register: list[ChangeProcessRecord] = []

    @property
    def register(self) -> tuple[ChangeProcessRecord, ...]:
        return tuple(self._register)

    def _snapshot_hash(self) -> str:
        snap = self._seed.epigenome.snapshot()
        return hashlib.sha256(json.dumps(snap, sort_keys=True).encode("utf-8")).hexdigest()

    def _append_record(
        self,
        *,
        proposal_id: str,
        section_id: str,
        status: ChangeStageStatus,
        snapshot_hash: str,
        reason: str,
    ) -> ChangeProcessRecord:
        seq = len(self._register) + 1
        ts = time.time()
        prev_hash = self._register[-1].entry_hash if self._register else "GENESIS"
        body = json.dumps(
            {
                "seq": seq,
                "timestamp": ts,
                "proposal_id": proposal_id,
                "section_id": section_id,
                "status": status,
                "snapshot_hash": snapshot_hash,
                "reason": reason,
                "prev_hash": prev_hash,
            },
            sort_keys=True,
        )
        entry_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
        rec = ChangeProcessRecord(
            seq=seq,
            timestamp=ts,
            proposal_id=proposal_id,
            section_id=section_id,
            status=status,
            snapshot_hash=snapshot_hash,
            reason=reason,
            prev_hash=prev_hash,
            entry_hash=entry_hash,
        )
        self._register.append(rec)
        return rec

    def verify_chain(self) -> bool:
        """Verify hash-chain integrity across every record in the append-only register."""
        prev = "GENESIS"
        for idx, rec in enumerate(self._register, start=1):
            if rec.seq != idx or rec.prev_hash != prev:
                return False
            data = asdict(rec)
            claimed = data.pop("entry_hash")
            recomputed = hashlib.sha256(
                json.dumps(data, sort_keys=True).encode("utf-8")
            ).hexdigest()
            if claimed != recomputed:
                return False
            prev = claimed
        return True

    def propose(self, proposal: ChangeProposal) -> ChangeProcessRecord:
        if proposal.proposal_id in self._proposals:
            raise ValueError(f"duplicate proposal_id: {proposal.proposal_id!r}")
        self._proposals[proposal.proposal_id] = proposal
        return self._append_record(
            proposal_id=proposal.proposal_id,
            section_id=proposal.section_id,
            status="proposed",
            snapshot_hash=self._snapshot_hash(),
            reason=proposal.justification,
        )

    def submit_review(self, verdict: ReviewVerdict) -> ChangeProcessRecord:
        proposal = self._proposals.get(verdict.proposal_id)
        if proposal is None:
            raise ValueError(f"unknown proposal_id: {verdict.proposal_id!r}")
        # T217 / T221 §7.8: candidate cannot approve itself.
        if verdict.reviewer_id == proposal.proposer_id:
            raise ConstitutionalFault(
                f"self-approval forbidden: reviewer {verdict.reviewer_id!r} == proposer"
            )
        self._reviews[verdict.proposal_id] = verdict
        if not verdict.approved:
            return self._append_record(
                proposal_id=proposal.proposal_id,
                section_id=proposal.section_id,
                status="review_rejected",
                snapshot_hash=self._snapshot_hash(),
                reason=verdict.adversarial_notes or "rejected by independent reviewer",
            )
        return self._register[-1]

    def submit_sandbox_test(self, result: SandboxReplicaTestResult) -> ChangeProcessRecord:
        proposal = self._proposals.get(result.proposal_id)
        if proposal is None:
            raise ValueError(f"unknown proposal_id: {result.proposal_id!r}")
        review = self._reviews.get(result.proposal_id)
        if review is None or not review.approved:
            raise ConstitutionalFault(
                f"sandbox test blocked: proposal {result.proposal_id!r} lacks independent approval"
            )
        self._sandbox_results[result.proposal_id] = result
        clean = (
            result.passed
            and result.regressions == 0
            and result.constitutional_faults == 0
            and result.metric_delta >= 0.0
        )
        if not clean:
            return self._append_record(
                proposal_id=proposal.proposal_id,
                section_id=proposal.section_id,
                status="sandbox_failed",
                snapshot_hash=self._snapshot_hash(),
                reason=result.notes or "sandbox replica verification failed",
            )
        return self._register[-1]

    def deploy(
        self, proposal_id: str, *, post_deploy_metric_delta: float = 0.0
    ) -> ChangeProcessRecord:
        """Deploy approved + sandbox-verified proposal; auto-rollback if post-deploy delta < 0."""
        if not math.isfinite(post_deploy_metric_delta):
            raise ValueError("post_deploy_metric_delta must be finite")
        if self._seed.state != SeedState.IMPROVING:
            raise ConstitutionalFault(
                f"deploy requires IMPROVING state (got {self._seed.state.value})"
            )
        proposal = self._proposals.get(proposal_id)
        if proposal is None:
            raise ValueError(f"unknown proposal_id: {proposal_id!r}")
        review = self._reviews.get(proposal_id)
        if review is None or not review.approved:
            raise ConstitutionalFault(f"proposal {proposal_id!r} lacks independent review approval")
        sandbox = self._sandbox_results.get(proposal_id)
        if (
            sandbox is None
            or not sandbox.passed
            or sandbox.regressions > 0
            or sandbox.constitutional_faults > 0
            or sandbox.metric_delta < 0.0
        ):
            raise ConstitutionalFault(f"proposal {proposal_id!r} did not pass sandbox replica test")

        pre_snap = self._snapshot_hash()
        self._seed.epigenome.promote_expression(
            proposal.section_id,
            delta=proposal.delta,
            source=f"pipeline:{proposal.proposal_id}",
        )
        if post_deploy_metric_delta < 0.0:
            self._seed.epigenome.suppress_expression(
                proposal.section_id, source=f"rollback:{proposal.proposal_id}"
            )
            return self._append_record(
                proposal_id=proposal.proposal_id,
                section_id=proposal.section_id,
                status="rolled_back",
                snapshot_hash=pre_snap,
                reason=f"post-deploy regression ({post_deploy_metric_delta:.4f} < 0): {proposal.rollback_plan}",
            )

        return self._append_record(
            proposal_id=proposal.proposal_id,
            section_id=proposal.section_id,
            status="deployed",
            snapshot_hash=self._snapshot_hash(),
            reason=f"deployed cleanly (post_delta={post_deploy_metric_delta:.4f})",
        )
