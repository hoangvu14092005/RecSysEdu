import hashlib
import json
from datetime import datetime

import pyarrow.parquet as pq
import pytest

from recsysedu.data.prepare import prepare_dataset
from recsysedu.data.split import build_temporal_split


def _prepared(tmp_path, users, course_ids=None):
    course_ids = course_ids or ['C_1', 'C_2', 'C_3', 'C_4', 'C_5']
    (tmp_path / 'course.json').write_text(
        '\n'.join(json.dumps({'id': item}) for item in course_ids), encoding='utf-8')
    (tmp_path / 'user.json').write_text(
        '\n'.join(json.dumps({'id': user_id, 'course_order': courses,
                              'enroll_time': times})
                  for user_id, courses, times in users), encoding='utf-8')
    prepared = tmp_path / 'prepared'
    prepare_dataset(tmp_path / 'course.json', tmp_path / 'user.json', prepared,
                    dataset_version='fixture-v1', time_basis='source_local_naive',
                    sample_users=0, seed=17)
    return prepared


def _split(prepared, output, seed=17):
    return build_temporal_split(prepared / 'interactions.parquet',
                                prepared / 'courses.parquet', output,
                                split_version='fixture-split-v1', seed=seed)


def _rows(output, name):
    return pq.read_table(output / f'{name}.parquet').to_pylist()


def test_split_uses_last_two_strict_times_and_never_overlaps(tmp_path):
    prepared = _prepared(tmp_path, [
        ('U_1', ['C_4', 'C_1', 'C_3', 'C_2'],
         ['2020-04-01', '2020-01-01', '2020-03-01', '2020-02-01']),
        ('U_2', ['C_2', 'C_5', 'C_1'],
         ['2020-01-01', '2020-03-01', '2020-02-01']),
    ])
    output = tmp_path / 'split'
    manifest = _split(prepared, output)
    train, valid, test = (_rows(output, name) for name in ('train', 'valid', 'test'))
    assert [(r['user_id'], r['course_id']) for r in train] == [
        ('U_1', 'C_1'), ('U_1', 'C_2'), ('U_2', 'C_2')]
    assert [(r['user_id'], r['course_id']) for r in valid] == [
        ('U_1', 'C_3'), ('U_2', 'C_1')]
    assert [(r['user_id'], r['course_id']) for r in test] == [
        ('U_1', 'C_4'), ('U_2', 'C_5')]
    pairs = [[(r['user_id'], r['course_id']) for r in rows]
             for rows in (train, valid, test)]
    assert len(set().union(*map(set, pairs))) == sum(map(len, pairs))
    for user_id in ('U_1', 'U_2'):
        assert max(r['event_time'] for r in train if r['user_id'] == user_id) < next(
            r['event_time'] for r in valid if r['user_id'] == user_id) < next(
                r['event_time'] for r in test if r['user_id'] == user_id)
    assert test[0]['event_time'] == datetime(2020, 4, 1)
    assert manifest['protocol_id'] == 'leave_last_two_out_v1'
    assert _rows(output, 'candidate_universe') == [
        {'course_id': 'C_1'}, {'course_id': 'C_2'}]


def test_split_quarantines_boundary_ties_without_course_id_ordering(tmp_path):
    prepared = _prepared(tmp_path, [
        ('U_good', ['C_1', 'C_2', 'C_3', 'C_4'],
         ['2020-01-01', '2020-01-01', '2020-02-01', '2020-03-01']),
        ('U_train_valid_tie', ['C_1', 'C_2', 'C_3'],
         ['2020-01-01', '2020-01-01', '2020-03-01']),
        ('U_valid_test_tie', ['C_3', 'C_4', 'C_5'],
         ['2020-01-01', '2020-02-01', '2020-02-01']),
    ])
    output = tmp_path / 'split'
    manifest = _split(prepared, output)
    for name in ('train', 'valid', 'test'):
        assert {row['user_id'] for row in _rows(output, name)} == {'U_good'}
    assert manifest['boundary_tie_user_count'] == 2
    assert manifest['boundary_tie_interaction_count'] == 6
    assert manifest['split_user_count'] == 1


def test_split_marks_cold_targets_and_builds_warm_cohorts_from_train_universe(tmp_path):
    prepared = _prepared(tmp_path, [
        ('U_1', ['C_1', 'C_4', 'C_5'],
         ['2020-01-01', '2020-02-01', '2020-03-01']),
        ('U_2', ['C_2', 'C_5', 'C_1'],
         ['2020-01-01', '2020-02-01', '2020-03-01']),
        ('U_3', ['C_3', 'C_1', 'C_2'],
         ['2020-01-01', '2020-02-01', '2020-03-01']),
    ])
    output = tmp_path / 'split'
    manifest = _split(prepared, output)
    assert _rows(output, 'candidate_universe') == [
        {'course_id': 'C_1'}, {'course_id': 'C_2'}, {'course_id': 'C_3'}]
    assert [(r['user_id'], r['target_in_train']) for r in _rows(output, 'valid')] == [
        ('U_1', False), ('U_2', False), ('U_3', True)]
    assert [(r['user_id'], r['target_in_train']) for r in _rows(output, 'test')] == [
        ('U_1', False), ('U_2', True), ('U_3', True)]
    assert [r['user_id'] for r in _rows(output, 'valid_cohort')] == ['U_3']
    assert [r['user_id'] for r in _rows(output, 'test_cohort')] == ['U_2', 'U_3']
    assert manifest['cold_target_counts'] == {'valid': 2, 'test': 1}
    assert manifest['warm_cohort_sizes'] == {'valid': 1, 'test': 2}


def test_split_repeats_byte_identical_outputs_for_same_input_and_seed(tmp_path):
    prepared = _prepared(tmp_path, [
        ('U_1', ['C_1', 'C_2', 'C_3'],
         ['2020-01-01', '2020-02-01', '2020-03-01']),
    ])
    first = _split(prepared, tmp_path / 'first')
    second = _split(prepared, tmp_path / 'second')
    assert first == second
    for filename, digest in first['output_hashes'].items():
        assert (tmp_path / 'first' / filename).read_bytes() == (
            tmp_path / 'second' / filename).read_bytes()
        assert hashlib.sha256((tmp_path / 'first' / filename).read_bytes()).hexdigest() == digest
    assert (tmp_path / 'first/split_manifest.json').read_bytes() == (
        tmp_path / 'second/split_manifest.json').read_bytes()
    assert first['dataset_hash'] == hashlib.sha256(
        (prepared / 'dataset_manifest.json').read_bytes()).hexdigest()
    assert first['dataset_version'] == 'fixture-v1'


def test_split_rejects_bad_manifest_and_leaves_no_output(tmp_path):
    prepared = _prepared(tmp_path, [
        ('U_1', ['C_1', 'C_2', 'C_3'],
         ['2020-01-01', '2020-02-01', '2020-03-01']),
    ])
    (prepared / 'dataset_manifest.json').write_text('{bad json', encoding='utf-8')
    with pytest.raises(ValueError, match='manifest'):
        _split(prepared, tmp_path / 'split')
    assert not (tmp_path / 'split').exists()
