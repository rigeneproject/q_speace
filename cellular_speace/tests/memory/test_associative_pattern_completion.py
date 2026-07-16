import pytest
import tempfile
from pathlib import Path

from speace_core.cellular_brain.memory.associative_pattern_completion import (
    AssociativePatternCompletion,
    StoredPattern,
)
from speace_core.cellular_brain.memory.morphology_events import MorphologyEventType


class FakeMorphologicalMemory:
    def __init__(self):
        self.events = []

    def log_event(self, event):
        self.events.append(event)


@pytest.fixture
def tmp_apc():
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "patterns.jsonl"
        mem = FakeMorphologicalMemory()
        apc = AssociativePatternCompletion(storage_path=str(path), memory=mem)
        yield apc


class TestStoredPattern:
    def test_to_dict_and_from_dict(self):
        pat = StoredPattern(label="test", pattern=[0.1, 0.2, 0.3])
        d = pat.to_dict()
        assert d["label"] == "test"
        assert d["pattern"] == [0.1, 0.2, 0.3]
        restored = StoredPattern.from_dict(d)
        assert restored.label == pat.label
        assert restored.pattern == pat.pattern
        assert restored.pattern_id == pat.pattern_id
        assert restored.created_at == pat.created_at


class TestAssociativePatternCompletion:
    def test_store_pattern(self, tmp_apc):
        record = tmp_apc.store_pattern("pattern_a", [1.0, 0.0, 0.0])
        assert record.label == "pattern_a"
        assert record.pattern == [1.0, 0.0, 0.0]
        assert tmp_apc.pattern_count() == 1
        assert any(
            str(e.event_type) == "MorphologyEventType.PATTERN_STORED" for e in tmp_apc.memory.events
        )

    def test_complete_pattern_exact_match(self, tmp_apc):
        tmp_apc.store_pattern("pattern_a", [1.0, 0.0, 0.0])
        result = tmp_apc.complete_pattern([1.0, 0.0, 0.0], threshold=0.9)
        assert result is not None
        assert result.label == "pattern_a"

    def test_complete_pattern_noisy_input(self, tmp_apc):
        tmp_apc.store_pattern("pattern_a", [1.0, 0.0, 0.0])
        # Slightly noisy vector should still match above threshold
        result = tmp_apc.complete_pattern([0.95, 0.05, 0.0], threshold=0.8)
        assert result is not None
        assert result.label == "pattern_a"

    def test_complete_pattern_partial_input(self, tmp_apc):
        tmp_apc.store_pattern("pattern_a", [1.0, 0.5, 0.2])
        # Shorter partial input (zero-padded internally)
        result = tmp_apc.complete_pattern([1.0, 0.5], threshold=0.8)
        assert result is not None
        assert result.label == "pattern_a"

    def test_complete_pattern_below_threshold_returns_none(self, tmp_apc):
        tmp_apc.store_pattern("pattern_a", [1.0, 0.0, 0.0])
        result = tmp_apc.complete_pattern([0.0, 1.0, 0.0], threshold=0.9)
        assert result is None

    def test_complete_pattern_empty_store_returns_none(self, tmp_apc):
        result = tmp_apc.complete_pattern([1.0, 0.0, 0.0])
        assert result is None

    def test_get_similar_states_ordering(self, tmp_apc):
        tmp_apc.store_pattern("a", [1.0, 0.0, 0.0])
        tmp_apc.store_pattern("b", [0.0, 1.0, 0.0])
        tmp_apc.store_pattern("c", [0.9, 0.1, 0.0])
        results = tmp_apc.get_similar_states([1.0, 0.0, 0.0])
        assert len(results) == 3
        # Highest similarity first
        labels = [tmp_apc._patterns[r[0]].label for r in results]
        assert labels[0] == "a"
        assert labels[1] == "c"
        assert labels[2] == "b"

    def test_get_similar_states_empty(self, tmp_apc):
        assert tmp_apc.get_similar_states([1.0, 0.0]) == []

    def test_persistence_jsonl(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "patterns.jsonl"
            mem = FakeMorphologicalMemory()
            apc = AssociativePatternCompletion(storage_path=str(path), memory=mem)
            apc.store_pattern("persisted", [0.1, 0.2, 0.3])

            apc2 = AssociativePatternCompletion(storage_path=str(path), memory=mem)
            assert apc2.pattern_count() == 1
            loaded = apc2.list_patterns()[0]
            assert loaded.label == "persisted"
            assert loaded.pattern == [0.1, 0.2, 0.3]

    def test_load_missing_file_safe(self, tmp_apc):
        # File was created by fixture init, but let's test with a nonexistent one
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "nonexistent" / "patterns.jsonl"
            mem = FakeMorphologicalMemory()
            apc = AssociativePatternCompletion(storage_path=str(path), memory=mem)
            # No file exists yet; should not raise
            apc._load()
            assert apc.pattern_count() == 0

    def test_cosine_similarity_orthogonal(self):
        score = AssociativePatternCompletion._cosine_similarity(
            [1.0, 0.0], [0.0, 1.0]
        )
        assert score == pytest.approx(0.0)

    def test_cosine_similarity_identical(self):
        score = AssociativePatternCompletion._cosine_similarity(
            [1.0, 2.0, 3.0], [1.0, 2.0, 3.0]
        )
        assert score == pytest.approx(1.0)

    def test_cosine_similarity_zero_vector(self):
        score = AssociativePatternCompletion._cosine_similarity(
            [0.0, 0.0], [1.0, 0.0]
        )
        assert score == pytest.approx(0.0)

    def test_multiple_patterns_same_label(self, tmp_apc):
        tmp_apc.store_pattern("same", [1.0, 0.0])
        tmp_apc.store_pattern("same", [0.0, 1.0])
        assert tmp_apc.pattern_count() == 2
        results = tmp_apc.get_similar_states([1.0, 0.0])
        assert len(results) == 2

    def test_complete_pattern_logs_event(self, tmp_apc):
        tmp_apc.store_pattern("target", [1.0, 0.0, 0.0])
        tmp_apc.memory.events.clear()
        tmp_apc.complete_pattern([1.0, 0.0, 0.0], threshold=0.9)
        types = [str(e.event_type) for e in tmp_apc.memory.events]
        assert any("PATTERN_COMPLETED" in t for t in types)

    def test_similarity_with_different_lengths(self):
        apc = AssociativePatternCompletion()
        score = apc._similarity([1.0, 0.5], [1.0, 0.5, 0.0])
        assert score == pytest.approx(1.0)
