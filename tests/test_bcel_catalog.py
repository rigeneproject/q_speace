"""BCEL catalog coverage (T202/T205/T206/T207 housekeeping).

Closes the gap between the conceptual BCEL classifications stated in
the spec docstrings (T202 §3, T205 §BCEL, T206 §BCEL, T207 §Safety)
and the canonical entries in ``q_speace.bcel.catalog``. The catalog is
the single source of truth consulted by tests, evaluations, and external
reviewers; the absence of these entries is a documentation regression
even when the underlying behaviour is correct.
"""

from __future__ import annotations

import pytest

from q_speace.bcel import BCELCatalog, BCELEquivalence


# Concepts the catalog MUST classify, regardless of classification.
# Drawn directly from T202 §3, T205/T206/T207 §BCEL tables.
REQUIRED_CONCEPTS: list[tuple[str, str]] = [
    # --- T202: pseudo-spiking layer ---
    ("Spike firing (biological action potential)", "accidental"),
    ("Spike-timing correlation → entanglement fidelity", "functional"),
    ("Event-driven neural energy", "functional"),
    ("Frequency-based plasticity (STDP-like)", "functional"),
    ("ILF-modulated spiking threshold", "functional"),
    # --- T205: SpikingBrain satellite ---
    ("MoBA top-k sparse softmax attention", "functional"),
    ("GLA / linear attention recurrence", "functional"),
    ("DSSA dual-path activation coding (SpB2.0)", "functional"),
    ("Brain area as cognitive subdivision", "functional"),
    ("SpikingBrain-7B / SpB2.0 model identity", "accidental"),
    # --- T206: hardening / calibration ---
    ("Biological confidence / introspection", "accidental"),
    ("Calibrated predictive confidence", "functional"),
    ("Conversation as cognitive agency", "accidental"),
    # --- existing quantum equivalences (regression guard) ---
    ("Entanglement (cell/planet communication)", "accidental"),
    ("Superposition (parallel hypotheses)", "functional"),
]


def test_catalog_has_all_required_concepts() -> None:
    cat = BCELCatalog()
    concepts = {entry.concept for entry in cat.all()}
    for concept, _expected_class in REQUIRED_CONCEPTS:
        assert concept in concepts, f"missing BCEL concept: {concept!r}"


@pytest.mark.parametrize("concept,expected_class", REQUIRED_CONCEPTS)
def test_catalog_classification(concept: str, expected_class: str) -> None:
    cat = BCELCatalog()
    entry: BCELEquivalence = cat.get(concept)
    assert entry.classification == expected_class, (
        f"{concept!r}: expected {expected_class}, got {entry.classification}"
    )


def test_catalog_is_functional_helper_matches_classification() -> None:
    cat = BCELCatalog()
    assert cat.is_functional("Calibrated predictive confidence") is True
    assert cat.is_functional("Biological confidence / introspection") is False
    assert cat.is_functional("Spike firing (biological action potential)") is False
    assert cat.is_functional("Spike-timing correlation → entanglement fidelity") is True


def test_catalog_get_unknown_concept_raises() -> None:
    cat = BCELCatalog()
    with pytest.raises(KeyError):
        cat.get("Not a real biological concept")


def test_fidelity_proxy_entry_explicitly_disclaims_quantum_fidelity() -> None:
    """The fidelity-proxy entry must state, in plain words, that the value
    is NOT a quantum-state fidelity. This is the exact text an external
    reviewer (or a future author) would read to understand the limit.
    """
    cat = BCELCatalog()
    entry = cat.get("Spike-timing correlation → entanglement fidelity")
    rule = entry.digital_rule.lower()
    assert "not" in rule and "quantum-state fidelity" in rule, (
        "fidelity-proxy entry must explicitly disclaim quantum-state fidelity; "
        f"got: {entry.digital_rule!r}"
    )


def test_spiking_brain_identity_entry_is_accidental() -> None:
    """The model-identity entry must be accidental: SPEACE must not depend
    on running the original BICLab model. This guards against future code
    that 'requires' SpikingBrain 7B to be loaded.
    """
    cat = BCELCatalog()
    entry = cat.get("SpikingBrain-7B / SpB2.0 model identity")
    assert entry.classification == "accidental"
    rule = entry.digital_rule.lower()
    assert "rtx 3060" in rule or "6 gb" in rule, (
        "identity entry should mention the 6 GB constraint that motivated "
        "treating the model identity as accidental; got: "
        f"{entry.digital_rule!r}"
    )


def test_brain_area_entry_mentions_thalamic_mediator() -> None:
    """The brain-area entry must state that ILF+Sevo+cost gate acts as the
    mediator between the brain area and the rest of SPEACE. This is the
    text a reviewer reads to verify the binding is not a backdoor.
    """
    cat = BCELCatalog()
    entry = cat.get("Brain area as cognitive subdivision")
    rule = entry.digital_rule.lower()
    assert "ilf" in rule and "sevo" in rule, (
        "brain-area entry must mention ILF + Sevo as the mediator; "
        f"got: {entry.digital_rule!r}"
    )