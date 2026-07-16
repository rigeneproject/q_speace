"""CognitiveObjectiveReduction (COR) — functional analog of Orch-OR for SPEACE.

COR emulates the Orch-OR chain at an informational, not quantum-physical, level:

    latent hypotheses (superposition)
           ↓
    cognitive pressure accumulation
           ↓
    metacognitive collapse (COR)
           ↓
    dominant configuration

The collapse condition is:

    H · M > Φ · Φ_threshold_factor

where:
    H  = cognitive entropy (disorder / uncertainty)
    Φ  = global coherence (ILF-like)
    M  = metacognitive pressure (error + contradiction + saturation)

When the condition is met, COR:
    1. Reads latent states from DigitalNeurons.
    2. Generates competing global hypotheses.
    3. Selects a dominant configuration.
    4. Applies it to the circuit / synapses / DNA parameters.
    5. Emits a Meta-Cognitive Event for the MetacognitiveMonitor.

This is a functional emulation. It does not claim to produce phenomenal
consciousness or objective quantum reduction.
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from speace_core.cellular_brain.dynamics.stdp_engine import STDPEngine
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class CORHypothesis:
    """A competing cognitive configuration produced during COR."""
    hypothesis_id: str
    label: str
    probability: float = 0.0
    source_neuron_ids: List[str] = field(default_factory=list)
    configuration: Dict[str, Any] = field(default_factory=dict)
    entropy: float = 0.0
    coherence_delta: float = 0.0


@dataclass
class CORResult:
    """Result of a Cognitive Objective Reduction event."""
    timestamp: float
    tick: int
    collapsed: bool
    entropy_h: float
    coherence_phi: float
    metacognitive_pressure_m: float
    threshold: float
    dominant_hypothesis: Optional[CORHypothesis] = None
    all_hypotheses: List[CORHypothesis] = field(default_factory=list)
    reconfiguration_applied: bool = False
    reconfiguration_summary: Dict[str, Any] = field(default_factory=dict)
    neurons_collapsed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "tick": self.tick,
            "collapsed": self.collapsed,
            "entropy_h": round(self.entropy_h, 6),
            "coherence_phi": round(self.coherence_phi, 6),
            "metacognitive_pressure_m": round(self.metacognitive_pressure_m, 6),
            "threshold": round(self.threshold, 6),
            "dominant_hypothesis": (
                {
                    "hypothesis_id": self.dominant_hypothesis.hypothesis_id,
                    "label": self.dominant_hypothesis.label,
                    "probability": round(self.dominant_hypothesis.probability, 6),
                    "source_neuron_ids": self.dominant_hypothesis.source_neuron_ids,
                    "entropy": round(self.dominant_hypothesis.entropy, 6),
                    "coherence_delta": round(self.dominant_hypothesis.coherence_delta, 6),
                }
                if self.dominant_hypothesis else None
            ),
            "all_hypotheses": [
                {
                    "hypothesis_id": h.hypothesis_id,
                    "label": h.label,
                    "probability": round(h.probability, 6),
                }
                for h in self.all_hypotheses
            ],
            "reconfiguration_applied": self.reconfiguration_applied,
            "reconfiguration_summary": self.reconfiguration_summary,
            "neurons_collapsed": self.neurons_collapsed,
        }


class CognitiveObjectiveReduction:
    """Functional Orch-OR engine for SPEACE.

    Monitors a neural circuit, accumulates cognitive pressure, and triggers a
    non-quantum collapse when entropy times metacognitive pressure exceeds
    the global coherence threshold.
    """

    def __init__(
        self,
        circuit: Any,
        coherence_source: Optional[Any] = None,
        metacognitive_source: Optional[Any] = None,
        ilf_source: Optional[Any] = None,
        phi_threshold_factor: float = 0.55,
        min_latent_states: int = 2,
        max_hypotheses: int = 8,
        collapse_refractory_ticks: int = 10,
        reconfigure_on_collapse: bool = True,
        report_dir: str = "data/dynamics/cor",
    ) -> None:
        self.circuit = circuit
        self.coherence_source = coherence_source
        self.metacognitive_source = metacognitive_source
        self.ilf_source = ilf_source

        self.phi_threshold_factor = max(0.01, phi_threshold_factor)
        self.min_latent_states = max(2, min_latent_states)
        self.max_hypotheses = max(2, max_hypotheses)
        self.collapse_refractory_ticks = max(0, collapse_refractory_ticks)
        self.reconfigure_on_collapse = reconfigure_on_collapse
        self.synaptic_reinforcement_rate = 0.03
        self.stdp_engine: Optional["STDPEngine"] = None

        self._report_dir = Path(report_dir)
        self._report_dir.mkdir(parents=True, exist_ok=True)
        self._report_path = self._report_dir / "cor_events.jsonl"

        self._tick: int = 0
        self._last_collapse_tick: int = -self.collapse_refractory_ticks - 1
        self._history: List[CORResult] = []

    # ------------------------------------------------------------------ #
    # Core API
    # ------------------------------------------------------------------ #

    def tick(self, tick: int, meta_state: Optional[Dict[str, Any]] = None) -> CORResult:
        """Run one COR evaluation step."""
        self._tick = tick
        h = self._compute_entropy()
        phi = self._compute_coherence()
        m = self._compute_metacognitive_pressure(meta_state)

        threshold = phi * self.phi_threshold_factor
        collapsed = (h * m) > threshold

        # Enforce refractory period and minimum structural conditions.
        if collapsed:
            if (tick - self._last_collapse_tick) < self.collapse_refractory_ticks:
                collapsed = False
            elif not self._has_sufficient_latent_states():
                collapsed = False

        hypotheses: List[CORHypothesis] = []
        dominant: Optional[CORHypothesis] = None
        reconfigured = False
        reconfiguration_summary: Dict[str, Any] = {}
        neurons_collapsed = 0

        if collapsed:
            self._last_collapse_tick = tick
            hypotheses = self._generate_hypotheses()
            dominant = self._select_dominant(hypotheses)
            if dominant is not None:
                neurons_collapsed = self._collapse_neurons_to(dominant)
                if self.reconfigure_on_collapse:
                    reconfigured, reconfiguration_summary = self._apply_reconfiguration(dominant)

        result = CORResult(
            timestamp=time.time(),
            tick=tick,
            collapsed=collapsed,
            entropy_h=h,
            coherence_phi=phi,
            metacognitive_pressure_m=m,
            threshold=threshold,
            dominant_hypothesis=dominant,
            all_hypotheses=hypotheses,
            reconfiguration_applied=reconfigured,
            reconfiguration_summary=reconfiguration_summary,
            neurons_collapsed=neurons_collapsed,
        )
        self._history.append(result)
        self._persist(result)
        return result

    def latest_result(self) -> Optional[CORResult]:
        return self._history[-1] if self._history else None

    def summary(self) -> Dict[str, Any]:
        return {
            "tick": self._tick,
            "last_collapse_tick": self._last_collapse_tick,
            "collapse_count": sum(1 for r in self._history if r.collapsed),
            "latest_entropy": self._history[-1].entropy_h if self._history else 0.0,
            "latest_coherence": self._history[-1].coherence_phi if self._history else 0.0,
        }

    # ------------------------------------------------------------------ #
    # Metric computation
    # ------------------------------------------------------------------ #

    def _compute_entropy(self) -> float:
        """Cognitive entropy from latent-state distribution across neurons."""
        all_states: List[float] = []
        for neuron in self._all_neurons():
            latent = getattr(neuron, "latent_states", None) or {}
            all_states.extend(latent.values())

        if len(all_states) < 2:
            # Fall back to activation variance if no latent states are present.
            activations = [n.activation for n in self._all_neurons()]
            if len(activations) < 2:
                return 0.0
            mean = sum(activations) / len(activations)
            variance = sum((a - mean) ** 2 for a in activations) / len(activations)
            return min(1.0, math.sqrt(variance))

        # Normalise latent values to a probability-like distribution.
        total = sum(all_states)
        if total <= 0:
            return 0.0
        probs = [v / total for v in all_states]
        entropy = -sum(p * math.log2(p + 1e-12) for p in probs)
        max_entropy = math.log2(len(probs))
        if max_entropy <= 0:
            return 0.0
        return min(1.0, entropy / max_entropy)

    def _compute_coherence(self) -> float:
        """Global coherence from available sources."""
        # Prefer ILF / field coherence if available.
        if self.ilf_source is not None:
            ilf = getattr(self.ilf_source, "latest_state", None)
            if ilf is not None:
                value = getattr(ilf, "value", None)
                if value is not None:
                    return float(value)
            ilf_value = getattr(self.ilf_source, "value", None)
            if ilf_value is not None:
                return float(ilf_value)

        if self.coherence_source is not None:
            report = getattr(self.coherence_source, "latest_report", lambda: None)()
            if report and "aggregate_coherence" in report:
                agg = report["aggregate_coherence"]
                if agg is not None:
                    return float(agg)
            metric = getattr(self.coherence_source, "aggregate_coherence", None)
            if metric is not None:
                return float(metric)

        # Fallback: high average activation = coherence.
        activations = [n.activation for n in self._all_neurons()]
        if not activations:
            return 0.5
        mean = sum(activations) / len(activations)
        return min(1.0, max(0.0, mean))

    def _compute_metacognitive_pressure(self, meta_state: Optional[Dict[str, Any]]) -> float:
        """Composite pressure from metacognitive errors, contradictions and saturation."""
        pressure = 0.0
        count = 0

        if meta_state is not None:
            err = meta_state.get("error_detection", {})
            if isinstance(err, dict):
                pressure += float(err.get("repetitive_loop", False))
                pressure += float(err.get("contradiction", False))
                pressure += float(err.get("similarity_collapse", False))
                pressure += float(err.get("memory_saturation", False))
                pressure += float(err.get("regulation_oscillation", False))
                count += 5

            obs = meta_state.get("cognitive_observation", {})
            if isinstance(obs, dict):
                # Low stability and high drift increase pressure.
                stability = obs.get("workspace_stability", 0.5)
                drift = obs.get("vector_drift", 0.0)
                pressure += (1.0 - stability) + drift
                count += 2

        # Add local per-neuron pressure.
        for neuron in self._all_neurons():
            pressure += getattr(neuron, "cor_pressure", 0.0)
            count += 1

        if count == 0:
            return 0.0
        return min(1.0, pressure / count)

    # ------------------------------------------------------------------ #
    # Hypothesis generation and selection
    # ------------------------------------------------------------------ #

    def _generate_hypotheses(self) -> List[CORHypothesis]:
        """Build competing global hypotheses from latent states of neurons."""
        neurons = [n for n in self._all_neurons() if getattr(n, "latent_states", None)]
        if not neurons:
            return []

        # Group neurons by their dominant latent label.
        label_votes: Dict[str, List[str]] = {}
        label_scores: Dict[str, float] = {}
        for neuron in neurons:
            latent = neuron.latent_states
            if not latent:
                continue
            dominant_label = max(latent, key=latent.get)
            label_votes.setdefault(dominant_label, []).append(neuron.cell_id)
            label_scores[dominant_label] = label_scores.get(dominant_label, 0.0) + latent[dominant_label]

        if not label_scores:
            return []

        total_score = sum(label_scores.values())
        hypotheses: List[CORHypothesis] = []
        for idx, (label, score) in enumerate(
            sorted(label_scores.items(), key=lambda x: x[1], reverse=True)[: self.max_hypotheses]
        ):
            prob = score / total_score if total_score > 0 else 0.0
            hypotheses.append(
                CORHypothesis(
                    hypothesis_id=f"cor_{self._tick}_{label}_{idx}",
                    label=label,
                    probability=prob,
                    source_neuron_ids=label_votes.get(label, []),
                    configuration={"dominant_label": label},
                    entropy=self._compute_entropy(),
                    coherence_delta=0.0,
                )
            )
        return hypotheses

    def _select_dominant(self, hypotheses: List[CORHypothesis]) -> Optional[CORHypothesis]:
        if not hypotheses:
            return None
        # Winner-take-all, with a small tie-breaker based on neuron count.
        return max(
            hypotheses,
            key=lambda h: (h.probability, len(h.source_neuron_ids)),
        )

    # ------------------------------------------------------------------ #
    # Collapse and reconfiguration
    # ------------------------------------------------------------------ #

    def _collapse_neurons_to(self, dominant: CORHypothesis) -> int:
        """Set each neuron's activation toward the dominant hypothesis."""
        label = dominant.configuration.get("dominant_label")
        count = 0
        for neuron in self._all_neurons():
            latent = getattr(neuron, "latent_states", None) or {}
            if label in latent:
                # Commit the neuron to the dominant latent state.
                boost = latent[label]
                neuron.activation = min(1.0, neuron.activation + boost * 0.5)
                neuron.cor_pressure = max(0.0, neuron.cor_pressure - 0.3)
                neuron.last_collapse_tick = self._tick
                count += 1
            else:
                # Suppress non-dominant alternatives.
                neuron.activation *= 0.8
        return count

    def _apply_reconfiguration(
        self, dominant: CORHypothesis
    ) -> Tuple[bool, Dict[str, Any]]:
        """Apply a safe, bounded reconfiguration after collapse.

        Conservative COR consolidation:
          - Only synapses recently active (pre/post spike timing recorded)
            and aligned with the dominant latent label are reinforced.
          - Reinforcement is routed through STDP when available, otherwise
            a tiny direct weight boost is applied.
          - Latent states are trimmed to free capacity.
        """
        summary: Dict[str, Any] = {"label": dominant.label}
        changes = 0
        stdp_changes = 0
        direct_changes = 0

        if not hasattr(self.circuit, "synapses"):
            return True, summary

        label = dominant.configuration.get("dominant_label")
        neuron_map = {n.cell_id: n for n in self._all_neurons()}

        # Conservative reinforcement: only recently active synapses
        # that connect neurons sharing the dominant label.
        for synapse in self.circuit.synapses:
            src = neuron_map.get(getattr(synapse, "source", None))
            tgt = neuron_map.get(getattr(synapse, "target", None))
            if src is None or tgt is None:
                continue
            src_latent = getattr(src, "latent_states", None) or {}
            tgt_latent = getattr(tgt, "latent_states", None) or {}
            if label not in src_latent or label not in tgt_latent:
                continue

            # Prefer STDP-based reinforcement for synapses with timing evidence.
            has_timing = (
                getattr(synapse, "last_pre_spike_tick", None) is not None
                and getattr(synapse, "last_post_spike_tick", None) is not None
            )
            if has_timing and self.stdp_engine is not None:
                delta_ticks = synapse.last_post_spike_tick - synapse.last_pre_spike_tick
                update = self.stdp_engine.update_synapse(
                    synapse,
                    delta_ticks=delta_ticks,
                    dopamine=0.3,  # moderate consolidation signal
                    base_plasticity=self.synaptic_reinforcement_rate,
                )
                if abs(update["delta"]) > 1e-9:
                    stdp_changes += 1
                    changes += 1
                    continue

            # Fallback: tiny direct weight boost bounded to avoid runaway growth.
            weight = getattr(synapse, "weight", 0.5)
            boost = self.synaptic_reinforcement_rate * 0.3
            new_weight = min(1.0, weight + boost)
            setattr(synapse, "weight", new_weight)
            # Also nudge trust in the same direction.
            trust = getattr(synapse, "trust", 0.5)
            setattr(synapse, "trust", min(1.0, trust + boost * 0.5))
            direct_changes += 1
            changes += 1

        summary["synapses_strengthened"] = changes
        summary["stdp_reinforced"] = stdp_changes
        summary["direct_reinforced"] = direct_changes

        # Trim weakest latent states to free capacity.
        for neuron in self._all_neurons():
            if len(getattr(neuron, "latent_states", {})) > self.min_latent_states:
                latent = neuron.latent_states
                sorted_items = sorted(latent.items(), key=lambda x: x[1], reverse=True)
                neuron.latent_states = dict(sorted_items[: self.min_latent_states])

        return True, summary

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _all_neurons(self) -> List[Any]:
        if self.circuit is None:
            return []
        return (
            list(getattr(self.circuit, "input_neurons", []))
            + list(getattr(self.circuit, "hidden_neurons", []))
            + list(getattr(self.circuit, "output_neurons", []))
        )

    def _has_sufficient_latent_states(self) -> bool:
        total = sum(
            len(getattr(n, "latent_states", {}) or {})
            for n in self._all_neurons()
        )
        return total >= self.min_latent_states

    def _persist(self, result: CORResult) -> None:
        try:
            with open(self._report_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(result.to_dict(), ensure_ascii=False) + "\n")
        except Exception:
            pass

    def seed_latent_state(
        self,
        neuron_id: str,
        states: Dict[str, float],
    ) -> bool:
        """Manually seed latent states for a neuron (for tests / bootstrapping)."""
        neuron_map = {n.cell_id: n for n in self._all_neurons()}
        neuron = neuron_map.get(neuron_id)
        if neuron is None:
            return False
        neuron.latent_states = dict(states)
        return True

    def reset(self) -> None:
        """Clear COR history and latent states."""
        self._history.clear()
        self._last_collapse_tick = -self.collapse_refractory_ticks - 1
        for neuron in self._all_neurons():
            neuron.latent_states = {}
            neuron.cor_pressure = 0.0

    def generate_meta_event_payload(self) -> Dict[str, Any]:
        """Produce a payload suitable for MetacognitiveMonitor."""
        result = self.latest_result()
        if result is None:
            return {}
        return {
            "event": "cognitive_objective_reduction",
            "collapsed": result.collapsed,
            "dominant_label": (
                result.dominant_hypothesis.label if result.dominant_hypothesis else None
            ),
            "entropy_h": result.entropy_h,
            "coherence_phi": result.coherence_phi,
            "metacognitive_pressure_m": result.metacognitive_pressure_m,
        }
