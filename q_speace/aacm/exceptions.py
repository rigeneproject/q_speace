"""Custom exceptions for the AACM package."""

from __future__ import annotations


class InvariantViolation(ValueError):
    """Raised when an AACM invariant is violated.

    Examples:
        - ``ResilienceManifest.omega < OMEGA_MIN``
        - ``LegitimationChannelRegistry.channels`` count < ``K_MIN``
        - checkpoint schema mismatch
    """
