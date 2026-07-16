"""Optional imports for simulator backends.

Importing brian2, nest, neuron, or pyNN may require native extensions
that are not always installed. This module provides a safe wrapper
that returns None when a backend is unavailable, plus a cached
registry of what's installed.
"""
from __future__ import annotations

import importlib
from functools import lru_cache
from typing import Any, Dict, List, Optional


@lru_cache(maxsize=None)
def optional_import(name: str) -> Optional[Any]:
    """Try to import `name`; cache and return the module or None."""
    try:
        return importlib.import_module(name)
    except Exception:
        return None


def is_available(name: str) -> bool:
    """True iff optional_import(name) returns a module."""
    return optional_import(name) is not None


@lru_cache(maxsize=None)
def available_backends() -> Dict[str, bool]:
    """Return a dict of supported backends and their availability."""
    return {
        "native": True,
        "brian2": is_available("brian2"),
        "nest": is_available("nest"),
        "neuron": is_available("neuron") or is_available("NEURON"),
        "pyNN": is_available("pyNN"),
    }


def detect_neuron_module() -> Optional[Any]:
    """NEURON can be imported either as `neuron` or `NEURON`."""
    return optional_import("neuron") or optional_import("NEURON")
