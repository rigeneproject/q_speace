from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum, auto


# ── Enums ───────────────────────────────────────────────────────

class BusType(Enum):
    NEURAL = "neural"
    ENDOCRINE = "endocrine"
    BOTH = "both"

class SignalType(Enum):
    STREAM = "stream"
    EVENT = "event"

class Polarity(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"

class EffectType(Enum):
    EXCITATION = "excitation"
    INHIBITION = "inhibition"
    MODULATION = "modulation"

class QoSSyncMode(Enum):
    SYNC = "sync"
    ASYNC = "async"
    DEFERRED = "deferred"

class TissueStatus(Enum):
    ACTIVE = "active"
    LOW_POWER = "low_power"
    PAUSED = "paused"
    CRISIS = "crisis"

class EventCategory(Enum):
    ALARM = "alarm"
    REWARD = "reward"
    NOVELTY = "novelty"
    DAMAGE = "damage"
    LEARNING = "learning"
    MUTATION = "mutation"
    CUSTOM = "custom"


# ── Core data types ─────────────────────────────────────────────

SynapseKey = Tuple[str, str, str, str]  # (molecule, source, target, receptor)


@dataclass
class SynapseCleft:
    molecule: str
    value: float
    source: str
    target: str
    receptor: str
    confidence: float = 0.9
    timestamp: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    masked: bool = False
    mask_until_tick: int = 0


@dataclass
class HormonePool:
    molecule: str
    concentration: float = 0.0
    baseline: float = 0.0
    clearance_rate: float = 0.92
    delay_ticks: int = 2
    max_concentration: float = 1.0
    last_secretion_tick: int = 0
    last_secretion_source: str = ""
    stream: bool = True
    event_mode: bool = False
    event_duration: int = 0
    event_decay: float = 0.80
    event_onset_tick: int = 0
    event_intensity: float = 0.0


@dataclass
class StreamSignal:
    id: str
    molecule: str
    value: float
    baseline: float = 0.5
    variance: float = 0.1
    confidence: float = 0.9
    decay_to_baseline: float = 0.03
    upper_alarm: Optional[float] = None
    lower_alarm: Optional[float] = None
    timestamp: int = 0


@dataclass
class EventSignal:
    id: str
    molecule: str
    intensity: float
    onset: int
    duration: int = 0
    decay: float = 0.80
    category: str = "custom"
    confidence: float = 0.9
    active: bool = True
    current_intensity: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def tick(self, current_tick: int) -> None:
        if not self.active:
            return
        elapsed = current_tick - self.onset
        if elapsed <= self.duration:
            self.current_intensity = self.intensity
        else:
            self.current_intensity *= self.decay
            if self.current_intensity < 0.01:
                self.active = False


@dataclass
class SignalOntologyEntry:
    id: str
    molecule: List[str]
    bus: str
    type: str
    range: List[float]
    unit: str = "fraction"
    decay: float = 0.95
    baseline: float = 0.5
    polarity: str = "neutral"
    vital: bool = False
    event_duration: int = 0
    upper_alarm: Optional[float] = None
    lower_alarm: Optional[float] = None
    description: str = ""


@dataclass
class ReceptorProfile:
    affinity: float = 0.5
    effect: str = "modulation"
    desensitization_rate: float = 0.001
    metabolic_cost: float = 0.005


@dataclass
class TissueMetabolicBudget:
    base_budget: float = 0.05
    current_usage: float = 0.0
    low_power_threshold: float = 0.7
    critical_threshold: float = 0.3
    publish_cost: float = 0.02
    sense_cost: float = 0.03
    subscribe_cost: float = 0.01

    @property
    def in_low_power(self) -> bool:
        return self.current_usage / self.base_budget > self.low_power_threshold

    @property
    def in_critical(self) -> bool:
        return self.current_usage / self.base_budget > self.critical_threshold

    @property
    def remaining(self) -> float:
        return max(0.0, self.base_budget - self.current_usage)


@dataclass
class TissueState:
    tissue_id: str
    organ_id: str
    local_signals: Dict[str, float] = field(default_factory=dict)
    receptor_occupancy: Dict[str, float] = field(default_factory=dict)
    internal_energy: float = 0.0
    status: TissueStatus = TissueStatus.ACTIVE
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OrganState:
    organ_id: str
    system_id: str
    tissues: Dict[str, TissueState] = field(default_factory=dict)


@dataclass
class SystemSnapshot:
    tick: int
    neural_synapses: Dict[SynapseKey, float] = field(default_factory=dict)
    endocrine_pools: Dict[str, float] = field(default_factory=dict)
    streams: Dict[str, float] = field(default_factory=dict)
    events: Dict[str, List[EventSignal]] = field(default_factory=dict)
    meta_signals: Dict[str, float] = field(default_factory=dict)
    estimates: Dict[str, float] = field(default_factory=dict)
    global_energy: float = 0.0
    temperature: float = 0.0
    metabolic_demand: float = 0.0
