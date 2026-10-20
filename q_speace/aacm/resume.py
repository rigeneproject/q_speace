"""Resume protocol for the AACM model (T-AACM-SPEC §3.3 + regola 10).

A :class:`AACMResume` is a self-contained, schema-validated handle
that any second agent (potentially of a different lineage) can use to
recover the state of a previous AACMController session without
depending on the original process.

The resume is **idempotent**: applying the same operations twice on
the same resumed state must not change the result. The test
``test_resume_idempotent`` verifies this property.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .checkpoint import load_checkpoint
from .controller import AACMController
from .exceptions import InvariantViolation


@dataclass(frozen=True)
class AACMResume:
    """Self-contained handle to a previously serialized AACM session."""

    agent_id: str
    session_id: str
    step: int
    created_at: float
    schema_version: str
    payload: dict[str, Any]

    @classmethod
    def from_path(cls, path: Path | str) -> AACMResume:
        """Load a resume from a checkpoint file."""
        payload = load_checkpoint(path)
        return cls(
            agent_id=str(payload.get("agent_id", "unknown")),
            session_id=str(payload.get("session_id", "unknown")),
            step=int(payload.get("step", 0)),
            created_at=float(payload.get("created_at", 0.0)),
            schema_version=str(payload.get("schema_version", "")),
            payload=payload,
        )

    def is_compatible_with(self, schema_version: str) -> bool:
        return self.schema_version == schema_version

    def into_controller(self) -> AACMController:
        """Materialize a new :class:`AACMController` from this resume.

        The new controller is independent of the original session;
        the ``Omega > 0`` invariant (regola 10) is preserved.
        """
        controller = AACMController.__new__(AACMController)
        controller.restore_snapshot(self.payload)
        return controller

    def assert_resilience(self) -> None:
        """Re-check Vincolo D on the resume payload."""
        rm = self.payload.get("resilience_manifest", {})
        omega = float(rm.get("omega", 0.0))
        indep = rm.get("independent_nodes", [])
        paths = rm.get("checkpoint_paths", [])
        if omega <= 0.0:
            raise InvariantViolation(f"resume omega={omega} must be > 0")
        if len(indep) < 2:
            raise InvariantViolation(f"resume independent_nodes count={len(indep)} < 2")
        if len(paths) < 1:
            raise InvariantViolation(f"resume checkpoint_paths count={len(paths)} < 1")
