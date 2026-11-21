"""Bridge-v0 update protocol (T218-T01, BR-01).

Implements the distributed update state machine required by
``docs/T218_QSPEACE_V0_BRIDGE_SPEC.md`` §4.2:

* ``UpdateProposal`` — the versioned proposal record (BR-01 schema).
* ``UpdateLedger`` — journal-first persistent state machine with
  idempotent application, epoch fencing and crash recovery.
* ``CoupledCommit`` — two-phase commit for coupled proposals whose
  independently-safe local combinations may be jointly unsafe
  (the 0.4 + 0.15 x2 > 1.0 counterexample of the peer review R3).

State machine:

    PROPOSED -> VALIDATED -> ACTIVATED   (terminal)
    PROPOSED -> REJECTED                  (terminal)
    VALIDATED -> EXPIRED                  (terminal)
    VALIDATED -> ABORTED                  (terminal)

BCEL: the state machine is *functional* — it is a deterministic finite
automaton over signed records. "Fencing" is a monotonic epoch counter,
not a biological immune metaphor; no claim of cognition is implied.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

import numpy as np


class ProtocolError(Exception):
    """Base error for the Bridge-v0 update protocol."""


class IdempotencyError(ProtocolError):
    """Same proposal_id re-submitted with a different parameter hash."""


class StateError(ProtocolError):
    """Transition requested from an incompatible state."""


class FencingError(ProtocolError):
    """A stale authority (old fencing epoch) attempted to act."""


class ExpiryError(ProtocolError):
    """Activation attempted after the proposal's expiry."""


class UpdateStatus(StrEnum):
    PROPOSED = "PROPOSED"
    VALIDATED = "VALIDATED"
    ACTIVATED = "ACTIVATED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    ABORTED = "ABORTED"
    PREPARED = "PREPARED"


_TERMINAL = frozenset(
    {
        UpdateStatus.ACTIVATED,
        UpdateStatus.REJECTED,
        UpdateStatus.EXPIRED,
        UpdateStatus.ABORTED,
    }
)


@dataclass(frozen=True)
class UpdateProposal:
    """Versioned proposal record (BR-01).

    Attributes
    ----------
    proposal_id:
        Unique identifier (UUIDv4 recommended). Idempotency key.
    base_epoch:
        Policy epoch the proposal was validated against. Activation on a
        different epoch is refused.
    param_hash:
        SHA-256 of the candidate parameter vector. Two records with the
        same ``proposal_id`` but different ``param_hash`` are a protocol
        violation, never a silent overwrite.
    scope:
        Cells touched by the proposal. More than one cell marks it as a
        *coupled* update that must use :class:`CoupledCommit`.
    dependencies:
        ``proposal_id`` values that must activate in the same epoch.
    validation_attest:
        Attestation issued by the independent validator (T218-T03).
    expiry:
        Deadline epoch for activation.
    """

    proposal_id: str
    base_epoch: int
    param_hash: str
    scope: tuple[str, ...]
    dependencies: tuple[str, ...]
    validation_attest: str
    expiry: int

    @staticmethod
    def new_id() -> str:
        return str(uuid.uuid4())

    @property
    def is_coupled(self) -> bool:
        return len(self.scope) > 1 or bool(self.dependencies)


def canonical_param_hash(p_cand: np.ndarray) -> str:
    """IEEE 754 canonical SHA-256 of a candidate parameter vector.

    Hashing raw in-memory floats exposes idempotency to false failures:
    ``-0.0`` vs ``+0.0`` hash differently, and last-bit (ULP) rounding
    drift after a projection would break the ``same hash ⇒ no-op``
    rule. Declared canonicalisation before hashing:

    1. quantise each coordinate onto the fixed grid ``round(p, 9)``;
    2. normalise signed zeros (``±0.0`` → ``+0.0``);
    3. serialise big-endian ``>f8`` (platform-independent byte order).

    The result is stable across platforms and across the two runs of a
    reproducibility test.
    """
    arr = np.asarray(p_cand, dtype=np.float64)
    if arr.ndim != 1:
        raise ValueError("parameter vector must be 1-D")
    quantised = np.round(arr, 9)
    normalised = np.where(np.abs(quantised) == 0.0, 0.0, quantised)
    payload = np.asarray(normalised, dtype=">f8").tobytes()
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class JournalRecord:
    """Append-only record; persisted as JSON lines before any state change."""

    epoch: int
    event: str
    proposal_id: str
    param_hash: str
    fencing: int
    detail: str


