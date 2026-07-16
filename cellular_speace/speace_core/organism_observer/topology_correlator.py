"""TopologyPerformanceCorrelator — correlazione delta topologici ↔ performance reali.

Collega la geometria funzionale (OFG) ai risultati osservabili:
  - Salute del runtime (health_score, tick_latency, memoria)
  - Performance cognitive (ARI, arc_accuracy)
  - ILF e derivate

Mantiene una matrice di correlazione (Pearson) aggiornata incrementalmente
per ogni coppia metrica-topologica × metrica-prestazionale, supporta
analisi a finestra mobile, lag detection, e produce insight classificati.
"""

from __future__ import annotations

import json
import math
import pathlib
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple

from speace_core.organism_observer.topology_diff import StructureDelta


# ------------------------------------------------------------------ #
# Metric lists — cosa osserviamo
# ------------------------------------------------------------------ #

TOPOLOGY_METRICS: Tuple[str, ...] = (
    "d_modularity_q",
    "d_global_efficiency",
    "d_avg_clustering",
    "d_small_world_sigma",
    "d_density",
    "d_node_count",
    "d_edge_count",
    "d_n_communities",
    "change_velocity",
    "entropy_change",
)

PERFORMANCE_METRICS: Tuple[str, ...] = (
    "health_score",
    "tick_latency_ms",
    "memory_rss_mb",
    "ari_score",
    "arc_accuracy",
    "d_ilf",
    "d_throughput",
    "d_error_rate",
)


# ------------------------------------------------------------------ #
# Data structures
# ------------------------------------------------------------------ #


@dataclass
class CorrelatedPair:
    """Correlazione tra una metrica topologica e una metrica di performance."""

    topology_metric: str = ""
    performance_metric: str = ""
    pearson_r: float = 0.0
    sample_size: int = 0
    p_value_approx: float = 1.0  # approssimazione: 2-sided t-test
    is_significant: bool = False
    slope: float = 0.0  # regressione lineare semplice (pendenza)
    intercept: float = 0.0


@dataclass
class CorrelatorReport:
    """Report cumulativo delle correlazioni osservate."""

    n_samples: int = 0
    n_topology_metrics: int = 0
    n_performance_metrics: int = 0
    pairs: List[CorrelatedPair] = field(default_factory=list)
    strongest_correlations: List[CorrelatedPair] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)
    timestamp: float = 0.0


# ------------------------------------------------------------------ #
# Core correlator
# ------------------------------------------------------------------ #


