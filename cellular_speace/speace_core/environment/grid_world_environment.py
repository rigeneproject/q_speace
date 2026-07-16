"""GridWorldEnvironment — simple embodied navigation task for SPEACE.

A 1-D or 2-D grid where SPEACE must move an agent toward a target.
The agent receives:
  - position vector as input
  - reward based on distance to target
  - feedback that shapes motor/output neurons

This exercises the cyber-physical / embodied action pathway in a
controlled, reversible way.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


class Action(int, Enum):
    LEFT = 0
    STAY = 1
    RIGHT = 2
    UP = 3
    DOWN = 4


@dataclass
class GridStep:
    agent_position: Tuple[int, ...]
    target_position: Tuple[int, ...]
    action: int
    distance_before: float
    distance_after: float
    reward: float
    done: bool


class GridWorldEnvironment:
    """Minimal grid-world for SPEACE navigation.

    Args:
        dimensions: 1 or 2 (1-D line or 2-D grid).
        size: length of each dimension.
        max_steps: episode length limit.
    """

    def __init__(
        self,
        dimensions: int = 1,
        size: int = 10,
        max_steps: int = 50,
        seed: Optional[int] = None,
    ):
        self.dimensions = dimensions
        self.size = size
        self.max_steps = max_steps
        self._rng = random.Random(seed)
        self._np_rng = np.random.default_rng(seed)

        self.agent: Tuple[int, ...] = tuple([0] * dimensions)
        self.target: Tuple[int, ...] = tuple([size - 1] * dimensions)
        self._step: int = 0
        self._episode: int = 0
        self._history: List[GridStep] = []

    def reset(self) -> List[float]:
        """Reset agent and target, return initial observation."""
        self._episode += 1
        self._step = 0
        self.agent = tuple(self._rng.randint(0, self.size - 1) for _ in range(self.dimensions))
        # Ensure target is not on the agent.
        while True:
            self.target = tuple(self._rng.randint(0, self.size - 1) for _ in range(self.dimensions))
            if self.target != self.agent:
                break
        self._history.clear()
        return self.observe()

    def observe(self) -> List[float]:
        """Flatten position and target into a normalized input vector."""
        vec: List[float] = []
        for d in range(self.dimensions):
            vec.append(self.agent[d] / self.size)
            vec.append(self.target[d] / self.size)
        # Pad to size 10 for standard orchestrator inputs.
        while len(vec) < 10:
            vec.append(0.0)
        return vec[:10]

    def _distance(self, a: Tuple[int, ...], b: Tuple[int, ...]) -> float:
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

    def decode_action(self, output_activations: List[float]) -> int:
        """Map output activations to an action.

        In 1-D: first three outputs = LEFT, STAY, RIGHT.
        In 2-D: first five outputs = LEFT, STAY, RIGHT, UP, DOWN.
        """
        n = 3 if self.dimensions == 1 else 5
        arr = np.array(output_activations[:n], dtype=float)
        # softmax with temperature
        exp = np.exp(arr - np.max(arr))
        probs = exp / (np.sum(exp) + 1e-12)
        return int(self._np_rng.choice(n, p=probs))

    def step(
        self,
        orchestrator: Any,
    ) -> GridStep:
        """Run one grid step with SPEACE."""
        obs = self.observe()
        distance_before = self._distance(self.agent, self.target)

        orchestrator.inject(obs)

        import asyncio
        asyncio.run(orchestrator._tick())

        action = self.decode_action(orchestrator.circuit.output_activations)
        new_agent = list(self.agent)
        if self.dimensions == 1:
            if action == Action.LEFT:
                new_agent[0] = max(0, new_agent[0] - 1)
            elif action == Action.RIGHT:
                new_agent[0] = min(self.size - 1, new_agent[0] + 1)
        else:
            if action == Action.LEFT:
                new_agent[0] = max(0, new_agent[0] - 1)
            elif action == Action.RIGHT:
                new_agent[0] = min(self.size - 1, new_agent[0] + 1)
            elif action == Action.UP:
                new_agent[1] = max(0, new_agent[1] - 1)
            elif action == Action.DOWN:
                new_agent[1] = min(self.size - 1, new_agent[1] + 1)

        self.agent = tuple(new_agent)
        self._step += 1
        distance_after = self._distance(self.agent, self.target)

        # Reward shaped by improvement and closeness.
        improvement = distance_before - distance_after
        closeness = 1.0 - (distance_after / (self.size * self.dimensions))
        reward = max(0.0, improvement * 0.5 + closeness * 0.3)
        done = (self.agent == self.target) or (self._step >= self.max_steps)

        orchestrator.feedback(reward)

        gs = GridStep(
            agent_position=self.agent,
            target_position=self.target,
            action=action,
            distance_before=distance_before,
            distance_after=distance_after,
            reward=reward,
            done=done,
        )
        self._history.append(gs)
        return gs

    def run_episode(
        self,
        orchestrator: Any,
    ) -> Dict[str, Any]:
        """Run one episode and return summary."""
        self.reset()
        total_reward = 0.0
        reached = False
        for _ in range(self.max_steps):
            gs = self.step(orchestrator)
            total_reward += gs.reward
            if gs.done:
                reached = (self.agent == self.target)
                break

        return {
            "episode": self._episode,
            "dimensions": self.dimensions,
            "size": self.size,
            "steps": self._step,
            "total_reward": total_reward,
            "reached_target": reached,
            "final_distance": self._distance(self.agent, self.target),
            "final_coherence_phi": getattr(
                orchestrator.latest_metrics, "coherence_phi", None
            ),
        }
