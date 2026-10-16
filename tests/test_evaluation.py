import csv
import hashlib
import json
from dataclasses import replace

import numpy as np
import pyarrow.parquet as pq
import pytest

from recsysedu.contracts import RunIdentity, ScoreResult
from recsysedu.data.prepare import prepare_dataset
from recsysedu.data.split import build_temporal_split
from recsysedu.evaluation.ranking import rank_candidates
from recsysedu.evaluation.run import evaluate_run


class StaticScorer:
    """Test score provider, with explicit candidate ordering and no fit method."""

    def score(self, user_id, candidate_ids):
        assert tuple(candidate_ids) == ('C_1', 'C_2', 'C_3')
        return ScoreResult(tuple(candidate_ids), np.array([9.0, 8.0, 7.0]),
                           fallback_status='fixture_fallback')


@pytest.fixture
def split_case(tmp_path):
    # Universe C_1/2/3. U_1 has a cold valid target but a warm test target.
    users = [
        ('U_1', ['C_1', 'C_4', 'C_2']),
        ('U_2', ['C_2', 'C_1', 'C_3']),
        ('U_3', ['C_3', 'C_2', 'C_1']),
    ]
    return _build_split(tmp_path, users)


def _build_split(tmp_path, users):
    course_path, user_path = tmp_path / 'course.json', tmp_path / 'user.json'
    course_path.write_text('\n'.join(json.dumps({'id': f'C_{i}'}) for i in range(1, 5)),
                           encoding='utf-8')
    user_path.write_text('\n'.join(json.dumps({
        'id': user_id, 'course_order': courses,
        'enroll_time': ['2020-01-01', '2020-02-01', '2020-03-01'],
    }) for user_id, courses in users), encoding='utf-8')
    prepared, split = tmp_path / 'prepared', tmp_path / 'split'
    prepare_dataset(course_path, user_path, prepared, dataset_version='fixture-v1',
                    time_basis='source_local_naive', sample_users=0, seed=17)
    manifest = build_temporal_split(prepared / 'interactions.parquet',
                                    prepared / 'courses.parquet', split,
                                    split_version='fixture-split-v1', seed=17)
    identity = RunIdentity('fixture-run', 'fixture-scorer', manifest['dataset_hash'],
                           manifest['split_hash'], manifest['protocol_id'], 17)
    return split, identity, manifest


def _recommendations(output):
    return [json.loads(line) for line in
            (output / 'recommendations.jsonl').read_text(encoding='utf-8').splitlines()]


def test_ranking_masks_seen_and_breaks_equal_scores_by_course_id():
    result = ScoreResult(('C_3', 'C_2', 'C_1', 'C_4'), np.array([1., 9., 1., -2.]))
    ranked = rank_candidates(result, {'C_2'}, k=10)
    assert [(item.course_id, item.rank, item.score) for item in ranked] == [
        ('C_1', 1, 1.0), ('C_3', 2, 1.0), ('C_4', 3, -2.0)]
    assert len(rank_candidates(result, set(), k=2)) == 2


@pytest.mark.parametrize('bad_score', [float('nan'), float('inf'), -float('inf')])
def test_ranking_rejects_nan_instead_of_silently_sorting_it(bad_score):
    result = ScoreResult(('C_1', 'C_2'), np.array([1., 2.]))
    # Recheck at the trust boundary even if a model has bypassed the dataclass guard.
    object.__setattr__(result, 'scores', np.array([bad_score, 2.]))
    with pytest.raises(ValueError, match='finite'):
        rank_candidates(result, {'C_1'}, k=10)


@pytest.mark.parametrize('k', [0, -1, True, 1.5])
def test_ranking_rejects_invalid_k(k):
    with pytest.raises(ValueError):
        rank_candidates(ScoreResult(('C_1',), np.array([1.])), set(), k=k)


def test_valid_uses_train_seen_while_test_masks_train_plus_valid(tmp_path, split_case):
    split, identity, _ = split_case
    valid_out, test_out = tmp_path / 'valid-run', tmp_path / 'test-run'
    valid = evaluate_run(StaticScorer(), split, valid_out, identity, evaluation_split='valid')
    test = evaluate_run(StaticScorer(), split, test_out, identity, evaluation_split='test')
    valid_recs = _recommendations(valid_out)
    test_recs = _recommendations(test_out)
    assert [(row['user_id'], [item['course_id'] for item in row['items']])
            for row in valid_recs] == [('U_2', ['C_1', 'C_3']), ('U_3', ['C_1', 'C_2'])]
    assert [(row['user_id'], [item['course_id'] for item in row['items']])
            for row in test_recs] == [('U_1', ['C_2', 'C_3']), ('U_2', ['C_3']),
                                     ('U_3', ['C_1'])]
    assert valid['cohort_size'] == 2
    assert test['cohort_size'] == 3
    assert valid['cold_target_count'] == 1
    assert test['cold_target_count'] == 0
    assert valid['metrics']['NDCG@10'] == pytest.approx((1 + 0.6309297536) / 2)
    assert test['metrics']['NDCG@10'] == 1.0
    assert test['metrics']['Precision@10'] == pytest.approx(0.1)
    # Lists cover C_1, C_2 and C_3: 3/3, not mean per-user coverage (4/9).
    assert test['metrics']['Coverage@10'] == 1.0
    assert test['short_list_user_count'] == 3
    assert test['fallback_counts'] == {'fixture_fallback': 3}
    assert test['profile_policy'] == 'train_only'


