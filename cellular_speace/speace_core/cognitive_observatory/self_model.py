import time
from typing import Any, Dict, List, Optional

import structlog

from speace_core.cognitive_observatory.models import SelfModel
from speace_core.cognitive_observatory.persistence.observatory_store import ObservatoryStore

logger = structlog.get_logger(__name__)


class SelfModelEngine:
    """L2 — Self Model.

    Maintains a live self-representation of SPEACE, updated from
    all available subsystems. Answers: "Who am I right now?"
    """

    def __init__(self, store: Optional[ObservatoryStore] = None) -> None:
        self._store = store or ObservatoryStore()
        self._model = SelfModel()

    @property
    def model(self) -> SelfModel:
        return self._model

    # ------------------------------------------------------------------ #
    # Updates
    # ------------------------------------------------------------------ #

    def update_identity(self, genome_identity: Dict[str, Any]) -> None:
        self._model.identity = genome_identity
        self._model.last_updated = time.time()

    def set_goals(self, goals: List[Dict[str, Any]]) -> None:
        self._model.active_goals = goals
        self._model.last_updated = time.time()

    def add_goal(self, goal: Dict[str, Any]) -> None:
        self._model.active_goals.append(goal)
        self._model.last_updated = time.time()

    def remove_goal(self, goal_name: str) -> None:
        self._model.active_goals = [
            g for g in self._model.active_goals
            if g.get("name") != goal_name
        ]
        self._model.last_updated = time.time()

    def set_constraints(self, constraints: List[str]) -> None:
        self._model.active_constraints = constraints
        self._model.last_updated = time.time()

    def update_capability(self, name: str, confidence: float) -> None:
        self._model.capabilities[name] = confidence
        self._model.last_updated = time.time()

    def add_weakness(self, weakness: str) -> None:
        if weakness not in self._model.known_weaknesses:
            self._model.known_weaknesses.append(weakness)
            self._model.last_updated = time.time()

    def add_error(self, error: Dict[str, Any]) -> None:
        self._model.known_errors.append(error)
        if len(self._model.known_errors) > 100:
            self._model.known_errors = self._model.known_errors[-100:]
        self._model.last_updated = time.time()

    def add_blind_spot(self, area: str) -> None:
        if area not in self._model.blind_spots:
            self._model.blind_spots.append(area)
            self._model.last_updated = time.time()

    def update_genome_state(self, state: Dict[str, Any]) -> None:
        self._model.genome_state = state
        self._model.last_updated = time.time()

    def update_ilf_state(self, ilf_data: Dict[str, float]) -> None:
        self._model.ilf_state = ilf_data
        self._model.last_updated = time.time()

    def update_bcel_coverage(self, coverage: Dict[str, Any]) -> None:
        self._model.bcel_coverage = coverage
        self._model.last_updated = time.time()

    def update_from_orchestrator(self, orchestrator_state: Dict[str, Any]) -> None:
        """Bulk update from orchestrator metrics."""
        if "identity" in orchestrator_state:
            self.update_identity(orchestrator_state["identity"])
        if "ilf" in orchestrator_state:
            self.update_ilf_state(orchestrator_state["ilf"])
        if "genome" in orchestrator_state:
            self.update_genome_state(orchestrator_state["genome"])
        if "goals" in orchestrator_state:
            self.set_goals(orchestrator_state["goals"])
        if "constraints" in orchestrator_state:
            self.set_constraints(orchestrator_state["constraints"])
        if "capabilities" in orchestrator_state:
            for name, conf in orchestrator_state["capabilities"].items():
                self.update_capability(name, conf)

    # ------------------------------------------------------------------ #
    # Analysis
    # ------------------------------------------------------------------ #

    def get_identity_consistency(self) -> float:
        """How consistent is the current self with the species orientation."""
        if not self._model.identity:
            return 0.5
        # Compare current identity keys with expected orientation
        invariants = self._model.identity.get("invariants", [])
        if not invariants:
            return 0.5
        active_constraints_set = set(self._model.active_constraints)
        invariant_names = {i.get("name", i) if isinstance(i, dict) else i for i in invariants}
        if not invariant_names:
            return 0.5
        overlap = len(active_constraints_set & invariant_names)
        return min(1.0, overlap / len(invariant_names) * 1.5)

    def get_self_summary(self) -> Dict[str, Any]:
        """Return a concise summary of the current self model."""
        return {
            "identity_name": self._model.identity.get("entity_name", "SPEACE"),
            "active_goals": [g.get("name", str(g)) for g in self._model.active_goals],
            "active_constraints": self._model.active_constraints[:5],
            "capabilities": dict(sorted(
                self._model.capabilities.items(),
                key=lambda x: -x[1],
            )[:10]),
            "known_weaknesses": self._model.known_weaknesses[:5],
            "recent_errors": len(self._model.known_errors),
            "blind_spots": self._model.blind_spots[:5],
            "ilf_summary": dict(self._model.ilf_state),
            "consistency": self.get_identity_consistency(),
            "last_updated": self._model.last_updated,
        }

    def clear(self) -> None:
        self._model = SelfModel()
