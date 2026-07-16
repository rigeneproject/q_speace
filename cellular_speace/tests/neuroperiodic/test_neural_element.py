"""Tests for the Neural Periodic Table module (T184)."""
import pytest

from speace_core.cellular_brain.neuroperiodic.neural_element import (
    CATALOG,
    ElementBlock,
    ElementGroup,
    ElementPeriod,
    NeuralElement,
    ValenceState,
    build_element,
    get_element_by_cell_type,
)
from speace_core.cellular_brain.neuroperiodic.neural_periodic_table import (
    NeuralPeriodicTable,
    PeriodicTableBuilder,
)
from speace_core.cellular_brain.neuroperiodic.synaptic_bond import (
    BondFormationEngine,
    BondRegistry,
    BondType,
    SynapticBond,
)
from speace_core.cellular_brain.neuroperiodic.periodic_law import PeriodicLaw
from speace_core.cellular_brain.neuroperiodic.neuroperiodic_integrator import (
    NeuroPeriodicIntegrator,
)


class TestNeuralElement:
    def test_build_all_elements(self):
        for z in sorted(CATALOG.keys()):
            el = build_element(z)
            assert el.atomic_number == z
            assert el.symbol
            assert el.name
            assert isinstance(el.period, ElementPeriod)
            assert isinstance(el.group, ElementGroup)
            assert isinstance(el.block, ElementBlock)
            assert isinstance(el.valence, ValenceState)

    def test_element_properties(self):
        el = build_element(1)  # Photoreceptor
        assert el.symbol == "Ph"
        assert el.period == ElementPeriod.SENSORY_TRANSDUCTION
        assert el.group == ElementGroup.SENSORY_VISUAL
        assert el.block == ElementBlock.P_BLOCK
        assert el.is_excitatory()
        assert not el.is_inhibitory()
        assert el.compatibility_score(el) == 0.3

    def test_inhibitory_element(self):
        el = build_element(20)  # InhibitoryInterneuron
        assert el.symbol == "In"
        assert el.is_inhibitory()
        assert not el.is_excitatory()
        assert el.electronegativity > 0.8

    def test_modulatory_element(self):
        el = build_element(15)  # Limbic
        assert el.symbol == "Lb"
        assert el.is_modulatory()

    def test_compatibility_scores(self):
        exc = build_element(1)   # Photoreceptor (excitatory)
        inh = build_element(20)  # Inhibitory (inhibitory)
        mod = build_element(15)  # Limbic (modulatory)

        # Excitatory + Inhibitory should have high compatibility
        exc_inh = exc.compatibility_score(inh)
        assert exc_inh > 0.6

        # Same element should have low compatibility (self-inhibition)
        exc_exc = exc.compatibility_score(exc)
        assert exc_exc < 0.5

    def test_get_by_cell_type(self):
        el = get_element_by_cell_type("prefrontal_neuron")
        assert el is not None
        assert el.symbol == "Pf"

        el = get_element_by_cell_type("nonexistent")
        assert el is None

    def test_modulatory_applies_signal_sign_from_genome(self):
        el = build_element(15)
        assert el.block == ElementBlock.D_BLOCK


class TestNeuralPeriodicTable:
    def test_build_default(self):
        table = PeriodicTableBuilder.build_default()
        assert table.count() == len(CATALOG)
        assert 1 in table.elements
        assert 27 in table.elements

    def test_lookup(self):
        table = PeriodicTableBuilder.build_default()
        el = table.get_by_symbol("Pf")
        assert el is not None
        assert el.name == "Prefrontal"
        assert table.get_by_z(999) is None

    def test_get_by_cell_type(self):
        table = PeriodicTableBuilder.build_default()
        el = table.get_by_cell_type("motor_neuron")
        assert el is not None
        assert el.symbol == "Mo"

    def test_period_groups(self):
        table = PeriodicTableBuilder.build_default()
        p4 = table.get_period(ElementPeriod.INTEGRATION)
        assert len(p4) >= 2

        exc_group = table.get_group(ElementGroup.EXECUTIVE_PFC)
        assert len(exc_group) >= 1

    def test_predict_property(self):
        table = PeriodicTableBuilder.build_default()
        el = table.get_by_symbol("Pf")
        pred = table.predict_property(el.period, el.group, "electronegativity")
        assert 0.0 <= pred <= 1.0

    def test_find_similar(self):
        table = PeriodicTableBuilder.build_default()
        el = table.get_by_symbol("Hp")
        similar = table.find_similar(el, n=3)
        assert len(similar) <= 3
        assert all(isinstance(e, NeuralElement) for e in similar)

    def test_predict_connection(self):
        table = PeriodicTableBuilder.build_default()
        src = table.get_by_symbol("Ph")
        tgt = table.get_by_symbol("Sc")
        pred = table.predict_connection(src, tgt)
        assert "compatibility" in pred
        assert "strength" in pred
        assert "polarity" in pred

    def test_to_periodic_grid(self):
        table = PeriodicTableBuilder.build_default()
        grid = table.to_periodic_grid()
        assert isinstance(grid, dict)
        assert len(grid) > 0