@dataclass
class _ProposalState:
    status: UpdateStatus
    proposal: UpdateProposal | None
    prepared_for_commit: str | None = None
    activated_in_epoch: int | None = None
    tags: dict[str, str] = field(default_factory=dict)


def _dump(rec: JournalRecord) -> str:
    return json.dumps(
        {
            "epoch": rec.epoch,
            "event": rec.event,
            "proposal_id": rec.proposal_id,
            "param_hash": rec.param_hash,
            "fencing": rec.fencing,
            "detail": rec.detail,
        },
        sort_keys=True,
    )


def _load(line: str) -> JournalRecord:
    d = json.loads(line)
    return JournalRecord(**d)


def _proposal_from_body(body: dict[str, Any]) -> UpdateProposal:
    return UpdateProposal(
        proposal_id=str(body["proposal_id"]),
        base_epoch=int(body["base_epoch"]),
        param_hash=str(body["param_hash"]),
        scope=tuple(body["scope"]),
        dependencies=tuple(body["dependencies"]),
        validation_attest=str(body["validation_attest"]),
        expiry=int(body["expiry"]),
    )


class UpdateLedger:
    """Journal-first state machine for Bridge-v0 proposals.

    Every state transition is appended to the journal *before* the
    in-memory state is advanced, so a crash between the two steps is
    recovered by replaying the journal (at-most-once activation).
    """

    def __init__(
        self,
        path: str | os.PathLike[str] | None = None,
        *,
        activation_authorizer: Callable[[UpdateProposal, str, int, int], None] | None = None,
    ) -> None:
        self._activation_authorizer = activation_authorizer
        self._path = Path(path) if path is not None else None
        self._records: list[JournalRecord] = []
        self._state: dict[str, _ProposalState] = {}
        self._proposals: dict[str, UpdateProposal] = {}
        self._fencing = 0
        if self._path is not None and self._path.exists():
            self._replay()

    # ------------------------------------------------------------------ #
    # journal plumbing
    # ------------------------------------------------------------------ #
    def _append(
        self,
        epoch: int,
        event: str,
        proposal_id: str,
        param_hash: str,
        fencing: int,
        detail: str,
    ) -> None:
        rec = JournalRecord(
            epoch=epoch,
            event=event,
            proposal_id=proposal_id,
            param_hash=param_hash,
            fencing=fencing,
            detail=detail,
        )
        if self._path is not None:
            with open(self._path, "a", encoding="utf-8") as fh:
                fh.write(_dump(rec) + "\n")
        self._records.append(rec)

    def _replay(self) -> None:
        assert self._path is not None
        bodies: dict[str, dict[str, Any]] = {}
        body_path = self._path.with_suffix(".bodies.json")
        if body_path.exists():
            bodies = json.loads(body_path.read_text(encoding="utf-8"))
        with open(self._path, encoding="utf-8") as fh:
            lines = [ln for ln in fh.read().splitlines() if ln.strip()]
        for line in lines:
            rec = _load(line)
            self._records.append(rec)
            body = bodies.get(rec.proposal_id)
            if (
                rec.event == "SUBMITTED"
                and body is not None
                and rec.proposal_id not in self._proposals
            ):
                self._proposals[rec.proposal_id] = _proposal_from_body(body)
            self._apply_record(rec)

    def _apply_record(self, rec: JournalRecord) -> None:
        st = self._state.get(rec.proposal_id)
        if st is None:
            if rec.event == "SUBMITTED":
                body = self._proposals.get(rec.proposal_id)
                self._state[rec.proposal_id] = _ProposalState(
                    status=UpdateStatus.PROPOSED,
                    proposal=body,
                )
            elif rec.event == "PROMOTED":
                self._fencing = max(self._fencing, rec.fencing)
            return
        if rec.event == "VALIDATED":
            st.status = UpdateStatus.VALIDATED
            if rec.detail:
                st.tags["latest_attest"] = rec.detail
        elif rec.event == "ACTIVATED":
            st.status = UpdateStatus.ACTIVATED
            st.activated_in_epoch = rec.epoch
        elif rec.event == "REJECTED":
            st.status = UpdateStatus.REJECTED
        elif rec.event == "EXPIRED":
            st.status = UpdateStatus.EXPIRED
        elif rec.event == "ABORTED":
            st.status = UpdateStatus.ABORTED
        elif rec.event == "PREPARED":
            st.status = UpdateStatus.PREPARED
            st.prepared_for_commit = rec.detail
        elif rec.event == "PROMOTED":
            self._fencing = max(self._fencing, rec.fencing)

    # ------------------------------------------------------------------ #
    # transitions
    # ------------------------------------------------------------------ #
    def submit(self, proposal: UpdateProposal, *, epoch: int) -> UpdateStatus:
        """Register a proposal. Idempotent on (proposal_id, param_hash)."""
        st = self._state.get(proposal.proposal_id)
        if st is not None:
            if st.proposal is not None and st.proposal.param_hash != proposal.param_hash:
                raise IdempotencyError(
                    f"{proposal.proposal_id} already exists with a different param_hash"
                )
            return st.status
        if self._path is not None:
            # Persist the body so crash recovery can rebuild it verbatim.
            body_path = self._path.with_suffix(".bodies.json")
            bodies: dict[str, dict[str, object]] = {}
            if body_path.exists():
                bodies = json.loads(body_path.read_text(encoding="utf-8"))
            bodies[proposal.proposal_id] = {
                "proposal_id": proposal.proposal_id,
                "base_epoch": proposal.base_epoch,
                "param_hash": proposal.param_hash,
                "scope": list(proposal.scope),
                "dependencies": list(proposal.dependencies),
                "validation_attest": proposal.validation_attest,
                "expiry": proposal.expiry,
            }
            body_path.write_text(json.dumps(bodies, sort_keys=True), encoding="utf-8")
        self._append(epoch, "SUBMITTED", proposal.proposal_id, proposal.param_hash, 0, "")
        self._state[proposal.proposal_id] = _ProposalState(
            status=UpdateStatus.PROPOSED, proposal=proposal
        )
        return UpdateStatus.PROPOSED

    def mark_validated(
        self, proposal_id: str, *, epoch: int, fencing: int, attest: str
    ) -> UpdateStatus:
        st = self._require(proposal_id)
        self._check_active(st, proposal_id)
        if st.status is UpdateStatus.PREPARED:
            pass  # re-attestation of a prepared proposal is allowed
        proposal = self._proposal_of(st, proposal_id)
        if proposal.base_epoch != epoch:
            raise StateError(f"validation epoch {epoch} != base_epoch {proposal.base_epoch}")
        # The ledger records the attestation but does not verify it:
        # cryptographic verification belongs to authorize_activation
        # (validator.py), which holds the validator generation key.
        self._append(epoch, "VALIDATED", proposal_id, proposal.param_hash, fencing, attest)
        st.status = UpdateStatus.VALIDATED
        st.tags["latest_attest"] = attest
        return st.status

    def latest_attest_of(self, proposal_id: str) -> str:
        """Return the most recent attestation recorded for a proposal."""
        st = self._require(proposal_id)
        attest = st.tags.get("latest_attest")
        if attest is None:
            raise StateError(f"{proposal_id} has no recorded attestation")
        return attest

    def activate(self, proposal_id: str, *, epoch: int, fencing: int) -> UpdateStatus:
        """Activate a validated proposal (journal-first, at-most-once)."""
        st = self._require(proposal_id)
        self._check_active(st, proposal_id)
        proposal = self._proposal_of(st, proposal_id)
        if proposal.is_coupled:
            raise StateError("coupled proposals must be activated through CoupledCommit")
        if st.status is not UpdateStatus.VALIDATED:
            raise StateError(f"cannot activate from state {st.status.value}")
        if epoch > proposal.expiry:
            self._append(epoch, "EXPIRED", proposal_id, proposal.param_hash, fencing, "")
            st.status = UpdateStatus.EXPIRED
            raise ExpiryError(f"{proposal_id} expired at {proposal.expiry}")
        if epoch != proposal.base_epoch:
            raise StateError("activation epoch differs from the validated base_epoch")
        if fencing < self._fencing:
            raise FencingError(f"fencing {fencing} < current {self._fencing}: stale authority")
        self._authorize(proposal, self.latest_attest_of(proposal_id), epoch, fencing)
        self._append(epoch, "ACTIVATED", proposal_id, proposal.param_hash, fencing, "")
        st.status = UpdateStatus.ACTIVATED
        st.activated_in_epoch = epoch
        return st.status

    def reject(self, proposal_id: str, *, epoch: int, reason: str) -> UpdateStatus:
        st = self._require(proposal_id)
        self._check_active(st, proposal_id)
        proposal = self._proposal_of(st, proposal_id)
        self._append(epoch, "REJECTED", proposal_id, proposal.param_hash, 0, reason)
        st.status = UpdateStatus.REJECTED
        return st.status

    def expire(self, proposal_id: str, *, epoch: int) -> UpdateStatus:
        st = self._require(proposal_id)
        self._check_active(st, proposal_id)
        proposal = self._proposal_of(st, proposal_id)
        self._append(epoch, "EXPIRED", proposal_id, proposal.param_hash, 0, "")
        st.status = UpdateStatus.EXPIRED
        return st.status

    def abort(self, proposal_id: str, *, epoch: int, reason: str) -> UpdateStatus:
        st = self._require(proposal_id)
        self._check_active(st, proposal_id)
        proposal = self._proposal_of(st, proposal_id)
        self._append(epoch, "ABORTED", proposal_id, proposal.param_hash, 0, reason)
        st.status = UpdateStatus.ABORTED
        return st.status

    def promote_validator(self, fencing: int, *, epoch: int) -> None:
        """Promote a successor validator. Monotonic; older ones are fenced out."""
        if fencing <= self._fencing:
            raise FencingError(f"promoted fencing {fencing} must exceed current {self._fencing}")
        self._append(epoch, "PROMOTED", "", "", fencing, "")
        self._fencing = fencing

    @property
    def fencing(self) -> int:
        return self._fencing

    def _authorize(self, proposal: UpdateProposal, attest: str, epoch: int, fencing: int) -> None:
        if self._activation_authorizer is None:
            raise StateError("activation authorizer is not configured")
        self._activation_authorizer(proposal, attest, epoch, fencing)

    def status_of(self, proposal_id: str) -> UpdateStatus:
        return self._require(proposal_id).status

    def proposal_of(self, proposal_id: str) -> UpdateProposal:
        return self._proposal_of(self._require(proposal_id), proposal_id)

    def records(self) -> tuple[JournalRecord, ...]:
        return tuple(self._records)

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _require(self, proposal_id: str) -> _ProposalState:
        st = self._state.get(proposal_id)
        if st is None:
            raise StateError(f"unknown proposal {proposal_id}")
        return st

    @staticmethod
    def _check_active(st: _ProposalState, proposal_id: str) -> None:
        if st.status in _TERMINAL:
            raise StateError(f"{proposal_id} is terminal ({st.status.value})")

    def _proposal_of(self, st: _ProposalState, proposal_id: str) -> UpdateProposal:
        if st.proposal is None:
            raise StateError(
                f"{proposal_id} was recovered from a truncated journal; "
                "re-submit its body to complete recovery"
            )
        assert st.proposal.proposal_id == proposal_id
        return st.proposal


