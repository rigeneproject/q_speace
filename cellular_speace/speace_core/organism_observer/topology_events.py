"""TopologyEvents — correlazione tra delta topologici e cambiamenti di stato.

Mette in relazione le variazioni della geometria funzionale (OFG) con:
  - Variazioni di ILF (coerenza del campo informazionale)
  - Performance metrics (throughput, latenza, error rate)
  - Eventi esterni (benchmark, evoluzione, riposo)

L'obiettivo e' trasformare la geometria da descrizione a variabile causale:
    TopologyDelta + ILFDelta + PerformanceDelta → insight sulla neuroplasticita'
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from speace_core.organism_observer.topology_history import TopologyHistory, TopologySnapshot
from speace_core.organism_observer.topology_diff import StructureDelta, TopologyDiff


@dataclass
class CorrelatedEvent:
    timestamp: float = 0.0
    tick: int = 0

    # Topology delta
    change_velocity: float = 0.0
    entropy_change: float = 0.0
    d_modularity_q: float = 0.0
    d_global_efficiency: float = 0.0
    d_small_world_sigma: float = 0.0
    d_avg_clustering: float = 0.0

    # ILF delta
    ilf_before: float = 0.0
    ilf_after: float = 0.0
    d_ilf: float = 0.0

    # Performance delta (opzionale)
    d_throughput: float = 0.0
    d_latency: float = 0.0
    d_error_rate: float = 0.0

    # Label dell'evento esterno (opzionale)
    context_label: str = ""

    # Correlazione grezza
    coherence_change_ratio: float = 0.0  # d_ilf / change_velocity
    topology_ilf_correlation: float = 0.0  # segno: +1 = same direction, -1 = opposite


@dataclass
class CorrelationReport:
    n_events: int = 0
    top_changes: List[CorrelatedEvent] = field(default_factory=list)
    mean_change_velocity: float = 0.0
    mean_entropy_change: float = 0.0
    mean_d_ilf: float = 0.0
    mean_coherence_change_ratio: float = 0.0
    n_positive_correlation: int = 0  # topologia e ILF si muovono insieme
    n_negative_correlation: int = 0  # topologia e ILF si muovono in direzioni opposte


class TopologyEvents:
    """Correla delta topologici con cambiamenti di ILF e performance.

    Usage::

        history = TopologyHistory(graph)
        events = TopologyEvents(history)

        # Dopo aver campionato alcuni snapshot...
        event = events.record_event(
            ilf_provider=lambda: orchestrator.get_field_state().ilf_value,
            context_label="benchmark_arc",
        )
        print(event.d_ilf, event.change_velocity)

        # Report cumulativo
        report = events.report()
        print(f"Correlazioni positive: {report.n_positive_correlation}")
    """

    def __init__(self, history: TopologyHistory) -> None:
        self.history = history
        self._events: List[CorrelatedEvent] = []

    # ------------------------------------------------------------------ #
    # Recording
    # ------------------------------------------------------------------ #

    def record_event(
        self,
        ilf_provider: Optional[Callable[[], float]] = None,
        ilf_before: Optional[float] = None,
        ilf_after: Optional[float] = None,
        performance_provider: Optional[Callable[[], Dict[str, float]]] = None,
        perf_before: Optional[Dict[str, float]] = None,
        perf_after: Optional[Dict[str, float]] = None,
        context_label: str = "",
    ) -> Optional[CorrelatedEvent]:
        """Registra un evento correlato basandosi sugli ultimi due snapshot.

        Args:
            ilf_provider: Callable che restituisce il valore ILF corrente.
            ilf_before: Valore ILF prima dell'evento (se gia' noto).
            ilf_after: Valore ILF dopo l'evento (se gia' noto).
            performance_provider: Callable che restituisce performance metrics.
            perf_before: Performance prima (se gia' note).
            perf_after: Performance dopo (se gia' note).
            context_label: Label opzionale (es. "benchmark_arc", "evolution").
        """
        snaps = self.history.snapshots()
        if len(snaps) < 2:
            return None

        older = snaps[-2]
        newer = snaps[-1]

        delta = TopologyDiff.compute(older, newer)

        # ILF
        if ilf_provider is not None:
            ilf_after = ilf_provider()
        if ilf_before is None:
            ilf_before = older.raw.get("degree_centrality", {}).get("_ilf_value", 0.5)
        if ilf_after is None:
            ilf_after = 0.5

        d_ilf = ilf_after - ilf_before

        # Performance
        d_throughput = 0.0
        d_latency = 0.0
        d_error_rate = 0.0
        if perf_before and perf_after:
            d_throughput = perf_after.get("throughput", 0.0) - perf_before.get("throughput", 0.0)
            d_latency = perf_after.get("latency", 0.0) - perf_before.get("latency", 0.0)
            d_error_rate = perf_after.get("error_rate", 0.0) - perf_before.get("error_rate", 0.0)

        # Indice di correlazione
        coherence_change_ratio = 0.0
        if abs(delta.change_velocity) > 1e-12:
            coherence_change_ratio = d_ilf / delta.change_velocity

        topology_ilf_correlation = 0.0
        if delta.change_velocity != 0.0 and d_ilf != 0.0:
            # Segno del prodotto: +1 se si muovono nella stessa direzione
            topology_ilf_correlation = 1.0 if (delta.change_velocity > 0) == (d_ilf > 0) else -1.0

        event = CorrelatedEvent(
            timestamp=newer.timestamp,
            tick=newer.tick,
            change_velocity=delta.change_velocity,
            entropy_change=delta.entropy_change,
            d_modularity_q=delta.d_modularity_q,
            d_global_efficiency=delta.d_global_efficiency,
            d_small_world_sigma=delta.d_small_world_sigma,
            d_avg_clustering=delta.d_avg_clustering,
            ilf_before=ilf_before,
            ilf_after=ilf_after,
            d_ilf=d_ilf,
            d_throughput=d_throughput,
            d_latency=d_latency,
            d_error_rate=d_error_rate,
            context_label=context_label,
            coherence_change_ratio=coherence_change_ratio,
            topology_ilf_correlation=topology_ilf_correlation,
        )

        self._events.append(event)
        return event

    def record_series(
        self,
        ilf_history: List[float],
        context_labels: Optional[List[str]] = None,
    ) -> int:
        """Crea eventi correlati per ogni coppia di snapshot consecutivi.

        Args:
            ilf_history: Lista di valori ILF in ordine temporale.
            context_labels: Label opzionali per ogni intervallo.

        Returns:
            Numero di eventi registrati.
        """
        snaps = self.history.snapshots()
        if len(snaps) < 2:
            return 0

        count = 0
        for i in range(1, len(snaps)):
            ilf_before = ilf_history[i - 1] if i - 1 < len(ilf_history) else 0.5
            ilf_after = ilf_history[i] if i < len(ilf_history) else 0.5
            label = context_labels[i - 1] if context_labels and i - 1 < len(context_labels) else ""

            # Simula snapshot aggiuntivo inserendo ILF nei raw
            newer = snaps[i]
            older = snaps[i - 1]
            older.raw.setdefault("degree_centrality", {})
            newer.raw.setdefault("degree_centrality", {})

            delta = TopologyDiff.compute(older, newer)

            d_ilf = ilf_after - ilf_before

            coherence_change_ratio = 0.0
            if abs(delta.change_velocity) > 1e-12:
                coherence_change_ratio = d_ilf / delta.change_velocity

            topology_ilf_correlation = 0.0
            if delta.change_velocity != 0.0 and d_ilf != 0.0:
                topology_ilf_correlation = 1.0 if (delta.change_velocity > 0) == (d_ilf > 0) else -1.0

            event = CorrelatedEvent(
                timestamp=newer.timestamp,
                tick=newer.tick,
                change_velocity=delta.change_velocity,
                entropy_change=delta.entropy_change,
                d_modularity_q=delta.d_modularity_q,
                d_global_efficiency=delta.d_global_efficiency,
                d_small_world_sigma=delta.d_small_world_sigma,
                d_avg_clustering=delta.d_avg_clustering,
                ilf_before=ilf_before,
                ilf_after=ilf_after,
                d_ilf=d_ilf,
                context_label=label,
                coherence_change_ratio=coherence_change_ratio,
                topology_ilf_correlation=topology_ilf_correlation,
            )

            self._events.append(event)
            count += 1

        return count

    # ------------------------------------------------------------------ #
    # Queries & Report
    # ------------------------------------------------------------------ #

    @property
    def events(self) -> List[CorrelatedEvent]:
        return list(self._events)

    def recent(self, n: int = 10) -> List[CorrelatedEvent]:
        return self._events[-n:]

    def report(self) -> CorrelationReport:
        if not self._events:
            return CorrelationReport()

        n = len(self._events)
        mean_vel = sum(e.change_velocity for e in self._events) / n
        mean_entropy = sum(e.entropy_change for e in self._events) / n
        mean_d_ilf = sum(e.d_ilf for e in self._events) / n
        mean_ratio = sum(
            e.coherence_change_ratio for e in self._events if math.isfinite(e.coherence_change_ratio)
        ) / max(sum(1 for e in self._events if math.isfinite(e.coherence_change_ratio)), 1)

        n_pos = sum(1 for e in self._events if e.topology_ilf_correlation > 0)
        n_neg = sum(1 for e in self._events if e.topology_ilf_correlation < 0)

        # Top 5 cambiamenti piu' violenti
        sorted_events = sorted(self._events, key=lambda e: abs(e.change_velocity), reverse=True)

        return CorrelationReport(
            n_events=n,
            top_changes=sorted_events[:5],
            mean_change_velocity=mean_vel,
            mean_entropy_change=mean_entropy,
            mean_d_ilf=mean_d_ilf,
            mean_coherence_change_ratio=mean_ratio,
            n_positive_correlation=n_pos,
            n_negative_correlation=n_neg,
        )

    def find_by_context(self, context_label: str) -> List[CorrelatedEvent]:
        """Trova eventi associati a un dato contesto (es. 'evolution')."""
        return [e for e in self._events if e.context_label == context_label]