class TestSynapticBond:
    def test_bond_prediction(self):
        src = build_element(1)   # Photoreceptor
        tgt = build_element(20)  # Inhibitory
        bond_type = BondFormationEngine.predict_bond_type(src, tgt)
        assert bond_type in (BondType.COVALENT, BondType.IONIC)

    def test_bond_formation(self):
        src = build_element(1)
        tgt = build_element(5)
        bond = BondFormationEngine.form_bond(src, tgt, bond_id="test1")
        assert bond.source_z == 1
        assert bond.target_z == 5
        assert bond.bond_energy > 0.0
        assert isinstance(bond.bond_type, BondType)
        assert isinstance(bond.bond_order, object)
        assert isinstance(bond.polarity, object)

    def test_bond_strength(self):
        src = build_element(17)  # Motor
        tgt = build_element(18)  # Cerebellar
        bond = BondFormationEngine.form_bond(src, tgt)
        strength = bond.bond_strength()
        assert strength > 0.0

    def test_bond_registry(self):
        reg = BondRegistry()
        src = build_element(1)
        tgt = build_element(5)
        bond = BondFormationEngine.form_bond(src, tgt, bond_id="reg1")
        reg.register(bond)
        assert "reg1" in reg.bonds
        assert len(reg.get_outgoing(1)) == 1
        assert len(reg.get_incoming(5)) == 1

    def test_signal_delay(self):
        src = build_element(1)
        tgt = build_element(14)  # Prefrontal (long-range)
        bond = BondFormationEngine.form_bond(src, tgt)
        assert bond.signal_delay() > 0.0

    def test_energy_cost(self):
        src = build_element(1)
        tgt = build_element(5)
        bond = BondFormationEngine.form_bond(src, tgt)
        assert bond.energy_cost() > 0.0


class TestPeriodicLaw:
    def test_default_trends(self):
        law = PeriodicLaw.build_default()
        assert "electronegativity" in law.trends
        assert "ionization_energy" in law.trends
        assert "atomic_radius" in law.trends

    def test_trend_prediction(self):
        law = PeriodicLaw.build_default()
        el = build_element(14)  # Prefrontal
        value = law.predict_property(el, "electronegativity")
        assert 0.0 <= value <= 1.0

    def test_valence_rules(self):
        law = PeriodicLaw.build_default()
        assert len(law.valence_rules) >= 9

        exc = build_element(1)   # Photoreceptor
        inh = build_element(20)  # Inhibitory
        rules = law.get_applicable_rules(exc, inh)
        assert len(rules) >= 1

    def test_reaction_rules(self):
        law = PeriodicLaw.build_default()
        assert len(law.reaction_rules) >= 10

    def test_describe_pair(self):
        law = PeriodicLaw.build_default()
        src = build_element(1)
        tgt = build_element(5)
        desc = law.describe_pair(src, tgt)
        assert "compatibility" in desc
        assert "valence_rules" in desc


