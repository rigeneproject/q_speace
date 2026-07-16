"""STDPEngine — Spike-Timing-Dependent Plasticity for SPEACE.

Implements a bio-inspired STDP rule with neuromodulation:

    pre-synaptic spike  → record pre_time on outgoing synapses
    post-synaptic spike → record post_time on incoming synapses
    weight change ∝ exp(-|Δt| / tau) * sign(Δt) * gain

where:
    Δt = post_time - pre_time
    sign(Δt) > 0  => Long-Term Potentiation (LTP)
    sign(Δt) < 0  => Long-Term Depression (LTD)

Neuromodulation:
    gain = base_plasticity * (1 + dopamine * dopamine_gain)

A positive reward/dopamine increases the magnitude of plasticity;
a negative reward reduces or inverts it.

This engine is deterministic and operates on the existing DigitalSynapse
objects without creating new ones, preserving the parametric/lazy
representation of SPEACE.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from speace_core.cellular_brain.cells.digital_synapse import DigitalSynapse


class STDPEngine:
    """Spike-timing dependent plasticity engine.

    Args:
        tau_plus: time constant for LTP decay (ticks).
        tau_minus: time constant for LTD decay (ticks).
        a_plus: maximum LTP magnitude.
        a_minus: maximum LTD magnitude.
        dopamine_gain: multiplier for neuromodulatory effect.
        weight_clip: clip weight updates to [0, weight_clip].
        trust_clip: clip trust updates to [0, trust_clip].
    """

    def __init__(
        self,
        tau_plus: float = 10.0,
        tau_minus: float = 10.0,
        a_plus: float = 0.08,
        a_minus: float = 0.05,
        dopamine_gain: float = 2.0,
        weight_clip: float = 1.0,
        trust_clip: float = 1.0,
    ):
        self.tau_plus = max(1.0, tau_plus)
        self.tau_minus = max(1.0, tau_minus)
        self.a_plus = a_plus
        self.a_minus = a_minus
        self.dopamine_gain = dopamine_gain
        self.weight_clip = weight_clip
        self.trust_clip = trust_clip

    def compute_weight_delta(
        self,
        delta_ticks: float,
        dopamine: float = 0.0,
        base_plasticity: float = 1.0,
    ) -> float:
        """Return the STDP weight change for a given timing interval.

        delta_ticks = post_time - pre_time.
        dopamine: neuromodulatory signal (-1..+1 typical).
        base_plasticity: cell/circuit-level scaling.
        """
        mod = base_plasticity * (1.0 + dopamine * self.dopamine_gain)
        if delta_ticks > 0:
            # LTP: pre before post
            return self.a_plus * math.exp(-delta_ticks / self.tau_plus) * mod
        elif delta_ticks < 0:
            # LTD: post before pre
            return -self.a_minus * math.exp(delta_ticks / self.tau_minus) * mod
        else:
            return 0.0

    def update_synapse(
        self,
        synapse: DigitalSynapse,
        delta_ticks: float,
        dopamine: float = 0.0,
        base_plasticity: float = 1.0,
    ) -> Dict[str, Any]:
        """Apply one STDP update to a synapse.

        Returns a dict describing the change for logging/monitoring.
        """
        delta = self.compute_weight_delta(delta_ticks, dopamine, base_plasticity)
        old_weight = synapse.weight
        old_trust = synapse.trust

        synapse.weight = max(0.0, min(self.weight_clip, synapse.weight + delta))
        # Trust follows weight direction but with smaller step.
        trust_delta = delta * 0.5
        synapse.trust = max(0.0, min(self.trust_clip, synapse.trust + trust_delta))
        synapse.use_count += 1

        return {
            "delta": delta,
            "old_weight": old_weight,
            "new_weight": synapse.weight,
            "old_trust": old_trust,
            "new_trust": synapse.trust,
            "delta_ticks": delta_ticks,
            "dopamine": dopamine,
        }

    def apply_updates(
        self,
        synapses: List[DigitalSynapse],
        dopamine: float = 0.0,
        base_plasticity: float = 1.0,
    ) -> List[Dict[str, Any]]:
        """Apply STDP updates to all synapses that have both pre and post times.

        Only synapses with recorded spike timing are updated.
        """
        results: List[Dict[str, Any]] = []
        for syn in synapses:
            if syn.last_pre_spike_tick is None or syn.last_post_spike_tick is None:
                continue
            delta_ticks = syn.last_post_spike_tick - syn.last_pre_spike_tick
            result = self.update_synapse(syn, delta_ticks, dopamine, base_plasticity)
            result["source"] = syn.source
            result["target"] = syn.target
            results.append(result)
        return results

    def summary(self) -> Dict[str, Any]:
        return {
            "tau_plus": self.tau_plus,
            "tau_minus": self.tau_minus,
            "a_plus": self.a_plus,
            "a_minus": self.a_minus,
            "dopamine_gain": self.dopamine_gain,
        }
