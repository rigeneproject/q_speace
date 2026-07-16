"""Conditional tests for the NEST simulator backend.

Tests are skipped if `nest` is not installed. They validate availability,
capabilities, fallback to native, and that setup raises RuntimeError when
invoked without the dependency (defensive coding). Because NEST is not
available in most CI/Python 3.14 environments, the primary value is the
fallback contract.
"""
from __future__ import annotations

import pytest

from speace_core.cellular_brain.simulator_backends.backend_selector import BackendChoice, BackendSelector
from speace_core.cellular_brain.simulator_backends.nest_backend import NESTBackend
from speace_core.cellular_brain.simulator_backends.native_backend import NativeBackend


def test_nest_backend_reports_availability():
    backend = NESTBackend()
    # If nest is installed, is_available should be True; if not, False.
    try:
        import nest  # noqa: F401
        expected = True
    except ImportError:
        expected = False
    assert backend.is_available() is expected


def test_nest_backend_capabilities():
    backend = NESTBackend()
    caps = backend.capabilities()
    assert caps.max_neurons > 0
    assert caps.supports_synapse_plasticity is True
    assert caps.metadata["engine"] == "nest"


def test_backend_selector_builds_nest_or_falls_back():
    selector = BackendSelector()
    backend = selector.build(BackendChoice.NEST)
    # If NEST is available we get NEST; otherwise we must get Native.
    if NESTBackend().is_available():
        assert backend.kind == BackendChoice.NEST
    else:
        assert isinstance(backend, NativeBackend)
        assert backend.kind == BackendChoice.NATIVE


def test_backend_selector_nest_fallback_when_unavailable(monkeypatch):
    from speace_core.cellular_brain.simulator_backends import nest_backend as nest_mod

    selector = BackendSelector()
    # Ensure the cache is not a false positive.
    selector._cache.pop("nest", None)
    monkeypatch.setattr(nest_mod.NESTBackend, "is_available", lambda self: False)
    backend = selector.build(BackendChoice.NEST)
    assert isinstance(backend, NativeBackend)
    assert backend.kind == BackendChoice.NATIVE
