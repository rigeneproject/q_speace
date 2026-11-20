"""Deterministic section locking for the T222 preregistration.

Spec: ``docs/T222_NCM_CODEC_SPEC.md`` section 6.3 and
``docs/T222_PREREG.json`` -> ``locking_protocol``.

A section is locked independently (not the whole file) so that
``pre_evaluation`` can be completed after calibration without invalidating
``pre_calibration``. The digest covers every field of the section except the
top-level ``lock_sha256`` field itself. Serialization is canonical:

- UTF-8 without BOM;
- ``json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False,
  allow_nan=False)``.

The protocol is a reproducibility aid, not a signature: it detects accidental
or unilateral edits to a locked section, not a malicious rewrite of both the
section and its hash.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Mapping, Sequence
from typing import Any

EXCLUDED_FIELDS: tuple[str, ...] = ("lock_sha256",)


def canonical_json(
    value: Any,
    *,
    excluded_fields: Sequence[str] = EXCLUDED_FIELDS,
) -> str:
    """Serialize a JSON value deterministically for hashing.

    Only top-level keys are excluded. Nested objects are serialized as-is with
    sorted keys, so nested ``lock_sha256`` keys (if any) are not special.
    """
    if isinstance(value, Mapping):
        excluded = set(excluded_fields)
        payload: Any = {str(key): item for key, item in value.items() if str(key) not in excluded}
    else:
        payload = value
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def compute_lock_sha256(section: Mapping[str, Any]) -> str:
    """Return the hex SHA-256 of a canonically serialized section."""
    encoded = canonical_json(section).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def lock_section(section: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copy of ``section`` with ``locked`` set and its digest written.

    The input mapping is not mutated. The digest is computed with the new
    ``locked`` value included and the ``lock_sha256`` field excluded.
    """
    locked = dict(section)
    locked["locked"] = True
    locked["lock_sha256"] = compute_lock_sha256(locked)
    return locked


def verify_lock(section: Mapping[str, Any]) -> bool:
    """Return True when ``lock_sha256`` matches the section content."""
    expected = section.get("lock_sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        return False
    return hmac.compare_digest(expected, compute_lock_sha256(section))