def test_evaluator_writes_consistent_hashed_artifacts(tmp_path, split_case):
    split, identity, _ = split_case
    output = tmp_path / 'run'
    result = evaluate_run(StaticScorer(), split, output, identity, evaluation_split='valid')
    assert {path.name for path in output.iterdir()} == {
        'metrics.csv', 'per_user_metrics.parquet', 'recommendations.jsonl', 'run_manifest.json'}
    saved = json.loads((output / 'run_manifest.json').read_text(encoding='utf-8'))
    assert saved == result
    assert saved['primary_metric'] == 'NDCG@10'
    assert saved['split_hash'] == identity.split_hash
    assert saved['dataset_hash'] == identity.dataset_hash
    assert saved['protocol_id'] == identity.protocol_id
    for filename, digest in saved['output_hashes'].items():
        assert hashlib.sha256((output / filename).read_bytes()).hexdigest() == digest
    users = pq.read_table(output / 'per_user_metrics.parquet').to_pylist()
    assert [row['user_id'] for row in users] == ['U_2', 'U_3']
    assert [row['NDCG@10'] for row in users] == pytest.approx([1.0, 0.6309297536])
    with (output / 'metrics.csv').open(encoding='utf-8', newline='') as stream:
        summary = list(csv.DictReader(stream))
    assert len(summary) == 1
    assert float(summary[0]['Coverage@10']) == 1.0
    assert int(summary[0]['cohort_size']) == 2


@pytest.mark.parametrize('field', ['dataset_hash', 'split_hash', 'protocol_id'])
def test_evaluator_rejects_mismatched_dataset_split_or_protocol_hash(
        tmp_path, split_case, field):
    split, identity, _ = split_case
    with pytest.raises(ValueError, match=field):
        evaluate_run(StaticScorer(), split, tmp_path / 'bad-run',
                     replace(identity, **{field: 'wrong'}), evaluation_split='valid')
    assert not (tmp_path / 'bad-run').exists()


@pytest.mark.parametrize('filename', ['train.parquet', 'valid.parquet', 'test.parquet',
                                     'valid_cohort.parquet', 'candidate_universe.parquet',
                                     'split_manifest.json'])
def test_evaluator_rejects_tampered_split_before_scoring(tmp_path, split_case, filename):
    split, identity, _ = split_case
    path = split / filename
    if filename == 'split_manifest.json':
        value = json.loads(path.read_text(encoding='utf-8'))
        value['warm_cohort_sizes']['valid'] = 123
        path.write_text(json.dumps(value), encoding='utf-8')
    else:
        path.write_bytes(path.read_bytes() + b'tampered')
    with pytest.raises(ValueError, match='hash'):
        evaluate_run(StaticScorer(), split, tmp_path / 'bad-run', identity,
                     evaluation_split='valid')
    assert not (tmp_path / 'bad-run').exists()


@pytest.mark.parametrize('returned_ids', [('C_1', 'C_2'), ('C_3', 'C_2', 'C_1'),
                                         ('C_1', 'C_2', 'padding')])
def test_evaluator_rejects_incomplete_reordered_or_unknown_candidates(
        tmp_path, split_case, returned_ids):
    class WrongScorer:
        def score(self, user_id, candidate_ids):
            return ScoreResult(returned_ids, np.ones(len(returned_ids)))

    split, identity, _ = split_case
    with pytest.raises(ValueError, match='candidate'):
        evaluate_run(WrongScorer(), split, tmp_path / 'bad-run', identity,
                     evaluation_split='valid')
    assert not (tmp_path / 'bad-run').exists()


def test_failed_run_never_publishes_partial_output(tmp_path, split_case):
    class FailingScorer(StaticScorer):
        def score(self, user_id, candidate_ids):
            if user_id == 'U_3':
                raise RuntimeError('score failed mid-run')
            return super().score(user_id, candidate_ids)

    split, identity, _ = split_case
    with pytest.raises(RuntimeError, match='score failed'):
        evaluate_run(FailingScorer(), split, tmp_path / 'bad-run', identity,
                     evaluation_split='valid')
    assert not (tmp_path / 'bad-run').exists()
    assert not list(tmp_path.glob('.evaluation-*'))


