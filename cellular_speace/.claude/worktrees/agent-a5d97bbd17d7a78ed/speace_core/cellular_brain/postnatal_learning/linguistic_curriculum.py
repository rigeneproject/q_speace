import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field


class LinguisticStage(str, Enum):
    LINGUISTIC_BABBLING = "linguistic_babbling"
    IMITATION_SANDBOX = "imitation_sandbox"
    SEMANTIC_GROUNDING = "semantic_grounding"


class LinguisticCurriculumState(BaseModel):
    stage: LinguisticStage = LinguisticStage.LINGUISTIC_BABBLING
    exposure_count: int = 0
    imitation_attempts: int = 0
    imitation_successes: int = 0
    grounded_concepts: Set[str] = Field(default_factory=set)
    concept_grounding_scores: Dict[str, float] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LinguisticCurriculum:
    """Postnatal linguistic curriculum engine.

    Stages:
      1. linguistic_babbling     — unstructured exposure, pattern absorption
      2. imitation_sandbox       — safe repetition and echoing
      3. semantic_grounding      — linking symbols to meaning
    """

    def __init__(
        self,
        base_path: str = "data/linguistic_curriculum",
        initial_stage: Optional[LinguisticStage] = None,
    ):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.state_path = self.base_path / "state.json"
        self.exposure_log_path = self.base_path / "exposure_log.jsonl"

        self._stage_order = [
            LinguisticStage.LINGUISTIC_BABBLING,
            LinguisticStage.IMITATION_SANDBOX,
            LinguisticStage.SEMANTIC_GROUNDING,
        ]

        self._state = self._load_state(initial_stage)

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #

    def _load_state(self, initial_stage: Optional[LinguisticStage]) -> LinguisticCurriculumState:
        if self.state_path.exists():
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            # Rehydrate set from list
            data["grounded_concepts"] = set(data.get("grounded_concepts", []))
            return LinguisticCurriculumState(**data)
        return LinguisticCurriculumState(stage=initial_stage or LinguisticStage.LINGUISTIC_BABBLING)

    def _save_state(self) -> None:
        dump = self._state.model_dump()
        dump["grounded_concepts"] = sorted(dump["grounded_concepts"])
        self.state_path.write_text(json.dumps(dump, ensure_ascii=False, indent=2), encoding="utf-8")

    def _log_exposure(self, entry: Dict[str, Any]) -> None:
        with open(self.exposure_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # ------------------------------------------------------------------ #
    # Stage management
    # ------------------------------------------------------------------ #

    def current_stage(self) -> LinguisticStage:
        return self._state.stage

    def advance_stage(self, criteria_met: bool = False) -> LinguisticStage:
        """Advance to the next stage if criteria are met."""
        if not criteria_met:
            return self._state.stage
        idx = self._stage_order.index(self._state.stage)
        if idx < len(self._stage_order) - 1:
            self._state.stage = self._stage_order[idx + 1]
            self._save_state()
        return self._state.stage

    # ------------------------------------------------------------------ #
    # Learning interface
    # ------------------------------------------------------------------ #

    def expose_input(
        self,
        tokens: List[str],
        imitation_target: Optional[List[str]] = None,
        imitation_output: Optional[List[str]] = None,
        grounded_concept: Optional[str] = None,
        grounding_score: float = 0.0,
    ) -> Dict[str, Any]:
        """Expose the curriculum to linguistic input."""
        self._state.exposure_count += 1
        entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stage": self._state.stage.value,
            "tokens": tokens,
            "exposure_count": self._state.exposure_count,
        }

        if imitation_target is not None and imitation_output is not None:
            self._state.imitation_attempts += 1
            accuracy = self._compute_imitation_accuracy(imitation_target, imitation_output)
            if accuracy >= 0.8:
                self._state.imitation_successes += 1
            entry["imitation_accuracy"] = accuracy

        if grounded_concept is not None:
            current = self._state.concept_grounding_scores.get(grounded_concept, 0.0)
            updated = min(1.0, current + grounding_score)
            self._state.concept_grounding_scores[grounded_concept] = updated
            if updated >= 0.7:
                self._state.grounded_concepts.add(grounded_concept)
            entry["grounded_concept"] = grounded_concept
            entry["grounding_score"] = updated

        self._log_exposure(entry)
        self._save_state()
        return entry

    def get_learning_metrics(self) -> Dict[str, Any]:
        return {
            "stage": self._state.stage.value,
            "exposure_count": self._state.exposure_count,
            "imitation_attempts": self._state.imitation_attempts,
            "imitation_successes": self._state.imitation_successes,
            "imitation_accuracy": (
                self._state.imitation_successes / max(1, self._state.imitation_attempts)
            ),
            "grounded_concepts_count": len(self._state.grounded_concepts),
            "grounded_concepts": sorted(self._state.grounded_concepts),
            "concept_grounding_scores": dict(self._state.concept_grounding_scores),
        }

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _compute_imitation_accuracy(target: List[str], output: List[str]) -> float:
        if not target:
            return 0.0
        matches = sum(1 for t, o in zip(target, output) if t == o)
        max_len = max(len(target), len(output))
        return matches / max_len if max_len > 0 else 0.0
