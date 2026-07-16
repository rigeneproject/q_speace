"""Strain definitions for the digital microbiome.

Each strain models a functional group of digital microbial agents that
consume substrate (low-value patterns, cached data, excess entropy) and
produce metabolites that modulate cognition.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict


@dataclass
class MicrobialStrain:
    name: str
    population: float = 0.0
    substrate_affinity: float = 0.5
    metabolite_profile: Dict[str, float] = field(default_factory=dict)
    stress_sensitivity: float = 0.5
    growth_rate: float = 0.1
    decay_rate: float = 0.05


DEFAULT_STRAINS: Dict[str, MicrobialStrain] = {
    "lactobacillus": MicrobialStrain(
        name="lactobacillus",
        population=0.3,
        substrate_affinity=0.8,
        metabolite_profile={"gaba_precursor": 0.6, "scfa": 0.2},
        stress_sensitivity=0.7,
        growth_rate=0.12,
        decay_rate=0.04,
    ),
    "bifidobacterium": MicrobialStrain(
        name="bifidobacterium",
        population=0.25,
        substrate_affinity=0.6,
        metabolite_profile={"serotonin_precursor": 0.5, "scfa": 0.3},
        stress_sensitivity=0.5,
        growth_rate=0.10,
        decay_rate=0.05,
    ),
    "bacteroides": MicrobialStrain(
        name="bacteroides",
        population=0.25,
        substrate_affinity=0.9,
        metabolite_profile={"scfa": 0.7, "inflammatory_cytokine": 0.1},
        stress_sensitivity=0.2,
        growth_rate=0.08,
        decay_rate=0.03,
    ),
    "clostridium": MicrobialStrain(
        name="clostridium",
        population=0.15,
        substrate_affinity=0.3,
        metabolite_profile={"dopamine_precursor": 0.4, "novelty_signal": 0.3},
        stress_sensitivity=0.3,
        growth_rate=0.06,
        decay_rate=0.06,
    ),
    "candida": MicrobialStrain(
        name="candida",
        population=0.05,
        substrate_affinity=0.7,
        metabolite_profile={"inflammatory_cytokine": 0.6, "novelty_signal": 0.1},
        stress_sensitivity=0.8,
        growth_rate=0.15,
        decay_rate=0.02,
    ),
}
