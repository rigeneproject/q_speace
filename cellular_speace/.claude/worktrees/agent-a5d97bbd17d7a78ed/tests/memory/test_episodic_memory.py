import pytest
import tempfile
from pathlib import Path

from speace_core.cellular_brain.memory.episodic_memory import (
    Episode,
    EpisodeEvent,
    EpisodicMemory,
)


class FakeMorphologicalMemory:
    def __init__(self):
        self.events = []

    def log_event(self, event):
        self.events.append(event)


class TestEpisodicMemory:
    def test_start_episode_creates_episode(self):
        mem = FakeMorphologicalMemory()
        em = EpisodicMemory(memory=mem)
        ep = em.start_episode(trigger="test_trigger", initial_metrics={"cognitive_score": 0.5})
        assert ep.episode_id.startswith("ep-")
        assert ep.trigger == "test_trigger"
        assert ep.initial_metrics["cognitive_score"] == 0.5
        assert ep.outcome == "unknown"

    def test_record_event_appends_to_episode(self):
        mem = FakeMorphologicalMemory()
        em = EpisodicMemory(memory=mem)
        ep = em.start_episode(trigger="test")
        ev = em.record_event(
            episode_id=ep.episode_id,
            event_type="semantic_recall",
            source_module="semantic_memory",
            metrics={"recall_success": 1.0},
        )
        assert ev is not None
        assert ev.event_type == "semantic_recall"
        loaded = em.get_episode(ep.episode_id)
        assert loaded is not None
        assert len(loaded.events) == 1

    def test_close_episode_computes_metric_deltas(self):
        mem = FakeMorphologicalMemory()
        em = EpisodicMemory(memory=mem)
        ep = em.start_episode(
            trigger="test",
            initial_metrics={"cognitive_score": 0.5, "coherence_phi": 0.4},
        )
        closed = em.close_episode(
            episode_id=ep.episode_id,
            final_metrics={"cognitive_score": 0.6, "coherence_phi": 0.45},
            outcome="validated",
        )
        assert closed is not None
        assert closed.outcome == "validated"
        assert closed.cognitive_delta == pytest.approx(0.1)
        assert closed.phi_delta == pytest.approx(0.05)

    def test_episode_persistence_jsonl(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "episodes.jsonl"
            mem = FakeMorphologicalMemory()
            em = EpisodicMemory(storage_path=str(path), memory=mem)
            ep = em.start_episode(trigger="persist")
            em.record_event(ep.episode_id, "event_a", "mod")
            em.close_episode(ep.episode_id, {"cognitive_score": 0.8}, "ok")

            em2 = EpisodicMemory(storage_path=str(path), memory=mem)
            loaded = em2.load_episodes()
            assert len(loaded) >= 1
            ids = [e.episode_id for e in loaded]
            assert ep.episode_id in ids

    def test_load_recent_episodes(self):
        mem = FakeMorphologicalMemory()
        em = EpisodicMemory(memory=mem)
        ep1 = em.start_episode(trigger="first")
        ep2 = em.start_episode(trigger="second")
        recent = em.get_recent_episodes(limit=1)
        assert len(recent) == 1
        assert recent[0].episode_id == ep2.episode_id

    def test_link_assembly(self):
        mem = FakeMorphologicalMemory()
        em = EpisodicMemory(memory=mem)
        ep = em.start_episode(trigger="test")
        assert em.link_assembly(ep.episode_id, "asm-a") is True
        loaded = em.get_episode(ep.episode_id)
        assert "asm-a" in loaded.linked_assemblies

    def test_link_proposal(self):
        mem = FakeMorphologicalMemory()
        em = EpisodicMemory(memory=mem)
        ep = em.start_episode(trigger="test")
        assert em.link_proposal(ep.episode_id, "prop-1") is True
        loaded = em.get_episode(ep.episode_id)
        assert "prop-1" in loaded.linked_proposals

    def test_record_event_missing_episode_returns_none(self):
        mem = FakeMorphologicalMemory()
        em = EpisodicMemory(memory=mem)
        assert em.record_event("missing", "ev", "mod") is None

    def test_close_missing_episode_returns_none(self):
        mem = FakeMorphologicalMemory()
        em = EpisodicMemory(memory=mem)
        assert em.close_episode("missing", {}) is None

    def test_morphological_events_logged_for_episode_start(self):
        mem = FakeMorphologicalMemory()
        em = EpisodicMemory(memory=mem)
        em.start_episode(trigger="test")
        types = [str(e.event_type) for e in mem.events]
        assert any("EPISODE_STARTED" in t for t in types)

    def test_morphological_events_logged_for_episode_close(self):
        mem = FakeMorphologicalMemory()
        em = EpisodicMemory(memory=mem)
        ep = em.start_episode(trigger="test")
        mem.events.clear()
        em.close_episode(ep.episode_id, {}, "ok")
        types = [str(e.event_type) for e in mem.events]
        assert any("EPISODE_CLOSED" in t for t in types)

    def test_no_episode_corruption_on_duplicate_close(self):
        mem = FakeMorphologicalMemory()
        em = EpisodicMemory(memory=mem)
        ep = em.start_episode(trigger="test")
        em.close_episode(ep.episode_id, {"cognitive_score": 0.5}, "ok")
        # Second close on same episode
        second = em.close_episode(ep.episode_id, {"cognitive_score": 0.6}, "ok2")
        assert second is not None
        # The episode should reflect the latest close
        loaded = em.get_episode(ep.episode_id)
        assert loaded.outcome == "ok2"
