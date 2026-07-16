"""Causal Memory for SPEACE.

Traccia gli outcomes del sistema (energia, coerenza, riflessi, drive) in una
finestra scorrevole e rileva pattern ripetuti. Quando un pattern supera una
soglia, emette un *CausalInsight* che suggerisce un'azione epigenetica.

Questo è il primo anello del ciclo chiuso:
    esperienza → memoria causale → epigenetica → ristrutturazione → nuova esperienza
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ------------------------------------------------------------------ #
# Data types
# ------------------------------------------------------------------ #


@dataclass
class CausalObservation:
    """Singola osservazione dello stato dell'organismo a un dato tick."""

    tick: int
    energy: float
    coherence: float
    active_neurons: int
    action_tendency: str
    dominant_drive: Optional[str]
    reflexes: List[str]
    injected_thought: bool
    modularity: Optional[float] = None
    small_world_sigma: Optional[float] = None
    global_efficiency: Optional[float] = None
    connectome_density: Optional[float] = None
    resilience: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tick": self.tick,
            "energy": round(self.energy, 4),
            "coherence": round(self.coherence, 4),
            "active_neurons": self.active_neurons,
            "action_tendency": self.action_tendency,
            "dominant_drive": self.dominant_drive,
            "reflexes": self.reflexes,
            "injected_thought": self.injected_thought,
            "modularity": round(self.modularity, 4) if self.modularity is not None else None,
            "small_world_sigma": round(self.small_world_sigma, 4) if self.small_world_sigma is not None else None,
            "global_efficiency": round(self.global_efficiency, 4) if self.global_efficiency is not None else None,
            "connectome_density": round(self.connectome_density, 4) if self.connectome_density is not None else None,
            "resilience": round(self.resilience, 4) if self.resilience is not None else None,
        }


@dataclass
class CausalInsight:
    """Pattern rilevato dalla memoria causale con azione epigenetica suggerita."""

    pattern_name: str
    confidence: float  # 0.0–1.0
    suggested_actions: List[str]  # e.g. ["methylate:plasticity", "acetylate:repair"]
    evidence: List[int]  # tick dei fatti che supportano il pattern
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern": self.pattern_name,
            "confidence": round(self.confidence, 3),
            "suggested_actions": self.suggested_actions,
            "evidence_count": len(self.evidence),
            "description": self.description,
        }


# ------------------------------------------------------------------ #
# Pattern detectors
# ------------------------------------------------------------------ #


class PatternDetector:
    """Base class per i detector di pattern."""
    def __init__(self, name: str, min_observations: int = 3):
        self.name = name
        self.min_observations = min_observations

    def detect(self, window: List[CausalObservation]) -> Optional[CausalInsight]:
        raise NotImplementedError


class RepeatedEnergyCollapseDetector(PatternDetector):
    """Rileva: energia sotto soglia per N tick consecutivi."""

    def __init__(self, threshold: float = 0.35, consecutive: int = 5):
        super().__init__("repeated_energy_collapse", min_observations=consecutive)
        self.threshold = threshold
        self.consecutive = consecutive

    def detect(self, window: List[CausalObservation]) -> Optional[CausalInsight]:
        if len(window) < self.consecutive:
            return None
        recent = window[-self.consecutive:]
        if all(o.energy < self.threshold for o in recent):
            return CausalInsight(
                pattern_name=self.name,
                confidence=min(1.0, 0.5 + 0.1 * sum(1 for o in recent if o.reflexes)),
                suggested_actions=[
                    "methylate:plasticity",  # sopprimi plasticità inutile
                    "acetylate:energy_conservation",  # potenzia risparmio energetico
                ],
                evidence=[o.tick for o in recent],
                description=f"Energia sotto {self.threshold} per {self.consecutive} tick consecutivi.",
            )
        return None


