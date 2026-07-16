"""MicrobiomeModulator — digital microbiota population model.

Maintains a population of digital microbial strains that consume
substrate and produce metabolites.  Population dynamics respond to:

- Available substrate (excess patterns, cached data, waste)
- Stress level (efferent signal from brain)
- Competition between strains (shared substrate pool)
"""

from __future__ import annotations

import math
import random
from typing import Dict, List, Optional

from speace_core.cellular_brain.enteroception.strain_definitions import (
    DEFAULT_STRAINS,
    MicrobialStrain,
)


class MicrobiomeModulator:
    def __init__(
        self,
        strains: Optional[Dict[str, MicrobialStrain]] = None,
        substrate_capacity: float = 100.0,
        diversity_threshold: float = 0.4,
        stress_suppression_factor: float = 0.3,
        metabolite_decay: float = 0.95,
        seed: int = 42,
    ):
        self._strains: Dict[str, MicrobialStrain] = {
            k: s
            for k, s in (strains or DEFAULT_STRAINS).items()
        }
        self._substrate_capacity = substrate_capacity
        self._diversity_threshold = diversity_threshold
        self._stress_suppression_factor = stress_suppression_factor
        self._metabolite_decay = metabolite_decay
        self._rng = random.Random(seed)

        self.substrate: float = 10.0
        self.metabolites: Dict[str, float] = {
            "scfa": 0.0,
            "serotonin_precursor": 0.0,
            "gaba_precursor": 0.0,
            "dopamine_precursor": 0.0,
            "inflammatory_cytokine": 0.0,
            "novelty_signal": 0.0,
        }

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def tick(
        self,
        stress_level: float = 0.0,
        substrate_input: float = 0.0,
        coherence: float = 0.5,
    ) -> Dict[str, float]:
        """Advance the microbiome by one metabolic cycle.

        Args:
            stress_level: Global stress [0, 1] from ANS / drives.
            substrate_input: Fresh substrate added this tick.
            coherence: Current coherence phi — modulates metabolite yield.

        Returns:
            Updated metabolite levels.
        """
        self.substrate = min(self._substrate_capacity, self.substrate + substrate_input)

        self._apply_stress_suppression(stress_level)
        self._grow_strains()
        self._produce_metabolites(coherence)
        self._decay_metabolites()
        self._normalise_populations()

        return dict(self.metabolites)

    def get_diversity(self) -> float:
        """Shannon entropy of the strain population distribution."""
        pops = [s.population for s in self._strains.values()]
        total = sum(pops)
        if total == 0:
            return 0.0
        entropy = -sum(
            (p / total) * math.log(p / total + 1e-12) for p in pops if p > 0
        )
        max_entropy = math.log(len(pops))
        return entropy / max_entropy if max_entropy > 0 else 0.0

    def get_strain_summary(self) -> Dict[str, float]:
        return {name: s.population for name, s in self._strains.items()}

    def get_dominant_metabolites(self, top_n: int = 3) -> List[str]:
        sorted_m = sorted(self.metabolites, key=self.metabolites.get, reverse=True)
        return [m for m in sorted_m if self.metabolites.get(m, 0) > 0.01][:top_n]

    def reset(self, substrate: float = 10.0) -> None:
        self.substrate = substrate
        self.metabolites = {k: 0.0 for k in self.metabolites}
        for name, strain in self._strains.items():
            default = DEFAULT_STRAINS.get(name)
            strain.population = default.population if default else 0.0

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    def _apply_stress_suppression(self, stress: float) -> None:
        for strain in self._strains.values():
            suppression = stress * strain.stress_sensitivity * self._stress_suppression_factor
            strain.population *= max(0.05, 1.0 - suppression)

    def _grow_strains(self) -> None:
        total_pop = sum(s.population for s in self._strains.values())
        if total_pop == 0:
            return

        for strain in self._strains.values():
            if self.substrate <= 0:
                break

            affinity_factor = strain.substrate_affinity * (1.0 - total_pop / self._substrate_capacity)
            growth = strain.population * strain.growth_rate * affinity_factor
            consumed = growth * 0.5
            if consumed <= self.substrate:
                strain.population += growth
                self.substrate -= consumed
            else:
                strain.population += self.substrate * 2.0
                self.substrate = 0.0

        for strain in self._strains.values():
            decay = strain.population * strain.decay_rate
            strain.population -= decay

    def _produce_metabolites(self, coherence: float) -> None:
        for strain in self._strains.values():
            for met, yield_factor in strain.metabolite_profile.items():
                if met in self.metabolites:
                    coherence_mod = 0.5 + coherence * 0.5
                    produced = strain.population * yield_factor * coherence_mod
                    self.metabolites[met] = min(1.0, self.metabolites[met] + produced)

    def _decay_metabolites(self) -> None:
        for k in self.metabolites:
            self.metabolites[k] *= self._metabolite_decay

    def _normalise_populations(self) -> None:
        total = sum(s.population for s in self._strains.values())
        if total > 0:
            for s in self._strains.values():
                s.population = max(0.0, min(1.0, s.population / total))
