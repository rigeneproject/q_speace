"""ThoughtPhaseTransitionEngine — T2: transizioni di fase nella produzione del pensiero.

Guidato da:
  - densità informativa nei comparti (InformationDensityEngine)
  - connettività (TopologyMetrics, RegionConnectome)

Transizioni caratterizzate da:
  - progressi incrementali (IncrementalProgressTracker)
  - cambiamenti nella coerenza (Phi, CoherenceObserver)
  - accoppiamento di scala (ScaleCouplingEngine)
  - dinamica di replicazione (ReplicationDynamicsEngine)
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class ThoughtPhase(Enum):
    EXPLORATION = "exploration"
    EXPLOITATION = "exploitation"
    ASSIMILATION = "assimilation"
    ACCOMMODATION = "accommodation"
    DIVERGENT = "divergent"
    CONVERGENT = "convergent"
    CRITICAL = "critical"
    METACOGNITIVE = "metacognitive"
    DEFAULT = "default"
    INTEGRATION = "integration"


@dataclass
class PhaseTransition:
    source_phase: ThoughtPhase
    target_phase: ThoughtPhase
    timestamp: float
    trigger: str  # "info_density" | "connectivity" | "coherence" | "scale_coupling"
    trigger_value: float
    magnitude: float  # 0=incremental, 1=abrupt
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CompartmentPhaseState:
    compartment_id: str
    current_phase: ThoughtPhase = ThoughtPhase.DEFAULT
    info_density: float = 0.0
    connectivity_density: float = 0.0
    coherence_phi: float = 0.0
    scale_coupling_strength: float = 0.0
    phase_stability: float = 1.0  # lower = more likely to transition
    transitions: List[PhaseTransition] = field(default_factory=list)


class ThoughtPhaseTransitionEngine:
    """Monitora compartimenti e rileva transizioni di fase cognitive.

    Le transizioni sono guidate da soglie su:
      - information density (da InformationDensityEngine)
      - connectivity density (da TopologyMetrics/RegionConnectome)
      - coherence phi (da HomeostasisEngine)
      - scale coupling strength (da ScaleCouplingEngine)

    Quando una metrica supera una soglia configurabile, il compartimento
    transisce a una nuova fase del pensiero.
    """

    def __init__(
        self,
        density_engine=None,
        topology_metrics=None,
        coherence_provider=None,
        scale_coupling_engine=None,
        density_thresholds: Optional[Dict[str, float]] = None,
        connectivity_thresholds: Optional[Dict[str, float]] = None,
        transition_hooks: Optional[Dict[Tuple[ThoughtPhase, ThoughtPhase], Callable]] = None,
    ):
        self.density_engine = density_engine
        self.topology_metrics = topology_metrics
        self.coherence_provider = coherence_provider
        self.scale_coupling_engine = scale_coupling_engine

        self.density_thresholds = density_thresholds or {
            "exploration_min": 0.15,
            "exploitation_min": 0.35,
            "divergent_min": 0.25,
            "convergent_min": 0.40,
            "critical_min": 0.50,
            "metacognitive_min": 0.45,
            "integration_min": 0.55,
        }

        self.connectivity_thresholds = connectivity_thresholds or {
            "exploration_min": 0.05,
            "exploitation_min": 0.15,
            "divergent_min": 0.10,
            "convergent_min": 0.20,
            "critical_min": 0.25,
            "metacognitive_min": 0.20,
            "integration_min": 0.30,
        }

        self.transition_hooks = transition_hooks or {}

        self._compartment_states: Dict[str, CompartmentPhaseState] = {}
        self._global_phase: ThoughtPhase = ThoughtPhase.DEFAULT
        self._transition_history: List[PhaseTransition] = []

        # Phase transition probabilities (from -> to)
        self._transition_matrix: Dict[Tuple[ThoughtPhase, ThoughtPhase], float] = {
            (ThoughtPhase.DEFAULT, ThoughtPhase.EXPLORATION): 1.0,
            (ThoughtPhase.EXPLORATION, ThoughtPhase.ASSIMILATION): 0.6,
            (ThoughtPhase.EXPLORATION, ThoughtPhase.DIVERGENT): 0.4,
            (ThoughtPhase.ASSIMILATION, ThoughtPhase.ACCOMMODATION): 0.5,
            (ThoughtPhase.ASSIMILATION, ThoughtPhase.CONVERGENT): 0.5,
            (ThoughtPhase.DIVERGENT, ThoughtPhase.CONVERGENT): 0.7,
            (ThoughtPhase.DIVERGENT, ThoughtPhase.EXPLORATION): 0.3,
            (ThoughtPhase.CONVERGENT, ThoughtPhase.EXPLOITATION): 0.6,
            (ThoughtPhase.CONVERGENT, ThoughtPhase.INTEGRATION): 0.4,
            (ThoughtPhase.EXPLOITATION, ThoughtPhase.INTEGRATION): 0.5,
            (ThoughtPhase.EXPLOITATION, ThoughtPhase.METACOGNITIVE): 0.5,
            (ThoughtPhase.INTEGRATION, ThoughtPhase.METACOGNITIVE): 0.6,
            (ThoughtPhase.INTEGRATION, ThoughtPhase.CRITICAL): 0.4,
            (ThoughtPhase.METACOGNITIVE, ThoughtPhase.CRITICAL): 0.3,
            (ThoughtPhase.METACOGNITIVE, ThoughtPhase.INTEGRATION): 0.7,
            (ThoughtPhase.CRITICAL, ThoughtPhase.INTEGRATION): 0.8,
            (ThoughtPhase.CRITICAL, ThoughtPhase.METACOGNITIVE): 0.2,
        }

    # ------------------------------------------------------------------ #
    # Core tick
    # ------------------------------------------------------------------ #

    def tick(self, tick: int) -> List[PhaseTransition]:
        """Esegue un passo di monitoraggio e rilevamento transizioni."""
        transitions: List[PhaseTransition] = []

        densities = self._get_densities()
        connectivity = self._get_connectivity()
        coherence = self._get_coherence()
        scale_coupling = self._get_scale_coupling()

        # Per ogni compartimento, valuta transizione
        all_compartments = self._list_compartments()
        for comp_id in all_compartments:
            d = densities.get(comp_id, 0.0)
            c = connectivity.get(comp_id, 0.0)
            phi = coherence.get(comp_id, 0.0)
            sc = scale_coupling.get(comp_id, 0.0)

            state = self._compartment_states.setdefault(
                comp_id,
                CompartmentPhaseState(compartment_id=comp_id),
            )
            state.info_density = d
            state.connectivity_density = c
            state.coherence_phi = phi
            state.scale_coupling_strength = sc

            new_phase = self._evaluate_phase(d, c, phi, sc, state.current_phase)
            if new_phase != state.current_phase:
                magnitude = self._compute_transition_magnitude(
                    state.current_phase, new_phase, d, c, phi
                )
                trigger = self._identify_trigger(d, c, phi, sc)
                trigger_value = {
                    "info_density": d,
                    "connectivity": c,
                    "coherence": phi,
                    "scale_coupling": sc,
                }.get(trigger, 0.0)

                transition = PhaseTransition(
                    source_phase=state.current_phase,
                    target_phase=new_phase,
                    timestamp=time.time(),
                    trigger=trigger,
                    trigger_value=trigger_value,
                    magnitude=magnitude,
                    metadata={
                        "tick": tick,
                        "compartment": comp_id,
                        "info_density": d,
                        "connectivity_density": c,
                        "coherence_phi": phi,
                        "scale_coupling": sc,
                    },
                )
                state.transitions.append(transition)
                state.current_phase = new_phase
                state.phase_stability = 1.0 - magnitude
                transitions.append(transition)
                self._transition_history.append(transition)

                self._call_hook(transition)
            else:
                # Increment stability when no transition
                state.phase_stability = min(1.0, state.phase_stability + 0.05)

        # Update global phase (mode of compartment phases)
        self._update_global_phase()

        return transitions

    # ------------------------------------------------------------------ #
    # Phase evaluation
    # ------------------------------------------------------------------ #

    def _evaluate_phase(
        self,
        info_density: float,
        connectivity: float,
        coherence: float,
        scale_coupling: float,
        current: ThoughtPhase,
    ) -> ThoughtPhase:
        """Determina la fase del pensiero basata sulle metriche."""
        thresholds = self.density_thresholds
        conn_th = self.connectivity_thresholds

        # Critical state: high density + high connectivity + high coherence
        if (
            info_density >= thresholds.get("critical_min", 0.50)
            and connectivity >= conn_th.get("critical_min", 0.25)
            and coherence > 0.7
        ):
            return ThoughtPhase.CRITICAL

        # Metacognitive: high density + moderate connectivity + high coherence
        if (
            info_density >= thresholds.get("metacognitive_min", 0.45)
            and connectivity >= conn_th.get("metacognitive_min", 0.20)
            and coherence > 0.5
        ):
            return ThoughtPhase.METACOGNITIVE

        # Integration: moderate-high density + moderate-high connectivity
        if (
            info_density >= thresholds.get("integration_min", 0.55)
            and connectivity >= conn_th.get("integration_min", 0.30)
        ):
            return ThoughtPhase.INTEGRATION

        # Convergent: high density + high connectivity
        if (
            info_density >= thresholds.get("convergent_min", 0.40)
            and connectivity >= conn_th.get("convergent_min", 0.20)
        ):
            return ThoughtPhase.CONVERGENT

        # Divergent: moderate density + low connectivity
        if (
            info_density >= thresholds.get("divergent_min", 0.25)
            and connectivity < conn_th.get("convergent_min", 0.20)
        ):
            return ThoughtPhase.DIVERGENT

        # Exploitation: moderate density + moderate connectivity
        if (
            info_density >= thresholds.get("exploitation_min", 0.35)
            and connectivity >= conn_th.get("exploitation_min", 0.15)
        ):
            return ThoughtPhase.EXPLOITATION

        # Assimilation: low-moderate density + low connectivity
        if (
            info_density >= thresholds.get("exploration_min", 0.15)
            and connectivity >= conn_th.get("exploration_min", 0.05)
        ):
            # Distinguish between assimilation and accommodation
            if scale_coupling > 0.3:
                return ThoughtPhase.ACCOMMODATION
            return ThoughtPhase.ASSIMILATION

        # Exploration: low density + low connectivity
        if info_density < thresholds.get("exploration_min", 0.15):
            return ThoughtPhase.EXPLORATION

        return current

    # ------------------------------------------------------------------ #
    # Transition characteristics
    # ------------------------------------------------------------------ #

    def _compute_transition_magnitude(
        self,
        source: ThoughtPhase,
        target: ThoughtPhase,
        info_density: float,
        connectivity: float,
        coherence: float,
    ) -> float:
        """0 = incrementale, 1 = abrupt.

        Un cambiamento piccolo nelle metriche guida una transizione
        incrementale; un salto grande guida una transizione abrupta.
        """
        # Distance in the thought phase graph
        phase_distance = 0.0
        if (source, target) in self._transition_matrix:
            prob = self._transition_matrix[(source, target)]
            # Lower probability = more distant transition = more abrupt
            phase_distance = 1.0 - prob

        # Metric-based magnitude
        metric_magnitude = abs(info_density + connectivity + coherence) / 3.0

        return round(min(1.0, (phase_distance + metric_magnitude) / 2.0), 4)

    def _identify_trigger(
        self,
        info_density: float,
        connectivity: float,
        coherence: float,
        scale_coupling: float,
    ) -> str:
        """Identifica quale metrica ha principalmente guidato la transizione."""
        scores = {
            "info_density": info_density,
            "connectivity": connectivity,
            "coherence": coherence,
            "scale_coupling": scale_coupling,
        }
        return max(scores, key=scores.get)

    # ------------------------------------------------------------------ #
    # Data providers
    # ------------------------------------------------------------------ #

    def _get_densities(self) -> Dict[str, float]:
        if not self.density_engine:
            return {}
        report = self.density_engine.compute_all()
        return {
            cid: cdata.get("combined_density", 0.0)
            for cid, cdata in report.get("compartments", {}).items()
        }

    def _get_connectivity(self) -> Dict[str, float]:
        if not self.topology_metrics:
            return {}
        try:
            report = self.topology_metrics.compute_all()
            return {
                "global": report.get("density", 0.0),
            }
        except Exception:
            return {}

    def _get_coherence(self) -> Dict[str, float]:
        if not self.coherence_provider:
            return {}
        try:
            if hasattr(self.coherence_provider, "observe"):
                report = self.coherence_provider.observe()
                return {
                    "global": report.get("aggregate_coherence", 0.0),
                }
            return {}
        except Exception:
            return {}

    def _get_scale_coupling(self) -> Dict[str, float]:
        if not self.scale_coupling_engine:
            return {}
        try:
            metrics = self.scale_coupling_engine.get_global_coupling_metrics()
            return {
                "global": metrics.get("global_coupling_strength", 0.0),
            }
        except Exception:
            return {}

    def _list_compartments(self) -> List[str]:
        compartments = ["global"]
        if self.density_engine:
            report = self.density_engine.compute_all()
            compartments.extend(report.get("compartments", {}).keys())
        return list(set(compartments))

    # ------------------------------------------------------------------ #
    # Global phase
    # ------------------------------------------------------------------ #

    def _update_global_phase(self) -> None:
        """Global phase = mode of compartment phases."""
        if not self._compartment_states:
            return
        phases = [s.current_phase for s in self._compartment_states.values()]
        if not phases:
            return
        self._global_phase = max(set(phases), key=phases.count)

    def get_global_phase(self) -> ThoughtPhase:
        return self._global_phase

    # ------------------------------------------------------------------ #
    # Hooks
    # ------------------------------------------------------------------ #

    def register_transition_hook(
        self,
        source: ThoughtPhase,
        target: ThoughtPhase,
        hook: Callable,
    ) -> None:
        self.transition_hooks[(source, target)] = hook

    def _call_hook(self, transition: PhaseTransition) -> None:
        hook = self.transition_hooks.get(
            (transition.source_phase, transition.target_phase)
        )
        if hook:
            try:
                hook(transition)
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    # Diagnostics
    # ------------------------------------------------------------------ #

    def get_transition_history(
        self,
        limit: int = 100,
        phase_filter: Optional[ThoughtPhase] = None,
    ) -> List[PhaseTransition]:
        history = self._transition_history[-limit:]
        if phase_filter:
            history = [
                t for t in history
                if t.source_phase == phase_filter or t.target_phase == phase_filter
            ]
        return history

    def get_compartment_state(self, compartment_id: str) -> Optional[CompartmentPhaseState]:
        return self._compartment_states.get(compartment_id)

    def get_all_compartment_states(self) -> Dict[str, CompartmentPhaseState]:
        return dict(self._compartment_states)

    def get_phase_transition_rate(self) -> float:
        """Media di transizioni per tick nelle ultime 100 osservazioni."""
        recent = self._transition_history[-100:]
        if not recent or len(recent) < 2:
            return 0.0
        time_span = recent[-1].timestamp - recent[0].timestamp
        if time_span <= 0:
            return 0.0
        return len(recent) / time_span

    def get_incremental_progress_score(self) -> float:
        """Proporzione di transizioni incrementali (magnitude < 0.3)."""
        recent = self._transition_history[-200:]
        if not recent:
            return 0.0
        incremental = sum(1 for t in recent if t.magnitude < 0.3)
        return incremental / len(recent)
