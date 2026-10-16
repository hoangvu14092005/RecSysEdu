import json

import numpy as np
import pandas as pd
import pytest

from recsysedu.adapters.recbole import BPRScorer
from recsysedu.contracts import ScoreResult
from recsysedu.evaluation.ranking import rank_candidates
from recsysedu.models.content import ContentConfig, fit_content
from recsysedu.models.hybrid import HybridModel, select_alpha
from recsysedu.models.popularity import PopularityModel


def _components():
    content = PopularityModel(('C_1', 'C_2', 'C_3'), (3., 2., 1.))
    bpr = BPRScorer(np.array([[0.], [1.]]), np.array([[0.], [-2.], [0.], [2.]]),
                    {'U_1': 1}, {'C_1': 1, 'C_2': 2, 'C_3': 3})
    return content, bpr


@pytest.mark.parametrize('alpha,expected', [(0, [1., .5, 0.]), (1, [0., .5, 1.]),
                                           (.25, [.75, .5, .25])])
def test_alpha_endpoints_and_mix_preserve_candidate_order(alpha, expected):
    content, bpr = _components()
    result = HybridModel(content, bpr, alpha, content).score('U_1', ('C_1', 'C_2', 'C_3'))
    np.testing.assert_allclose(result.scores, expected)
    assert result.course_ids == ('C_1', 'C_2', 'C_3')
    assert result.fallback_status == 'none'
    assert f'hybrid_alpha:{float(alpha)}' in result.evidence['C_2']
    reordered = HybridModel(content, bpr, alpha, content).score('U_1', ('C_3', 'C_1'))
    assert reordered.course_ids == ('C_3', 'C_1')
    np.testing.assert_allclose(reordered.scores, [alpha, 1 - alpha])


def test_constant_components_and_empty_candidates_remain_finite():
    content, bpr = _components()
    constant = PopularityModel(('C_1', 'C_2', 'C_3'), (9., 9., 9.))
    hybrid = HybridModel(constant, bpr, .5, content)
    np.testing.assert_allclose(hybrid.score('U_1', ('C_1', 'C_2', 'C_3')).scores,
                               [0., .25, .5])
    assert hybrid.score('U_1', ()).scores.size == 0
    np.testing.assert_array_equal(hybrid.score('U_1', ('C_2',)).scores, [0.])


def test_hybrid_equal_scores_use_shared_deterministic_tie_break():
    content, bpr = _components()
    result = HybridModel(content, bpr, .5, content).score('U_1', ('C_3', 'C_2', 'C_1'))
    assert [item.course_id for item in rank_candidates(result, set(), k=10)] == [
        'C_1', 'C_2', 'C_3']


@pytest.mark.parametrize('bad_ids', [('C_3', 'C_2', 'C_1'), ('C_1', 'C_2')])
def test_hybrid_rejects_component_candidate_order_or_length_mismatch(bad_ids):
    class WrongScorer:
        def score(self, user_id, candidate_ids):
            return ScoreResult(bad_ids, np.ones(len(bad_ids)))

    content, bpr = _components()
    for model in (HybridModel(WrongScorer(), bpr, .5, content),
                  HybridModel(content, WrongScorer(), .5, content)):
        with pytest.raises(ValueError, match='candidate'):
            model.score('U_1', ('C_1', 'C_2', 'C_3'))


def test_missing_bpr_user_falls_back_to_content_then_popularity(tmp_path):
    popularity, bpr = _components()
    courses = pd.DataFrame({'course_id': ['C_1', 'C_2', 'C_3'],
                            'name': ['python basics', 'python advanced', 'history'],
                            'about': ['', '', '']})
    train = pd.DataFrame({'user_id': ['U_2', 'U_3', 'U_4'],
                          'course_id': ['C_1', 'C_2', 'C_3']})
    content = fit_content(courses, train, ContentConfig(), tmp_path / 'features', popularity)
    hybrid = HybridModel(content, bpr, 1., popularity)
    result = hybrid.score('U_2', ('C_2', 'C_3'))
    np.testing.assert_allclose(result.scores, [1., 0.])
    assert result.fallback_status == 'content_unknown_bpr_user'
    assert 'fallback:content_unknown_bpr_user' in result.evidence['C_2']
    result = hybrid.score('U_missing', ('C_1', 'C_2', 'C_3'))
    np.testing.assert_allclose(result.scores, [1., .5, 0.])
    assert result.fallback_status == 'popularity_unknown_bpr_user_empty_content'


