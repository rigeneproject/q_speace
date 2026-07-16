"""Unit tests for the digital gut-brain axis (enteroception)."""

import math

import pytest

# Import modules directly to avoid triggering speace_core.__init__
# which imports orchestrator (has a pre-existing circular/import issue).
from speace_core.cellular_brain.enteroception.enteric_signal_bus import (
    ENTERCEPTION_CHANNELS,
    EntericSignalBus,
    EnteroceptiveSnapshot,
)
from speace_core.cellular_brain.enteroception.microbiome_modulator import (
    MicrobiomeModulator,
)
from speace_core.cellular_brain.enteroception.strain_definitions import (
    DEFAULT_STRAINS,
    MicrobialStrain,
)


# ------------------------------------------------------------------ #
# Strain definitions
# ------------------------------------------------------------------ #

class TestStrainDefinitions:
    def test_default_strains_exist(self):
        assert "lactobacillus" in DEFAULT_STRAINS
        assert "bifidobacterium" in DEFAULT_STRAINS
        assert "bacteroides" in DEFAULT_STRAINS
        assert "clostridium" in DEFAULT_STRAINS
        assert "candida" in DEFAULT_STRAINS

    def test_strain_has_required_fields(self):
        s = DEFAULT_STRAINS["lactobacillus"]
        assert isinstance(s, MicrobialStrain)
        assert s.substrate_affinity > 0
        assert len(s.metabolite_profile) > 0
        assert 0 <= s.stress_sensitivity <= 1

    def test_strains_cover_all_metabolites(self):
        all_mets = set()
        for s in DEFAULT_STRAINS.values():
            all_mets.update(s.metabolite_profile.keys())
        assert "scfa" in all_mets
        assert "gaba_precursor" in all_mets
        assert "serotonin_precursor" in all_mets
        assert "dopamine_precursor" in all_mets
        assert "novelty_signal" in all_mets


# ------------------------------------------------------------------ #
# MicrobiomeModulator
# ------------------------------------------------------------------ #

class TestMicrobiomeModulator:
    def test_initial_state(self):
        mod = MicrobiomeModulator()
        assert mod.substrate == 10.0
        assert all(v == 0.0 for v in mod.metabolites.values())

    def test_tick_produces_metabolites(self):
        mod = MicrobiomeModulator()
        mets = mod.tick(stress_level=0.0, substrate_input=5.0, coherence=0.5)
        assert isinstance(mets, dict)
        assert all(k in mets for k in ("scfa", "serotonin_precursor", "gaba_precursor", "dopamine_precursor", "inflammatory_cytokine", "novelty_signal"))

    def test_diversity_is_high_initially(self):
        mod = MicrobiomeModulator()
        div = mod.get_diversity()
        assert 0.0 < div <= 1.0

    def test_stress_reduces_diversity(self):
        mod = MicrobiomeModulator()
        no_stress = mod.get_diversity()
        mod.tick(stress_level=0.9, substrate_input=0.0, coherence=0.5)
        stressed = mod.get_diversity()
        assert stressed <= no_stress

    def test_substrate_is_consumed(self):
        mod = MicrobiomeModulator(substrate_capacity=50.0)
        mod.substrate = 50.0
        mod.tick(stress_level=0.0, substrate_input=0.0, coherence=0.5)
        assert mod.substrate < 50.0

    def test_metabolites_decay_over_time(self):
        mod = MicrobiomeModulator(metabolite_decay=0.1)
        for k in mod.metabolites:
            mod.metabolites[k] = 0.5
        mod._decay_metabolites()
        assert all(v < 0.5 - 0.01 for v in mod.metabolites.values())

    def test_increased_substrate_boosts_metabolites(self):
        mod = MicrobiomeModulator()
        before = sum(mod.metabolites.values())
        mod.tick(stress_level=0.0, substrate_input=10.0, coherence=0.5)
        after = sum(mod.metabolites.values())
        assert after > before

    def test_dominant_metabolites_returns_top_n(self):
        mod = MicrobiomeModulator()
        for _ in range(3):
            mod.tick(stress_level=0.0, substrate_input=5.0, coherence=0.5)
        dom = mod.get_dominant_metabolites(top_n=2)
        assert len(dom) <= 2
        assert all(m in mod.metabolites for m in dom)

    def test_reset_restores_initial_state(self):
        mod = MicrobiomeModulator()
        mod.tick(stress_level=0.0, substrate_input=10.0, coherence=0.5)
        mod.reset()
        assert mod.substrate == 10.0
        assert all(v == 0.0 for v in mod.metabolites.values())

    def test_get_strain_summary(self):
        mod = MicrobiomeModulator()
        summary = mod.get_strain_summary()
        assert len(summary) == len(DEFAULT_STRAINS)
        total = sum(summary.values())
        assert abs(total - 1.0) < 0.01


