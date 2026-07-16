"""Test per TopologyPerformanceCorrelator."""

import json
import math
import pathlib
import tempfile
import time

from speace_core.organism_observer.topology_diff import StructureDelta
from speace_core.organism_observer.topology_correlator import (
    TopologyPerformanceCorrelator,
    CorrelatedPair,
    CorrelatorReport,
    TOPOLOGY_METRICS,
)


def _make_delta(**overrides) -> StructureDelta:
    """Crea StructureDelta con default sensati."""
    d = StructureDelta()
    for k, v in overrides.items():
        setattr(d, k, v)
    return d


# ------------------------------------------------------------------ #
# Recording
# ------------------------------------------------------------------ #


class TestRecord:
    def test_record_from_structure_delta(self):
        corr = TopologyPerformanceCorrelator()
        delta = _make_delta(d_modularity_q=0.1, d_global_efficiency=0.05)
        corr.record(delta, {"health_score": 0.8, "ari_score": 0.6})
        assert corr.sample_count == 1

    def test_record_from_keywords(self):
        corr = TopologyPerformanceCorrelator()
        corr.record_from_events(
            d_modularity_q=0.1,
            change_velocity=0.5,
            health_score=0.9,
            ari_score=0.7,
        )
        assert corr.sample_count == 1

    def test_record_nan_performance_ignored(self):
        corr = TopologyPerformanceCorrelator()
        corr.record(_make_delta(d_modularity_q=0.1), {"health_score": float("nan")})
        # Non deve crasare, ma non deve accumulare NaN
        assert corr._observed_performance_metrics() == []

    def test_multiple_records_increment(self):
        corr = TopologyPerformanceCorrelator()
        for i in range(10):
            corr.record(
                _make_delta(d_modularity_q=i * 0.01, change_velocity=i * 0.02),
                {"health_score": 0.8 - i * 0.01},
            )
        assert corr.sample_count == 10


# ------------------------------------------------------------------ #
# Correlazione
# ------------------------------------------------------------------ #


class TestCorrelationMatrix:
    def test_perfect_positive_correlation(self):
        corr = TopologyPerformanceCorrelator()
        # d_modularity_q e health_score perfettamente in fase
        for i in range(50):
            x = i * 0.02
            corr.record(
                _make_delta(d_modularity_q=x, change_velocity=abs(x - 0.5)),
                {"health_score": 0.5 + x},
            )
        matrix = corr.correlation_matrix(min_samples=3)
        r = matrix.get("d_modularity_q", {}).get("health_score", {}).get("pearson_r", 0.0)
        assert abs(r - 1.0) < 0.001, f"Expected R≈1.0, got {r}"

    def test_perfect_negative_correlation(self):
        corr = TopologyPerformanceCorrelator()
        for i in range(50):
            x = i * 0.02
            corr.record(
                _make_delta(d_modularity_q=x),
                {"health_score": 1.0 - x},
            )
        matrix = corr.correlation_matrix(min_samples=3)
        r = matrix.get("d_modularity_q", {}).get("health_score", {}).get("pearson_r", 0.0)
        assert abs(r - (-1.0)) < 0.001, f"Expected R≈-1.0, got {r}"

    def test_no_correlation(self):
        corr = TopologyPerformanceCorrelator()
        import random
        rng = random.Random(42)
        for i in range(100):
            corr.record(
                _make_delta(d_modularity_q=rng.gauss(0, 1)),
                {"health_score": rng.gauss(0.5, 0.1)},
            )
        matrix = corr.correlation_matrix(min_samples=3)
        r = matrix.get("d_modularity_q", {}).get("health_score", {}).get("pearson_r", 0.0)
        assert abs(r) < 0.3, f"Expected R≈0, got {r}"

    def test_insufficient_samples(self):
        corr = TopologyPerformanceCorrelator()
        corr.record(_make_delta(d_modularity_q=0.1), {"health_score": 0.8})
        corr.record(_make_delta(d_modularity_q=0.2), {"health_score": 0.7})
        matrix = corr.correlation_matrix(min_samples=3)
        assert matrix == {}, f"Expected empty matrix, got {matrix}"

    def test_sliding_window(self):
        corr = TopologyPerformanceCorrelator()
        # 50 campioni trend positivo, 50 trend negativo
        for i in range(50):
            x = i * 0.02
            corr.record(
                _make_delta(d_modularity_q=x),
                {"health_score": 0.5 + x},
            )
        for i in range(50):
            x = i * 0.02
            corr.record(
                _make_delta(d_modularity_q=x),
                {"health_score": 1.0 - x},
            )
        # Ultimi 20: trend negativo → R negativo
        slid = corr.sliding_correlation(window=20, min_samples=3)
        r = slid.get("d_modularity_q", {}).get("health_score", {}).get("pearson_r", 0.0)
        assert r < -0.5, f"Expected R < -0.5, got {r}"


