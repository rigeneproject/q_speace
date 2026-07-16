"""AutonomousCognitiveLoop — closed-loop cognitive substrate for SPEACE.

This module wires together the Global Workspace, temporal dynamics engine,
read-only cyber-physical sensors, the embodied action actuator, and a causal
world model into a single self-sustaining tick loop.  It is intentionally
minimal and safe: it only performs reversible, logged actions inside the
project's ``data/`` tree.
"""

from __future__ import annotations

import json
import math
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from speace_core.cellular_brain.cognition.global_workspace import GlobalWorkspace
from speace_core.cellular_brain.dynamics.temporal_dynamics_engine import (
    TemporalDynamicsEngine,
)
from speace_core.cellular_brain.embodiment.cyber_physical_sensor_array import (
    CyberPhysicalSensorArray,
)
from speace_core.cellular_brain.embodiment.embodied_action_actuator import (
    EmbodiedActionActuator,
)
from speace_core.cellular_brain.world_model.causal_world_model import (
    CausalWorldModel,
)


@dataclass
class AutonomousLoopStats:
    """Runtime statistics for the autonomous cognitive loop."""

    ticks: int = 0
    sensor_samples: int = 0
    actions_attempted: int = 0
    actions_successful: int = 0
    prediction_errors: List[float] = field(default_factory=list)
    average_coherence: float = 0.0
    average_awareness: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticks": self.ticks,
            "sensor_samples": self.sensor_samples,
            "actions_attempted": self.actions_attempted,
            "actions_successful": self.actions_successful,
            "prediction_error_latest": round(self.prediction_errors[-1], 6) if self.prediction_errors else None,
            "prediction_error_mean": round(sum(self.prediction_errors) / max(len(self.prediction_errors), 1), 6),
            "average_coherence": round(self.average_coherence, 4),
            "average_awareness": round(self.average_awareness, 4),
        }


