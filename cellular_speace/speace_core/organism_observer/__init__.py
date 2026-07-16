"""Organism Observer — misura la geometria funzionale dell'organismo.

Cattura il flusso di messaggi tra sottosistemi (OFG) e calcola
metriche topologiche per descrivere la struttura emergente.
"""

from speace_core.organism_observer.event_collector import EventCollector
from speace_core.organism_observer.functional_graph import FunctionalGraph
from speace_core.organism_observer.topology_metrics import TopologyMetrics
from speace_core.organism_observer.topology_history import TopologyHistory, TopologySnapshot
from speace_core.organism_observer.topology_diff import TopologyDiff, StructureDelta
from speace_core.organism_observer.topology_events import TopologyEvents, CorrelatedEvent, CorrelationReport
from speace_core.organism_observer.topology_memory import MorphologicalMemory, SavedMorphology
from speace_core.organism_observer.topology_correlator import (
    TopologyPerformanceCorrelator,
    CorrelatedPair,
    CorrelatorReport,
)

__all__ = [
    "EventCollector",
    "FunctionalGraph",
    "TopologyMetrics",
    "TopologyHistory",
    "TopologySnapshot",
    "TopologyDiff",
    "StructureDelta",
    "TopologyEvents",
    "CorrelatedEvent",
    "CorrelationReport",
    "MorphologicalMemory",
    "SavedMorphology",
    "TopologyPerformanceCorrelator",
    "CorrelatedPair",
    "CorrelatorReport",
]
