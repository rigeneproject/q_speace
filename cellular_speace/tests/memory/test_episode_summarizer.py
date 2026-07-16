import pytest

from speace_core.cellular_brain.memory.episodic_memory import Episode, EpisodeEvent
from speace_core.cellular_brain.memory.episode_summarizer import EpisodeSummarizer


class TestEpisodeSummarizer:
    def test_classify_recovery(self):
        ep = Episode(
            episode_id="ep-1",
            start_time="now",
            trigger="test",
            cognitive_delta=0.05,
            phi_delta=0.03,
        )
        assert EpisodeSummarizer.classify(ep) == "RECOVERY_EPISODE"

    def test_classify_regression(self):
        ep = Episode(
            episode_id="ep-2",
            start_time="now",
            trigger="test",
            cognitive_delta=-0.05,
            phi_delta=-0.04,
        )
        assert EpisodeSummarizer.classify(ep) == "REGRESSION_EPISODE"

    def test_classify_self_improvement(self):
        ep = Episode(
            episode_id="ep-3",
            start_time="now",
            trigger="self_improvement_cycle",
            events=[
                EpisodeEvent(
                    event_id="e1",
                    timestamp="t",
                    event_type="architecture_proposal_created",
                    source_module="self_improvement",
                )
            ],
        )
        assert EpisodeSummarizer.classify(ep) == "SELF_IMPROVEMENT_EPISODE"

    def test_classify_semantic_learning(self):
        ep = Episode(
            episode_id="ep-4",
            start_time="now",
            trigger="test",
            events=[
                EpisodeEvent(
                    event_id="e1",
                    timestamp="t",
                    event_type="cell_assembly_created",
                    source_module="semantic_memory",
                )
            ],
        )
        assert EpisodeSummarizer.classify(ep) == "SEMANTIC_LEARNING_EPISODE"

    def test_classify_stability(self):
        ep = Episode(
            episode_id="ep-5",
            start_time="now",
            trigger="test",
            events=[
                EpisodeEvent(
                    event_id="e1",
                    timestamp="t",
                    event_type="region_stability_checked",
                    source_module="brainstem",
                )
            ],
        )
        assert EpisodeSummarizer.classify(ep) == "STABILITY_EPISODE"

    def test_classify_neutral(self):
        ep = Episode(
            episode_id="ep-6",
            start_time="now",
            trigger="test",
            cognitive_delta=0.0,
            phi_delta=0.0,
        )
        assert EpisodeSummarizer.classify(ep) == "NEUTRAL_EPISODE"

    def test_generate_markdown_contains_fields(self):
        summarizer = EpisodeSummarizer()
        ep = Episode(
            episode_id="ep-7",
            start_time="2026-05-17T10:00:00",
            end_time="2026-05-17T10:01:00",
            trigger="benchmark_run",
            outcome="validated",
            cognitive_delta=0.1,
            phi_delta=0.05,
            events=[
                EpisodeEvent(
                    event_id="e1",
                    timestamp="2026-05-17T10:00:30",
                    event_type="tick",
                    source_module="orchestrator",
                )
            ],
            linked_assemblies=["asm-a"],
            linked_proposals=["prop-1"],
            semantic_tags=["tag1"],
        )
        md = summarizer.generate_markdown_report(ep)
        assert "ep-7" in md
        assert "benchmark_run" in md
        assert "validated" in md
        assert "0.1000" in md or "0.1" in md
        assert "asm-a" in md
        assert "prop-1" in md
        assert "tag1" in md

    def test_generate_batch_markdown(self):
        summarizer = EpisodeSummarizer()
        episodes = [
            Episode(
                episode_id="ep-8",
                start_time="now",
                trigger="test",
                outcome="validated",
                cognitive_delta=0.1,
            ),
            Episode(
                episode_id="ep-9",
                start_time="now",
                trigger="test",
                outcome="regression",
                cognitive_delta=-0.1,
            ),
        ]
        md = summarizer.generate_batch_markdown_report(episodes)
        assert "Batch Report" in md
        assert "RECOVERY_EPISODE" in md or "REGRESSION_EPISODE" in md
