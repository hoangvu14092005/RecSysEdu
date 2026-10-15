import hashlib
import json
from datetime import datetime, timezone

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from recsysedu.data.prepare import prepare_dataset


def raw_files(tmp_path, users, courses=None):
    courses = courses or [
        {'id': 'C_1', 'name': 'One', 'about': None, 'field': ['CS', 'CS']},
        {'id': 'C_2'}, {'id': 'C_003'}, {'id': 'special'},
    ]
    for filename, records in [('course.json', courses), ('user.json', users)]:
        (tmp_path / filename).write_text('\n'.join(map(json.dumps, records)), encoding='utf-8')
    return tmp_path / 'course.json', tmp_path / 'user.json'


def user(user_id='U_1', **changes):
    value = {'id': user_id, 'course_order': ['C_1', 2, 3],
             'enroll_time': ['2020-01-01', '2020-02-01', '2020-03-01']}
    return value | changes


def prepare(tmp_path, paths, **changes):
    config = dict(dataset_version='fixture-v1', time_basis='source_local_naive',
                  sample_users=0, seed=20261016)
    return prepare_dataset(*paths, tmp_path / 'prepared', **(config | changes))


def test_prepare_maps_only_catalog_ids_and_keeps_earliest_duplicate(tmp_path):
    paths = raw_files(tmp_path, [user(
        course_order=['C_1', 2, 3, 'special', 'C_1'],
        enroll_time=['2020-04-01', '2020-02-01', '2020-03-01',
                     '2020-03-02', '2020-01-01'])])
    before = [path.read_bytes() for path in paths]
    manifest = prepare(tmp_path, paths)
    rows = pq.read_table(tmp_path / 'prepared/interactions.parquet').to_pylist()
    assert [(row['course_id'], row['event_time']) for row in rows] == [
        ('C_1', datetime(2020, 1, 1)), ('C_2', datetime(2020, 2, 1)),
        ('C_003', datetime(2020, 3, 1)), ('special', datetime(2020, 3, 2))]
    assert rows[0]['event_time_raw'] == '2020-01-01'
    assert all(row['interaction'] == 1 and row['source_record'] for row in rows)
    assert len({(row['user_id'], row['course_id']) for row in rows}) == len(rows)
    courses = pq.read_table(tmp_path / 'prepared/courses.parquet').to_pylist()
    assert set(row['course_id'] for row in rows) <= set(row['course_id'] for row in courses)
    assert courses[0]['about'] == ''
    assert courses[0]['fields'] == ['CS']
    assert manifest['error_counts']['duplicate_interaction'] == 1
    assert [path.read_bytes() for path in paths] == before


def test_prepare_rejects_unknown_ids_and_bad_histories_with_reason_codes(tmp_path):
    paths = raw_files(tmp_path, [
        user(course_order=['C_1', 2, 3, 999, True, 2.0, '2', 'special'],
             enroll_time=['2020-01-01'] * 7 + ['bad']),
        user('U_mismatch', enroll_time=[]),
        user('U_bad_type', course_order=None),
        user('U_short', course_order=['C_1'], enroll_time=['2020-01-01']),
        user('U_1'), user('', course_order=[], enroll_time=[]),
    ])
    manifest = prepare(tmp_path, paths)
    counts = manifest['error_counts']
    assert counts['unknown_course_id'] == 4
    assert counts['invalid_timestamp'] == 1
    assert counts['array_length_mismatch'] == 1
    assert counts['invalid_history_type'] == 1
    assert counts['insufficient_history'] == 1
    assert counts['duplicate_user_id'] == 1
    assert counts['invalid_user_id'] == 1
    rejects = pq.read_table(tmp_path / 'prepared/rejects.parquet').to_pylist()
    assert {row['reason_code'] for row in rejects} == set(counts)
    assert sum(row['count'] for row in rejects) == sum(counts.values())
    assert manifest['users_scanned'] == 6
    assert manifest['selected_user_count'] == 1


