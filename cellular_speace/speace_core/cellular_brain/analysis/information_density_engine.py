"""InformationDensityEngine — T1: metrica di densità informativa per compartimento.

Calcola per ogni compartimento (BrainRegion, NeuralCircuit) la densità
informativa combinata come somma pesata di:
  - entropia di attivazione
  - entropia di distribuzione pesi sinaptici
  - densità di connettività (edge/possible)
  - diversità del segnale

La densità informativa e la connettività guidano transizioni di fase nella
produzione del pensiero (collegato a ThoughtPhaseTransitionEngine).
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class CompartmentInfoDensity:
    compartment_id: str
    compartment_type: str  # "region" | "circuit" | "tissue"
    activation_entropy: float = 0.0
    weight_entropy: float = 0.0
    connectivity_density: float = 0.0
    signal_diversity: float = 0.0
    combined_density: float = 0.0
    neuron_count: int = 0
    synapse_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class InformationDensityEngine:
    """Calcola metriche di densità informativa per compartimento.

    Usage::

        engine = InformationDensityEngine(circuit, region_connectome)
        report = engine.compute_all()
    """

    def __init__(
        self,
        circuit=None,
        region_connectome=None,
        entropy_base: float = 2.0,
        weights: Optional[Dict[str, float]] = None,
    ):
        self.circuit = circuit
        self.region_connectome = region_connectome
        self.entropy_base = entropy_base
        self.weights = weights or {
            "activation_entropy": 0.30,
            "weight_entropy": 0.25,
            "connectivity_density": 0.25,
            "signal_diversity": 0.20,
        }
        self._history: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------ #
    # Compartment-level metrics
    # ------------------------------------------------------------------ #

    def compute_region_density(self, region) -> CompartmentInfoDensity:
        """Calcola densità informativa per una BrainRegion."""
        neurons = self._get_region_neurons(region)
        synapses = self._get_region_synapses(region)

        act_entropy = self._activation_entropy(neurons)
        w_entropy = self._weight_entropy(synapses)
        conn_density = self._connectivity_density(neurons, synapses)
        sig_diversity = self._signal_diversity(neurons, synapses)

        combined = (
            self.weights["activation_entropy"] * act_entropy
            + self.weights["weight_entropy"] * w_entropy
            + self.weights["connectivity_density"] * conn_density
            + self.weights["signal_diversity"] * sig_diversity
        )

        return CompartmentInfoDensity(
            compartment_id=region.region_id,
            compartment_type="region",
            activation_entropy=round(act_entropy, 4),
            weight_entropy=round(w_entropy, 4),
            connectivity_density=round(conn_density, 4),
            signal_diversity=round(sig_diversity, 4),
            combined_density=round(combined, 4),
            neuron_count=len(neurons),
            synapse_count=len(synapses),
        )

    def compute_circuit_density(self) -> CompartmentInfoDensity:
        """Calcola densità informativa per il circuito principale."""
        if not self.circuit:
            return CompartmentInfoDensity(
                compartment_id="circuit_root",
                compartment_type="circuit",
            )

        all_neurons = (
            self.circuit.input_neurons
            + self.circuit.hidden_neurons
            + self.circuit.output_neurons
        )
        synapses = self.circuit.synapses

        act_entropy = self._activation_entropy(all_neurons)
        w_entropy = self._weight_entropy(synapses)
        conn_density = self._connectivity_density(all_neurons, synapses)
        sig_diversity = self._signal_diversity(all_neurons, synapses)

        combined = (
            self.weights["activation_entropy"] * act_entropy
            + self.weights["weight_entropy"] * w_entropy
            + self.weights["connectivity_density"] * conn_density
            + self.weights["signal_diversity"] * sig_diversity
        )

        return CompartmentInfoDensity(
            compartment_id="circuit_root",
            compartment_type="circuit",
            activation_entropy=round(act_entropy, 4),
            weight_entropy=round(w_entropy, 4),
            connectivity_density=round(conn_density, 4),
            signal_diversity=round(sig_diversity, 4),
            combined_density=round(combined, 4),
            neuron_count=len(all_neurons),
            synapse_count=len(synapses),
        )

    # ------------------------------------------------------------------ #
    # Core metric calculations
    # ------------------------------------------------------------------ #

    def _activation_entropy(self, neurons: list) -> float:
        """Shannon entropy of activation distribution in a compartment."""
        if not neurons:
            return 0.0

        activations = [getattr(n, "activation", 0.0) for n in neurons]
        # Discretize into 20 bins
        bins = [0.0] * 20
        for a in activations:
            idx = min(int(abs(a) * 20), 19)
            bins[idx] += 1.0

        total = sum(bins)
        if total == 0:
            return 0.0

        probs = [c / total for c in bins if c > 0]
        if not probs:
            return 0.0

        entropy = -sum(p * math.log(p, self.entropy_base) for p in probs)
        max_entropy = math.log(len(bins), self.entropy_base)
        return entropy / max_entropy if max_entropy > 0 else 0.0

    def _weight_entropy(self, synapses: list) -> float:
        """Shannon entropy of synaptic weight distribution."""
        if not synapses:
            return 0.0

        weights = [getattr(s, "weight", 0.0) for s in synapses]
        # Discretize into 20 bins
        bins = [0.0] * 20
        for w in weights:
            idx = min(int(abs(w) * 20), 19)
            bins[idx] += 1.0

        total = sum(bins)
        if total == 0:
            return 0.0

        probs = [c / total for c in bins if c > 0]
        if not probs:
            return 0.0

        entropy = -sum(p * math.log(p, self.entropy_base) for p in probs)
        max_entropy = math.log(len(bins), self.entropy_base)
        return entropy / max_entropy if max_entropy > 0 else 0.0

    def _connectivity_density(self, neurons: list, synapses: list) -> float:
        """Rapporto tra connessioni effettive e possibili."""
        n = len(neurons)
        if n < 2:
            return 0.0

        # Build adjacency set
        adj: set[tuple[str, str]] = set()
        seen_ids: set[str] = {getattr(n, "cell_id", f"n_{i}") for i, n in enumerate(neurons)}
        for s in synapses:
            src = getattr(s, "source", None) or getattr(s, "source_id", None)
            tgt = getattr(s, "target", None) or getattr(s, "target_id", None)
            if src and tgt and src in seen_ids and tgt in seen_ids:
                adj.add((src, tgt))

        max_possible = n * (n - 1)
        actual = len(adj)
        return actual / max_possible if max_possible > 0 else 0.0

    def _signal_diversity(self, neurons: list, synapses: list) -> float:
        """Unique signal types / total signals."""
        signal_types: set[str] = set()
        total = 0

        for n in neurons:
            sig = getattr(n, "signal_type", None) or getattr(n, "cell_type", None)
            if sig:
                signal_types.add(str(sig))
                total += 1

        if total == 0:
            return 0.0

        return len(signal_types) / total

    # ------------------------------------------------------------------ #
    # Composite
    # ------------------------------------------------------------------ #

    def compute_all(self) -> Dict[str, Any]:
        """Calcola densità per tutti i compartimenti disponibili."""
        compartments: List[CompartmentInfoDensity] = []

        compartments.append(self.compute_circuit_density())

        if self.region_connectome and hasattr(self.region_connectome, "regions"):
            regions_dict = self.region_connectome.regions
            for region in regions_dict.values():
                if hasattr(region, "region_id"):
                    compartments.append(self.compute_region_density(region))

        densities = [c.combined_density for c in compartments if c.neuron_count > 0]

        report = {
            "timestamp": __import__("time").time(),
            "compartments": {
                c.compartment_id: {
                    "type": c.compartment_type,
                    "activation_entropy": c.activation_entropy,
                    "weight_entropy": c.weight_entropy,
                    "connectivity_density": c.connectivity_density,
                    "signal_diversity": c.signal_diversity,
                    "combined_density": c.combined_density,
                    "neuron_count": c.neuron_count,
                    "synapse_count": c.synapse_count,
                }
                for c in compartments
            },
            "global_avg_density": round(sum(densities) / len(densities), 4) if densities else 0.0,
            "global_max_density": round(max(densities), 4) if densities else 0.0,
            "global_min_density": round(min(densities), 4) if densities else 0.0,
            "n_compartments": len(compartments),
        }

        self._history.append(report)
        return report

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._history[-limit:]

    def get_density_trend(self, compartment_id: str = "circuit_root") -> List[float]:
        return [
            r["compartments"].get(compartment_id, {}).get("combined_density", 0.0)
            for r in self._history[-100:]
        ]

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _get_region_neurons(self, region) -> list:
        if not self.circuit:
            return []
        all_n = (
            self.circuit.input_neurons
            + self.circuit.hidden_neurons
            + self.circuit.output_neurons
        )
        neuron_ids = set(region.neuron_ids or [])
        return [n for n in all_n if n.cell_id in neuron_ids]

    def _get_region_synapses(self, region) -> list:
        if not self.circuit:
            return []
        neuron_ids = set(region.neuron_ids or [])
        return [
            s for s in self.circuit.synapses
            if (getattr(s, "source", None) or getattr(s, "source_id", None)) in neuron_ids
            and (getattr(s, "target", None) or getattr(s, "target_id", None)) in neuron_ids
        ]