class TopologyPerformanceCorrelator:
    """Correla metriche topologiche con metriche di performance reali.

    Usage::

        correlator = TopologyPerformanceCorrelator()
        correlator.record(structure_delta, {"health_score": 0.85, "ari_score": 0.62})
        correlator.record(structure_delta2, {"health_score": 0.82, "ari_score": 0.65})

        matrix = correlator.correlation_matrix()
        print(matrix["d_modularity_q"]["health_score"]["pearson_r"])

        insight = correlator.report()
        for line in insight.insights:
            print(line)

        correlator.save("data/organism_observer/correlations.jsonl")
    """

    def __init__(
        self,
        persist_path: str = "data/organism_observer/correlations.jsonl",
        window_size: int = 0,
    ) -> None:
        """Inizializza il correlatore.

        Args:
            persist_path: Path per salvataggio JSONL.
            window_size: Se > 0, usa una finestra mobile degli ultimi
                         N campioni invece dell'intera storia.
        """
        self.persist_path = pathlib.Path(persist_path)
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        self.window_size = window_size

        # Storia completa — lista di (StructureDelta, performance_dict)
        self._samples: List[Tuple[Dict[str, float], Dict[str, float]]] = []

        # Accumulatori per correlazione incrementale (Pearson online)
        # Per ogni coppia (topo, perf): (n, sum_x, sum_y, sum_xx, sum_yy, sum_xy)
        self._accumulators: Dict[str, Dict[str, List[float]]] = {}

    # ------------------------------------------------------------------ #
    # Recording
    # ------------------------------------------------------------------ #

    def record(
        self,
        structure_delta: StructureDelta,
        performance: Dict[str, float],
    ) -> None:
        """Registra un punto dati: delta topologico + metriche di performance.

        Estrae automaticamente le metriche topologiche da StructureDelta.
        Accetta qualsiasi chiave numerica in `performance`.
        """
        topo = self._extract_topo(structure_delta)

        self._samples.append((topo, dict(performance)))

        # Applica finestra mobile
        if self.window_size > 0 and len(self._samples) > self.window_size:
            old = self._samples.pop(0)
            self._remove_from_accumulators(*old)

        self._add_to_accumulators(topo, performance)

    def record_from_events(
        self,
        d_modularity_q: float = 0.0,
        d_global_efficiency: float = 0.0,
        d_avg_clustering: float = 0.0,
        d_small_world_sigma: float = 0.0,
        d_density: float = 0.0,
        d_node_count: float = 0.0,
        d_edge_count: float = 0.0,
        d_n_communities: float = 0.0,
        change_velocity: float = 0.0,
        entropy_change: float = 0.0,
        **performance: float,
    ) -> None:
        """Record diretto da keyword args (utile se non si ha StructureDelta)."""
        topo = {
            "d_modularity_q": d_modularity_q,
            "d_global_efficiency": d_global_efficiency,
            "d_avg_clustering": d_avg_clustering,
            "d_small_world_sigma": d_small_world_sigma,
            "d_density": d_density,
            "d_node_count": d_node_count,
            "d_edge_count": d_edge_count,
            "d_n_communities": d_n_communities,
            "change_velocity": change_velocity,
            "entropy_change": entropy_change,
        }
        self._samples.append((topo, dict(performance)))

        if self.window_size > 0 and len(self._samples) > self.window_size:
            old = self._samples.pop(0)
            self._remove_from_accumulators(*old)

        self._add_to_accumulators(topo, performance)

    # ------------------------------------------------------------------ #
    # Correlation matrix
    # ------------------------------------------------------------------ #

    @staticmethod
    def _has_variance(acc: List[float]) -> bool:
        n, sx, sy, sxx, syy, sxy = acc
        if n < 3:
            return False
        var_x = n * sxx - sx * sx
        var_y = n * syy - sy * sy
        return var_x > 1e-15 and var_y > 1e-15

    def correlation_matrix(
        self, min_samples: int = 3
    ) -> Dict[str, Dict[str, Dict[str, float]]]:
        """Calcola la matrice di correlazione di Pearson.

        Returns:
            {topology_metric: {performance_metric: {"pearson_r": ..., "slope": ...}}}
            Solo metriche con varianza (almeno 2 valori distinti) sono incluse.
        """
        matrix: Dict[str, Dict[str, Dict[str, float]]] = {}
        perf_metrics = self._observed_performance_metrics()
        if not perf_metrics:
            return matrix

        for t_metric in TOPOLOGY_METRICS:
            t_row: Dict[str, Dict[str, float]] = {}
            for p_metric in perf_metrics:
                acc = self._accumulators.get(t_metric, {}).get(p_metric)
                if acc is None or acc[0] < min_samples:
                    continue
                if not self._has_variance(acc):
                    continue
                r, slope, intercept = self._pearson_from_acc(acc)
                t_row[p_metric] = {
                    "pearson_r": round(r, 6),
                    "slope": round(slope, 6),
                    "intercept": round(intercept, 6),
                    "n": int(acc[0]),
                }
            if t_row:
                matrix[t_metric] = t_row

        return matrix

    def sliding_correlation(
        self, window: int, min_samples: int = 3
    ) -> Dict[str, Dict[str, Dict[str, float]]]:
        """Matrice di correlazione sugli ultimi N campioni.

        Args:
            window: Numero di campioni recenti da considerare.
            min_samples: Minimo campioni per calcolare R.

        Returns:
            Stessa struttura di correlation_matrix() ma ricalcolata
            sulla finestra.
        """
        if not self._samples:
            return {}

        recent = self._samples[-window:]
        if len(recent) < min_samples:
            return {}

        # Ricalcola da zero sulla finestra
        acc: Dict[str, Dict[str, List[float]]] = {}
        for topo, perf in recent:
            for t_key, t_val in topo.items():
                if not math.isfinite(t_val):
                    continue
                for p_key, p_val in perf.items():
                    if not isinstance(p_val, (int, float)) or not math.isfinite(p_val):
                        continue
                    acc.setdefault(t_key, {}).setdefault(p_key, [0.0] * 6)
                    a = acc[t_key][p_key]
                    a[0] += 1.0
                    a[1] += t_val
                    a[2] += p_val
                    a[3] += t_val * t_val
                    a[4] += p_val * p_val
                    a[5] += t_val * p_val

        matrix: Dict[str, Dict[str, Dict[str, float]]] = {}
        for t_metric in TOPOLOGY_METRICS:
            if t_metric not in acc:
                continue
            matrix[t_metric] = {}
            for p_metric, a in acc[t_metric].items():
                if a[0] < min_samples:
                    continue
                r, slope, intercept = self._pearson_from_acc(a)
                matrix[t_metric][p_metric] = {
                    "pearson_r": round(r, 6),
                    "slope": round(slope, 6),
                    "intercept": round(intercept, 6),
                    "n": int(a[0]),
                }

        return matrix

    # ------------------------------------------------------------------ #
    # Correlated pairs & report
    # ------------------------------------------------------------------ #

    def correlated_pairs(
        self, min_samples: int = 5, min_abs_r: float = 0.0
    ) -> List[CorrelatedPair]:
        """Restituisce tutte le coppie (topo, perf) con correlazione calcolata.

        Args:
            min_samples: Minimo campioni per calcolare R.
            min_abs_r: Filtro per |R| minimo.
        """
        pairs: List[CorrelatedPair] = []
        matrix = self.correlation_matrix(min_samples=min_samples)

        for t_metric in TOPOLOGY_METRICS:
            if t_metric not in matrix:
                continue
            for p_metric, info in matrix[t_metric].items():
                r = info.get("pearson_r", 0.0)
                if abs(r) < min_abs_r:
                    continue
                n = info.get("n", 0)
                # p-value approssimato: t = r * sqrt((n-2) / (1-r^2))
                p_val = 1.0
                if abs(r) < 1.0 and n > 2:
                    t_stat = r * math.sqrt((n - 2) / (1 - r * r))
                    p_val = 2.0 * (1.0 - self._approx_normal_cdf(abs(t_stat)))

                pair = CorrelatedPair(
                    topology_metric=t_metric,
                    performance_metric=p_metric,
                    pearson_r=round(r, 6),
                    sample_size=n,
                    p_value_approx=round(p_val, 6),
                    is_significant=p_val < 0.05,
                    slope=round(info.get("slope", 0.0), 6),
                    intercept=round(info.get("intercept", 0.0), 6),
                )
                pairs.append(pair)

        pairs.sort(key=lambda p: abs(p.pearson_r), reverse=True)
        return pairs

    def top_predictors(
        self,
        performance_metric: str,
        n: int = 5,
        min_samples: int = 5,
    ) -> List[CorrelatedPair]:
        """Metriche topologiche che meglio predicono una performance.

        Args:
            performance_metric: Nome della metrica target.
            n: Numero di top predictor da restituire.
            min_samples: Minimo campioni.

        Returns:
            Lista ordinata per |R| decrescente.
        """
        all_pairs = self.correlated_pairs(min_samples=min_samples)
        filtered = [p for p in all_pairs if p.performance_metric == performance_metric]
        filtered.sort(key=lambda p: abs(p.pearson_r), reverse=True)
        return filtered[:n]

    def report(self, min_samples: int = 5) -> CorrelatorReport:
        """Genera un report con insight classificati."""
        pairs = self.correlated_pairs(min_samples=min_samples)
        significant = [p for p in pairs if p.is_significant]
        strongest = pairs[:10]

        insights: List[str] = []
        if significant:
            best = significant[0]
            insights.append(
                f"{best.topology_metric} → {best.performance_metric}: "
                f"R={best.pearson_r:.4f} (p≈{best.p_value_approx:.4f}, "
                f"n={best.sample_size})"
            )
        for p in significant[1:6]:
            insights.append(
                f"{p.topology_metric} → {p.performance_metric}: "
                f"R={p.pearson_r:.4f}"
            )

        if not insights and pairs:
            top = pairs[0]
            insights.append(
                f"Nessuna correlazione significativa. "
                f"Migliore: {top.topology_metric} → {top.performance_metric} "
                f"R={top.pearson_r:.4f} (n={top.sample_size})"
            )
        elif not pairs:
            insights.append("Campioni insufficienti per correlazioni.")

        # Metriche topologiche piu' predictive (media |R|)
        topo_importance: Dict[str, List[float]] = {}
        for p in pairs:
            topo_importance.setdefault(p.topology_metric, []).append(
                abs(p.pearson_r)
            )
        if topo_importance:
            avg_imp = {
                k: sum(v) / len(v) for k, v in topo_importance.items()
            }
            ranked = sorted(avg_imp.items(), key=lambda x: x[1], reverse=True)
            if ranked:
                insights.append(
                    f"Topo-piu' predittiva: {ranked[0][0]} "
                    f"(media |R|={ranked[0][1]:.4f})"
                )

        return CorrelatorReport(
            n_samples=len(self._samples),
            n_topology_metrics=len(TOPOLOGY_METRICS),
            n_performance_metrics=len(self._observed_performance_metrics()),
            pairs=pairs,
            strongest_correlations=strongest,
            insights=insights,
            timestamp=time.time(),
        )

    # ------------------------------------------------------------------ #
    # Properties & queries
    # ------------------------------------------------------------------ #

    @property
    def sample_count(self) -> int:
        return len(self._samples)

    @property
    def observed_topology_metrics(self) -> List[str]:
        seen: set = set()
        for t, _ in self._samples:
            seen.update(t.keys())
        return [m for m in TOPOLOGY_METRICS if m in seen]

    def _observed_performance_metrics(self) -> List[str]:
        seen: set = set()
        for _, p in self._samples:
            for k, v in p.items():
                if isinstance(v, (int, float)) and math.isfinite(v):
                    seen.add(k)
        return sorted(seen)

    def clear(self) -> None:
        self._samples.clear()
        self._accumulators.clear()

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #

    def save(self, path: Optional[str] = None) -> int:
        """Salva i campioni su JSONL."""
        dst = pathlib.Path(path) if path else self.persist_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not self._samples:
            return 0
        count = 0
        try:
            with dst.open("w", encoding="utf-8") as f:
                for topo, perf in self._samples:
                    line = {
                        "topology": topo,
                        "performance": perf,
                        "timestamp": time.time(),
                    }
                    f.write(json.dumps(line) + "\n")
                    count += 1
            return count
        except OSError:
            return 0

    def load(self, path: Optional[str] = None) -> int:
        """Carica campioni da JSONL."""
        src = pathlib.Path(path) if path else self.persist_path
        if not src.exists():
            return 0
        count = 0
        try:
            with src.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    topo = data.get("topology", {})
                    perf = data.get("performance", {})
                    if not topo or not perf:
                        continue
                    self._samples.append((topo, perf))
                    self._add_to_accumulators(topo, perf)
                    count += 1
            return count
        except OSError:
            return 0

    # ------------------------------------------------------------------ #
    # Private: estrazione dati
    # ------------------------------------------------------------------ #

    @staticmethod
    def _extract_topo(delta: StructureDelta) -> Dict[str, float]:
        return {
            "d_modularity_q": delta.d_modularity_q,
            "d_global_efficiency": delta.d_global_efficiency,
            "d_avg_clustering": delta.d_avg_clustering,
            "d_small_world_sigma": delta.d_small_world_sigma,
            "d_density": delta.d_density,
            "d_node_count": delta.d_node_count,
            "d_edge_count": delta.d_edge_count,
            "d_n_communities": delta.d_n_communities,
            "change_velocity": delta.change_velocity,
            "entropy_change": delta.entropy_change,
        }

    # ------------------------------------------------------------------ #
    # Private: accumulatori incrementali
    # ------------------------------------------------------------------ #

    def _add_to_accumulators(
        self,
        topo: Dict[str, float],
        perf: Dict[str, float],
    ) -> None:
        """Aggiorna accumulatori per ogni coppia (topo, perf) valida."""
        for t_key, t_val in topo.items():
            if not math.isfinite(t_val):
                continue
            for p_key, p_val in perf.items():
                if not isinstance(p_val, (int, float)) or not math.isfinite(p_val):
                    continue
                acc = self._accumulators.setdefault(
                    t_key, {}
                ).setdefault(p_key, [0.0] * 6)
                # n, sum_x, sum_y, sum_xx, sum_yy, sum_xy
                acc[0] += 1.0
                acc[1] += t_val
                acc[2] += p_val
                acc[3] += t_val * t_val
                acc[4] += p_val * p_val
                acc[5] += t_val * p_val

    def _remove_from_accumulators(
        self,
        topo: Dict[str, float],
        perf: Dict[str, float],
    ) -> None:
        """Rimuove un punto dati dagli accumulatori (finestra mobile)."""
        for t_key, t_val in topo.items():
            if not math.isfinite(t_val):
                continue
            for p_key, p_val in perf.items():
                if not isinstance(p_val, (int, float)) or not math.isfinite(p_val):
                    continue
                acc = self._accumulators.get(t_key, {}).get(p_key)
                if acc is None or acc[0] < 1:
                    continue
                acc[0] -= 1.0
                acc[1] -= t_val
                acc[2] -= p_val
                acc[3] -= t_val * t_val
                acc[4] -= p_val * p_val
                acc[5] -= t_val * p_val

    # ------------------------------------------------------------------ #
    # Private: statistica
    # ------------------------------------------------------------------ #

    @staticmethod
    def _pearson_from_acc(
        acc: List[float],
    ) -> Tuple[float, float, float]:
        """Calcola Pearson r, slope, intercept da accumulatori.

        acc = [n, sum_x, sum_y, sum_xx, sum_yy, sum_xy]
        """
        n = acc[0]
        if n < 3:
            return 0.0, 0.0, 0.0

        sx = acc[1]
        sy = acc[2]
        sxx = acc[3]
        syy = acc[4]
        sxy = acc[5]

        # Numeratore covarianza
        cov = n * sxy - sx * sy
        var_x = n * sxx - sx * sx
        var_y = n * syy - sy * sy

        if var_x <= 0.0 or var_y <= 0.0:
            return 0.0, 0.0, sy / n if n > 0 else 0.0

        r = cov / (math.sqrt(var_x) * math.sqrt(var_y))
        r = max(-1.0, min(1.0, r))

        # Regressione lineare: slope = cov / var_x
        slope = cov / var_x
        mean_x = sx / n
        mean_y = sy / n
        intercept = mean_y - slope * mean_x

        return r, slope, intercept

    @staticmethod
    def _approx_normal_cdf(z: float) -> float:
        """Approssimazione CDF normale standard (Abramowitz & Stegun 26.2.17)."""
        if z < 0:
            return 1.0 - TopologyPerformanceCorrelator._approx_normal_cdf(-z)
        b0 = 0.2316419
        b1 = 0.319381530
        b2 = -0.356563782
        b3 = 1.781477937
        b4 = -1.821255978
        b5 = 1.330274429
        t = 1.0 / (1.0 + b0 * z)
        phi = math.exp(-z * z / 2.0) / math.sqrt(2.0 * math.pi)
        return 1.0 - phi * (b1 * t + b2 * t * t + b3 * (t ** 3) + b4 * (t ** 4) + b5 * (t ** 5))
