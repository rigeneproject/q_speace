"""Fractal QCA cascade with coarse-grained (RG) signatures.

Implements the A+B framework agreed for Q-SPEACE:
  * Each level is a :class:`FractalQCA` with REAL long-range coupling
    (Option B: the d^-1.8 exponent is now effective).
  * Levels are coupled ONLY through coarse-grained signatures
    (coherence_phi, entropy S, sigma) — never through full quantum states.
    This is the renormalization-group / slaving-principle move that kills
    phantom coupling and the 2**64 explosion of the planet level (Option A
    architecture). Bottom-up = lower-level *variance* (noise) feeds the
    higher level; top-down = higher-level coherence seeds the lower level.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .fractal_qca import FractalQCA


@dataclass
class LevelSignature:
    """Coarse-grained order parameter crossing a scale membrane."""

    name: str
    n_qubits: int
    coherence_phi: float
    entropy_s: float
    sigma: float


class MacroLevel:
    """Planet/solar level kept signature-only (2**64 state is infeasible).

    It never holds a real quantum state; it only tracks the RG signature
    received from the topmost simulated level.
    """

    def __init__(
        self,
        name: str = "planet",
        n_qubits: int = 64,
        coherence_phi: float = 0.5,
        entropy_s: float = 0.5,
        sigma: float = 0.0,
    ) -> None:
        self.name = name
        self.n_qubits = n_qubits
        self.coherence_phi = coherence_phi
        self.entropy_s = entropy_s
        self.sigma = sigma

    def couple(self, lower_sigma: float, upper_phi: float | None = None) -> None:
        """Bottom-up noise raises sigma; top-down coherence seeds phi."""
        self.sigma = 0.5 * self.sigma + 0.5 * lower_sigma
        if upper_phi is not None:
            self.coherence_phi = 0.5 * self.coherence_phi + 0.5 * upper_phi

    def signature(self) -> LevelSignature:
        return LevelSignature(
            self.name, self.n_qubits, self.coherence_phi, self.entropy_s, self.sigma
        )


class FractalQCACascade:
    """Multi-scale QCA coupled through coarse-grained signatures (RG)."""

    def __init__(self, level_sizes: tuple[int, ...] = (2, 8), seed: int = None) -> None:
        self.real_levels = [FractalQCA(n, seed=seed) for n in level_sizes]
        self.macro_levels: list[MacroLevel] = []
        self.history: list[list[LevelSignature]] = []

    def add_macro_level(self, n_qubits: int = 64, name: str = "planet") -> MacroLevel:
        m = MacroLevel(name=name, n_qubits=n_qubits)
        self.macro_levels.append(m)
        return m

    def step(self, external_ds: list[float] | None = None) -> list[LevelSignature]:
        n = len(self.real_levels)
        ds = external_ds or [0.1] * n
        for k in range(n):
            self.real_levels[k].step(delta_s_info=ds[k])
        sigs = [lvl.signature() for lvl in self.real_levels]

        # Bottom-up: lower-level variance (noise) raises the upper level.
        for k in range(n - 1):
            self.real_levels[k + 1].inject_noise(sigs[k].sigma)
        # Top-down: upper-level coherence seeds the lower level.
        for k in range(n - 1, 0, -1):
            self.real_levels[k - 1].seed_from(sigs[k].coherence_phi)
        # Macro (planet) levels couple to the topmost simulated signature.
        if self.macro_levels and sigs:
            top = sigs[-1]
            for m in self.macro_levels:
                m.couple(lower_sigma=top.sigma)

        self.history.append(sigs)
        return sigs

    def run(
        self, ticks: int = 10, external_ds: list[float] | None = None
    ) -> list[list[LevelSignature]]:
        return [self.step(external_ds) for _ in range(ticks)]


def experiment_cross_scale(
    ticks: int = 20, atom_noise: float = 0.2, seed: int = None
) -> tuple[float, float]:
    """Empirical proof of cross-scale emergence (Option A crux).

    Runs the cascade twice: a baseline (natural atomic noise only) and a
    perturbed run where extra noise is injected at the atom level every
    tick. Returns (brain_sigma_baseline, brain_sigma_noisy). If the noisy
    brain sigma is significantly larger, atomic noise has propagated upward
    — i.e. cross-scale emergence, not just local connectivity.
    """
    baseline = FractalQCACascade(level_sizes=(2, 8), seed=seed)
    for _ in range(ticks):
        baseline.step()
    brain_sigma_baseline = baseline.real_levels[1].signature().sigma

    noisy = FractalQCACascade(level_sizes=(2, 8), seed=seed)
    for _ in range(ticks):
        noisy.real_levels[0].inject_noise(atom_noise)
        noisy.step()
    brain_sigma_noisy = noisy.real_levels[1].signature().sigma

    return brain_sigma_baseline, brain_sigma_noisy


def qi_bridge_cqasm(
    atom_coherence: float = 0.5,
    brain_seed: float = 0.5,
    version: str = "1.0",
) -> str:
    """5-qubit cQASM for Starmon-5: phi_bridge + bottom-up/top-down demo.

    Qubits 0-1 = atom level, 2-4 = brain level. A CNOT from atom_1 to
    brain_0 is the cross-scale phi_bridge. Rotation angles encode the
    coarse-grained signatures passed across the membrane.
    """
    from .quantum import BrainQuantumCircuit, GateType
    from .quantum.backends import to_cqasm

    circ = BrainQuantumCircuit("qi_bridge")
    for r in ("atom_0", "atom_1", "brain_0", "brain_1", "brain_2"):
        circ.add_qubit(r)
    for r in ("atom_0", "atom_1", "brain_0", "brain_1", "brain_2"):
        circ.add_gate(GateType.H, target=r)
    # intra-region entanglement
    circ.add_gate(GateType.CNOT, control="atom_0", target="atom_1")
    circ.add_gate(GateType.CNOT, control="brain_0", target="brain_1")
    circ.add_gate(GateType.CNOT, control="brain_1", target="brain_2")
    # phi_bridge: atom -> brain cross-scale coupling
    circ.add_gate(GateType.CNOT, control="atom_1", target="brain_0")
    # signature-driven rotations (coarse-grained params crossing membrane)
    circ.add_gate(GateType.RY, target="atom_0", angle=float(np.pi * atom_coherence))
    circ.add_gate(GateType.RY, target="brain_2", angle=float(np.pi * brain_seed))
    return to_cqasm(circ, version=version)
