"""Tests for the BackendSelector."""
import pytest

from speace_core.cellular_brain.simulator_backends import (
    BackendChoice,
    BackendSelector,
    available_backends,
    recommend_backend,
    WorkloadSpec,
)


class TestBackendSelector:
    def test_available_backends(self):
        avail = available_backends()
        assert avail["native"] is True

    def test_recommend_small_workload_native(self):
        sel = BackendSelector()
        choice = sel.recommend(neuron_count=10, allow_external_deps=False)
        assert choice == BackendChoice.NATIVE

    def test_recommend_large_workload_native_by_default(self):
        # Without external deps, large workloads also fall back to native
        choice = recommend_backend(WorkloadSpec(neuron_count=200_000,
                                                allow_external_deps=False))
        assert choice == BackendChoice.NATIVE

    def test_recommend_with_prefers_python(self):
        # If prefers_python=True, Brian2 is not selected even if available
        choice = recommend_backend(WorkloadSpec(
            neuron_count=100, allow_external_deps=True, prefers_python=True
        ))
        assert choice == BackendChoice.NATIVE

    def test_build_native(self):
        sel = BackendSelector()
        backend = sel.build(BackendChoice.NATIVE)
        assert backend.is_available() is True

    def test_build_cache(self):
        sel = BackendSelector()
        b1 = sel.build(BackendChoice.NATIVE)
        b2 = sel.build(BackendChoice.NATIVE)
        assert b1 is b2

    def test_build_invalid_choice(self):
        sel = BackendSelector()
        with pytest.raises(ValueError):
            sel.build("nope")  # type: ignore[arg-type]