class AutonomousCognitiveLoop:
    """A minimal closed-loop cognitive organ for SPEACE.

    The loop creates a small recurrent neural circuit, drives it with
    cyber-physical sensor readings, broadcasts the circuit state into the
    Global Workspace, and periodically performs a safe embodied action.
    Every action is audited and fed into a causal world model so SPEACE can
    learn action->effect relationships from its own behavior.

    The loop is deterministic given ``seed`` and is safe to run in tests
    with a temporary ``data_root``.
    """

    def __init__(
        self,
        data_root: Optional[Path] = None,
        seed: int = 42,
        n_neurons: int = 8,
        tick_dt: float = 0.1,
        action_interval_ticks: int = 10,
    ):
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.tick_dt = tick_dt
        self.action_interval_ticks = action_interval_ticks

        if data_root is None:
            self.data_root = Path("data") / "agi_runtime"
        else:
            self.data_root = Path(data_root)
        self.data_root.mkdir(parents=True, exist_ok=True)

        self.runtime_log_path = self.data_root / "loop_state.jsonl"
        self.prediction_error_path = self.data_root / "prediction_errors.jsonl"
        self.thoughts_path = self.data_root / "spontaneous_thoughts.jsonl"

        # Subsystems
        self.sensors = CyberPhysicalSensorArray(history_size=100)
        self.actuator = EmbodiedActionActuator(
            project_root=PROJECT_ROOT,
            data_root=str(self.data_root / "embodied_action_actuator"),
        )
        self.world_model = CausalWorldModel(
            data_root=str(self.data_root / "causal_world_model")
        )

        # Neural circuit
        self.neuron_ids = [f"n{i}" for i in range(n_neurons)]
        self.neurons = [
            {"cell_id": nid, "threshold": 0.5} for nid in self.neuron_ids
        ]
        self.synapses = self._seed_synapses(n_neurons)

        self.dynamics = TemporalDynamicsEngine(
            neurons=self.neurons,
            synapses=self.synapses,
            tau=1.0,
            tau_w=10.0,
            tau_e=5.0,
            noise_std=0.05,
            supply=0.1,
            consumption=0.05,
            plasticity_rate=0.05,
        )

        self.workspace = GlobalWorkspace(
            broadcast_dim=64,
            symbolic_dim=16,
            num_modules=10,
            seed=seed,
        )

        self.stats = AutonomousLoopStats()
        self._coherence_accum: float = 0.0
        self._awareness_accum: float = 0.0
        self._last_sensor_vector: Optional[np.ndarray] = None

    # ------------------------------------------------------------------ #
    # Seeding
    # ------------------------------------------------------------------ #

    def _seed_synapses(self, n: int) -> List[Dict[str, Any]]:
        """Create a small recurrent circuit with feed-forward and feedback."""
        synapses: List[Dict[str, Any]] = []
        # Feed-forward chain
        for i in range(n - 1):
            synapses.append(
                {
                    "source": f"n{i}",
                    "target": f"n{i + 1}",
                    "weight": 0.4 + 0.1 * self.rng.random(),
                    "decay": 0.001,
                }
            )
        # A few random feedback / lateral connections
        for _ in range(max(2, n // 2)):
            src = f"n{self.rng.integers(0, n)}"
            tgt = f"n{self.rng.integers(0, n)}"
            if src != tgt:
                synapses.append(
                    {"source": src, "target": tgt, "weight": 0.2, "decay": 0.001}
                )
        return synapses

    # ------------------------------------------------------------------ #
    # Perception
    # ------------------------------------------------------------------ #

    def read_sensors(self) -> Dict[str, Any]:
        """Sample the cyber-physical sensor array."""
        snapshot = self.sensors.read_all()
        self.stats.sensor_samples += 1
        return snapshot

    def _sensor_vector(self, snapshot: Dict[str, Any]) -> np.ndarray:
        """Flatten a few scalar sensor readings into a fixed-size vector."""
        cpu = snapshot.get("cpu", {})
        mem = snapshot.get("memory", {})
        disk = snapshot.get("disk", {})
        net = snapshot.get("network", {})

        # Extract normalized scalar features.
        features = [
            float(cpu.get("usage_percent_normalized", 0.0) or 0.0),
            float(cpu.get("frequency_mhz_normalized", 0.0) or 0.0),
            float(cpu.get("temperature_celsius_normalized", 0.0) or 0.0),
            float(mem.get("percent_normalized", 0.0) or 0.0),
            float(
                disk.get("drives", [{}])[0].get("percent_normalized", 0.0)
                if disk.get("drives")
                else 0.0
            ),
            float(net.get("bytes_sent", 0.0) or 0.0) / 1e6,  # MB
            float(net.get("bytes_received", 0.0) or 0.0) / 1e6,
            (time.time() % 60.0) / 60.0,  # time of minute as a cyclic feature
        ]
        vec = np.array(features, dtype=np.float64)
        # Pad or truncate to 64 dimensions to match workspace broadcast.
        broadcast = np.zeros(64, dtype=np.float64)
        broadcast[: min(len(vec), 64)] = vec[:64]
        return broadcast

    # ------------------------------------------------------------------ #
    # Tick
    # ------------------------------------------------------------------ #

    def tick(self) -> Dict[str, Any]:
        """Run one full autonomous cognitive cycle."""
        # 1. Sense the body
        snapshot = self.read_sensors()
        sensor_vec = self._sensor_vector(snapshot)
        self._last_sensor_vector = sensor_vec

        # Publish a simplified environment state for downstream monitors.
        env_state_path = self.data_root.parent / "embodiment" / "environment_state.jsonl"
        self._append_jsonl(env_state_path, {
            "timestamp": time.time(),
            "sensors": ["cpu", "memory", "disk", "network"],
            "cpu_usage": snapshot.get("cpu", {}).get("usage_percent"),
            "memory_percent": snapshot.get("memory", {}).get("percent"),
        })

        # 2. Drive sensory neurons from sensor features
        n_features = min(len(sensor_vec), len(self.neuron_ids))
        for i in range(n_features):
            stimulus = float(sensor_vec[i])
            self.dynamics.inject_input(self.neuron_ids[i], stimulus)

        # 3. Advance continuous neural dynamics
        self.dynamics.step(self.tick_dt)

        # 4. Build a neural-state representation and broadcast it
        neural_repr = self._neural_state_vector()
        self.workspace.broadcast("sensory", sensor_vec.tolist())
        self.workspace.broadcast("neural", neural_repr.tolist())

        # 5. Advance workspace (attention, recurrence, prediction)
        ws_state = self.workspace.step()

        # 6. Track prediction error for continuous learning metric
        pred_error = float(ws_state.get("prediction_error", 0.0) or 0.0)
        self.stats.prediction_errors.append(pred_error)
        self._append_jsonl(self.prediction_error_path, {
            "tick": self.stats.ticks,
            "prediction_error": pred_error,
            "timestamp": time.time(),
        })

        # 7. Periodic safe embodied action + causal learning
        action_record: Optional[Dict[str, Any]] = None
        if self.stats.ticks > 0 and self.stats.ticks % self.action_interval_ticks == 0:
            action_record = self._perform_safe_action(ws_state)

        # 8. Spontaneous thought if workspace is coherent and aware
        thought = None
        if ws_state.get("coherence", 0.0) > 0.6 and ws_state.get("awareness_level", 0.0) > 0.4:
            thought = self._spontaneous_thought(ws_state)

        # Update running averages
        self._coherence_accum += float(ws_state.get("coherence", 0.0) or 0.0)
        self._awareness_accum += float(ws_state.get("awareness_level", 0.0) or 0.0)
        self.stats.average_coherence = self._coherence_accum / (self.stats.ticks + 1)
        self.stats.average_awareness = self._awareness_accum / (self.stats.ticks + 1)
        self.stats.ticks += 1

        # 9. Persist loop state
        record = {
            "tick": self.stats.ticks,
            "timestamp": time.time(),
            "workspace": {
                "coherence": round(ws_state.get("coherence", 0.0), 4),
                "awareness_level": round(ws_state.get("awareness_level", 0.0), 4),
                "energy": round(ws_state.get("energy", 0.0), 4),
                "prediction_error": round(pred_error, 6),
                "winning_module": ws_state.get("winning_module"),
            },
            "sensors": {
                "cpu_usage": snapshot.get("cpu", {}).get("usage_percent"),
                "memory_percent": snapshot.get("memory", {}).get("percent"),
            },
            "action": action_record,
            "thought": thought,
        }
        self._append_jsonl(self.runtime_log_path, record)

        return record

    def _neural_state_vector(self) -> np.ndarray:
        """Return the current continuous activations as a 64-dim vector."""
        activations = np.array([self.dynamics.get_neuron_state(nid) for nid in self.neuron_ids], dtype=np.float64)
        broadcast = np.zeros(64, dtype=np.float64)
        broadcast[: min(len(activations), 64)] = activations[:64]
        return broadcast

    def _perform_safe_action(self, ws_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute a reversible, logged embodied action if coherence permits."""
        if ws_state.get("coherence", 0.0) < 0.3:
            return None

        self.stats.actions_attempted += 1
        log_path = str(self.data_root / "autonomous_log.txt")
        content = (
            f"Autonomous tick {self.stats.ticks} | coherence={ws_state.get('coherence'):.3f} | "
            f"awareness={ws_state.get('awareness_level'):.3f}\n"
        )
        try:
            result = self.actuator.execute_action(
                "write_text_file",
                {"path": log_path, "content": content},
                approval_level="automatic",
            )
            success = bool(result.get("success", False))
            if success:
                self.stats.actions_successful += 1

            # Record in causal world model
            effect = "log_written" if success else "log_failed"
            self.world_model.record_observation(
                action_name="write_text_file",
                action_params={"path": log_path},
                effect=effect,
                confidence=1.0 if success else 0.0,
                context={"tick": self.stats.ticks, "coherence": ws_state.get("coherence")},
            )

            return {
                "action_type": "write_text_file",
                "success": success,
                "effect": effect,
                "path": log_path,
            }
        except Exception as exc:
            return {"action_type": "write_text_file", "success": False, "error": str(exc)}

    def _spontaneous_thought(self, ws_state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a minimal symbolic thought from workspace focus."""
        focus = ws_state.get("winning_module", "spontaneous")
        symbolic = ws_state.get("symbolic_state", [])
        # Very primitive semantics: high-symbolic dimensions become "concepts".
        concepts = [f"dim_{i}" for i, v in enumerate(symbolic[:8]) if float(v) > 0.3]
        thought_text = f"Focus: {focus}; active concepts: {', '.join(concepts) if concepts else 'none'}"
        record = {
            "tick": self.stats.ticks,
            "timestamp": time.time(),
            "text": thought_text,
            "coherence": round(ws_state.get("coherence", 0.0), 4),
            "awareness_level": round(ws_state.get("awareness_level", 0.0), 4),
        }
        self._append_jsonl(self.thoughts_path, record)
        return record

    # ------------------------------------------------------------------ #
    # Public run helpers
    # ------------------------------------------------------------------ #

    def run(self, n_ticks: int = 100, tick_interval: Optional[float] = None) -> AutonomousLoopStats:
        """Run the autonomous loop for a fixed number of ticks."""
        for _ in range(n_ticks):
            self.tick()
            if tick_interval is not None:
                time.sleep(tick_interval)
        return self.stats

    def summary(self) -> Dict[str, Any]:
        """Return a summary of the loop's activity."""
        return {
            "loop_id": f"acl-{uuid.uuid4().hex[:8]}",
            "seed": self.seed,
            "data_root": str(self.data_root),
            "stats": self.stats.to_dict(),
            "world_model": self.world_model.summary(),
        }

    # ------------------------------------------------------------------ #
    # Utility
    # ------------------------------------------------------------------ #

    def _append_jsonl(self, path: Path, record: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")


# Resolve project root once at module load time.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
