import copy
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DigitalDNAVariant(BaseModel):
    variant_id: str = Field(default_factory=lambda: f"ddna_{uuid.uuid4().hex[:12]}")
    parent_id: Optional[str] = None
    generation: int = 0
    mutation_rate: float = 1.0
    routing_gain: float = 1.0
    plasticity_gain: float = 1.0
    inhibition_decay: float = 1.0
    neurogenesis_rate: float = 1.0
    perturbation_strength: float = 0.1

    # T-COR — Cognitive Objective Reduction genes
    cor_enabled: bool = False
    cor_phi_threshold_factor: float = 0.55
    cor_min_latent_states: int = 2
    cor_max_hypotheses: int = 8
    cor_collapse_refractory_ticks: int = 10

    fitness_score: float = 0.0
    entropy_before: float = 0.0
    entropy_after: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DigitalDNAExpressionManager:
    """T55 — Manage digital DNA variants, mutation, and selection."""

    def __init__(self, report_dir: str = "reports/evolutionary_kernel"):
        self.report_dir = Path(report_dir)
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self._variants: List[DigitalDNAVariant] = []
        self._selected: Optional[DigitalDNAVariant] = None
        self._generation_counter: int = 0

    # ------------------------------------------------------------------ #
    # Variant factory
    # ------------------------------------------------------------------ #

    def create_variant(
        self,
        parent: Optional[DigitalDNAVariant] = None,
        parameter_changes: Optional[Dict[str, float]] = None,
    ) -> DigitalDNAVariant:
        base = parent if parent is not None else DigitalDNAVariant()
        variant = DigitalDNAVariant(
            parent_id=base.variant_id if parent else None,
            generation=base.generation + 1,
            mutation_rate=base.mutation_rate,
            routing_gain=base.routing_gain,
            plasticity_gain=base.plasticity_gain,
            inhibition_decay=base.inhibition_decay,
            neurogenesis_rate=base.neurogenesis_rate,
            perturbation_strength=base.perturbation_strength,
            cor_enabled=base.cor_enabled,
            cor_phi_threshold_factor=base.cor_phi_threshold_factor,
            cor_min_latent_states=base.cor_min_latent_states,
            cor_max_hypotheses=base.cor_max_hypotheses,
            cor_collapse_refractory_ticks=base.cor_collapse_refractory_ticks,
        )
        if parameter_changes:
            for key, value in parameter_changes.items():
                if hasattr(variant, key):
                    setattr(variant, key, value)
        self._variants.append(variant)
        self._generation_counter = max(self._generation_counter, variant.generation)
        return variant

    # ------------------------------------------------------------------ #
    # Mutation operators
    # ------------------------------------------------------------------ #

    def mutate_variant(
        self,
        variant: DigitalDNAVariant,
        mutation_sigma: float = 0.1,
    ) -> DigitalDNAVariant:
        import random
        changes: Dict[str, Any] = {}
        for param in ["mutation_rate", "routing_gain", "plasticity_gain", "inhibition_decay", "neurogenesis_rate", "cor_phi_threshold_factor"]:
            current = getattr(variant, param)
            delta = random.gauss(0.0, mutation_sigma)
            changes[param] = max(0.1, min(2.0, current + delta))
        # COR integer parameters
        for param in ["cor_min_latent_states", "cor_max_hypotheses", "cor_collapse_refractory_ticks"]:
            current = getattr(variant, param)
            delta = random.randint(-1, 1)
            changes[param] = max(1, current + delta)
        # COR boolean toggle
        if random.random() < 0.1:
            changes["cor_enabled"] = not variant.cor_enabled
        return self.create_variant(parent=variant, parameter_changes=changes)

    def crossover_variants(
        self,
        a: DigitalDNAVariant,
        b: DigitalDNAVariant,
    ) -> DigitalDNAVariant:
        import random
        changes: Dict[str, Any] = {}
        for param in [
            "mutation_rate", "routing_gain", "plasticity_gain", "inhibition_decay",
            "neurogenesis_rate", "cor_phi_threshold_factor",
            "cor_min_latent_states", "cor_max_hypotheses", "cor_collapse_refractory_ticks",
        ]:
            changes[param] = getattr(random.choice([a, b]), param)
        changes["cor_enabled"] = random.choice([a, b]).cor_enabled
        child = self.create_variant(parent=a, parameter_changes=changes)
        child.parent_id = f"cross({a.variant_id},{b.variant_id})"
        return child

    # ------------------------------------------------------------------ #
    # Selection
    # ------------------------------------------------------------------ #

    def select_best_variant(self) -> Optional[DigitalDNAVariant]:
        if not self._variants:
            return None
        best = max(self._variants, key=lambda v: v.fitness_score)
        self._selected = best
        return best

    def evaluate_fitness(
        self,
        variant: DigitalDNAVariant,
        coherence_phi: float,
        mean_energy: float,
        cognitive_score: float,
    ) -> float:
        fitness = (
            0.35 * coherence_phi
            + 0.25 * mean_energy
            + 0.25 * cognitive_score
            + 0.10 * max(0.0, 1.0 - abs(variant.entropy_after - variant.entropy_before))
            + 0.05 * (1.0 - variant.perturbation_strength)
        )
        variant.fitness_score = fitness
        return fitness

    # ------------------------------------------------------------------ #
    # Expression → parameter dict
    # ------------------------------------------------------------------ #

    @staticmethod
    def express(variant: DigitalDNAVariant) -> Dict[str, Any]:
        return {
            "mutation_rate": variant.mutation_rate,
            "routing_gain": variant.routing_gain,
            "plasticity_gain": variant.plasticity_gain,
            "inhibition_decay": variant.inhibition_decay,
            "neurogenesis_rate": variant.neurogenesis_rate,
            "perturbation_strength": variant.perturbation_strength,
            "cor_enabled": variant.cor_enabled,
            "cor_phi_threshold_factor": variant.cor_phi_threshold_factor,
            "cor_min_latent_states": variant.cor_min_latent_states,
            "cor_max_hypotheses": variant.cor_max_hypotheses,
            "cor_collapse_refractory_ticks": variant.cor_collapse_refractory_ticks,
        }

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #

    def save_variants(self) -> Path:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = self.report_dir / f"ddna_variants_{timestamp}.json"
        data = [v.model_dump() for v in self._variants]
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return path

    def load_variants(self, path: Path) -> None:
        data = json.loads(path.read_text(encoding="utf-8"))
        self._variants = [DigitalDNAVariant.model_validate(v) for v in data]