def test_hybrid_does_not_hide_other_bpr_errors_as_unknown_user_fallback():
    class BrokenBPR:
        def score(self, user_id, candidate_ids):
            raise ValueError('damaged embedding artifact')

    content, _ = _components()
    hybrid = HybridModel(content, BrokenBPR(), .5, content)
    with pytest.raises(ValueError, match='damaged embedding'):
        hybrid.score('U_1', ('C_1', 'C_2'))


def test_hybrid_normalizes_extreme_finite_scores_without_overflow():
    content, _ = _components()
    extreme = PopularityModel(('C_1', 'C_2', 'C_3'), (-1e308, 0., 1e308))
    hybrid = HybridModel(content, extreme, 1., content)
    np.testing.assert_allclose(hybrid.score('U_1', ('C_1', 'C_2', 'C_3')).scores,
                               [0., .5, 1.])


def test_hybrid_preserves_component_evidence_and_marks_content_fallback():
    class EvidenceScorer:
        def score(self, user_id, candidate_ids):
            return ScoreResult(tuple(candidate_ids), np.array([3., 2., 1.]),
                               'popularity_empty_profile', {'C_2': ('observed:C_7',)})

    popularity, bpr = _components()
    result = HybridModel(EvidenceScorer(), bpr, .25, popularity).score(
        'U_1', ('C_1', 'C_2', 'C_3'))
    assert result.fallback_status == 'content:popularity_empty_profile'
    assert result.evidence['C_2'][:2] == ('observed:C_7', 'hybrid_alpha:0.25')
    scores = dict(item.split(':', 1) for item in result.evidence['C_2'][2:])
    assert float(scores['content_normalized']) == pytest.approx(.5)
    assert float(scores['bpr_normalized']) == pytest.approx(.5)


@pytest.mark.parametrize('alpha', [-1, 1.01, True, float('nan'), float('inf'), '0.5'])
def test_hybrid_rejects_invalid_alpha(alpha):
    content, bpr = _components()
    with pytest.raises(ValueError, match='alpha'):
        HybridModel(content, bpr, alpha, content)


def _run(run_id, ndcg):
    return dict(run_id=run_id, dataset_hash='dataset', split_hash='split', protocol_id='protocol',
                seed=17, evaluation_split='valid', k=10, primary_metric='NDCG@10',
                cohort_size=12, candidate_universe_size=3, candidate_policy='full_train_universe',
                profile_policy='train_only', seen_policy='train',
                tie_break_policy='score_desc_course_id_asc', metric_status='measured',
                metrics={'NDCG@10': ndcg})


def test_alpha_selection_uses_validation_ndcg_then_smallest_alpha_and_persists(tmp_path):
    runs = {1.: _run('r1', .9), 0.: _run('r0', .5), .5: _run('r05', .9)}
    path = tmp_path / 'selection.json'
    assert select_alpha(runs, [1., 0., .5], artifact_path=path) == .5
    manifest = json.loads(path.read_text(encoding='utf-8'))
    assert manifest['selected_alpha'] == .5
    assert manifest['selected_ndcg'] == .9
    assert manifest['evaluation_split'] == 'valid'
    assert [row['alpha'] for row in manifest['validation_runs']] == [0., .5, 1.]
    assert manifest['validation_runs'][1]['run_id'] == 'r05'
    assert manifest['validation_runs'][1]['manifest_hash']
    with pytest.raises(ValueError, match='exists'):
        select_alpha(runs, [1., 0., .5], artifact_path=path)


@pytest.mark.parametrize('change', [
    {'evaluation_split': 'test'}, {'split_hash': 'other'}, {'cohort_size': 13},
    {'seed': 18}, {'metric_status': 'not_available'}, {'k': 5},
    {'metrics': {'NDCG@10': float('nan')}}, {'metrics': {'NDCG@10': 1.1}},
])
def test_selection_rejects_test_unmeasured_or_incompatible_runs(change, tmp_path):
    runs = {0.: _run('r0', .5), 1.: _run('r1', .9) | change}
    path = tmp_path / 'rejected.json'
    with pytest.raises(ValueError):
        select_alpha(runs, [0., 1.], artifact_path=path)
    assert not path.exists()


@pytest.mark.parametrize('alphas', [[], [0., 0.], [0., 1.], [True]])
def test_selection_requires_exactly_one_run_per_unique_alpha(alphas):
    with pytest.raises(ValueError):
        select_alpha({0.: _run('r0', .5)}, alphas)
