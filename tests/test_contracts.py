import numpy as np
import pytest

from recsysedu.contracts import RankedItem, Recommender, RunIdentity, ScoreResult


def test_score_result_preserves_candidate_order_and_defaults():
    result = ScoreResult(("C_3", "C_1", "C_2"), np.array([0.3, 0.9, 0.4]))

    assert result.course_ids == ("C_3", "C_1", "C_2")
    np.testing.assert_array_equal(result.scores, [0.3, 0.9, 0.4])
    assert result.fallback_status == "none"
    assert result.evidence == {}


def test_score_result_keeps_valid_scores_when_input_array_changes():
    scores = np.array([0.3, 0.9])
    result = ScoreResult(("C_3", "C_1"), scores)

    scores[0] = float("nan")
    np.testing.assert_array_equal(result.scores, [0.3, 0.9])
    with pytest.raises(ValueError):
        result.scores[0] = float("inf")


@pytest.mark.parametrize(
    ("course_ids", "scores"),
    [
        (("C_1", "C_2"), np.array([0.5])),
        (("C_1", "C_1"), np.array([0.5, 0.6])),
        (("C_1",), np.array([float("nan")])),
        (("C_1",), np.array([float("inf")])),
        (("C_1",), np.array([-float("inf")])),
        (("C_1",), np.array([[0.5]])),
    ],
)
def test_score_result_rejects_length_mismatch_and_non_finite_scores(course_ids, scores):
    with pytest.raises(ValueError):
        ScoreResult(course_ids, scores)


def test_score_result_requires_source_ids_and_numpy_scores():
    with pytest.raises((TypeError, ValueError)):
        ScoreResult((1,), np.array([0.5]))
    with pytest.raises((TypeError, ValueError)):
        ScoreResult(("C_1",), [0.5])


def test_run_identity_requires_non_empty_matching_hash_fields():
    valid = dict(
        run_id="run-1",
        model_id="popularity",
        dataset_hash="dataset-sha256",
        split_hash="split-sha256",
        protocol_id="temporal-v1",
        seed=42,
    )
    identity = RunIdentity(**valid)
    assert identity.dataset_hash == valid["dataset_hash"]
    assert identity.split_hash == valid["split_hash"]

    for field in ("run_id", "model_id", "dataset_hash", "split_hash", "protocol_id"):
        with pytest.raises(ValueError):
            RunIdentity(**(valid | {field: "  "}))


@pytest.mark.parametrize("rank", [0, -1, True, 1.5])
def test_ranked_item_requires_rank_from_one_and_finite_score(rank):
    with pytest.raises(ValueError):
        RankedItem("C_1", rank, 0.5)


@pytest.mark.parametrize("score", [float("nan"), float("inf"), -float("inf")])
def test_ranked_item_rejects_non_finite_score(score):
    with pytest.raises(ValueError):
        RankedItem("C_1", 1, score)


def test_recommender_protocol_accepts_structural_implementation():
    class StaticRecommender:
        def score(self, user_id, candidate_ids):
            assert user_id == "U_1"
            return ScoreResult(tuple(candidate_ids), np.array([0.5, 0.2]))

    model: Recommender = StaticRecommender()
    result = model.score("U_1", ("C_2", "C_1"))
    assert result.course_ids == ("C_2", "C_1")
