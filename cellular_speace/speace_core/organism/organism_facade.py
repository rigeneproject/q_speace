import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from speace_core.bootstrap.node_identity import NodeIdentityManager
from speace_core.cellular_brain.cognition.self_model import SelfModel
from speace_core.cellular_brain.identity_kernel import (
    AutobiographicalNarrativeEngine,
    IdentityKernel,
    OntogeneticStageTracker,
)
from speace_core.cellular_brain.organism.organism_lifecycle import OrganismLifecycleManager
from speace_core.cellular_brain.organism.organism_state_synthesizer import OrganismStateSynthesizer
from speace_core.cognitive_observatory.self_model import SelfModelEngine
from speace_core.dna.models import GenomeIdentity

IDENTITY_VECTOR_DIMENSIONS: List[str] = [
    "coherence_phi",
    "energy_level",
    "developmental_stage_norm",
    "clone_count_norm",
    "narrative_coherence",
    "metabolic_mode_norm",
    "health_score",
    "identity_divergence",
    "self_model_consistency",
    "bcel_coverage",
]

IDENTITY_VECTOR_SIZE = len(IDENTITY_VECTOR_DIMENSIONS)

METABOLIC_MODE_MAP: Dict[str, float] = {
    "critical": 0.0,
    "stress": 0.25,
    "conservation": 0.5,
    "recovery": 0.75,
    "normal": 1.0,
}


def _norm_stage(stage: str) -> float:
    stages = ["stage_0", "stage_1", "stage_2", "stage_3", "stage_4", "stage_5", "stage_6", "stage_7"]
    if stage in stages:
        return stages.index(stage) / max(1, len(stages) - 1)
    return 0.0


