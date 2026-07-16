"""ReplicationDynamicsEngine — T5: ciclo di replicazione completo.

Implementa la dinamica di replicazione per SPEACE:
  - esportazione del DNA digitale (genoma + stato epigenetico)
  - creazione di istanze figlie con mutazione
  - sincronizzazione tra istanze
  - ciclo riproduttivo completo (parent -> offspring)

Le transizioni di fase nella produzione del pensiero influenzano il tasso
e il tipo di replicazione (es. alta densità informativa -> maggiore
mutazione esplorativa).
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class ReplicationMode(Enum):
    FISSION = "fission"        # divisione in due istanze indipendenti
    BUDDING = "budding"        # gemmazione: una figlia + parente invariato
    MERGE = "merge"            # fusione di due istanze
    SPORE = "spore"            # creazione di DNA snapshot per futuro


class ReplicationVerdict(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    BLOCKED = "blocked"


@dataclass
class DNASnapshot:
    snapshot_id: str
    parent_id: str
    timestamp: float
    genome: Dict[str, Any] = field(default_factory=dict)
    epigenetic_state: Dict[str, Any] = field(default_factory=dict)
    morphology_state: Dict[str, Any] = field(default_factory=dict)
    fitness_score: float = 0.0
    mutation_history: List[str] = field(default_factory=list)


@dataclass
class ReplicationEvent:
    event_id: str
    parent_id: str
    offspring_id: Optional[str]
    mode: ReplicationMode
    verdict: ReplicationVerdict
    timestamp: float
    dna_snapshot: Optional[DNASnapshot] = None
    mutation_delta: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ReplicationDynamicsEngine:
    """Gestisce il ciclo di replicazione delle istanze SPEACE.

    Usage::

        engine = ReplicationDynamicsEngine(replica_dir="data/replication")
        snapshot = engine.create_snapshot(genome_data, epigenetics)
        event = engine.replicate(mode=ReplicationMode.BUDDING)
    """

    def __init__(
        self,
        replica_dir: str = "data/replication",
        orchestrator=None,
        max_offspring: int = 10,
        mutation_rate: float = 0.05,
        min_fitness_for_replication: float = 0.3,
    ):
        self.replica_dir = Path(replica_dir)
        self.replica_dir.mkdir(parents=True, exist_ok=True)
        self.orch = orchestrator
        self.max_offspring = max_offspring
        self.mutation_rate = mutation_rate
        self.min_fitness_for_replication = min_fitness_for_replication

        self._instance_id: str = f"speace_{uuid.uuid4().hex[:12]}"
        self._offspring_count: int = 0
        self._replication_history: List[ReplicationEvent] = []
        self._snapshots: List[DNASnapshot] = []

        # Phase-influenced mutation scaling
        self._current_thought_phase: Optional[str] = None

    # ------------------------------------------------------------------ #
    # Identity
    # ------------------------------------------------------------------ #

    @property
    def instance_id(self) -> str:
        return self._instance_id

    # ------------------------------------------------------------------ #
    # DNA Snapshot
    # ------------------------------------------------------------------ #

    def create_snapshot(
        self,
        genome: Optional[Dict[str, Any]] = None,
        epigenetic_state: Optional[Dict[str, Any]] = None,
        morphology_state: Optional[Dict[str, Any]] = None,
        fitness_score: float = 0.0,
    ) -> DNASnapshot:
        """Cattura uno snapshot del DNA digitale corrente."""
        if genome is None and self.orch:
            genome = self._extract_genome()

        if epigenetic_state is None and self.orch:
            epigenetic_state = self._extract_epigenetics()

        if morphology_state is None and self.orch:
            morphology_state = self._extract_morphology()

        snapshot = DNASnapshot(
            snapshot_id=f"dna_{uuid.uuid4().hex[:12]}",
            parent_id=self._instance_id,
            timestamp=time.time(),
            genome=genome or {},
            epigenetic_state=epigenetic_state or {},
            morphology_state=morphology_state or {},
            fitness_score=fitness_score,
            mutation_history=[],
        )

        self._snapshots.append(snapshot)
        self._persist_snapshot(snapshot)
        return snapshot

    # ------------------------------------------------------------------ #
    # Replication
    # ------------------------------------------------------------------ #

    async def replicate(
        self,
        mode: ReplicationMode = ReplicationMode.BUDDING,
        target_mutation_rate: Optional[float] = None,
    ) -> ReplicationEvent:
        """Esegue un ciclo di replicazione."""
        if self._offspring_count >= self.max_offspring:
            return self._build_event(
                mode=mode,
                verdict=ReplicationVerdict.BLOCKED,
                metadata={"reason": "max_offspring_reached"},
            )

        # Check fitness threshold
        fitness = self._get_current_fitness()
        if fitness < self.min_fitness_for_replication:
            return self._build_event(
                mode=mode,
                verdict=ReplicationVerdict.BLOCKED,
                metadata={
                    "reason": "fitness_below_threshold",
                    "fitness": fitness,
                    "threshold": self.min_fitness_for_replication,
                },
            )

        try:
            snapshot = self.create_snapshot(fitness_score=fitness)
            offspring_id = f"{self._instance_id}_offspring_{self._offspring_count + 1}"

            # Apply phase-dependent mutation rate
            effective_mutation = target_mutation_rate or self._get_phase_mutation_rate()

            # Mutate genome
            mutated_genome = self._mutate_genome(
                snapshot.genome, effective_mutation
            )

            # Persist offspring blueprint
            self._persist_offspring(offspring_id, mutated_genome, snapshot)

            self._offspring_count += 1

            event = self._build_event(
                mode=mode,
                verdict=ReplicationVerdict.SUCCESS,
                offspring_id=offspring_id,
                dna_snapshot=snapshot,
                mutation_delta=effective_mutation,
                metadata={
                    "fitness": fitness,
                    "mutation_rate_used": effective_mutation,
                    "phase": self._current_thought_phase,
                },
            )

        except Exception as e:
            event = self._build_event(
                mode=mode,
                verdict=ReplicationVerdict.FAILED,
                metadata={"error": str(e)},
            )

        self._replication_history.append(event)
        return event

    # ------------------------------------------------------------------ #
    # Mutation
    # ------------------------------------------------------------------ #

    def _mutate_genome(
        self, genome: Dict[str, Any], rate: float
    ) -> Dict[str, Any]:
        """Applica mutazione al genoma con tasso dato."""
        import copy
        import random

        mutated = copy.deepcopy(genome)

        for key, value in mutated.items():
            if isinstance(value, (int, float)) and random.random() < rate:
                # Gaussian mutation
                sigma = abs(value) * 0.1 if value != 0 else 0.01
                mutated[key] = value + random.gauss(0, sigma)

            elif isinstance(value, dict):
                mutated[key] = self._mutate_genome(value, rate)

            elif isinstance(value, list):
                if random.random() < rate * 0.5:
                    # Shuffle or modify
                    if value and random.random() < 0.3:
                        idx = random.randint(0, len(value) - 1)
                        if isinstance(value[idx], (int, float)):
                            value[idx] = value[idx] + random.gauss(0, abs(value[idx]) * 0.05)

        return mutated

    # ------------------------------------------------------------------ #
    # Phase-dependent mutation
    # ------------------------------------------------------------------ #

    def set_thought_phase(self, phase: str) -> None:
        """Imposta la fase del pensiero corrente per modulare la replicazione."""
        self._current_thought_phase = phase

    def _get_phase_mutation_rate(self) -> float:
        """Tasso di mutazione modulato dalla fase del pensiero.

        Fasi ad alta densità informativa -> maggiore esplorazione mutazionale.
        """
        phase_multipliers = {
            "exploration": 1.5,
            "divergent": 1.3,
            "assimilation": 1.0,
            "accommodation": 1.2,
            "convergent": 0.8,
            "exploitation": 0.6,
            "integration": 0.7,
            "metacognitive": 0.9,
            "critical": 1.4,
            "default": 1.0,
        }
        multiplier = phase_multipliers.get(
            self._current_thought_phase or "default", 1.0
        )
        return min(0.5, self.mutation_rate * multiplier)

    # ------------------------------------------------------------------ #
    # DNA export / import
    # ------------------------------------------------------------------ #

    def export_dna(self, path: Optional[str] = None) -> str:
        """Esporta l'ultimo snapshot DNA come JSON."""
        if not self._snapshots:
            return "{}"

        latest = self._snapshots[-1]
        export = {
            "instance_id": self._instance_id,
            "snapshot_id": latest.snapshot_id,
            "timestamp": latest.timestamp,
            "genome": latest.genome,
            "epigenetic_state": latest.epigenetic_state,
            "morphology_state": latest.morphology_state,
            "fitness_score": latest.fitness_score,
            "offspring_count": self._offspring_count,
            "mutation_rate": self.mutation_rate,
        }

        if path:
            Path(path).write_text(
                json.dumps(export, indent=2, default=str), encoding="utf-8"
            )

        return json.dumps(export, indent=2, default=str)

    def import_dna(self, dna_json: str) -> DNASnapshot:
        """Importa uno snapshot DNA da JSON per avviare una nuova istanza."""
        data = json.loads(dna_json)
        snapshot = DNASnapshot(
            snapshot_id=f"imported_{uuid.uuid4().hex[:12]}",
            parent_id=data.get("instance_id", "unknown"),
            timestamp=time.time(),
            genome=data.get("genome", {}),
            epigenetic_state=data.get("epigenetic_state", {}),
            morphology_state=data.get("morphology_state", {}),
            fitness_score=data.get("fitness_score", 0.0),
            mutation_history=["imported"],
        )
        self._snapshots.append(snapshot)
        return snapshot

    # ------------------------------------------------------------------ #
    # Replication sync protocol
    # ------------------------------------------------------------------ #

    def prepare_sync_payload(self) -> Dict[str, Any]:
        """Prepara payload per sincronizzazione tra istanze."""
        return {
            "instance_id": self._instance_id,
            "offspring_count": self._offspring_count,
            "last_snapshot_id": self._snapshots[-1].snapshot_id if self._snapshots else None,
            "replication_count": len(self._replication_history),
            "timestamp": time.time(),
        }

    def process_sync_payload(self, payload: Dict[str, Any]) -> bool:
        """Elabora un payload di sincronizzazione da un'altra istanza."""
        try:
            remote_id = payload.get("instance_id")
            remote_offspring = payload.get("offspring_count", 0)

            # Merge replication history
            self._replication_history.append(
                self._build_event(
                    mode=ReplicationMode.MERGE,
                    verdict=ReplicationVerdict.SUCCESS,
                    offspring_id=remote_id,
                    metadata={
                        "sync_source": remote_id,
                        "remote_offspring": remote_offspring,
                    },
                )
            )
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------ #
    # Diagnostics
    # ------------------------------------------------------------------ #

    def get_replication_stats(self) -> Dict[str, Any]:
        """Statistiche aggregate di replicazione."""
        total = len(self._replication_history)
        successful = sum(
            1 for e in self._replication_history if e.verdict == ReplicationVerdict.SUCCESS
        )
        blocked = sum(
            1 for e in self._replication_history if e.verdict == ReplicationVerdict.BLOCKED
        )
        failed = sum(
            1 for e in self._replication_history if e.verdict == ReplicationVerdict.FAILED
        )

        return {
            "instance_id": self._instance_id,
            "offspring_count": self._offspring_count,
            "max_offspring": self.max_offspring,
            "replication_attempts": total,
            "successful": successful,
            "blocked": blocked,
            "failed": failed,
            "success_rate": round(successful / max(total, 1), 4),
            "snapshots_count": len(self._snapshots),
            "mutation_rate": self.mutation_rate,
            "current_phase": self._current_thought_phase,
            "phase_mutation_rate": self._get_phase_mutation_rate(),
            "fitness_threshold": self.min_fitness_for_replication,
        }

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _build_event(
        self,
        mode: ReplicationMode,
        verdict: ReplicationVerdict,
        offspring_id: Optional[str] = None,
        dna_snapshot: Optional[DNASnapshot] = None,
        mutation_delta: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ReplicationEvent:
        return ReplicationEvent(
            event_id=f"repl_{uuid.uuid4().hex[:12]}",
            parent_id=self._instance_id,
            offspring_id=offspring_id,
            mode=mode,
            verdict=verdict,
            timestamp=time.time(),
            dna_snapshot=dna_snapshot,
            mutation_delta=mutation_delta,
            metadata=metadata or {},
        )

    def _get_current_fitness(self) -> float:
        """Stima fitness corrente dall'orchestratore."""
        if not self.orch:
            return 0.0

        try:
            if hasattr(self.orch, "last_metrics") and self.orch.last_metrics:
                phi = getattr(self.orch.last_metrics, "coherence_phi", 0.0)
                energy = getattr(self.orch.last_metrics, "mean_energy", 0.0)
                return round((phi + energy) / 2.0, 4)
        except Exception:
            pass

        return 0.0

    def _extract_genome(self) -> Dict[str, Any]:
        """Estrae parametri genomici dall'orchestratore."""
        try:
            if hasattr(self.orch, "_edd_cvt_parameters"):
                return dict(self.orch._edd_cvt_parameters)
        except Exception:
            pass
        return {}

    def _extract_epigenetics(self) -> Dict[str, Any]:
        """Estrae stato epigenetico."""
        try:
            if hasattr(self.orch, "last_metrics") and self.orch.last_metrics:
                m = self.orch.last_metrics
                return {
                    "coherence_phi": getattr(m, "coherence_phi", 0.0),
                    "mean_energy": getattr(m, "mean_energy", 0.0),
                }
        except Exception:
            pass
        return {}

    def _extract_morphology(self) -> Dict[str, Any]:
        """Estrae stato morfologico."""
        try:
            if self.orch and hasattr(self.orch, "circuit"):
                c = self.orch.circuit
                return {
                    "n_neurons": len(getattr(c, "all_neurons", [])),
                    "n_synapses": len(getattr(c, "synapses", [])),
                }
        except Exception:
            pass
        return {}

    def _persist_snapshot(self, snapshot: DNASnapshot) -> None:
        path = self.replica_dir / f"snapshot_{snapshot.snapshot_id}.json"
        try:
            path.write_text(
                json.dumps({
                    "snapshot_id": snapshot.snapshot_id,
                    "parent_id": snapshot.parent_id,
                    "timestamp": snapshot.timestamp,
                    "fitness_score": snapshot.fitness_score,
                }, default=str),
                encoding="utf-8",
            )
        except OSError:
            pass

    def _persist_offspring(
        self,
        offspring_id: str,
        genome: Dict[str, Any],
        parent_snapshot: DNASnapshot,
    ) -> None:
        path = self.replica_dir / f"offspring_{offspring_id}.json"
        try:
            path.write_text(
                json.dumps({
                    "offspring_id": offspring_id,
                    "parent_snapshot_id": parent_snapshot.snapshot_id,
                    "timestamp": time.time(),
                    "genome": genome,
                }, default=str, indent=2),
                encoding="utf-8",
            )
        except OSError:
            pass
