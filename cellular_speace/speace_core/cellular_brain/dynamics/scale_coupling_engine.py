"""ScaleCouplingEngine — T3: accoppiamento cross-scala esplicito.

Monitora e quantifica l'accoppiamento tra livelli:
  - Micro: neuroni individuali
  - Meso: circuiti neurali
  - Macro: regioni cerebrali
  - Mega: organismo intero

Ogni livello ha metriche di stato; l'engine calcola la forza di
accoppiamento (coerenza, flusso informativo) tra livelli adiacenti.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ScaleLevelState:
    level: str  # "micro" | "meso" | "macro" | "mega"
    mean_activation: float = 0.0
    mean_energy: float = 0.0
    coherence: float = 0.0
    complexity: float = 0.0
    synchrony: float = 0.0
    n_units: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CrossScaleCoupling:
    source_level: str
    target_level: str
    coupling_strength: float = 0.0  # 0 = decoupled, 1 = perfectly coupled
    coherence_correlation: float = 0.0
    info_flow: float = 0.0
    phase_lag: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class ScaleCouplingEngine:
    """Calcola metriche di accoppiamento cross-scala.

    Usage::

        engine = ScaleCouplingEngine(circuit, region_connectome)
        report = engine.tick()
    """

    LEVELS = ["micro", "meso", "macro", "mega"]

    def __init__(
        self,
        circuit=None,
        region_connectome=None,
        orchestrator=None,
        history_size: int = 100,
    ):
        self.circuit = circuit
        self.region_connectome = region_connectome
        self.orch = orchestrator

        self._level_history: Dict[str, List[ScaleLevelState]] = {
            lvl: [] for lvl in self.LEVELS
        }
        self._coupling_history: Dict[Tuple[str, str], List[CrossScaleCoupling]] = {}
        self._history_size = history_size

        self._phase_coupling_engine = None

    def set_phase_coupling_engine(self, engine) -> None:
        self._phase_coupling_engine = engine

    # ------------------------------------------------------------------ #
    # Tick
    # ------------------------------------------------------------------ #

    def tick(self) -> Dict[str, Any]:
        """Esegue un passo di osservazione cross-scala."""
        micro = self._observe_micro()
        meso = self._observe_meso()
        macro = self._observe_macro()
        mega = self._observe_mega()

        levels = {"micro": micro, "meso": meso, "macro": macro, "mega": mega}

        for lvl_name, lvl_state in levels.items():
            self._level_history[lvl_name].append(lvl_state)
            if len(self._level_history[lvl_name]) > self._history_size:
                self._level_history[lvl_name].pop(0)

        # Compute pairwise couplings
        couplings: Dict[str, CrossScaleCoupling] = {}
        pairs = [("micro", "meso"), ("meso", "macro"), ("macro", "mega")]
        for src, tgt in pairs:
            if src in levels and tgt in levels:
                coupling = self._compute_cross_coupling(
                    levels[src], levels[tgt], src, tgt
                )
                key = f"{src}_to_{tgt}"
                couplings[key] = coupling
                self._coupling_history.setdefault((src, tgt), []).append(coupling)
                hist = self._coupling_history[(src, tgt)]
                if len(hist) > self._history_size:
                    hist.pop(0)

        return {
            "timestamp": time.time(),
            "levels": {k: v.__dict__ for k, v in levels.items()},
            "couplings": {k: v.__dict__ for k, v in couplings.items()},
            "global_coupling_strength": self._global_coupling(couplings),
        }

    # ------------------------------------------------------------------ #
    # Level observations
    # ------------------------------------------------------------------ #

    def _observe_micro(self) -> ScaleLevelState:
        """Micro: neuroni individuali."""
        if not self.circuit:
            return ScaleLevelState(level="micro")

        all_n = (
            self.circuit.input_neurons
            + self.circuit.hidden_neurons
            + self.circuit.output_neurons
        )
        if not all_n:
            return ScaleLevelState(level="micro")

        activations = [getattr(n, "activation", 0.0) for n in all_n]
        energies = [getattr(n, "energy", 1.0) for n in all_n]
        mean_act = sum(activations) / len(activations)
        mean_en = sum(energies) / len(energies)

        # Synchrony: variance of activations (low variance = high synchrony)
        act_var = (
            sum((a - mean_act) ** 2 for a in activations) / len(activations)
            if len(activations) > 1
            else 0.0
        )
        synchrony = 1.0 - min(1.0, act_var * 5)

        return ScaleLevelState(
            level="micro",
            mean_activation=mean_act,
            mean_energy=mean_en,
            synchrony=synchrony,
            n_units=len(all_n),
        )

    def _observe_meso(self) -> ScaleLevelState:
        """Meso: circuiti."""
        if not self.circuit:
            return ScaleLevelState(level="meso")

        synapses = self.circuit.synapses
        weights = [getattr(s, "weight", 0.0) for s in synapses] if synapses else [0.0]

        mean_w = sum(weights) / len(weights) if weights else 0.0
        w_var = (
            sum((w - mean_w) ** 2 for w in weights) / len(weights)
            if len(weights) > 1
            else 0.0
        )

        # Coherence proxy: weight distribution stability
        coherence = 1.0 - min(1.0, w_var * 2)

        return ScaleLevelState(
            level="meso",
            mean_activation=mean_w,
            coherence=coherence,
            complexity=len(weights),
            synchrony=coherence,
            n_units=len(synapses) if synapses else 0,
        )

    def _observe_macro(self) -> ScaleLevelState:
        """Macro: regioni cerebrali."""
        if not self.region_connectome:
            return ScaleLevelState(level="macro")

        regions_dict = self.region_connectome.regions
        connections = self.region_connectome.connections

        n_regions = len(regions_dict)
        n_connections = len(connections)

        # Complexity: number of distinct region types
        types = set()
        for r in regions_dict.values():
            rt = getattr(r, "region_type", None) or (
                r.get("region_type") if isinstance(r, dict) else None
            )
            if rt:
                types.add(str(rt))

        return ScaleLevelState(
            level="macro",
            complexity=len(types),
            synchrony=n_connections / max(n_regions * (n_regions - 1), 1),
            n_units=n_regions,
        )

    def _observe_mega(self) -> ScaleLevelState:
        """Mega: organismo intero."""
        coherence = 0.0
        if self.orch and hasattr(self.orch, "last_metrics") and self.orch.last_metrics:
            coherence = getattr(self.orch.last_metrics, "coherence_phi", 0.0)

        return ScaleLevelState(
            level="mega",
            coherence=coherence,
            n_units=1,
        )

    # ------------------------------------------------------------------ #
    # Cross-scale coupling computation
    # ------------------------------------------------------------------ #

    def _compute_cross_coupling(
        self,
        source: ScaleLevelState,
        target: ScaleLevelState,
        src_name: str,
        tgt_name: str,
    ) -> CrossScaleCoupling:
        """Calcola forza di accoppiamento tra due livelli."""
        # Coherence correlation
        coh_corr = abs(source.coherence - target.coherence)
        coh_corr = 1.0 - min(1.0, coh_corr)

        # Synchrony coupling
        sync_coupling = abs(source.synchrony - target.synchrony)
        sync_coupling = 1.0 - min(1.0, sync_coupling * 2)

        # Activation correlation
        act_coupling = abs(source.mean_activation - target.mean_activation)
        act_coupling = 1.0 - min(1.0, abs(act_coupling))

        # Phase coupling from Kuramoto engine
        phase_lag = 0.0
        if self._phase_coupling_engine:
            try:
                # Check if oscillators bridge these levels
                src_osc = f"{src_name}_hub"
                tgt_osc = f"{tgt_name}_hub"
                oscs = self._phase_coupling_engine.list_oscillators()
                if src_osc in oscs and tgt_osc in oscs:
                    phase_lag = abs(
                        self._phase_coupling_engine.get_phase_difference(
                            src_osc, tgt_osc
                        )
                    )
            except Exception:
                pass

        coupling_strength = round(
            (coh_corr * 0.3 + sync_coupling * 0.25 + act_coupling * 0.25
             + (1.0 - phase_lag / math.pi) * 0.2),
            4,
        )

        info_flow = round(
            (coupling_strength * source.n_units / max(target.n_units, 1))
            * min(1.0, source.complexity / max(target.complexity, 1)),
            4,
        ) if target.n_units > 0 else 0.0

        return CrossScaleCoupling(
            source_level=src_name,
            target_level=tgt_name,
            coupling_strength=coupling_strength,
            coherence_correlation=round(coh_corr, 4),
            info_flow=info_flow,
            phase_lag=round(phase_lag, 4),
        )

    def _global_coupling(self, couplings: Dict[str, CrossScaleCoupling]) -> float:
        if not couplings:
            return 0.0
        strengths = [c.coupling_strength for c in couplings.values()]
        return round(sum(strengths) / len(strengths), 4)

    # ------------------------------------------------------------------ #
    # Diagnostics
    # ------------------------------------------------------------------ #

    def get_global_coupling_metrics(self) -> Dict[str, float]:
        """Restituisce metriche aggregate di accoppiamento."""
        # Latest coupling per pair
        coupling_by_pair = {}
        for (src, tgt), history in self._coupling_history.items():
            if history:
                coupling_by_pair[f"{src}_to_{tgt}"] = history[-1].coupling_strength

        global_strength = (
            sum(coupling_by_pair.values()) / len(coupling_by_pair)
            if coupling_by_pair
            else 0.0
        )

        return {
            "global_coupling_strength": round(global_strength, 4),
            "micro_meso_coupling": coupling_by_pair.get("micro_to_meso", 0.0),
            "meso_macro_coupling": coupling_by_pair.get("meso_to_macro", 0.0),
            "macro_mega_coupling": coupling_by_pair.get("macro_to_mega", 0.0),
            "n_levels_active": sum(
                1 for lvl in self.LEVELS if self._level_history[lvl]
            ),
        }

    def get_coupling_trend(
        self, src_level: str = "micro", tgt_level: str = "meso"
    ) -> List[float]:
        """Trend storico della forza di accoppiamento tra due livelli."""
        history = self._coupling_history.get((src_level, tgt_level), [])
        return [c.coupling_strength for c in history]

    def get_level_trend(self, level: str, metric: str = "coherence") -> List[float]:
        """Trend storico di una metrica per un livello."""
        history = self._level_history.get(level, [])
        return [getattr(s, metric, 0.0) for s in history]
