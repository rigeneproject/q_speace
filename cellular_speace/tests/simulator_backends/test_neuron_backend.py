"""Conditional tests for the NEURON simulator backend.

Tests are skipped if `neuron` is not installed. They validate availability,
capabilities, fallback to native, and the fallback contract when the backend
reports unavailable.
"""
from __future__ import annotations

import pytest

from speace_core.cellular_brain.simulator_backends.backend_selector import BackendChoice, BackendSelector
from speace_core.cellular_brain.simulator_backends.native_backend import NativeBackend
from speace_core.cellular_brain.simulator_backends.neuron_backend import NEURONBackend


def test_neuron_backend_reports_availability():
    backend = NEURONBackend()
    try:
        import neuron  # noqa: F401
        expected = True
    except ImportError:
        expected = False
    assert backend.is_available() is expected


def test_neuron_backend_capabilities():
    backend = NEURONBackend()
    caps = backend.capabilities()
    assert caps.max_neurons > 0
    assert caps.supports_single_neuron_morphology is True
    assert caps.metadata["engine"] == "neuron"


def test_backend_selector_builds_neuron_or_falls_back():
    selector = BackendSelector()
    backend = selector.build(BackendChoice.NEURON)
    if NEURONBackend().is_available():
        assert backend.kind == BackendChoice.NEURON
    else:
        assert isinstance(backend, NativeBackend)
        assert backend.kind == BackendChoice.NATIVE


def test_backend_selector_neuron_fallback_when_unavailable(monkeypatch):
    from speace_core.cellular_brain.simulator_backends import neuron_backend as neuron_mod

    selector = BackendSelector()
    selector._cache.pop("neuron", None)
    monkeypatch.setattr(neuron_mod.NEURONBackend, "is_available", lambda self: False)
    backend = selector.build(BackendChoice.NEURON)
    assert isinstance(backend, NativeBackend)
    assert backend.kind == BackendChoice.NATIVE