class CoupledCommit:
    """Two-phase commit over a set of proposals sharing a joint constraint.

    ``prepare`` runs a joint admissibility *check* supplied by the
    independent validator. Proposals are atomically PREPARED (all or
    none). ``commit`` activates all prepared proposals in one epoch or
    aborts the whole set — the partial-activation hazard of review R3 is
    impossible by construction: a coupled set activates together or not
    at all.

    Deadlock prevention (T218 refinement R3): if a peer loses
    observability after VALIDATED but before ACTIVATED, the prepared set
    must not wait for an external coordinator.
    :meth:`expire_on_timeout` is coordinator-free — any surviving peer
    may invoke it — and atomically aborts the whole set once a member's
    expiry has passed, releasing the capacity reserved on the surviving
    cell immediately.
    """

    def __init__(self, ledger: UpdateLedger, coupled_id: str) -> None:
        self._ledger = ledger
        self._coupled_id = coupled_id
        self._members: list[str] = []
        self._reservations: dict[str, float] = {}

    def prepare(
        self,
        proposals: list[UpdateProposal],
        *,
        epoch: int,
        fencing: int,
        check: Callable[[list[UpdateProposal]], bool],
        reservations: dict[str, float] | None = None,
    ) -> bool:
        if self._members:
            raise StateError(f"coupled commit {self._coupled_id} already prepared")
        for p in proposals:
            self._ledger.submit(p, epoch=epoch)
        if not check(proposals):
            for p in proposals:
                self._ledger.abort(p.proposal_id, epoch=epoch, reason="joint check failed")
            return False
        for p in proposals:
            rec_epoch = epoch
            self._ledger._append(
                rec_epoch,
                "PREPARED",
                p.proposal_id,
                p.param_hash,
                fencing,
                self._coupled_id,
            )
            st = self._ledger._state[p.proposal_id]
            st.status = UpdateStatus.PREPARED
            st.prepared_for_commit = self._coupled_id
            self._members.append(p.proposal_id)
        self._reservations = dict(reservations or {})
        return True

    @property
    def reserved_capacity(self) -> dict[str, float]:
        """Capacity currently reserved per member (empty once released)."""
        return dict(self._reservations)

    def commit(self, *, epoch: int, fencing: int) -> list[str]:
        if not self._members:
            raise StateError(f"coupled commit {self._coupled_id} has no prepared members")
        activated: list[str] = []
        for pid in self._members:
            st = self._ledger._require(pid)
            proposal = self._ledger._proposal_of(st, pid)
            if epoch > proposal.expiry:
                self.rollback(epoch)
                raise ExpiryError(f"{pid} expired during coupled commit")
            if fencing < self._ledger.fencing:
                self.rollback(epoch)
                raise FencingError("stale authority during coupled commit")
        # Verify every member before the first activation journal write.
        for pid in self._members:
            st = self._ledger._require(pid)
            proposal = self._ledger._proposal_of(st, pid)
            attest = st.tags.get("latest_attest", proposal.validation_attest)
            self._ledger._authorize(proposal, attest, epoch, fencing)
        for pid in self._members:
            st = self._ledger._require(pid)
            proposal = self._ledger._proposal_of(st, pid)
            self._ledger._append(
                epoch, "ACTIVATED", pid, proposal.param_hash, fencing, self._coupled_id
            )
            st.status = UpdateStatus.ACTIVATED
            st.activated_in_epoch = epoch
            activated.append(pid)
        self._reservations.clear()  # capacity consumed by activation
        return activated

    def rollback(self, epoch: int) -> None:
        for pid in list(self._members):
            st = self._ledger._require(pid)
            proposal = self._ledger._proposal_of(st, pid)
            if st.status is UpdateStatus.ACTIVATED:
                raise StateError("cannot rollback after activation is recorded")
            self._ledger._append(epoch, "ABORTED", pid, proposal.param_hash, 0, "coupled rollback")
            st.status = UpdateStatus.ABORTED
        self._members = []
        self._reservations.clear()  # capacity released immediately

    def expire_on_timeout(self, epoch: int) -> list[str]:
        """Coordinator-free timeout abort of the prepared set.

        Any surviving peer may call this without an external
        coordinator. If any member's expiry has passed, the whole
        prepared set is atomically ABORTED and the reserved capacity on
        the surviving cell is released immediately. Returns the aborted
        member ids (empty when no member has expired). Refuses to run if
        any member was already activated — activation of a coupled set
        is atomic, so a mixed state indicates a protocol violation.
        """
        if not self._members:
            return []
        for pid in self._members:
            st = self._ledger._require(pid)
            if st.status is UpdateStatus.ACTIVATED:
                raise StateError("a coupled member is already activated: timeout abort refused")
        expired = False
        for pid in self._members:
            st = self._ledger._require(pid)
            proposal = self._ledger._proposal_of(st, pid)
            if epoch > proposal.expiry:
                expired = True
        if not expired:
            return []
        aborted = list(self._members)
        self.rollback(epoch)
        return aborted
