"""FunctionalActivationGate — lazy on-demand activation of neural sub-functions.

In a biological brain, not all neurons express all of their possible
functions continuously. A pyramidal cell in the prefrontal cortex does
not behave like a photoreceptor. SPEACE models this with a
FunctionalActivationGate: each DigitalNeuron carries a set of latent
functional modes (latent_states, receptor profiles, wave modes, etc.),
but those modes are only enabled when an incoming signal matches a
pattern declared in the Digital DNA.

This avoids the need to materialize billions of specialised neurons as
separate objects. Instead, a generic DigitalNeuron can be parametrically
configured on-demand by its gate, driven by genome-defined activation
rules.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from speace_core.cellular_brain.base.digital_signal import DigitalSignal


class ActivationRule(BaseModel):
    """A DNA-driven rule that enables a latent function on signal match."""
    rule_id: str
    description: str = ""
    # Patterns that trigger the rule. A signal matches if its meaning or
    # any of its tags is in this set.
    trigger_meanings: List[str] = Field(default_factory=list)
    trigger_tags: List[str] = Field(default_factory=list)
    # Minimum signal strength to trigger
    min_strength: float = 0.0
    # Latent state to activate (adds/overrides an entry in latent_states)
    activate_latent_state: Optional[str] = None
    latent_state_weight: float = 0.5
    # Receptor profile hint (e.g. "excitatory", "inhibitory", "auditory")
    activate_receptor_profile: Optional[str] = None
    # Functional flags
    enable_wave: bool = False
    wave_frequency: float = 10.0
    # Modulatory effects
    threshold_delta: float = 0.0
    plasticity_delta: float = 0.0


class FunctionalActivationGate(BaseModel):
    """Lazy activation gate attached to a DigitalNeuron.

    The gate is configured from Digital DNA (``functional_activation_rules``)
    and evaluates incoming signals. When a signal matches a rule, the
    corresponding latent function is enabled on the host neuron.
    """
    rules: List[ActivationRule] = Field(default_factory=list)
    active_function_tags: List[str] = Field(default_factory=list)
    activation_log: List[Dict[str, Any]] = Field(default_factory=list)

    def match_signal(self, signal: DigitalSignal) -> List[ActivationRule]:
        """Return all rules triggered by ``signal``."""
        matched: List[ActivationRule] = []
        meaning = signal.meaning or ""
        tags = getattr(signal, "tags", []) or []
        for rule in self.rules:
            if rule.min_strength > 0 and signal.strength < rule.min_strength:
                continue
            if meaning in rule.trigger_meanings:
                matched.append(rule)
                continue
            if any(tag in rule.trigger_tags for tag in tags):
                matched.append(rule)
        return matched

    def apply(
        self,
        signal: DigitalSignal,
        neuron: Any,
    ) -> List[str]:
        """Apply matching rules to ``neuron`` and return activated tags."""
        matched = self.match_signal(signal)
        activated: List[str] = []
        for rule in matched:
            self._apply_rule(rule, neuron)
            tag = rule.activate_latent_state or rule.activate_receptor_profile or rule.rule_id
            if tag not in self.active_function_tags:
                self.active_function_tags.append(tag)
            activated.append(tag)
            self.activation_log.append(
                {
                    "rule_id": rule.rule_id,
                    "signal_meaning": signal.meaning,
                    "signal_strength": signal.strength,
                    "latent_state": rule.activate_latent_state,
                }
            )
        return activated

    def _apply_rule(self, rule: ActivationRule, neuron: Any) -> None:
        """Mutate the host neuron according to the rule."""
        # Latent state
        if rule.activate_latent_state is not None:
            if not hasattr(neuron, "latent_states"):
                neuron.latent_states = {}
            neuron.latent_states[rule.activate_latent_state] = rule.latent_state_weight
            # Re-normalise
            total = sum(neuron.latent_states.values())
            if total > 0:
                neuron.latent_states = {
                    k: v / total for k, v in neuron.latent_states.items()
                }

        # Receptor profile
        if rule.activate_receptor_profile is not None and hasattr(neuron, "init_receptor_profile"):
            try:
                neuron.init_receptor_profile(rule.activate_receptor_profile)
            except Exception:
                pass

        # Wave mode
        if rule.enable_wave and hasattr(neuron, "emit_wave"):
            neuron.emit_wave = True
            if hasattr(neuron, "wave_frequency"):
                neuron.wave_frequency = rule.wave_frequency

        # Threshold / plasticity modulation
        if rule.threshold_delta != 0.0 and hasattr(neuron, "threshold"):
            neuron.threshold = max(0.1, min(1.0, neuron.threshold + rule.threshold_delta))
        if rule.plasticity_delta != 0.0 and hasattr(neuron, "plasticity_rate"):
            neuron.plasticity_rate = max(0.0, min(1.0, neuron.plasticity_rate + rule.plasticity_delta))

    @classmethod
    def from_genome(cls, genome: Any) -> "FunctionalActivationGate":
        """Build a gate from Digital DNA functional activation rules."""
        if genome is None:
            return cls()
        fap = getattr(genome, "functional_activation", None)
        if fap is None:
            return cls()
        rules_data = getattr(fap, "rules", [])
        if not rules_data:
            return cls()
        rules: List[ActivationRule] = []
        for item in rules_data:
            if isinstance(item, ActivationRule):
                rules.append(item)
            elif hasattr(item, "model_dump"):
                rules.append(ActivationRule(**item.model_dump()))
            elif isinstance(item, dict):
                rules.append(ActivationRule(**item))
        return cls(rules=rules)

    def summary(self) -> Dict[str, Any]:
        return {
            "rule_count": len(self.rules),
            "active_function_tags": list(self.active_function_tags),
            "activation_count": len(self.activation_log),
        }
