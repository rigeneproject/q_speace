"""Tests for LazyMaterializationManager and ParametricCatalog."""
import pytest

from speace_core.cellular_brain.base.digital_signal import DigitalSignal
from speace_core.cellular_brain.lazy import (
    FunctionSpec,
    LazyMaterializationManager,
    MaterializedNeuron,
    ParametricCatalog,
    SignalKey,
    SignalRouter,
    default_catalog,
)


class TestParametricCatalog:
    def test_default_catalog_not_empty(self):
        cat = default_catalog()
        assert cat.count() > 0
        assert "sensory" in cat._by_region
        assert "hippocampus" in cat._by_region

    def test_find_one(self):
        cat = default_catalog()
        spec = cat.find_one("hippocampus", "encoding")
        assert spec is not None
        assert spec.region == "hippocampus"
        assert spec.function == "encoding"

    def test_find_one_missing(self):
        cat = default_catalog()
        spec = cat.find_one("nowhere", "void")
        assert spec is None

    def test_add_idempotent(self):
        cat = ParametricCatalog()
        spec = FunctionSpec(key="k", region="r", function="f")
        cat.add(spec)
        cat.add(spec)
        assert cat.count() == 1

    def test_function_spec_matches_signal(self):
        spec = FunctionSpec(key="r.f", region="r", function="f")
        assert spec.matches_signal(SignalKey(region="r", function="f", key="r.f"))


class TestSignalRouter:
    def test_parse_dotted(self):
        k = SignalKey.from_string("sensory.visual")
        assert k.region == "sensory"
        assert k.function == "visual"

    def test_parse_simple(self):
        k = SignalKey.from_string("processing")
        assert k.region == "generic"
        assert k.function == "processing"

    def test_key_from_signal_with_meaning(self):
        r = SignalRouter()
        sig = DigitalSignal(source="s", meaning="hippocampus.encoding", strength=1.0)
        k = r.key_from_signal(sig)
        assert k.key == "hippocampus.encoding"

    def test_key_from_signal_no_meaning(self):
        r = SignalRouter()
        sig = DigitalSignal(source="s", strength=1.0)
        k = r.key_from_signal(sig)
        assert k.region == "generic"


class TestLazyMaterializationManager:
    def test_demand_creates(self):
        mgr = LazyMaterializationManager()
        sig = DigitalSignal(source="x", meaning="hippocampus.encoding", strength=1.0)
        mn = mgr.demand(sig)
        assert isinstance(mn, MaterializedNeuron)
        assert mgr.stats().materializations == 1

    def test_demand_reuses(self):
        mgr = LazyMaterializationManager()
        sig = DigitalSignal(source="x", meaning="hippocampus.encoding", strength=1.0)
        mn1 = mgr.demand(sig)
        mn2 = mgr.demand(sig)
        assert mn1.neuron.cell_id == mn2.neuron.cell_id
        s = mgr.stats()
        assert s.materializations == 1
        assert s.hits == 1

    def test_demand_different_functions(self):
        mgr = LazyMaterializationManager()
        sig1 = DigitalSignal(source="x", meaning="hippocampus.encoding", strength=1.0)
        sig2 = DigitalSignal(source="x", meaning="prefrontal.decision", strength=1.0)
        mn1 = mgr.demand(sig1)
        mn2 = mgr.demand(sig2)
        assert mn1.neuron.cell_id != mn2.neuron.cell_id

    def test_demand_specific(self):
        mgr = LazyMaterializationManager()
        mn = mgr.demand_specific("sensory", "visual")
        assert mn.spec.function == "visual"

    def test_demand_falls_back_to_generic(self):
        mgr = LazyMaterializationManager()
        sig = DigitalSignal(source="x", meaning="nowhere.void", strength=1.0)
        mn = mgr.demand(sig)
        # falls back to generic.processing
        assert mn.spec.function == "processing"

    def test_connect(self):
        mgr = LazyMaterializationManager()
        mn1 = mgr.demand_specific("sensory", "visual")
        mn2 = mgr.demand_specific("prefrontal", "decision")
        syn = mgr.connect(mn1, mn2, weight=0.7, delay_ms=2.0)
        assert syn.source == mn1.neuron.cell_id
        assert syn.target == mn2.neuron.cell_id
        assert syn.weight == 0.7
        # target registered
        assert mn2.neuron.cell_id in mn1.neuron.targets

    def test_list_active(self):
        mgr = LazyMaterializationManager()
        mgr.demand_specific("sensory", "visual")
        mgr.demand_specific("sensory", "auditory")
        active = mgr.list_active()
        assert len(active) == 2

    def test_unmaterialize_idle(self):
        mgr = LazyMaterializationManager()
        mgr.demand_specific("sensory", "visual")
        mgr.demand_specific("sensory", "auditory")
        n = mgr.unmaterialize_idle(idle_threshold_seconds=0.0)
        assert n == 2
        assert mgr.stats().active_neurons == 0

    def test_reset(self):
        mgr = LazyMaterializationManager()
        mgr.demand_specific("sensory", "visual")
        mgr.reset()
        assert mgr.stats().active_neurons == 0

    def test_get_by_id(self):
        mgr = LazyMaterializationManager()
        mn = mgr.demand_specific("sensory", "visual")
        found = mgr.get_by_id(mn.neuron.cell_id)
        assert found is mn
