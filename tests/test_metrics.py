import pytest

from recsysedu.evaluation.metrics import metrics_at_k


@pytest.mark.parametrize('ranking,ndcg,hit', [
    (['C_target'], 1.0, 1.0),
    (['C_other', 'C_target'], 0.6309297536, 1.0),
    (['C_other'], 0.0, 0.0),
    ([f'C_{i}' for i in range(10)] + ['C_target'], 0.0, 0.0),
])
def test_hand_calculated_single_target_metrics(ranking, ndcg, hit):
    result = metrics_at_k(ranking, ['C_target'], 20, k=10)
    assert result['NDCG@10'] == pytest.approx(ndcg)
    assert result['HitRate@10'] == hit
    assert result['Recall@10'] == hit
    assert result['Precision@10'] == hit / 10
    assert result['Coverage@10'] == min(len(ranking), 10) / 20


def test_multi_target_ndcg_uses_all_ground_truth_for_ideal_ranking():
    result = metrics_at_k(['C_a', 'C_miss', 'C_b'], ['C_a', 'C_b', 'C_c'], 10, k=3)
    assert result['NDCG@3'] == pytest.approx(0.7039180890)
    assert result['Recall@3'] == pytest.approx(2 / 3)
    assert result['Precision@3'] == pytest.approx(2 / 3)
    assert result['Coverage@3'] == 0.3


def test_empty_ranking_is_a_valid_miss():
    assert metrics_at_k([], ['C_target'], 20, k=10) == {
        'NDCG@10': 0.0, 'HitRate@10': 0.0, 'Recall@10': 0.0,
        'Precision@10': 0.0, 'Coverage@10': 0.0,
    }


@pytest.mark.parametrize('ranking,targets,size,k', [
    (['C_a', 'C_a'], ['C_a'], 2, 10),
    (['C_a'], [], 2, 10),
    (['C_a'], ['C_a', 'C_a'], 2, 10),
    (['C_a'], ['C_a'], 0, 10),
    (['C_a', 'C_b'], ['C_a'], 1, 10),
    (['C_a'], ['C_a'], 2, 0),
    (['C_a'], ['C_a'], 2, True),
])
def test_metrics_reject_invalid_inputs(ranking, targets, size, k):
    with pytest.raises(ValueError):
        metrics_at_k(ranking, targets, size, k=k)