def test_prepare_requires_declared_time_basis_and_is_seed_reproducible(tmp_path):
    paths = raw_files(tmp_path, [user(f'U_{i:02}') for i in range(30)])
    for basis in [None, '', 'local', 'Mars/Unknown']:
        with pytest.raises(ValueError, match='time_basis'):
            prepare(tmp_path, paths, time_basis=basis)
    first = prepare(tmp_path, paths, sample_users=5)
    second = prepare_dataset(*paths, tmp_path / 'repeat', dataset_version='fixture-v1',
                             time_basis='source_local_naive', sample_users=5, seed=20261016)
    assert first['output_hashes'] == second['output_hashes']
    assert first['eligible_user_count'] == 30
    assert first['selected_user_count'] == 5
    assert first['row_counts']['interactions'] == 15
    assert first['requested_user_count'] == 5
    cohort = pq.read_table(tmp_path / 'prepared/cohort_users.parquet').to_pylist()
    assert len({row['user_id'] for row in cohort}) == 5
    prepare_dataset(*paths, tmp_path / 'other-seed', dataset_version='fixture-v1',
                    time_basis='source_local_naive', sample_users=5, seed=42)
    other_cohort = pq.read_table(tmp_path / 'other-seed/cohort_users.parquet').to_pylist()
    assert cohort != other_cohort
    assert any(int(row['user_id'][2:]) >= 5 for row in cohort)
    all_users = prepare_dataset(*paths, tmp_path / 'all', dataset_version='all-v1',
                               time_basis='source_local_naive', sample_users=0, seed=3)
    assert all_users['selected_user_count'] == 30


@pytest.mark.parametrize('basis,arrow_type,expected', [
    ('source_local_naive', pa.timestamp('us'), datetime(2020, 1, 1)),
    ('Asia/Shanghai', pa.timestamp('us', tz='UTC'), datetime(2019, 12, 31, 16,
                                                         tzinfo=timezone.utc)),
])
def test_prepare_timestamp_schema_and_manifest_hashes(tmp_path, basis, arrow_type, expected):
    paths = raw_files(tmp_path, [user()])
    manifest = prepare(tmp_path, paths, time_basis=basis)
    table = pq.read_table(tmp_path / 'prepared/interactions.parquet')
    assert table.schema.field('event_time').type == arrow_type
    assert table.to_pylist()[0]['event_time'] == expected
    assert table.to_pylist()[0]['event_time_raw'] == '2020-01-01'
    assert manifest['time_basis'] == basis
    assert manifest['temporal_dataset_ready'] is False
    assert manifest['dataset_version'] == 'fixture-v1'
    for filename, digest in manifest['output_hashes'].items():
        assert hashlib.sha256((tmp_path / 'prepared' / filename).read_bytes()).hexdigest() == digest
    for path in paths:
        assert manifest['raw_files'][path.name]['sha256'] == hashlib.sha256(
            path.read_bytes()).hexdigest()
    saved = json.loads((tmp_path / 'prepared/dataset_manifest.json').read_text(encoding='utf-8'))
    assert saved == manifest
    assert set(manifest['schemas']) == {'courses', 'interactions', 'rejects', 'cohort_users'}


@pytest.mark.parametrize('changes', [
    {'sample_users': -1}, {'sample_users': True}, {'sample_users': '5'},
    {'seed': None}, {'seed': True}, {'dataset_version': ''}, {'dataset_version': None},
])
def test_prepare_invalid_options_leave_no_output(tmp_path, changes):
    paths = raw_files(tmp_path, [user()])
    with pytest.raises(ValueError):
        prepare(tmp_path, paths, **changes)
    assert not (tmp_path / 'prepared').exists()


def test_prepare_requires_exact_positive_sample_count_before_publication(tmp_path):
    paths = raw_files(tmp_path, [user('U_eligible'), user(
        'U_ineligible', course_order=['C_1'], enroll_time=['2020-01-01'])])
    with pytest.raises(ValueError, match=r'sample_users=2.*eligible_user_count=1'):
        prepare(tmp_path, paths, sample_users=2)
    assert not (tmp_path / 'prepared').exists()
    assert not list(tmp_path.glob('.prepare-*'))
    manifest = prepare(tmp_path, paths, sample_users=0)
    assert manifest['selected_user_count'] == 1


def test_prepare_refuses_overwrite_and_conflicting_or_ambiguous_catalog(tmp_path):
    paths = raw_files(tmp_path, [user()])
    prepare(tmp_path, paths)
    with pytest.raises(ValueError, match='exist|tồn tại'):
        prepare(tmp_path, paths)
    for courses in [[{'id': 'C_1', 'name': 'A'}, {'id': 'C_1', 'name': 'B'}],
                    [{'id': 'C_1'}, {'id': 'C_01'}]]:
        paths = raw_files(tmp_path, [user()], courses)
        with pytest.raises(ValueError, match='catalog|Catalog'):
            prepare_dataset(*paths, tmp_path / 'bad', dataset_version='bad-v1',
                            time_basis='source_local_naive', sample_users=0, seed=3)
        assert not (tmp_path / 'bad').exists()


