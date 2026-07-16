"""Unit tests for the Biological-Cybernetic Equivalence Layer."""

import pytest

from speace_core.bcel import (
    BCELCatalog,
    BiologicalComponent,
    ConstraintClassifier,
    CyberneticSynthesizer,
)
from speace_core.bcel.models import ConstraintKind


def test_catalog_knows_dna_rna():
    catalog = BCELCatalog()
    eq = catalog.get("DNA-RNA expression")
    assert eq is not None
    assert eq.digital_implementation == "Digital DNA -> Digital RNA -> Workspace"


def test_classifier_detects_accidental_constraint():
    classifier = ConstraintClassifier()
    component = BiologicalComponent(
        name="chemical synapse",
        function="signal transmission",
        biological_constraints=["thermal noise in ion channels"],
    )
    assert classifier.classify(component, component.biological_constraints[0]) is ConstraintKind.ACCIDENTAL


def test_classifier_detects_functional_constraint():
    classifier = ConstraintClassifier()
    component = BiologicalComponent(
        name="synapse",
        function="signal transmission",
        biological_constraints=["synaptic delay acts as low-pass filter"],
    )
    assert classifier.classify(component, component.biological_constraints[0]) is ConstraintKind.FUNCTIONAL


def test_synthesizer_drops_accidental_keeps_functional():
    catalog = BCELCatalog()
    synthesizer = CyberneticSynthesizer(catalog=catalog)
    component = BiologicalComponent(
        name="chemical synapse",
        function="directed signal transmission",
        biological_constraints=[
            "neurotransmitter diffusion delay",
            "thermal noise in ion channels",
            "synaptic delay stabilizes network",
        ],
    )
    eq = synthesizer.synthesize(component)
    assert "neurotransmitter diffusion delay" in eq.removed_constraints
    assert "thermal noise in ion channels" in eq.removed_constraints
    assert any("synaptic delay" in fc.biological_form for fc in eq.kept_constraints)



def test_catalog_contains_expanded_entries():
    catalog = BCELCatalog()
    for name in ["biological homeostasis", "immune response", "cellular metabolism", "apoptosis", "neural refractory period"]:
        assert catalog.get(name) is not None, f"missing {name}"
from speace_core.bcel.stress_tester import ConstraintStressTester, StressTestResult
from speace_core.bcel.models import FunctionalConstraint


@pytest.mark.asyncio
async def test_stress_tester_default_placeholder():
    tester = ConstraintStressTester()
    fc = FunctionalConstraint(
        name="test_constraint",
        invariant="coherence_preservation",
        biological_form="placeholder",
        mathematical_form="placeholder",
    )
    result = await tester.run(fc)
    assert isinstance(result, StressTestResult)
    assert "placeholder" in result.test_name
    assert "could not be executed" in result.interpretation

