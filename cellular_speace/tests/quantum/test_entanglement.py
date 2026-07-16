"""Tests for the EntanglementRegistry."""
import pytest

from speace_core.cellular_brain.quantum.entanglement_registry import (
    EntangledPair,
    EntanglementRegistry,
)


class TestEntanglementRegistry:
    def test_empty(self):
        reg = EntanglementRegistry()
        assert reg.count() == 0
        assert reg.connected_components() == []

    def test_entangle_adds_pair(self):
        reg = EntanglementRegistry()
        p = reg.entangle("a", "b", fidelity=0.9, label="AB")
        assert isinstance(p, EntangledPair)
        assert reg.count() == 1
        assert reg.is_entangled("a", "b")

    def test_self_entanglement_rejected(self):
        reg = EntanglementRegistry()
        with pytest.raises(ValueError):
            reg.entangle("a", "a")

    def test_pairs_of(self):
        reg = EntanglementRegistry()
        reg.entangle("a", "b")
        reg.entangle("a", "c")
        pairs = reg.pairs_of("a")
        assert len(pairs) == 2

    def test_partners_of(self):
        reg = EntanglementRegistry()
        reg.entangle("a", "b")
        reg.entangle("a", "c")
        partners = reg.partners_of("a")
        assert partners == {"b", "c"}

    def test_degree(self):
        reg = EntanglementRegistry()
        reg.entangle("a", "b")
        reg.entangle("a", "c")
        reg.entangle("a", "d")
        assert reg.degree("a") == 3
        assert reg.degree("b") == 1
        assert reg.degree("z") == 0

    def test_disentangle(self):
        reg = EntanglementRegistry()
        reg.entangle("a", "b")
        reg.entangle("a", "c")
        ok = reg.disentangle("a", "b")
        assert ok
        assert not reg.is_entangled("a", "b")
        assert reg.is_entangled("a", "c")
        assert reg.count() == 1

    def test_disentangle_missing(self):
        reg = EntanglementRegistry()
        reg.entangle("a", "b")
        assert reg.disentangle("x", "y") is False

    def test_connected_components(self):
        reg = EntanglementRegistry()
        reg.entangle("a", "b")
        reg.entangle("b", "c")
        reg.entangle("x", "y")
        comps = reg.connected_components()
        comps_sets = [frozenset(c) for c in comps]
        assert frozenset({"a", "b", "c"}) in comps_sets
        assert frozenset({"x", "y"}) in comps_sets

    def test_clear(self):
        reg = EntanglementRegistry()
        reg.entangle("a", "b")
        reg.clear()
        assert reg.count() == 0

    def test_pair_other(self):
        reg = EntanglementRegistry()
        p = reg.entangle("a", "b")
        assert p.other("a") == "b"
        assert p.other("b") == "a"
        with pytest.raises(KeyError):
            p.other("z")

    def test_pair_involves(self):
        reg = EntanglementRegistry()
        p = reg.entangle("a", "b")
        assert p.involves("a")
        assert p.involves("b")
        assert not p.involves("z")
