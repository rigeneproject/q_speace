"""SignalRouter — convert a DigitalSignal into a SignalKey for lazy lookup.

The router extracts a (region, function) pair from a DigitalSignal's
`meaning` field (e.g. "sensory.visual", "hippocampus.encoding") or
falls back to the signal's source/target region.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from speace_core.cellular_brain.base.digital_signal import DigitalSignal


@dataclass
class SignalKey:
    """A normalized (region, function) pair for lazy lookup."""
    region: str
    function: str
    key: str  # "{region}.{function}"

    @classmethod
    def from_string(cls, s: str) -> "SignalKey":
        if "." in s:
            region, function = s.split(".", 1)
        elif ":" in s:
            region, function = s.split(":", 1)
        else:
            region, function = "generic", s or "processing"
        return cls(region=region.lower(), function=function.lower(), key=f"{region}.{function}")


class SignalRouter:
    """Routes DigitalSignals to (region, function) keys."""

    def __init__(self) -> None:
        self._default_region = "generic"
        self._default_function = "processing"

    def key_from_signal(
        self,
        signal: DigitalSignal,
        target_region: Optional[str] = None,
    ) -> SignalKey:
        """Extract a key from a signal's meaning, with sensible fallbacks."""
        if signal.meaning:
            return SignalKey.from_string(signal.meaning)
        if target_region is not None:
            return SignalKey(region=target_region, function="processing", key=f"{target_region}.processing")
        return SignalKey(
            region=self._default_region,
            function=self._default_function,
            key=f"{self._default_region}.{self._default_function}",
        )

    def set_default(self, region: str, function: str) -> None:
        self._default_region = region
        self._default_function = function