class ReflexInefficacyDetector(PatternDetector):
    """Rileva: riflessi spesso attivati ma senza miglioramento di coerenza."""

    def __init__(self, window_size: int = 10, efficacy_threshold: float = 0.3):
        super().__init__("reflex_inefficacy", min_observations=window_size)
        self.window_size = window_size
        self.efficacy_threshold = efficacy_threshold

    def detect(self, window: List[CausalObservation]) -> Optional[CausalInsight]:
        if len(window) < self.window_size:
            return None
        recent = window[-self.window_size:]
        reflex_count = sum(1 for o in recent if o.reflexes)
        if reflex_count < 3:
            return None
        # Coherence delta medio dopo un riflesso
        deltas = []
        for i in range(1, len(recent)):
            if recent[i - 1].reflexes:
                deltas.append(recent[i].coherence - recent[i - 1].coherence)
        if not deltas:
            return None
        avg_delta = sum(deltas) / len(deltas)
        if avg_delta < self.efficacy_threshold:
            return CausalInsight(
                pattern_name=self.name,
                confidence=min(1.0, 0.4 + 0.1 * reflex_count),
                suggested_actions=[
                    "methylate:energy_expression",
                    "acetylate:repair_expression",
                ],
                evidence=[o.tick for o in recent if o.reflexes][-5:],
                description=f"Riflessi frequenti ({reflex_count}/{self.window_size}) ma coerenza non migliora (delta={avg_delta:.3f}).",
            )
        return None


class DriveStagnationDetector(PatternDetector):
    """Rileva: stesso drive dominante per molti tick (stagnazione comportamentale)."""

    def __init__(self, max_same_drive: int = 15):
        super().__init__("drive_stagnation", min_observations=max_same_drive)
        self.max_same_drive = max_same_drive

    def detect(self, window: List[CausalObservation]) -> Optional[CausalInsight]:
        if len(window) < self.max_same_drive:
            return None
        recent = window[-self.max_same_drive:]
        drives = [o.dominant_drive for o in recent if o.dominant_drive is not None]
        if len(drives) < self.max_same_drive:
            return None
        if all(d == drives[0] for d in drives):
            return CausalInsight(
                pattern_name=self.name,
                confidence=0.6,
                suggested_actions=[
                    "acetylate:plasticity",  # aumenta plasticità per sbloccare
                    "methylate:routing_habit",  # riduci abitudine di routing
                ],
                evidence=[o.tick for o in recent],
                description=f"Drive '{drives[0]}' dominante per {self.max_same_drive}+ tick.",
            )
        return None


class SuccessfulRecoveryDetector(PatternDetector):
    """Rileva: dopo un riflesso la coerenza migliora significativamente (pattern positivo)."""

    def __init__(self, window_size: int = 20, improvement_threshold: float = 0.15):
        super().__init__("successful_recovery", min_observations=window_size)
        self.window_size = window_size
        self.improvement_threshold = improvement_threshold

    def detect(self, window: List[CausalObservation]) -> Optional[CausalInsight]:
        if len(window) < self.window_size:
            return None
        recent = window[-self.window_size:]
        successes = 0
        evidence_ticks = []
        for i in range(1, len(recent)):
            if recent[i - 1].reflexes and recent[i].coherence - recent[i - 1].coherence > self.improvement_threshold:
                successes += 1
                evidence_ticks.append(recent[i].tick)
        if successes >= 3:
            return CausalInsight(
                pattern_name=self.name,
                confidence=min(1.0, 0.3 + 0.15 * successes),
                suggested_actions=[
                    "acetylate:repair_expression",  # consolida riparazione
                    "acetylate:energy_expression",  # potenzia metabolismo
                ],
                evidence=evidence_ticks,
                description=f"{successes} recuperi riusciti dopo riflessi (delta>{self.improvement_threshold}).",
            )
        return None