class Organism:
    def __init__(
        self,
        genome_identity: Optional[GenomeIdentity] = None,
        node_identity: Optional[NodeIdentityManager] = None,
        identity_kernel: Optional[IdentityKernel] = None,
        self_model_cognition: Optional[SelfModel] = None,
        self_model_observatory: Optional[SelfModelEngine] = None,
        lifecycle: Optional[OrganismLifecycleManager] = None,
        state_synthesizer: Optional[OrganismStateSynthesizer] = None,
        storage_path: str = "data/organism",
    ):
        self._storage = Path(storage_path)
        self._storage.mkdir(parents=True, exist_ok=True)

        self._genome_identity = genome_identity or GenomeIdentity()
        self._node_identity = node_identity or NodeIdentityManager()
        self._identity_kernel = identity_kernel or IdentityKernel()
        self._self_model_cognition = self_model_cognition or SelfModel()
        self._self_model_observatory = self_model_observatory or SelfModelEngine()
        self._lifecycle = lifecycle or OrganismLifecycleManager()
        self._state_synthesizer = state_synthesizer or OrganismStateSynthesizer()

        self._organism_id: str = self._load_or_create_organism_id()
        self._birth_tick: int = 0
        self._identity_vector: List[float] = [0.0] * IDENTITY_VECTOR_SIZE
        self._last_divergence: float = 0.0

    @property
    def organism_id(self) -> str:
        return self._organism_id

    @property
    def identity_vector(self) -> List[float]:
        return list(self._identity_vector)

    @property
    def genome_identity(self) -> GenomeIdentity:
        return self._genome_identity

    @property
    def lifecycle(self) -> OrganismLifecycleManager:
        return self._lifecycle

    @property
    def identity_kernel(self) -> IdentityKernel:
        return self._identity_kernel

    def _load_or_create_organism_id(self) -> str:
        id_file = self._storage / "organism_id.json"
        if id_file.exists():
            try:
                data = json.loads(id_file.read_text(encoding="utf-8"))
                return data["organism_id"]
            except Exception:
                pass
        seed = f"{self._genome_identity.entity_name}:{self._node_identity.generate_node_id()}:{datetime.now(timezone.utc).isoformat()}"
        oid = str(uuid.uuid5(uuid.NAMESPACE_DNS, seed))
        id_file.write_text(json.dumps({"organism_id": oid, "created_at": datetime.now(timezone.utc).isoformat()}, indent=2), encoding="utf-8")
        return oid

    def update(self, orchestrator: Any = None) -> None:
        if orchestrator is None:
            return

        metrics = getattr(orchestrator, "latest_metrics", {})
        if not isinstance(metrics, dict):
            metrics = {}

        coherence = metrics.get("coherence_phi", 0.0)
        energy = metrics.get("mean_energy", 0.5)
        tick = getattr(orchestrator, "current_tick", 0)

        developmental = self._identity_kernel.stage_tracker.current_stage
        clone_count = getattr(orchestrator, "clone_count", 1)
        metabolic_mode = metrics.get("metabolic_mode", "normal")
        health = metrics.get("health_score", 1.0)
        bcel_cov = metrics.get("bcel_coverage", 0.0)

        raw_divergence = abs(self._identity_kernel.last_coherence.coherence_score - 1.0) if self._identity_kernel.last_coherence else 0.0

        self_model_consistency = 0.5
        cci = getattr(orchestrator, "_cci", None)
        if cci is not None:
            if hasattr(cci, "c_identity"):
                self_model_consistency = cci.c_identity

        self._identity_vector = [
            min(1.0, max(0.0, coherence)),
            min(1.0, max(0.0, energy)),
            _norm_stage(developmental),
            min(1.0, max(0.0, clone_count / 10.0)),
            min(1.0, max(0.0, 1.0 - raw_divergence)),
            METABOLIC_MODE_MAP.get(metabolic_mode, 0.5),
            min(1.0, max(0.0, health)),
            min(1.0, max(0.0, 1.0 - raw_divergence)),
            min(1.0, max(0.0, self_model_consistency)),
            min(1.0, max(0.0, bcel_cov)),
        ]

        state_snapshot = {
            "identity_vector": self._identity_vector,
            "developmental_stage": developmental,
            "coherence_phi": coherence,
            "event": "organism_update",
            "metadata": {"tick": tick, "organism_id": self._organism_id},
        }
        self._self_model_cognition.update(state_snapshot)

        genome_state = {
            "entity_name": self._genome_identity.entity_name,
            "nature": self._genome_identity.nature,
            "core_function": self._genome_identity.core_function,
        }
        self._self_model_observatory.update_identity(genome_state)

        lifecycle_state = self._lifecycle.classify_lifecycle_state(
            health_score=health,
            metabolic_mode=metabolic_mode,
            safety_risk=metrics.get("safety_risk_score", 0.0),
        )
        self._lifecycle.transition_to(lifecycle_state, reason="organism_tick_update")

    def is_self(self, candidate_vector: List[float], threshold: float = 0.15) -> bool:
        if not candidate_vector or len(candidate_vector) != IDENTITY_VECTOR_SIZE:
            return False
        dist = sum((a - b) ** 2 for a, b in zip(self._identity_vector, candidate_vector)) ** 0.5
        return dist < threshold

    def self_distance(self, candidate_vector: List[float]) -> float:
        if not candidate_vector or len(candidate_vector) != IDENTITY_VECTOR_SIZE:
            return 1.0
        return sum((a - b) ** 2 for a, b in zip(self._identity_vector, candidate_vector)) ** 0.5

    def get_identity_signature(self) -> Dict[str, Any]:
        return {
            "organism_id": self._organism_id,
            "entity_name": self._genome_identity.entity_name,
            "identity_vector": self._identity_vector,
            "dimensions": IDENTITY_VECTOR_DIMENSIONS,
            "developmental_stage": self._identity_kernel.stage_tracker.current_stage,
            "lifecycle_state": self._lifecycle.current_state,
            "self_model_entries": len(self._self_model_cognition.coherence_history),
        }

    def get_identity_digest(self) -> str:
        return hashlib.sha256(
            json.dumps(self._identity_vector, sort_keys=True).encode()
        ).hexdigest()[:16]

    def snapshot(self) -> Dict[str, Any]:
        return {
            "organism_id": self._organism_id,
            "identity_vector": self._identity_vector,
            "developmental_stage": self._identity_kernel.stage_tracker.current_stage,
            "lifecycle_state": self._lifecycle.current_state,
            "birth_tick": self._birth_tick,
            "identity_digest": self.get_identity_digest(),
        }