def test_evaluator_refuses_overwrite(tmp_path, split_case):
    split, identity, _ = split_case
    output = tmp_path / 'existing'
    output.mkdir()
    (output / 'keep.txt').write_text('keep', encoding='utf-8')
    with pytest.raises(ValueError, match='exist'):
        evaluate_run(StaticScorer(), split, output, identity, evaluation_split='valid')
    assert (output / 'keep.txt').read_text(encoding='utf-8') == 'keep'


def test_evaluator_rejects_non_protocol_k_before_creating_output(tmp_path, split_case):
    split, identity, _ = split_case
    output = tmp_path / 'bad-k-run'
    with pytest.raises(ValueError, match='k=10'):
        evaluate_run(StaticScorer(), split, output, identity,
                     evaluation_split='valid', k=1)
    assert not output.exists()
    assert not list(tmp_path.glob('.evaluation-*'))
    accepted = evaluate_run(StaticScorer(), split, tmp_path / 'k10-run', identity,
                            evaluation_split='valid', k=10)
    assert accepted['k'] == 10


@pytest.mark.parametrize('evaluation_split,k', [('train', 10), ('valid', 0), ('valid', True)])
def test_evaluator_rejects_invalid_evaluation_parameters(
        tmp_path, split_case, evaluation_split, k):
    split, identity, _ = split_case
    with pytest.raises(ValueError):
        evaluate_run(StaticScorer(), split, tmp_path / 'bad-run', identity,
                     evaluation_split=evaluation_split, k=k)


def test_evaluator_preserves_ranked_item_evidence_after_masking_and_sorting(tmp_path, split_case):
    class EvidenceScorer:
        def score(self, user_id, candidate_ids):
            return ScoreResult(tuple(candidate_ids), np.array([1., 2., 3.]), evidence={
                'C_1': ('source-course:C_a',), 'C_2': ('source-course:C_b',)})

    split, identity, _ = split_case
    output = tmp_path / 'evidence-run'
    evaluate_run(EvidenceScorer(), split, output, identity, evaluation_split='valid')
    recs = _recommendations(output)
    assert [(item['course_id'], item['evidence']) for item in recs[0]['items']] == [
        ('C_3', []), ('C_1', ['source-course:C_a'])]
    assert [(item['course_id'], item['evidence']) for item in recs[1]['items']] == [
        ('C_2', ['source-course:C_b']), ('C_1', ['source-course:C_a'])]


def test_source_user_and_course_ids_can_overlap(tmp_path):
    split, identity, _ = _build_split(tmp_path, [
        ('C_1', ['C_1', 'C_2', 'C_3']),
        ('C_2', ['C_2', 'C_3', 'C_1']),
        ('C_3', ['C_3', 'C_1', 'C_2']),
    ])
    result = evaluate_run(StaticScorer(), split, tmp_path / 'run', identity,
                          evaluation_split='valid')
    assert result['cohort_size'] == 3


def test_evaluator_flushes_all_users_across_output_batches(tmp_path):
    patterns = [['C_1', 'C_2', 'C_3'], ['C_2', 'C_3', 'C_1'], ['C_3', 'C_1', 'C_2']]
    split, identity, _ = _build_split(tmp_path, [
        (f'U_{i:04}', patterns[i % 3]) for i in range(1029)])
    output = tmp_path / 'run'
    result = evaluate_run(StaticScorer(), split, output, identity, evaluation_split='valid')
    assert result['cohort_size'] == 1029
    users = pq.read_table(output / 'per_user_metrics.parquet').to_pylist()
    assert len(users) == 1029
    assert users[0]['user_id'] == 'U_0000'
    assert users[-1]['user_id'] == 'U_1028'
    assert len({row['user_id'] for row in users}) == 1029
    assert len(_recommendations(output)) == 1029


def test_empty_warm_cohort_is_rejected_without_fabricated_metrics(tmp_path):
    split, identity, _ = _build_split(tmp_path, [('U_1', ['C_1', 'C_2', 'C_3'])])
    with pytest.raises(ValueError, match='empty warm cohort'):
        evaluate_run(StaticScorer(), split, tmp_path / 'bad-run', identity,
                     evaluation_split='valid')
    assert not (tmp_path / 'bad-run').exists()


def test_input_mutation_during_scoring_prevents_publication(tmp_path, split_case):
    split, identity, _ = split_case

    class MutatingScorer(StaticScorer):
        def score(self, user_id, candidate_ids):
            if user_id == 'U_3':
                with (split / 'train.parquet').open('ab') as stream:
                    stream.write(b'changed-during-run')
            return super().score(user_id, candidate_ids)

    with pytest.raises(ValueError, match='hash'):
        evaluate_run(MutatingScorer(), split, tmp_path / 'bad-run', identity,
                     evaluation_split='valid')
    assert not (tmp_path / 'bad-run').exists()
