import json

from recsysedu.data.audit import audit_dataset, iter_records


def test_reader_handles_json_lines_and_arrays(tmp_path):
    rows = [{'id': 'C_1'}, {'id': 'C_2'}]
    for filename, text in [('lines.json', '\n'.join(map(json.dumps, rows))),
                           ('array.json', json.dumps(rows))]:
        path = tmp_path / filename
        path.write_text(text, encoding='utf-8')
        assert list(iter_records(path)) == rows


def test_audit_counts_errors_without_inventing_timezone(tmp_path):
    courses = [{'id': f'C_{i}', 'field': ['CS']} for i in range(1, 5)]
    users = [
        {'id': 'U_valid', 'course_order': ['C_1', 'C_2', 'C_3'],
         'enroll_time': ['2020-01-01 00:00:00', '2020-02-01 00:00:00', '2020-03-01 00:00:00']},
        {'id': 'U_mismatch', 'course_order': ['C_1', 'C_2'], 'enroll_time': []},
        {'id': 'U_errors', 'course_order': ['C_1', 'C_1', 'C_missing', 'C_4'],
         'enroll_time': ['2020-01-01', '2020-02-01', '2020-03-01', 'bad-time']},
        {'id': 'U_tie', 'course_order': ['C_1', 'C_2', 'C_3'],
         'enroll_time': ['2020-01-01', '2020-02-01', '2020-02-01']},
    ]
    for name, rows in [('course.json', courses), ('user.json', users)]:
        (tmp_path / name).write_text('\n'.join(map(json.dumps, rows)), encoding='utf-8')
    report = audit_dataset(tmp_path / 'course.json', tmp_path / 'user.json')
    assert report['users_scanned'] == 4
    assert report['errors']['array_length_mismatch'] == 1
    assert report['errors']['unknown_course_id'] == 1
    assert report['errors']['invalid_timestamp'] == 1
    assert report['errors']['duplicate_interaction'] == 1
    assert report['users_with_3_known_unique_courses'] == 2
    assert report['users_with_strict_holdout_boundaries'] == 1
    assert report['timezone_status'] == 'unresolved'
    assert report['temporal_dataset_ready'] is False
    assert 'U_valid' not in json.dumps(report)


def test_limit_is_reported_as_partial_audit(tmp_path):
    (tmp_path / 'course.json').write_text('{"id":"C_1","field":[]}', encoding='utf-8')
    (tmp_path / 'user.json').write_text(
        '\n'.join(json.dumps({'id': f'U_{i}', 'course_order': [], 'enroll_time': []})
                  for i in range(3)), encoding='utf-8')
    report = audit_dataset(tmp_path / 'course.json', tmp_path / 'user.json', max_users=1)
    assert report['users_scanned'] == 1
    assert report['scope'] == 'limited'
    assert report['timezone_status'] == 'no_valid_times'


def test_numeric_enrollments_join_only_existing_catalog_ids(tmp_path):
    (tmp_path / 'course.json').write_text(
        '[{"id":"C_1","field":[]},{"id":"C_2","field":[]}]', encoding='utf-8')
    user = {'id': 'U_1', 'course_order': [1, 2, 999, True],
            'enroll_time': ['2020-01-01'] * 4}
    (tmp_path / 'user.json').write_text(json.dumps(user), encoding='utf-8')
    report = audit_dataset(tmp_path / 'course.json', tmp_path / 'user.json')
    assert report['known_unique_pairs'] == 2
    assert report['course_id_resolution']['numeric_catalog_match'] == 2
    assert report['errors']['unknown_course_id'] == 2
    assert report['timestamp_awareness']['naive'] == 4