# ------------------------------------------------------------------ #
# CorrelatedPairs & Report
# ------------------------------------------------------------------ #


class TestCorrelatedPairs:
    def test_correlated_pairs_returns_list(self):
        corr = TopologyPerformanceCorrelator()
        for i in range(20):
            x = i * 0.02
            corr.record(
                _make_delta(d_modularity_q=x, d_global_efficiency=-x),
                {"health_score": 0.5 + x, "ari_score": 0.5 - x},
            )
        pairs = corr.correlated_pairs(min_samples=3)
        assert len(pairs) >= 1
        assert all(isinstance(p, CorrelatedPair) for p in pairs)
        assert pairs[0].sample_size >= 3

    def test_top_predictors(self):
        corr = TopologyPerformanceCorrelator()
        for i in range(30):
            x = i * 0.02
            corr.record(
                _make_delta(d_modularity_q=x, d_global_efficiency=0.0),
                {"health_score": 0.5 + x},
            )
        preds = corr.top_predictors("health_score", n=3)
        assert len(preds) >= 1
        # d_modularity_q deve essere un predictor forte
        top = preds[0]
        assert top.topology_metric == "d_modularity_q"

    def test_report_structure(self):
        corr = TopologyPerformanceCorrelator()
        for i in range(50):
            x = i * 0.01
            corr.record(
                _make_delta(d_modularity_q=x, change_velocity=0.1),
                {"health_score": 0.5 + x, "tick_latency_ms": 100 - x * 50},
            )
        report = corr.report(min_samples=3)
        assert isinstance(report, CorrelatorReport)
        assert report.n_samples == 50
        assert len(report.insights) >= 1


# ------------------------------------------------------------------ #
# Persistence
# ------------------------------------------------------------------ #


class TestPersistence:
    def test_save_and_load(self):
        corr = TopologyPerformanceCorrelator()
        for i in range(20):
            x = i * 0.05
            corr.record(
                _make_delta(d_modularity_q=x),
                {"health_score": 0.5 + x},
            )
        assert corr.sample_count == 20

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
        ) as f:
            tmp_path = f.name

        try:
            saved = corr.save(tmp_path)
            assert saved == 20

            corr2 = TopologyPerformanceCorrelator()
            loaded = corr2.load(tmp_path)
            assert loaded == 20
            assert corr2.sample_count == 20
            assert corr2._observed_performance_metrics() == ["health_score"]
        finally:
            pathlib.Path(tmp_path).unlink(missing_ok=True)

    def test_save_empty(self):
        corr = TopologyPerformanceCorrelator()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
        ) as f:
            tmp_path = f.name
        try:
            assert corr.save(tmp_path) == 0
            corr2 = TopologyPerformanceCorrelator()
            assert corr2.load(tmp_path) == 0
        finally:
            pathlib.Path(tmp_path).unlink(missing_ok=True)


# ------------------------------------------------------------------ #
# Edge cases
# ------------------------------------------------------------------ #


class TestEdgeCases:
    def test_clear(self):
        corr = TopologyPerformanceCorrelator()
        corr.record(_make_delta(d_modularity_q=0.1), {"health_score": 0.8})
        assert corr.sample_count == 1
        corr.clear()
        assert corr.sample_count == 0
        assert corr.correlation_matrix() == {}

    def test_observed_metrics_empty(self):
        corr = TopologyPerformanceCorrelator()
        assert corr._observed_performance_metrics() == []

    def test_non_finite_topo_ignored(self):
        corr = TopologyPerformanceCorrelator()
        corr.record(_make_delta(d_modularity_q=float("inf")), {"health_score": 0.8})
        # L'accumulatore per d_modularity_q non deve esistere
        assert "d_modularity_q" not in corr._accumulators

    def test_many_performance_metrics(self):
        corr = TopologyPerformanceCorrelator()
        for i in range(20):
            corr.record(
                _make_delta(d_modularity_q=i * 0.01),
                {
                    "health_score": 0.8 - i * 0.01,
                    "ari_score": 0.5 + i * 0.005,
                    "arc_accuracy": 0.3 + i * 0.01,
                    "tick_latency_ms": float(200 - i * 2),
                    "memory_rss_mb": float(500 + i),
                },
            )
        obs = corr._observed_performance_metrics()
        assert "health_score" in obs
        assert "ari_score" in obs
        assert "arc_accuracy" in obs
        assert "tick_latency_ms" in obs
        assert "memory_rss_mb" in obs

    def test_single_metric_topology(self):
        """Solo alcune metriche topologiche hanno varianza."""
        corr = TopologyPerformanceCorrelator()
        for i in range(20):
            corr.record(
                _make_delta(d_modularity_q=i * 0.01),
                {"health_score": 0.5 + i * 0.01},
            )
        matrix = corr.correlation_matrix(min_samples=3)
        assert "d_modularity_q" in matrix
        # change_velocity e' sempre 0 (non settato) → no varianza → non in matrix
        assert "change_velocity" not in matrix
