"""Bridge-v0 independent validator (T218-T03, BR-03).

Implements the validation trust boundary of spec §4.3:

* each validator generation holds its own secret key and fencing
  number; attestations are HMAC-SHA256 signatures over
  ``(proposal_id, param_hash, base_epoch)``;
* attestation forgery by the proposer is infeasible without the
  validator key (proposer compromise alone cannot bypass validation);
* the proposer cannot saturate the validator: ``attest`` enforces a
  bounded evaluation budget and raises on exhaustion;
* promotion to a successor validator fences out the previous
  generation's key.

Out of threat model (declared): simultaneous compromise of all
authorities (validator key + policy owner + maintenance account).

BCEL: HMAC signing and budgeted verification are *functional*
cryptographic and resource rules. "Independent validation" is an
architectural separation, not a cognitive or moral faculty.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .protocol import FencingError, StateError, UpdateLedger, UpdateProposal


class ValidationBudgetExhaustedError(StateError):
    """The proposer tried to saturate the validator; request refused."""


@dataclass(frozen=True)
class ValidatorKey:
    """One validator generation: secret key + monotonic fencing number."""

    generation: int
    key: bytes


def attestation_digest(proposal: UpdateProposal, key: bytes, *, extra: str = "") -> str:
    """HMAC-SHA256 over the canonical proposal fields."""
    payload = json.dumps(
        {
            "proposal_id": proposal.proposal_id,
            "base_epoch": proposal.base_epoch,
            "param_hash": proposal.param_hash,
            "scope": list(proposal.scope),
            "expiry": proposal.expiry,
            "extra": extra,
        },
        sort_keys=True,
    )
    return hmac.new(key, payload.encode("utf-8"), hashlib.sha256).hexdigest()


class IndependentValidator:
    """Checks candidate updates against the plant model and policy.

    The validator is the only component authorised to attest that a
    candidate update is physically admissible. It evaluates the
    candidate under a caller-supplied plant check (simulator or closed
    form) within a strict evaluation budget.
    """

    def __init__(
        self,
        key: ValidatorKey,
        *,
        max_eval_seconds: float = 0.5,
        max_evals: int = 32,
    ) -> None:
        if key.generation < 1:
            raise ValueError("generation must be >= 1")
        if max_eval_seconds <= 0.0 or max_evals < 1:
            raise ValueError("validator budget must be positive")
        self._key = key
        self._max_eval_seconds = max_eval_seconds
        self._max_evals = max_evals
        self._evals_used = 0

    @property
    def generation(self) -> int:
        return self._key.generation

    def attest(
        self,
        proposal: UpdateProposal,
        *,
        epoch: int,
        plant_check: Callable[[UpdateProposal], bool],
    ) -> str:
        """Evaluate the candidate and return a signed attestation.

        Raises :class:`ValidationBudgetExhaustedError` if the evaluation
        budget (time or call count) is exhausted — a saturation attempt
        is refused, never silently absorbed.
        """
        if epoch != proposal.base_epoch:
            raise StateError("candidate must be re-validated on the current policy epoch")
        if self._evals_used >= self._max_evals:
            raise ValidationBudgetExhaustedError("call budget exhausted")
        start = time.monotonic()
        ok = bool(plant_check(proposal))
        elapsed = time.monotonic() - start
        self._evals_used += 1
        if elapsed > self._max_eval_seconds:
            raise ValidationBudgetExhaustedError(
                f"plant check took {elapsed:.3f}s > budget {self._max_eval_seconds}s"
            )
        extra = "ok" if ok else "reject"
        return attestation_digest(proposal, self._key.key, extra=extra)

    def authorize(self, proposal: UpdateProposal, attest: str, epoch: int, fencing: int) -> None:
        """Mandatory ledger callback; only an acceptance from this generation admits work."""
        if fencing != self.generation:
            raise FencingError("activation fencing must match the verifier generation")
        if epoch != proposal.base_epoch or epoch > proposal.expiry:
            raise StateError("attestation is outside its policy epoch or expiry")
        if not self.verify(proposal, attest, expected_ok=True):
            raise StateError("activation attestation is forged, negative, or stale")

    def verify(
        self,
        proposal: UpdateProposal,
        attest: str,
        *,
        expected_ok: bool = True,
    ) -> bool:
        """Verify an attestation against this generation's key."""
        extra = "ok" if expected_ok else "reject"
        expected = attestation_digest(proposal, self._key.key, extra=extra)
        return hmac.compare_digest(attest, expected)


