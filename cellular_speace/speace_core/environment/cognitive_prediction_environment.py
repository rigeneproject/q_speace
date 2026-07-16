"""CognitivePredictionEnvironment — external task for SPEACE.

This environment turns SPEACE into a sequential prediction agent. It:
  1. Generates a sequence of input patterns (periodic, Markov, or linguistic).
  2. Injects the current pattern into SPEACE's input neurons.
  3. Reads SPEACE's output activations as a prediction.
  4. Compares the prediction with the next true pattern.
  5. Returns a reward to SPEACE via feedback(score).

This gives the brain a meaningful external signal to organize around,
instead of random input. The task is simple enough to run on the MVP
architecture but rich enough to exercise memory, plasticity, COR collapse,
and the simulator backend.
"""
from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class SequenceMode(str, Enum):
    PERIODIC = "periodic"
    MARKOV = "markov"
    RANDOM_WALK = "random_walk"
    LINGUISTIC = "linguistic"


@dataclass
class PredictionEpisode:
    step: int
    input_pattern: List[float]
    predicted_pattern: List[float]
    true_next_pattern: List[float]
    reward: float
    error: float
    cor_collapsed: bool = False
    simulator_step: bool = False


class CognitivePredictionEnvironment:
    """External sequential prediction task for SPEACE.

    Args:
        input_size: dimension of each input/output pattern (must match
            orchestrator input/output neurons).
        mode: type of sequence generator.
        episode_length: number of steps per episode.
        noise: Gaussian noise added to patterns.
        reward_scale: multiplier for computed reward.
    """

    def __init__(
        self,
        input_size: int = 10,
        output_size: int = 10,
        mode: SequenceMode = SequenceMode.PERIODIC,
        episode_length: int = 200,
        noise: float = 0.05,
        reward_scale: float = 1.0,
        seed: Optional[int] = None,
    ):
        self.input_size = input_size
        self.output_size = output_size
        self.mode = mode
        self.episode_length = episode_length
        self.noise = noise
        self.reward_scale = reward_scale
        self._rng = random.Random(seed)
        self._np_rng = np.random.default_rng(seed)

        self._sequence: List[List[float]] = []
        self._step: int = 0
        self._episode: int = 0
        self._history: List[PredictionEpisode] = []
        self._last_true_next: Optional[List[float]] = None

        # Markov state
        self._markov_state: int = 0

        # Linguistic curriculum: simple symbol→next-symbol map
        self._linguistic_vocabulary: List[str] = [
            "a", "b", "c", "d", "e", "f", "g", "h", "i", "j",
        ]
        self._linguistic_index: int = 0

    # ------------------------------------------------------------------ #
    # Sequence generation
    # ------------------------------------------------------------------ #

    def reset_episode(self) -> None:
        """Generate a fresh sequence for a new episode."""
        self._sequence = []
        self._step = 0
        self._episode += 1
        self._markov_state = self._rng.randint(0, self.input_size - 1)
        self._linguistic_index = 0

        if self.mode == SequenceMode.PERIODIC:
            period = self._rng.randint(3, max(3, self.input_size // 2))
            base = [0.0] * self.input_size
            active = self._rng.sample(range(self.input_size), k=period)
            for idx in active:
                base[idx] = self._rng.uniform(0.5, 1.0)
            for _ in range(self.episode_length + 1):
                shifted = base[-1:] + base[:-1]
                base = shifted
                self._sequence.append([v + self._np_rng.normal(0, self.noise) for v in base])

        elif self.mode == SequenceMode.MARKOV:
            # Build a simple transition matrix biased toward neighbours.
            trans = np.zeros((self.input_size, self.input_size))
            for i in range(self.input_size):
                trans[i, i] = 0.5
                trans[i, (i + 1) % self.input_size] = 0.3
                trans[i, (i - 1) % self.input_size] = 0.2
            state = self._rng.randint(0, self.input_size - 1)
            for _ in range(self.episode_length + 1):
                pattern = [0.0] * self.input_size
                pattern[state] = 1.0
                self._sequence.append([v + self._np_rng.normal(0, self.noise) for v in pattern])
                state = int(self._np_rng.choice(self.input_size, p=trans[state]))

        elif self.mode == SequenceMode.RANDOM_WALK:
            pos = self._rng.uniform(0.0, 1.0)
            for _ in range(self.episode_length + 1):
                pos += self._np_rng.normal(0, 0.1)
                pos = max(0.0, min(1.0, pos))
                pattern = [0.0] * self.input_size
                idx = int(pos * (self.input_size - 1))
                pattern[idx] = 0.5 + 0.5 * pos
                self._sequence.append([v + self._np_rng.normal(0, self.noise) for v in pattern])

        elif self.mode == SequenceMode.LINGUISTIC:
            # Repeating short phrases: a b c d a b c d ...
            phrase = self._linguistic_vocabulary[: max(3, self.input_size // 3)]
            for _ in range(self.episode_length + 1):
                sym = phrase[self._linguistic_index % len(phrase)]
                self._linguistic_index += 1
                pattern = self._symbol_to_pattern(sym)
                self._sequence.append([v + self._np_rng.normal(0, self.noise) for v in pattern])

    def _symbol_to_pattern(self, symbol: str) -> List[float]:
        pattern = [0.0] * self.input_size
        idx = self._linguistic_vocabulary.index(symbol) % self.input_size
        pattern[idx] = 1.0
        return pattern

    # ------------------------------------------------------------------ #
    # Interaction with SPEACE
    # ------------------------------------------------------------------ #

    def current_input(self) -> List[float]:
        """Return the input pattern for the current step."""
        if not self._sequence or self._step >= len(self._sequence):
            self.reset_episode()
        return list(self._sequence[self._step])

    def true_next(self) -> List[float]:
        """Return the target pattern (next step)."""
        next_idx = min(self._step + 1, len(self._sequence) - 1)
        return list(self._sequence[next_idx])

    def evaluate_prediction(
        self,
        predicted: List[float],
        true: List[float],
    ) -> Tuple[float, float]:
        """Return (reward, error). Reward is higher when error is lower."""
        pred = np.array(predicted, dtype=float)
        tgt = np.array(true, dtype=float)
        if pred.shape != tgt.shape:
            pred = np.resize(pred, tgt.shape)
        error = float(np.mean((pred - tgt) ** 2))
        # Reward: 1.0 for perfect match, 0.0 for max mismatch, shaped.
        reward = max(0.0, 1.0 - math.sqrt(error))
        return reward * self.reward_scale, error

    def step(
        self,
        orchestrator: Any,
    ) -> PredictionEpisode:
        """Run one environment step with the given orchestrator.

        The orchestrator must have:
          - ``inject(pattern)``
          - ``circuit.output_activations`` property
          - ``feedback(score)``
        """
        input_pattern = self.current_input()
        true_next = self.true_next()

        orchestrator.inject(input_pattern)

        # Run one SPEACE tick (async)
        import asyncio
        asyncio.run(orchestrator._tick())

        predicted = list(orchestrator.circuit.output_activations)
        reward, error = self.evaluate_prediction(predicted, true_next)
        orchestrator.feedback(reward)
        # Teacher signal: transiently boost the correct output neurons to
        # strengthen the input-to-output association via STDP on the next tick.
        for i, val in enumerate(true_next[: len(orchestrator.circuit.output_neurons)]):
            if val > 0.1:
                n = orchestrator.circuit.output_neurons[i]
                n.activation = max(n.activation, 0.6)

        cor_collapsed = False
        if getattr(orchestrator, "_last_cor_result", None) is not None:
            cor_collapsed = orchestrator._last_cor_result.collapsed

        simulator_step = (
            orchestrator.simulator_backend_enabled
            and len(orchestrator._simulator_backend_log) > 0
        )

        episode = PredictionEpisode(
            step=self._step,
            input_pattern=input_pattern,
            predicted_pattern=predicted,
            true_next_pattern=true_next,
            reward=reward,
            error=error,
            cor_collapsed=cor_collapsed,
            simulator_step=simulator_step,
        )
        self._history.append(episode)
        self._step += 1
        return episode

    def run_episode(
        self,
        orchestrator: Any,
    ) -> Dict[str, Any]:
        """Run a full episode and return summary metrics."""
        self.reset_episode()
        for _ in range(self.episode_length):
            self.step(orchestrator)
            if self._step >= len(self._sequence) - 1:
                break

        rewards = [e.reward for e in self._history[-self._step:]]
        errors = [e.error for e in self._history[-self._step:]]
        cor_count = sum(1 for e in self._history[-self._step:] if e.cor_collapsed)
        sim_count = sum(1 for e in self._history[-self._step:] if e.simulator_step)

        # Simple learning trend: compare first half vs second half reward.
        mid = len(rewards) // 2
        first = sum(rewards[:mid]) / max(1, mid)
        second = sum(rewards[mid:]) / max(1, len(rewards) - mid)

        return {
            "episode": self._episode,
            "mode": self.mode.value,
            "steps": len(rewards),
            "mean_reward": sum(rewards) / max(1, len(rewards)),
            "mean_error": sum(errors) / max(1, len(errors)),
            "first_half_reward": first,
            "second_half_reward": second,
            "learning_trend": second - first,
            "cor_collapses": cor_count,
            "simulator_backend_steps": sim_count,
            "final_coherence_phi": getattr(
                orchestrator.latest_metrics, "coherence_phi", None
            ),
            "final_mean_energy": getattr(
                orchestrator.latest_metrics, "mean_energy", None
            ),
            "final_active_neurons": getattr(
                orchestrator.latest_metrics, "active_neurons", None
            ),
        }

    def summary(self) -> Dict[str, Any]:
        if not self._history:
            return {"steps": 0}
        recent = self._history[-100:]
        return {
            "total_steps": len(self._history),
            "episodes": self._episode,
            "mean_reward": sum(e.reward for e in recent) / len(recent),
            "mean_error": sum(e.error for e in recent) / len(recent),
            "cor_collapses": sum(1 for e in recent if e.cor_collapsed),
        }
