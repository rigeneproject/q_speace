import pytest
import tempfile
from pathlib import Path

from speace_core.cellular_brain.memory.episodic_memory import EpisodicMemory
from speace_core.cellular_brain.memory.episodic_recall import EpisodicRecall


class FakeMorphologicalMemory:
    def __init__(self):
        self.events = []

    def log_event(self, event):
        self.events.append(event)


class TestEpisodicRecall:
    def _build_store(self, outcomes):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "episodes.jsonl"
            mem = FakeMorphologicalMemory()
            em = EpisodicMemory(storage_path=str(path), memory=mem)
            for trigger, out, cog_init, cog_fin, evs in outcomes:
                ep = em.start_episode(trigger=trigger, initial_metrics={"cognitive_score": cog_init, "coherence_phi": 0.5})
                for ev_type, src in evs:
                    em.record_event(ep.episode_id, ev_type, src)
                em.close_episode(ep.episode_id, {"cognitive_score": cog_fin, "coherence_phi": 0.5}, out)
            return em, mem

    def test_recall_by_outcome(self):
        em, mem = self._build_store([
            ("t1", "regression", 0.5, 0.1, [("ev_a", "mod")]),
            ("t2", "recovery", 0.5, 0.8, [("ev_b", "mod")]),
            ("t3", "regression", 0.5, 0.2, [("ev_c", "mod")]),
        ])
        recall = EpisodicRecall(episodic_memory=em, memory=mem)
        results = recall.recall_by_outcome("regression")
        assert len(results) == 2

    def test_recall_similar_metrics(self):
        em, mem = self._build_store([
            ("t1", "ok", 0.5, 0.6, []),
            ("t2", "ok", 0.8, 0.9, []),
        ])
        recall = EpisodicRecall(episodic_memory=em, memory=mem)
        result = recall.recall_similar_metrics({"cognitive_score": 0.9}, top_k=2)
        assert len(result.matched_episodes) <= 2
        assert result.query == "similar_metrics"

    def test_find_regression_precursors(self):
        em, mem = self._build_store([
            ("t1", "regression", 0.5, 0.1, [("ev_a", "mod")]),
            ("t2", "regression", 0.5, 0.0, [("ev_a", "mod"), ("ev_d", "mod")]),
        ])
        recall = EpisodicRecall(episodic_memory=em, memory=mem)
        precursors = recall.find_regression_precursors()
        assert "ev_a" in precursors
        assert "ev_d" in precursors

    def test_find_recovery_patterns(self):
        em, mem = self._build_store([
            ("t1", "recovery", 0.5, 0.8, [("ev_b", "mod")]),
            ("t2", "recovery", 0.5, 0.9, [("ev_b", "mod"), ("ev_e", "mod")]),
        ])
        recall = EpisodicRecall(episodic_memory=em, memory=mem)
        patterns = recall.find_recovery_patterns()
        assert "ev_b" in patterns
        assert "ev_e" in patterns

    def test_recall_empty_store_safe(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "episodes.jsonl"
            mem = FakeMorphologicalMemory()
            em = EpisodicMemory(storage_path=str(path), memory=mem)
            recall = EpisodicRecall(episodic_memory=em, memory=mem)
            assert recall.recall_by_outcome("any") == []
            assert recall.recall_similar_metrics({}).matched_episodes == []
            assert recall.find_regression_precursors() == []
            assert recall.find_recovery_patterns() == []

    def test_compute_metric_similarity_identical(self):
        score = EpisodicRecall._compute_metric_similarity(
            {"a": 1.0, "b": 1.0},
            {"a": 1.0, "b": 1.0},
        )
        assert score == pytest.approx(1.0)

    def test_compute_metric_similarity_orthogonal(self):
        score = EpisodicRecall._compute_metric_similarity(
            {"a": 1.0, "b": 0.0},
            {"a": 0.0, "b": 1.0},
        )
        assert score == pytest.approx(0.0)
