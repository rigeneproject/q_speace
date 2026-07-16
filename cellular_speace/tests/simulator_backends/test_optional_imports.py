"""Tests for optional import wrappers."""
import pytest

from speace_core.cellular_brain.simulator_backends.optional_imports import (
    available_backends,
    detect_neuron_module,
    is_available,
    optional_import,
)


class TestOptionalImports:
    def test_optional_import_existing(self):
        # numpy is always available
        m = optional_import("numpy")
        assert m is not None
        assert m.__name__ == "numpy"

    def test_optional_import_missing(self):
        m = optional_import("definitely_not_a_real_module_xyz")
        assert m is None

    def test_is_available(self):
        assert is_available("numpy") is True
        assert is_available("definitely_not_a_real_module_xyz") is False

    def test_available_backends_has_native(self):
        avail = available_backends()
        assert "native" in avail
        assert avail["native"] is True

    def test_detect_neuron_returns_none_or_module(self):
        m = detect_neuron_module()
        if m is not None:
            assert hasattr(m, "h")
