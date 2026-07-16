"""Tests for FunctionalActivationGate (lazy on-demand neural functions)."""
import pytest

from speace_core.cellular_brain.base.digital_signal import DigitalSignal
from speace_core.cellular_brain.cells.digital_neuron import DigitalNeuron
from speace_core.cellular_brain.cells.functional_activation_gate import (
    ActivationRule,
    FunctionalActivationGate,
)
from speace_core.dna.models import (
    SharedGenome,
    FunctionalActivationParams,
    FunctionalActivationRule,
)


def make_neuron():
    return DigitalNeuron(cell_id="n1", role="digital_neuron")


def test_gate_matches_signal_by_meaning():
    gate = FunctionalActivationGate(
        rules=[
            ActivationRule(
                rule_id="sensory",
                trigger_meanings=["visual"],
                activate_latent_state="visual_encoding",
                latent_state_weight=0.8,
            )
        ]
    )
    sig = DigitalSignal(source="s", target="n1", strength=0.5, meaning="visual")
    n = make_neuron()
    activated = gate.apply(sig, n)
    assert "visual_encoding" in activated
    assert "visual_encoding" in n.latent_states
    assert abs(n.latent_states["visual_encoding"] - 1.0) < 1e-9


def test_gate_no_match_leaves_neuron_unchanged():
    gate = FunctionalActivationGate(
        rules=[
            ActivationRule(
                rule_id="sensory",
                trigger_meanings=["visual"],
                activate_latent_state="visual_encoding",
            )
        ]
    )
    sig = DigitalSignal(source="s", target="n1", strength=0.5, meaning="motor")
    n = make_neuron()
    activated = gate.apply(sig, n)
    assert activated == []
    assert n.latent_states == {}


def test_gate_min_strength_filter():
    gate = FunctionalActivationGate(
        rules=[
            ActivationRule(
                rule_id="strong_signal",
                trigger_meanings=["alert"],
                min_strength=0.5,
                activate_latent_state="alert_mode",
            )
        ]
    )
    n = make_neuron()
    weak = DigitalSignal(source="s", target="n1", strength=0.2, meaning="alert")
    strong = DigitalSignal(source="s", target="n1", strength=0.7, meaning="alert")
    assert gate.apply(weak, n) == []
    assert gate.apply(strong, n) == ["alert_mode"]


def test_gate_receptor_profile_activation():
    gate = FunctionalActivationGate(
        rules=[
            ActivationRule(
                rule_id="inhibit",
                trigger_meanings=["suppress"],
                activate_receptor_profile="inhibitory",
                threshold_delta=-0.1,
            )
        ]
    )
    n = make_neuron()
    n.threshold = 0.5
    sig = DigitalSignal(source="s", target="n1", strength=0.5, meaning="suppress")
    gate.apply(sig, n)
    assert n.receptor_profile is not None
    assert n.threshold < 0.5


def test_gate_from_genome():
    genome = SharedGenome(
        functional_activation=FunctionalActivationParams(
            enabled=True,
            rules=[
                FunctionalActivationRule(
                    rule_id="lang",
                    trigger_meanings=["word"],
                    activate_latent_state="language",
                    latent_state_weight=0.6,
                )
            ],
        )
    )
    gate = FunctionalActivationGate.from_genome(genome)
    assert len(gate.rules) == 1
    n = make_neuron()
    sig = DigitalSignal(source="s", target="n1", strength=0.5, meaning="word")
    activated = gate.apply(sig, n)
    assert "language" in activated


def test_digital_neuron_uses_gate_on_receive():
    n = make_neuron()
    n.functional_activation_gate = FunctionalActivationGate(
        rules=[
            ActivationRule(
                rule_id="sensory",
                trigger_meanings=["auditory"],
                activate_latent_state="auditory_encoding",
            )
        ]
    )
    sig = DigitalSignal(source="s", target="n1", strength=0.4, meaning="auditory")
    import asyncio
    asyncio.run(n.receive(sig))
    assert "auditory_encoding" in n.latent_states