# ------------------------------------------------------------------ #
# EntericSignalBus
# ------------------------------------------------------------------ #

class TestEntericSignalBus:
    def test_initial_state(self):
        bus = EntericSignalBus(update_interval=10)
        assert bus._tick == 0
        assert bus._ticks_since_update == 0

    def test_read_returns_none_before_interval(self):
        bus = EntericSignalBus(update_interval=5)
        for _ in range(4):
            result = bus.read(None)
            assert result is None

    def test_read_returns_snapshot_at_interval(self):
        bus = EntericSignalBus(update_interval=3)
        for _ in range(2):
            bus.read(None)
        snap = bus.read(None)
        assert snap is not None
        assert isinstance(snap, EnteroceptiveSnapshot)

    def test_snapshot_has_all_channels(self):
        bus = EntericSignalBus(update_interval=1)
        snap = bus.read(None)
        assert snap is not None
        for ch in ENTERCEPTION_CHANNELS:
            assert ch in snap.signals

    def test_gut_feeling_is_computed(self):
        bus = EntericSignalBus(update_interval=1)
        snap = bus.read(None)
        assert snap is not None
        assert 0.0 <= snap.gut_feeling <= 1.0

    def test_vector_length_matches_channels(self):
        bus = EntericSignalBus(update_interval=1)
        bus.read(None)
        vec = bus.vector()
        assert len(vec) == len(ENTERCEPTION_CHANNELS)

    def test_broadcast_to_workspace_noop_without_workspace(self):
        bus = EntericSignalBus(update_interval=1)
        bus.read(None)
        bus.broadcast_to_workspace(None)

    def test_broadcast_to_workspace_pads_to_target_dim(self):
        bus = EntericSignalBus(update_interval=1)
        bus.read(None)
        mock = MockWorkspace()
        bus.broadcast_to_workspace(mock, target_dim=16)
        assert len(mock.last_broadcast.get("enteroception", [])) == 16

    def test_integrated_microbiome_produces_meaningful_signals(self):
        mod = MicrobiomeModulator()
        bus = EntericSignalBus(update_interval=1)
        snap = bus.read(mod, stress_level=0.0, coherence=0.5)
        assert snap is not None
        assert snap.signals["microbiome_diversity"] > 0.3
        assert snap.signals["gut_feeling"] <= 0.5

    def test_stress_increases_gut_feeling(self):
        mod = MicrobiomeModulator()
        bus = EntericSignalBus(update_interval=1)
        bus.read(mod, stress_level=0.0, coherence=0.5)
        low_feeling = bus.get_gut_feeling()
        for _ in range(5):
            bus.read(mod, stress_level=0.9, coherence=0.5)
        high_feeling = bus.get_gut_feeling()
        assert high_feeling >= low_feeling

    def test_save_history_creates_file(self, tmp_path):
        bus = EntericSignalBus(update_interval=1)
        for _ in range(3):
            bus.read(None)
        path = str(tmp_path / "gut_history.json")
        bus.save_history(path)
        assert tmp_path.joinpath("gut_history.json").exists()


class MockWorkspace:
    def __init__(self):
        self.last_broadcast = {}

    def broadcast(self, channel, data):
        self.last_broadcast[channel] = list(data)
