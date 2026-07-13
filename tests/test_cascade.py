"""Tests for the Fractal QCA cascade (A+B framework, RG signatures)."""
from __future__ import annotations

import numpy as np

from q_speace.fractal_qca import FractalQCA
from q_speace.fractal_qca_cascade import (
    FractalQCACascade,
    LevelSignature,
    MacroLevel,
    experiment_cross_scale,
    qi_bridge_cqasm,
)


def test_fractal_qca_long_range_runs():
    q = FractalQCA(num_cells=8, seed=1)
    res = q.run(ticks=5)
    assert len(res) == 5
    for r in res:
        assert 0.0 <= r.coherence_phi <= 1.0


def test_signature_has_sigma():
    q = FractalQCA(num_cells=8, seed=2)
    sig = q.signature()
    assert isinstance(sig, LevelSignature)
    assert sig.n_qubits == 8
    assert sig.sigma >= 0.0


def test_inject_noise_raises_variance():
    q = FractalQCA(num_cells=8, seed=3)
    before = q.signature().sigma
    q.inject_noise(0.3)
    after = q.signature().sigma
    assert after > before


def test_cascade_runs_and_couples():
    c = FractalQCACascade(level_sizes=(2, 8), seed=4)
    c.add_macro_level(n_qubits=64, name="planet")
    sigs = c.run(ticks=5)
    assert len(sigs) == 5
    # both real levels + macro tracked
    assert len(sigs[0]) == 2
    assert c.macro_levels[0].sigma >= 0.0


def test_cross_scale_emergence():
    base, noisy = experiment_cross_scale(ticks=20, atom_noise=0.2, seed=7)
    # Atomic noise must propagate upward to the brain level.
    assert noisy > base


def test_qi_bridge_cqasm_valid():
    cqasm = qi_bridge_cqasm(atom_coherence=0.5, brain_seed=0.5, version="1.0")
    assert cqasm.startswith("version 1.0")
    assert "qubits 5" in cqasm
    # the phi_bridge cross-scale CNOT is present
    assert "CNOT q[1], q[2]" in cqasm
    assert "measure q[4]" in cqasm