def test_prepare_quarantines_reader_errors_and_writes_empty_schemas(tmp_path):
    paths = raw_files(tmp_path, [])
    paths[1].write_text('broken\n[]\n' + json.dumps(user('U_short', course_order=[],
                                                     enroll_time=[])), encoding='utf-8')
    manifest = prepare(tmp_path, paths)
    assert manifest['error_counts'] == {'invalid_json': 1, 'invalid_record': 1,
                                        'insufficient_history': 1}
    assert manifest['selected_user_count'] == 0
    assert pq.read_table(tmp_path / 'prepared/interactions.parquet').schema.field(
        'event_time').type == pa.timestamp('us')
    assert pq.read_table(tmp_path / 'prepared/cohort_users.parquet').num_rows == 0


def test_prepare_sampling_reports_errors_from_unselected_users(tmp_path):
    paths = raw_files(tmp_path, [user(f'U_{i}') for i in range(10)] + [
        user('U_bad', enroll_time=[])])
    manifest = prepare(tmp_path, paths, sample_users=1)
    assert manifest['users_scanned'] == 11
    assert manifest['eligible_user_count'] == 10
    assert manifest['clean_interaction_count_before_sampling'] == 30
    assert manifest['error_counts']['array_length_mismatch'] == 1


def test_prepare_reservoir_ignores_ineligible_users_and_preserves_ties(tmp_path):
    eligible = [user(f'U_{i}') for i in range(15)]
    paths = raw_files(tmp_path, eligible)
    prepare(tmp_path, paths, sample_users=4)
    expected = pq.read_table(tmp_path / 'prepared/cohort_users.parquet').to_pylist()
    interleaved = []
    for index, row in enumerate(eligible):
        interleaved.extend([user(f'Short_{index}', course_order=[], enroll_time=[]), row])
    paths = raw_files(tmp_path, interleaved + [user(
        'U_tie', enroll_time=['2020-01-01', '2020-02-01', '2020-02-01'])])
    result = prepare_dataset(*paths, tmp_path / 'interleaved', dataset_version='fixture-v1',
                             time_basis='source_local_naive', sample_users=4, seed=20261016)
    assert result['eligible_user_count'] == 16
    assert result['error_counts']['insufficient_history'] == 15
    # Repeat without the extra tied user: irrelevant invalid histories must not alter sampling.
    paths = raw_files(tmp_path, interleaved)
    prepare_dataset(*paths, tmp_path / 'same-eligible', dataset_version='fixture-v1',
                    time_basis='source_local_naive', sample_users=4, seed=20261016)
    assert pq.read_table(tmp_path / 'same-eligible/cohort_users.parquet').to_pylist() == expected


def test_prepare_json_array_and_identical_catalog_duplicate(tmp_path):
    courses = [{'id': f'C_{i}'} for i in range(1, 4)]
    paths = raw_files(tmp_path, [user()], courses)
    paths[0].write_text(json.dumps(courses + [courses[0]]), encoding='utf-8')
    paths[1].write_text(json.dumps([user()]), encoding='utf-8')
    manifest = prepare(tmp_path, paths)
    assert manifest['selected_user_count'] == 1
    assert manifest['row_counts']['courses'] == 3
    assert manifest['error_counts']['duplicate_course_id'] == 1


def test_prepare_malformed_array_never_publishes_partial_dataset(tmp_path):
    paths = raw_files(tmp_path, [user()])
    paths[1].write_text('[{"id":"U_1"}', encoding='utf-8')
    with pytest.raises(ValueError, match='JSON array'):
        prepare(tmp_path, paths)
    assert not (tmp_path / 'prepared').exists()
    assert not list(tmp_path.glob('.prepare-*'))


@pytest.mark.parametrize('basis,stamp,reason', [
    ('source_local_naive', '2020-01-01T00:00:00Z', 'timestamp_awareness_mismatch'),
    ('America/New_York', '2020-03-08T02:30:00', 'nonexistent_local_time'),
    ('America/New_York', '2020-11-01T01:30:00', 'ambiguous_local_time'),
])
def test_prepare_quarantines_unresolvable_time_without_guessing(tmp_path, basis, stamp, reason):
    paths = raw_files(tmp_path, [user(enroll_time=[stamp, '2020-02-01', '2020-03-01'])])
    manifest = prepare(tmp_path, paths, time_basis=basis)
    assert manifest['error_counts'][reason] == 1
    assert manifest['selected_user_count'] == 0


@pytest.mark.parametrize('stamp', ['0001-01-01', '0001-01-01T00:00:00+08:00'])
def test_prepare_quarantines_timestamp_that_overflows_utc_conversion(tmp_path, stamp):
    paths = raw_files(tmp_path, [user(enroll_time=[stamp, '2020-02-01', '2020-03-01'])])
    manifest = prepare(tmp_path, paths, time_basis='Asia/Shanghai')
    assert manifest['error_counts']['invalid_timestamp'] == 1
    assert manifest['selected_user_count'] == 0