class TopologyChangeDetector(PatternDetector):
    """Rileva cambiamenti significativi nelle metriche topologiche globali.

    Basato su Livello 3 del modello Genoma-Connettoma:
    la morfologia del connettoma (modularita', small-worldness, efficienza)
    viene trattata come segnale epigenetico collettivo.

    Pattern rilevati:
    - Alta modularita' → aumenta specializzazione (silenzia plasticita' superflua)
    - Alta small-worldness → aumenta integrazione globale (attiva plasticita')
    - Alta efficienza → riduce pressione mutazionale (silenzia riparazione)
    - Bassa resilienza → aumenta plasticita' strutturale
    """

    def __init__(self, window_size: int = 10):
        super().__init__("topology_change", min_observations=window_size)
        self.window_size = window_size

    def detect(self, window: List[CausalObservation]) -> Optional[CausalInsight]:
        if len(window) < self.window_size:
            return None

        recent = window[-self.window_size:]

        # Estrai metriche topologiche (solo osservazioni che le hanno)
        topo_obs = [o for o in recent if o.modularity is not None]
        if len(topo_obs) < 3:
            return None

        avg_modularity = sum(o.modularity for o in topo_obs) / len(topo_obs)
        avg_small_world = sum(o.small_world_sigma for o in topo_obs if o.small_world_sigma is not None) / max(len([o for o in topo_obs if o.small_world_sigma is not None]), 1)
        avg_efficiency = sum(o.global_efficiency for o in topo_obs if o.global_efficiency is not None) / max(len([o for o in topo_obs if o.global_efficiency is not None]), 1)

        # Pattern 1: Modularita' molto alta → iper-specializzazione
        if avg_modularity > 0.7:
            return CausalInsight(
                pattern_name="high_modularity_specialization",
                confidence=min(1.0, 0.5 + avg_modularity * 0.3),
                suggested_actions=[
                    "methylate:plasticity",
                    "acetylate:routing_habit",
                ],
                evidence=[o.tick for o in topo_obs[-3:]],
                description=f"Modularita' alta ({avg_modularity:.3f}): favorire specializzazione, ridurre plasticita' superflua.",
            )

        # Pattern 2: Small-worldness alta → buona integrazione
        if avg_small_world > 1.5:
            return CausalInsight(
                pattern_name="high_small_world_integration",
                confidence=min(1.0, 0.4 + avg_small_world * 0.2),
                suggested_actions=[
                    "acetylate:plasticity",
                    "acetylate:energy_expression",
                ],
                evidence=[o.tick for o in topo_obs[-3:]],
                description=f"Small-worldness alta ({avg_small_world:.3f}): buona integrazione globale, mantenere plasticita'.",
            )

        # Pattern 3: Efficienza molto bassa → necessaria ristrutturazione
        if avg_efficiency < 0.3 and avg_efficiency > 0.0:
            return CausalInsight(
                pattern_name="low_efficiency_restructuring",
                confidence=min(1.0, 0.6 + (0.3 - avg_efficiency) * 0.5),
                suggested_actions=[
                    "acetylate:plasticity",
                    "acetylate:repair_expression",
                ],
                evidence=[o.tick for o in topo_obs[-3:]],
                description=f"Efficienza globale bassa ({avg_efficiency:.3f}): attivare ristrutturazione e plasticita'.",
            )

        # Pattern 4: Modularita' + efficienza in calo → declino strutturale
        if len(topo_obs) >= 6:
            first_half = topo_obs[:len(topo_obs)//2]
            second_half = topo_obs[len(topo_obs)//2:]
            mod_trend = (sum(o.modularity for o in second_half) / len(second_half)) - (sum(o.modularity for o in first_half) / len(first_half))
            eff_trend = (sum(o.global_efficiency for o in second_half if o.global_efficiency is not None) / max(len([o for o in second_half if o.global_efficiency is not None]), 1)) - (sum(o.global_efficiency for o in first_half if o.global_efficiency is not None) / max(len([o for o in first_half if o.global_efficiency is not None]), 1))
            if mod_trend < -0.1 and eff_trend < -0.05:
                return CausalInsight(
                    pattern_name="structural_decline",
                    confidence=min(1.0, 0.5 + abs(mod_trend + eff_trend)),
                    suggested_actions=[
                        "acetylate:plasticity",
                        "acetylate:repair_expression",
                        "acetylate:energy_conservation",
                    ],
                    evidence=[o.tick for o in topo_obs[-3:]],
                    description=f"Declino strutturale: modularita' ({mod_trend:+.3f}), efficienza ({eff_trend:+.3f}).",
                )

        return None


# ------------------------------------------------------------------ #
# Causal Memory
# ------------------------------------------------------------------ #


class CausalMemory:
    """Memoria causale: traccia outcomes, rileva pattern, emette insights.

    Mantiene una finestra scorrevole di osservazioni e la analizza con
    una serie di detector per trovare pattern ripetuti significativi.
    Ogni pattern genera un CausalInsight che può attivare cambi epigenetici.
    """

    def __init__(
        self,
        max_window: int = 100,
        detectors: Optional[List[PatternDetector]] = None,
    ):
        self.max_window = max_window
        self._observations: List[CausalObservation] = []
        self._insights: List[CausalInsight] = []
        self._detectors = detectors or [
            RepeatedEnergyCollapseDetector(),
            ReflexInefficacyDetector(),
            DriveStagnationDetector(),
            SuccessfulRecoveryDetector(),
            TopologyChangeDetector(),
        ]

    # ------------------------------------------------------------------ #
    # Record
    # ------------------------------------------------------------------ #

    def record(self, pulse_data: Dict[str, Any]) -> None:
        """Registra un'osservazione dall'ANS pulse."""
        obs = CausalObservation(
            tick=pulse_data.get("tick", 0),
            energy=pulse_data.get("energy", 0.0),
            coherence=pulse_data.get("coherence", 0.0),
            active_neurons=pulse_data.get("active_neurons", 0),
            action_tendency=pulse_data.get("action_tendency", ""),
            dominant_drive=pulse_data.get("dominant_drive"),
            reflexes=pulse_data.get("reflexes", []),
            injected_thought=pulse_data.get("injected_thought", False),
            modularity=pulse_data.get("modularity"),
            small_world_sigma=pulse_data.get("small_world_sigma"),
            global_efficiency=pulse_data.get("global_efficiency"),
            connectome_density=pulse_data.get("connectome_density"),
            resilience=pulse_data.get("resilience"),
        )
        self._observations.append(obs)
        if len(self._observations) > self.max_window:
            self._observations = self._observations[-self.max_window:]

    def record_observation(self, obs: CausalObservation) -> None:
        """Registra un'osservazione diretta."""
        self._observations.append(obs)
        if len(self._observations) > self.max_window:
            self._observations = self._observations[-self.max_window:]

    # ------------------------------------------------------------------ #
    # Analysis
    # ------------------------------------------------------------------ #

    def analyze(self) -> List[CausalInsight]:
        """Analizza la finestra corrente e restituisce nuovi insights."""
        if len(self._observations) < 5:
            return []
        new_insights: List[CausalInsight] = []
        for detector in self._detectors:
            try:
                insight = detector.detect(self._observations)
                if insight is not None:
                    # Evita duplicati (stesso pattern e evidence sovrapposta)
                    if not self._has_recent_similar(insight):
                        self._insights.append(insight)
                        new_insights.append(insight)
            except Exception:
                pass
        # Mantieni solo gli ultimi 50 insights
        if len(self._insights) > 50:
            self._insights = self._insights[-50:]
        return new_insights

    def _has_recent_similar(self, insight: CausalInsight, window: int = 20) -> bool:
        """Controlla se un insight simile è già stato emesso di recente."""
        for existing in self._insights[-window:]:
            if existing.pattern_name == insight.pattern_name:
                # Se la confidence è simile, è un duplicato
                if abs(existing.confidence - insight.confidence) < 0.2:
                    return True
        return False

    # ------------------------------------------------------------------ #
    # Query
    # ------------------------------------------------------------------ #

    def get_insights(self, limit: int = 10) -> List[CausalInsight]:
        return self._insights[-limit:]

    def get_recent_patterns(self, n: int = 3) -> Dict[str, int]:
        """Conta quanti insights per pattern negli ultimi N."""
        counts: Dict[str, int] = defaultdict(int)
        for insight in self._insights[-n:]:
            counts[insight.pattern_name] += 1
        return dict(counts)

    def get_observation_count(self) -> int:
        return len(self._observations)

    def get_window_size(self) -> int:
        return len(self._observations)

    def summary(self) -> Dict[str, Any]:
        return {
            "observations": len(self._observations),
            "insights_total": len(self._insights),
            "recent_insights": [i.to_dict() for i in self._insights[-5:]],
            "pattern_counts": self.get_recent_patterns(),
        }

    def clear(self) -> None:
        self._observations.clear()
        self._insights.clear()
