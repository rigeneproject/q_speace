"""EnvironmentAdapter — connect SPEACE orchestrator to external tasks.

Provides a unified interface to:
  - CognitivePredictionEnvironment (sequence prediction)
  - GridWorldEnvironment (embodied navigation)

The adapter handles:
  - genome loading
  - orchestrator setup with optional COR and simulator backend
  - running episodes
  - reporting
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional

from speace_core.dna.parser import load_genome
from speace_core.orchestrator import CellularBrainOrchestrator
from speace_core.environment.cognitive_prediction_environment import (
    CognitivePredictionEnvironment,
    SequenceMode,
)
from speace_core.environment.grid_world_environment import GridWorldEnvironment
from speace_core.environment.associative_recall_environment import (
    AssociativeRecallEnvironment,
)


class EnvironmentAdapter:
    """Run SPEACE against an external task environment."""

    def __init__(
        self,
        genome_path: Optional[Path] = None,
        enable_cor: bool = True,
        cor_phi_threshold_factor: float = 0.55,
        enable_simulator_backend: bool = True,
        simulator_backend_name: str = "native",
        simulator_backend_interval: int = 10,
        enable_functional_activation: bool = True,
    ):
        self.genome_path = genome_path or Path(
            r"C:\cellular_speace\speace_core\dna\genome\default_genome.yaml"
        )
        self.enable_cor = enable_cor
        self.cor_phi_threshold_factor = cor_phi_threshold_factor
        self.enable_simulator_backend = enable_simulator_backend
        self.simulator_backend_name = simulator_backend_name
        self.simulator_backend_interval = simulator_backend_interval
        self.enable_functional_activation = enable_functional_activation

        self.genome = load_genome(self.genome_path)
        self.orchestrator: Optional[CellularBrainOrchestrator] = None
        self._build_orchestrator()

    def _build_orchestrator(self) -> None:
        """Build and configure the SPEACE orchestrator."""
        orch = CellularBrainOrchestrator.build_mvp(
            self.genome,
            ilf_enabled=True,
            energy_field_enabled=True,
            homeostatic_drive_enabled=True,
            criticality_monitor_enabled=True,
            systemic_harmony_enabled=True,
        )

        if self.enable_cor:
            orch.cor_enabled = True
            orch.cor_phi_threshold_factor = self.cor_phi_threshold_factor
            orch.cor_min_latent_states = 2
            orch.cor_max_hypotheses = 4

        if self.enable_simulator_backend:
            orch.simulator_backend_enabled = True
            orch.simulator_backend_name = self.simulator_backend_name
            orch.simulator_backend_interval_ticks = self.simulator_backend_interval

        orch.model_post_init(None)
        self.orchestrator = orch

        # Seed latent superpositions and functional activation rules
        # on a subset of hidden neurons.
        for idx, n in enumerate(orch.circuit.hidden_neurons[:5]):
            if self.enable_functional_activation:
                n.functional_activation_gate.rules = [
                    r.model_copy() for r in self.genome.functional_activation.rules
                ]
            n.update_latent_states({"explore": 0.3, "exploit": 0.7})
            n.cor_pressure = 0.2

    def run_prediction_episode(
        self,
        mode: SequenceMode = SequenceMode.PERIODIC,
        steps: int = 100,
    ) -> Dict[str, Any]:
        """Run one prediction episode and return summary."""
        assert self.orchestrator is not None
        env = CognitivePredictionEnvironment(
            input_size=len(self.orchestrator.circuit.input_neurons),
            output_size=len(self.orchestrator.circuit.output_neurons),
            mode=mode,
            episode_length=steps,
        )
        return env.run_episode(self.orchestrator)

    def run_grid_episode(
        self,
        dimensions: int = 1,
        size: int = 10,
    ) -> Dict[str, Any]:
        """Run one grid-world episode and return summary."""
        assert self.orchestrator is not None
        env = GridWorldEnvironment(dimensions=dimensions, size=size)
        return env.run_episode(self.orchestrator)

    def run_associative_recall_episode(
        self,
        num_pairs: int = 4,
        study_repetitions: int = 3,
        test_length: int = 20,
    ) -> Dict[str, Any]:
        """Run one associative recall episode and return summary."""
        assert self.orchestrator is not None
        env = AssociativeRecallEnvironment(
            input_size=len(self.orchestrator.circuit.input_neurons),
            output_size=len(self.orchestrator.circuit.output_neurons),
            num_pairs=num_pairs,
            study_repetitions=study_repetitions,
            test_length=test_length,
        )
        return env.run_episode(self.orchestrator)

    def run_training_loop(
        self,
        episodes: int = 5,
        env_kind: str = "prediction",
        **env_kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """Run multiple episodes and return per-episode summaries."""
        summaries: List[Dict[str, Any]] = []
        for ep in range(episodes):
            if env_kind == "prediction":
                mode = env_kwargs.get("mode", SequenceMode.PERIODIC)
                # Rotate modes across episodes for variety.
                modes = list(SequenceMode)
                mode = modes[ep % len(modes)]
                summary = self.run_prediction_episode(mode=mode, steps=100)
            elif env_kind == "grid":
                summary = self.run_grid_episode(
                    dimensions=env_kwargs.get("dimensions", 1),
                    size=env_kwargs.get("size", 10),
                )
            elif env_kind == "associative":
                summary = self.run_associative_recall_episode(
                    num_pairs=env_kwargs.get("num_pairs", 4),
                    study_repetitions=env_kwargs.get("study_repetitions", 3),
                    test_length=env_kwargs.get("test_length", 20),
                )
            else:
                raise ValueError(f"Unknown env_kind: {env_kind}")
            summaries.append(summary)
        return summaries

    def report(self) -> Dict[str, Any]:
        """Current orchestrator status."""
        assert self.orchestrator is not None
        m = self.orchestrator.latest_metrics
        return {
            "tick": self.orchestrator.current_tick,
            "coherence_phi": getattr(m, "coherence_phi", None),
            "mean_energy": getattr(m, "mean_energy", None),
            "active_neurons": getattr(m, "active_neurons", None),
            "cor_enabled": self.orchestrator.cor_enabled,
            "simulator_backend_enabled": self.orchestrator.simulator_backend_enabled,
            "simulator_backend_log_size": len(self.orchestrator._simulator_backend_log),
        }
