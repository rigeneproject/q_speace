"""Schumann resonance experiment (task T19).

Builds a small quantum register, entangles it (Hadamard + CNOT as the
"connective tissue" of the organism), drives parametric rotations with
real Earth signals, and measures whether stable fractal patterns emerge
or the state collapses into chaos (tracked via coherence_phi).
"""
from __future__ import annotations

import numpy as np

from .earth_feed import EarthFeed, EarthSignals
from .quantum import BrainQuantumCircuit, GateType, QuantumBrainSimulator


def schumann_circuit(num_qubits: int = 4, angles: dict[str, float] = None) -> BrainQuantumCircuit:
    """Create the Schumann-resonance circuit: H + CNOT lattice + rotations."""
    angles = angles or {}
    circ = BrainQuantumCircuit(name="schumann_resonance")
    for i in range(num_qubits):
        circ.add_qubit(f"neuron_{i}")
    # Superposition + entanglement (connective tissue).
    for i in range(num_qubits):
        circ.add_gate(GateType.H, target=f"neuron_{i}")
    for i in range(num_qubits - 1):
        circ.add_gate(GateType.CNOT, control=f"neuron_{i}", target=f"neuron_{i + 1}")
    # Earth-driven parametric rotations.
    rx = angles.get("rx", 0.0)
    ry = angles.get("ry", 0.0)
    rz = angles.get("rz", 0.0)
    for i in range(num_qubits):
        circ.add_gate(GateType.RX, target=f"neuron_{i}", angle=rx)
        circ.add_gate(GateType.RY, target=f"neuron_{i}", angle=ry)
        circ.add_gate(GateType.RZ, target=f"neuron_{i}", angle=rz)
    return circ


def run_schumann(
    num_qubits: int = 4, ticks: int = 10, use_network: bool = False, seed: int = None
) -> dict[str, object]:
    """Run the Schumann experiment across ticks; return measurements + metrics."""
    feed = EarthFeed(use_network=use_network, seed=seed)
    sim = QuantumBrainSimulator(seed=seed)
    coherence_trace: list[float] = []
    last_measurements: list[tuple[str, str]] = []

    import math

    for t in range(ticks):
        signals: EarthSignals = feed.fetch(t)
        circ = schumann_circuit(num_qubits, signals.rotation_angles())
        measurements = sim.run(circ)
        state = sim.state(circ)
        probs = state.probabilities()
        nz = probs[probs > 0]
        entropy = float(-np.sum(nz * np.log(nz)))
        max_ent = math.log(2 ** num_qubits)
        coherence = 1.0 - (entropy / max_ent if max_ent > 0 else 0.0)
        coherence_trace.append(float(coherence))
        last_measurements = measurements

    return {
        "num_qubits": num_qubits,
        "ticks": ticks,
        "coherence_trace": coherence_trace,
        "mean_coherence": float(sum(coherence_trace) / len(coherence_trace)),
        "last_measurements": last_measurements,
    }
