"""Cross-regime generality SkillLibrary & bounded ReconsolidationWindow (T249-04).

Synthesized via BCEL from ``cellular_speace_ollama`` (``ARCSkillLibrary``) and
``speace_ds`` (``ReconsolidationManager``):
- Hippocampal indexing and memory-lability narratives are *accidental*.
- Cross-regime generality scoring (fixing the ``n_total`` denominator bug by
  dividing succeeded regimes by tested regimes), anti-overfit/fragile pruning,
  and bounded recall-update retention boosts survive as deterministic rules.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class ReusableSkill:
    """Tracked procedural strategy with cross-regime generality metrics."""

    skill_id: str
    description: str
    successes: int = 0
    trials: int = 0
    tested_regimes: set[str] = field(default_factory=set)
    succeeded_regimes: set[str] = field(default_factory=set)
    mean_latency_ms: float = 10.0
    retention_boost: float = 0.0

    def __post_init__(self) -> None:
        if not self.skill_id:
            raise ValueError("skill_id must be non-empty")
        if self.successes < 0 or self.trials < 0 or self.successes > self.trials:
            raise ValueError("0 <= successes <= trials is required")
        if not math.isfinite(self.mean_latency_ms) or self.mean_latency_ms < 0.0:
            raise ValueError("mean_latency_ms must be finite and >= 0")
        if not math.isfinite(self.retention_boost) or not (0.0 <= self.retention_boost <= 0.3):
            raise ValueError("retention_boost must be finite and in [0, 0.3]")

    @property
    def success_rate(self) -> float:
        return self.successes / self.trials if self.trials > 0 else 0.0

    @property
    def generality(self) -> float:
        if not self.tested_regimes:
            return 0.0
        return len(self.succeeded_regimes) / len(self.tested_regimes)

    @property
    def fitness(self) -> float:
        speed_factor = max(0.05, 1.0 - self.mean_latency_ms / 1000.0)
        base = self.success_rate * max(0.1, self.generality) * speed_factor
        return float(min(1.0, base + self.retention_boost))


class SkillLibrary:
    """Bounded skill cache with anti-overfit & fragility pruning (T249-04)."""

    def __init__(
        self,
        *,
        max_skills: int = 256,
        min_fitness: float = 0.20,
        min_generality: float = 0.35,
    ) -> None:
        if max_skills < 1:
            raise ValueError("max_skills must be >= 1")
        if not math.isfinite(min_fitness) or not (0.0 <= min_fitness <= 1.0):
            raise ValueError("min_fitness must be finite and in [0, 1]")
        if not math.isfinite(min_generality) or not (0.0 <= min_generality <= 1.0):
            raise ValueError("min_generality must be finite and in [0, 1]")
        self.max_skills = max_skills
        self.min_fitness = float(min_fitness)
        self.min_generality = float(min_generality)
        self._skills: dict[str, ReusableSkill] = {}

    def record_outcome(
        self,
        skill_id: str,
        *,
        regime: str,
        success: bool,
        latency_ms: float = 10.0,
        description: str = "",
    ) -> ReusableSkill:
        if not skill_id or not regime:
            raise ValueError("skill_id and regime must be non-empty")
        if not math.isfinite(latency_ms) or latency_ms < 0.0:
            raise ValueError("latency_ms must be finite and >= 0")

        skill = self._skills.get(skill_id)
        if skill is None:
            skill = ReusableSkill(
                skill_id=skill_id,
                description=description or skill_id,
                mean_latency_ms=float(latency_ms),
            )
            self._skills[skill_id] = skill

        prev_trials = skill.trials
        skill.trials += 1
        skill.tested_regimes.add(regime)
        if success:
            skill.successes += 1
            skill.succeeded_regimes.add(regime)
        skill.mean_latency_ms = (
            skill.mean_latency_ms * prev_trials + float(latency_ms)
        ) / skill.trials
        return skill

    def get(self, skill_id: str) -> ReusableSkill | None:
        return self._skills.get(skill_id)

    def top_skills(self, k: int = 5) -> list[ReusableSkill]:
        if k < 1:
            return []
        ranked = sorted(
            self._skills.values(),
            key=lambda s: (-s.fitness, -s.successes, s.skill_id),
        )
        return ranked[:k]

    def prune(self) -> list[str]:
        """Drop fragile and single-regime overfit skills, then enforce ``max_skills`` cap."""
        removed: list[str] = []
        for sid, skill in list(self._skills.items()):
            fragile = skill.trials >= 3 and skill.fitness < self.min_fitness
            overfit = (
                skill.trials >= 5
                and len(skill.tested_regimes) >= 3
                and skill.generality < self.min_generality
            )
            if fragile or overfit:
                removed.append(sid)
                del self._skills[sid]

        if len(self._skills) > self.max_skills:
            by_weakest = sorted(
                self._skills.values(),
                key=lambda s: (s.fitness, s.successes, s.skill_id),
            )
            overflow = len(self._skills) - self.max_skills
            for s in by_weakest[:overflow]:
                removed.append(s.skill_id)
                del self._skills[s.skill_id]
        return removed


class ReconsolidationWindow:
    """Time-bounded recall-update retention boost manager (T249-04)."""

    def __init__(self, window_seconds: float = 300.0) -> None:
        if not math.isfinite(window_seconds) or window_seconds <= 0.0:
            raise ValueError("window_seconds must be finite and > 0")
        self.window_seconds = float(window_seconds)
        self._open_windows: dict[str, tuple[float, int]] = {}

    def open_on_recall(self, skill_id: str, now: float) -> None:
        if not skill_id or not math.isfinite(now):
            raise ValueError("skill_id must be non-empty and now must be finite")
        if skill_id not in self._open_windows:
            self._open_windows[skill_id] = (float(now), 0)

    def record_context_update(self, skill_id: str, now: float) -> bool:
        if not math.isfinite(now):
            raise ValueError("now must be finite")
        entry = self._open_windows.get(skill_id)
        if entry is None:
            return False
        opened_at, updates = entry
        if now - opened_at > self.window_seconds:
            del self._open_windows[skill_id]
            return False
        self._open_windows[skill_id] = (opened_at, updates + 1)
        return True

    def commit(self, skill: ReusableSkill) -> float:
        """Close open window for ``skill`` and apply bounded boost ``min(0.3, 0.05 * n_upd)``."""
        entry = self._open_windows.pop(skill.skill_id, None)
        if entry is None:
            return skill.retention_boost
        _opened_at, updates = entry
        delta = min(0.30, 0.05 * updates)
        skill.retention_boost = float(min(0.30, skill.retention_boost + delta))
        return skill.retention_boost