class TestNeuroPeriodicIntegrator:
    def test_integrator_initialization(self):
        integrator = NeuroPeriodicIntegrator()
        assert integrator.table.count() == len(CATALOG)
        assert len(integrator.laws.trends) >= 4

    def test_get_element(self):
        integrator = NeuroPeriodicIntegrator()
        el = integrator.get_element("prefrontal_neuron")
        assert el is not None
        assert el.symbol == "Pf"

        el = integrator.get_element("nonexistent")
        assert el is None

    def test_classify_cell_type(self):
        integrator = NeuroPeriodicIntegrator()
        cls = integrator.classify_cell_type("motor_neuron")
        assert cls["classified"]
        assert cls["symbol"] == "Mo"
        assert cls["period"] == 6

    def test_classify_unknown(self):
        integrator = NeuroPeriodicIntegrator()
        cls = integrator.classify_cell_type("unknown_type")
        assert not cls["classified"]

    def test_predict_synapse(self):
        integrator = NeuroPeriodicIntegrator()
        pred = integrator.predict_synapse("prefrontal_neuron", "motor_neuron")
        assert pred.get("bond_type") is not None
        assert pred.get("compatibility", 0) > 0.3

    def test_predict_synapse_unknown(self):
        integrator = NeuroPeriodicIntegrator()
        pred = integrator.predict_synapse("unknown", "motor_neuron")
        assert "error" in pred

    def test_predict_circuit(self):
        integrator = NeuroPeriodicIntegrator()
        props = integrator.predict_circuit_properties([
            "sensory_neuron", "hippocampal_neuron", "prefrontal_neuron",
        ])
        assert props["element_count"] == 3
        assert props["block_diversity"] >= 1
        assert props["hierarchical_depth"] >= 1

    def test_suggest_differentiation(self):
        integrator = NeuroPeriodicIntegrator()
        ctx = {"region": "hippocampus", "energy": 0.8, "activation": 0.3}
        suggestion = integrator.suggest_differentiation(ctx)
        assert suggestion["classified"]
        assert len(suggestion["suggested_elements"]) > 0

    def test_analyze_region(self):
        integrator = NeuroPeriodicIntegrator()
        analysis = integrator.analyze_region("prefrontal", [
            "prefrontal_neuron", "inhibitory_neuron",
        ])
        assert analysis["element_count"] == 2
        assert "internal_bonds" in analysis

    def test_compare_elements(self):
        integrator = NeuroPeriodicIntegrator()
        comparison = integrator.compare_elements("Ph", "In")
        assert "similarity_score" in comparison
        assert "compatibility" in comparison
        assert "predicted_bond" in comparison

    def test_missing_elements(self):
        integrator = NeuroPeriodicIntegrator()
        missing = integrator.get_missing_elements()
        assert isinstance(missing, list)

    def test_glial_classification(self):
        integrator = NeuroPeriodicIntegrator()
        cls = integrator.classify_cell_type("digital_astrocyte")
        assert cls["classified"]
        assert cls["block"] == "g"


class TestIntegrationWithReceptorProfile:
    def test_receptor_profile_block(self):
        from speace_core.cellular_brain.base.receptor_profile import (
            default_excitatory_neuron_profile,
            default_inhibitory_neuron_profile,
            default_dopaminergic_neuron_profile,
        )
        exc_profile = default_excitatory_neuron_profile()
        assert exc_profile.classify_block() in ("p", "d", "mixed")

        inh_profile = default_inhibitory_neuron_profile()
        assert inh_profile.classify_block() in ("s", "mixed")

        dop_profile = default_dopaminergic_neuron_profile()
        assert dop_profile.classify_block() in ("d", "mixed")

    def test_receptor_valence_electrons(self):
        from speace_core.cellular_brain.base.receptor_profile import (
            default_excitatory_neuron_profile,
        )
        profile = default_excitatory_neuron_profile()
        assert profile.valence_electrons() >= 3

    def test_receptor_formula(self):
        from speace_core.cellular_brain.base.receptor_profile import (
            default_excitatory_neuron_profile,
        )
        profile = default_excitatory_neuron_profile()
        formula = profile.receptor_formula()
        assert "ampa" in formula or "nmda" in formula


class TestIntegrationWithDifferentiation:
    def test_periodic_differentiation_guidance(self):
        from speace_core.cellular_brain.regulation.cell_differentiation_engine import (
            CellDifferentiationEngine,
            DifferentiationContext,
        )
        integrator = NeuroPeriodicIntegrator()
        ctx = DifferentiationContext(
            region="prefrontal",
            energy=0.9,
            activation=0.5,
            connectivity=5,
            role="excitatory",
        )
        suggestion = integrator.suggest_differentiation(ctx.model_dump())
        assert suggestion["classified"]
        assert len(suggestion["suggested_elements"]) > 0


class TestPeriodicTableVisualization:
    def test_periodic_grid_structure(self):
        table = PeriodicTableBuilder.build_default()
        grid = table.to_periodic_grid()
        for period_key, groups in grid.items():
            assert isinstance(groups, dict)
            for group_key, elements in groups.items():
                assert isinstance(elements, list)
                for element in elements:
                    assert "z" in element
                    assert "symbol" in element
                    assert "name" in element