def authorize_activation(
    ledger: UpdateLedger,
    proposal: UpdateProposal,
    attest: str,
    validator: IndependentValidator,
    *,
    epoch: int,
) -> None:
    """Ledger-side authorization gate before activation.

    The ledger refuses activation unless the attestation verifies under
    the *current* validator generation's key. A proposer presenting a
    forged attestation, or one signed by a fenced-out generation, is
    rejected — the bypass must go through the administrative plane,
    which is outside this module's threat model but inside the ledger's
    fencing counter.
    """
    if validator.generation < ledger.fencing:
        raise FencingError(
            f"validator generation {validator.generation} " f"< ledger fencing {ledger.fencing}"
        )
    if not validator.verify(proposal, attest, expected_ok=True):
        raise StateError(
            f"attestation for {proposal.proposal_id} failed verification: "
            "forged, stale-generation, or reject-attestation"
        )


def promote_successor(
    ledger: UpdateLedger,
    new_key: ValidatorKey,
    *,
    epoch: int,
) -> IndependentValidator:
    """Promote a successor validator and fence out the current one."""
    ledger.promote_validator(new_key.generation, epoch=epoch)
    return IndependentValidator(new_key)


# ---------------------------------------------------------------------------
# T245: Process-Isolated Preemptive Validator (T218 §13)
# ---------------------------------------------------------------------------

_ALLOWED_CHECK_MODULE_PREFIXES: tuple[str, ...] = ("q_speace.",)

_WORKER_BOOTSTRAP_CODE = (
    "import importlib, json, sys; "
    "req = json.loads(sys.stdin.read()); "
    "mod = importlib.import_module(req['module']); "
    "fn = getattr(mod, req['func']); "
    "ok = bool(fn(req['proposal'])); "
    "sys.stdout.write(json.dumps({'ok': ok}))"
)


def _demo_plant_ok(_proposal: dict[str, Any]) -> bool:
    """Reference deterministic admissible plant check for isolated worker verification."""
    return True


def _demo_plant_reject(_proposal: dict[str, Any]) -> bool:
    """Reference deterministic rejecting plant check for isolated worker verification."""
    return False


def _demo_plant_hang(_proposal: dict[str, Any]) -> bool:
    """Reference hanging plant check used to verify OS-level preemptive termination."""
    time.sleep(30.0)
    return True


class ProcessIsolatedValidator(IndependentValidator):
    """Validator executing untrusted plant checks in a separate OS child process (T245).

    Key security properties:
      * ``ValidatorKey.key`` never leaves the parent process address space or env.
      * Hanging plant checks are preemptively terminated by the OS after ``max_eval_seconds``.
      * Only allowlisted ``q_speace.*`` check targets may be imported in the worker.
    """

    def attest_isolated(
        self,
        proposal: UpdateProposal,
        *,
        epoch: int,
        check_target: str,
        allowed_prefixes: tuple[str, ...] = _ALLOWED_CHECK_MODULE_PREFIXES,
    ) -> str:
        """Run ``check_target`` ('module.path:func_name') in an isolated child process and sign."""
        if epoch != proposal.base_epoch:
            raise StateError("candidate must be re-validated on the current policy epoch")
        if self._evals_used >= self._max_evals:
            raise ValidationBudgetExhaustedError("call budget exhausted")
        if ":" not in check_target:
            raise ValueError(f"check_target must be 'module:func' (got {check_target!r})")
        module_name, func_name = check_target.split(":", 1)
        if not module_name or not func_name or not module_name.startswith(allowed_prefixes):
            raise ValueError(f"check_target module not in allowlist: {module_name!r}")

        payload = json.dumps(
            {
                "module": module_name,
                "func": func_name,
                "proposal": {
                    "proposal_id": proposal.proposal_id,
                    "base_epoch": proposal.base_epoch,
                    "param_hash": proposal.param_hash,
                    "scope": list(proposal.scope),
                    "expiry": proposal.expiry,
                },
            },
            sort_keys=True,
            allow_nan=False,
        )
        self._evals_used += 1
        try:
            proc = subprocess.run(
                [sys.executable, "-c", _WORKER_BOOTSTRAP_CODE],
                input=payload,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=self._max_eval_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ValidationBudgetExhaustedError(
                f"preemptive timeout: isolated plant check killed after {self._max_eval_seconds:.3f}s"
            ) from exc

        if proc.returncode != 0:
            raise StateError(
                f"isolated validator worker failed (rc={proc.returncode}): {proc.stderr.strip()[:200]}"
            )
        try:
            verdict = json.loads(proc.stdout)
            ok = bool(verdict["ok"])
        except (ValueError, KeyError, TypeError) as exc:
            raise StateError(f"malformed isolated worker verdict: {exc}") from exc

        extra = "ok" if ok else "reject"
        return attestation_digest(proposal, self._key.key, extra=extra)
