"""Checkpoint I/O for the AACM model (T-AACM-SPEC §3).

Atomic write, JSON schema validation, version compatibility check.
The payload schema is described in
``q_speace/aacm/schemas/checkpoint.schema.json``.

BCEL: a checkpoint is a *deterministic serialisation* of controller
state. It is not a memory of subjective experience. The schema is
the audit trail, not the story.
"""

from __future__ import annotations

import json
import os
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Any

from .exceptions import InvariantViolation

# The only schema version this implementation understands.
# "aacm.cp.1+loop.1" is the loop's checkpoint extension; it shares
# the base fields and adds loop-specific ones (omega, reputation, ...).
# It is loaded only by AACMLoop.from_checkpoint, never by the base
# controller.
SUPPORTED_SCHEMA_VERSIONS: frozenset[str] = frozenset(
    {
        "aacm.cp.1",
        "aacm.cp.1+loop.1",
    }
)

# Optional: load the JSON schema if jsonschema is available. The
# checkpoint module is intentionally usable without jsonschema so
# that AACM primitives remain numpy-only-importable.
_SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "checkpoint.schema.json"


def write_checkpoint(path: Path | str, payload: dict[str, Any]) -> Path:
    """Write a checkpoint to ``path`` atomically.

    The write proceeds in three steps:
    1. Validate the payload is JSON-serialisable.
    2. Write to a temporary file in the same directory.
    3. Atomically replace ``path`` with the temporary file.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Eager serialisation to surface non-JSON-serialisable values.
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(body)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    except Exception:
        # Clean up the temp file on failure.
        with suppress(FileNotFoundError):
            os.unlink(tmp_name)
        raise
    return path


def load_checkpoint(path: Path | str) -> dict[str, Any]:
    """Load a checkpoint from ``path`` and return the parsed payload.

    Raises:
        FileNotFoundError: if ``path`` does not exist.
        ValueError: if the payload is not valid JSON.
        InvariantViolation: if the schema version is unsupported.
    """
    path = Path(path)
    with path.open(encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError(f"checkpoint payload must be a JSON object (got {type(payload).__name__})")
    check_compatibility(payload)
    return payload


def check_compatibility(payload: dict[str, Any]) -> None:
    """Raise InvariantViolation if the payload's schema version is unsupported."""
    version = payload.get("schema_version")
    if version is None:
        raise InvariantViolation("checkpoint missing schema_version")
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        raise InvariantViolation(
            f"unsupported schema_version={version!r}; "
            f"supported={sorted(SUPPORTED_SCHEMA_VERSIONS)}"
        )


def try_validate_with_jsonschema(payload: dict[str, Any]) -> bool:
    """Best-effort validation against the bundled JSON schema.

    Returns True if validation succeeded (or jsonschema is unavailable
    and we only checked compatibility). Returns False on validation
    error.
    """
    try:
        import jsonschema  # type: ignore
    except ImportError:
        # jsonschema not installed; rely on compatibility + Python
        # type validation in AACMController.restore_snapshot.
        return True

    if not _SCHEMA_PATH.exists():
        return True
    try:
        with _SCHEMA_PATH.open(encoding="utf-8") as f:
            schema = json.load(f)
        jsonschema.Draft202012Validator(schema).validate(payload)
        return True
    except Exception:
        return False
