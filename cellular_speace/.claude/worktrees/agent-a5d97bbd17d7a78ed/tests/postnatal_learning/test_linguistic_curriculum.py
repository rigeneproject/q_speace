import pytest
import tempfile

from speace_core.cellular_brain.postnatal_learning.linguistic_curriculum import (
    LinguisticCurriculum,
    LinguisticStage,
)


class TestLinguisticCurriculum:
    def test_initial_stage_is_babbling(self):
        with tempfile.TemporaryDirectory() as td:
            curriculum = LinguisticCurriculum(base_path=td)
            assert curriculum.current_stage() == LinguisticStage.LINGUISTIC_BABBLING

    def test_advance_stage_when_criteria_met(self):
        with tempfile.TemporaryDirectory() as td:
            curriculum = LinguisticCurriculum(base_path=td)
            next_stage = curriculum.advance_stage(criteria_met=True)
            assert next_stage == LinguisticStage.IMITATION_SANDBOX

    def test_advance_stage_blocked_when_criteria_not_met(self):
        with tempfile.TemporaryDirectory() as td:
            curriculum = LinguisticCurriculum(base_path=td)
            next_stage = curriculum.advance_stage(criteria_met=False)
            assert next_stage == LinguisticStage.LINGUISTIC_BABBLING

    def test_advance_stage_stops_at_final(self):
        with tempfile.TemporaryDirectory() as td:
            curriculum = LinguisticCurriculum(base_path=td)
            curriculum.advance_stage(criteria_met=True)
            curriculum.advance_stage(criteria_met=True)
            final = curriculum.advance_stage(criteria_met=True)
            assert final == LinguisticStage.SEMANTIC_GROUNDING

    def test_expose_input_increments_exposure_count(self):
        with tempfile.TemporaryDirectory() as td:
            curriculum = LinguisticCurriculum(base_path=td)
            curriculum.expose_input(["hello", "world"])
            metrics = curriculum.get_learning_metrics()
            assert metrics["exposure_count"] == 1

    def test_expose_input_tracks_imitation(self):
        with tempfile.TemporaryDirectory() as td:
            curriculum = LinguisticCurriculum(base_path=td)
            curriculum.expose_input(
                ["hello"],
                imitation_target=["hello"],
                imitation_output=["hello"],
            )
            metrics = curriculum.get_learning_metrics()
            assert metrics["imitation_attempts"] == 1
            assert metrics["imitation_successes"] == 1
            assert metrics["imitation_accuracy"] == pytest.approx(1.0)

    def test_expose_input_tracks_imitation_failure(self):
        with tempfile.TemporaryDirectory() as td:
            curriculum = LinguisticCurriculum(base_path=td)
            curriculum.expose_input(
                ["hello"],
                imitation_target=["hello"],
                imitation_output=["world"],
            )
            metrics = curriculum.get_learning_metrics()
            assert metrics["imitation_attempts"] == 1
            assert metrics["imitation_successes"] == 0
            assert metrics["imitation_accuracy"] < 1.0

    def test_expose_input_grounds_concept(self):
        with tempfile.TemporaryDirectory() as td:
            curriculum = LinguisticCurriculum(base_path=td)
            curriculum.expose_input(
                ["cat"],
                grounded_concept="cat",
                grounding_score=0.75,
            )
            metrics = curriculum.get_learning_metrics()
            assert "cat" in metrics["grounded_concepts"]
            assert metrics["grounded_concepts_count"] == 1
            assert metrics["concept_grounding_scores"]["cat"] == pytest.approx(0.75)

    def test_concept_grounding_requires_threshold(self):
        with tempfile.TemporaryDirectory() as td:
            curriculum = LinguisticCurriculum(base_path=td)
            curriculum.expose_input(
                ["dog"],
                grounded_concept="dog",
                grounding_score=0.3,
            )
            metrics = curriculum.get_learning_metrics()
            assert "dog" not in metrics["grounded_concepts"]
            assert metrics["grounded_concepts_count"] == 0

    def test_concept_grounding_accumulates(self):
        with tempfile.TemporaryDirectory() as td:
            curriculum = LinguisticCurriculum(base_path=td)
            curriculum.expose_input(
                ["bird"],
                grounded_concept="bird",
                grounding_score=0.4,
            )
            curriculum.expose_input(
                ["bird"],
                grounded_concept="bird",
                grounding_score=0.4,
            )
            metrics = curriculum.get_learning_metrics()
            assert metrics["concept_grounding_scores"]["bird"] == pytest.approx(0.8)
            assert "bird" in metrics["grounded_concepts"]

    def test_concept_grounding_clamped_at_one(self):
        with tempfile.TemporaryDirectory() as td:
            curriculum = LinguisticCurriculum(base_path=td)
            curriculum.expose_input(
                ["fish"],
                grounded_concept="fish",
                grounding_score=0.9,
            )
            curriculum.expose_input(
                ["fish"],
                grounded_concept="fish",
                grounding_score=0.9,
            )
            metrics = curriculum.get_learning_metrics()
            assert metrics["concept_grounding_scores"]["fish"] == pytest.approx(1.0)

    def test_persistence_across_instances(self):
        with tempfile.TemporaryDirectory() as td:
            c1 = LinguisticCurriculum(base_path=td)
            c1.expose_input(["a", "b"])
            c1.advance_stage(criteria_met=True)

            c2 = LinguisticCurriculum(base_path=td)
            assert c2.current_stage() == LinguisticStage.IMITATION_SANDBOX
            assert c2.get_learning_metrics()["exposure_count"] == 1

    def test_metrics_keys_present(self):
        with tempfile.TemporaryDirectory() as td:
            curriculum = LinguisticCurriculum(base_path=td)
            metrics = curriculum.get_learning_metrics()
            expected = {
                "stage",
                "exposure_count",
                "imitation_attempts",
                "imitation_successes",
                "imitation_accuracy",
                "grounded_concepts_count",
                "grounded_concepts",
                "concept_grounding_scores",
            }
            assert expected.issubset(set(metrics.keys()))

    def test_initial_stage_override(self):
        with tempfile.TemporaryDirectory() as td:
            curriculum = LinguisticCurriculum(
                base_path=td,
                initial_stage=LinguisticStage.IMITATION_SANDBOX,
            )
            assert curriculum.current_stage() == LinguisticStage.IMITATION_SANDBOX

    def test_expose_input_returns_entry(self):
        with tempfile.TemporaryDirectory() as td:
            curriculum = LinguisticCurriculum(base_path=td)
            entry = curriculum.expose_input(["x"])
            assert "timestamp" in entry
            assert "stage" in entry
            assert "tokens" in entry
            assert "exposure_count" in entry

    def test_imitation_accuracy_zero_when_empty_target(self):
        with tempfile.TemporaryDirectory() as td:
            curriculum = LinguisticCurriculum(base_path=td)
            entry = curriculum.expose_input(
                ["x"],
                imitation_target=[],
                imitation_output=["y"],
            )
            assert entry.get("imitation_accuracy", 0.0) == pytest.approx(0.0)

    def test_imitation_accuracy_partial_match(self):
        with tempfile.TemporaryDirectory() as td:
            curriculum = LinguisticCurriculum(base_path=td)
            entry = curriculum.expose_input(
                ["a", "b", "c"],
                imitation_target=["a", "b", "c"],
                imitation_output=["a", "x", "c"],
            )
            assert entry["imitation_accuracy"] == pytest.approx(2 / 3)
