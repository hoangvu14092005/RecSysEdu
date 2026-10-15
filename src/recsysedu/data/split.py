"""Deterministic leave-last-two-out split of a prepared course dataset."""

import hashlib
import json
import tempfile
from collections import defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


PROTOCOL_ID = 'leave_last_two_out_v1'
OUTPUT_NAMES = ('train', 'valid', 'test', 'valid_cohort', 'test_cohort',
                'candidate_universe')


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _dataset_identity(interactions_path, courses_path):
    """Check the exact prepared files before trusting their manifest as identity."""
    if interactions_path.parent != courses_path.parent:
        raise ValueError('interactions và courses phải thuộc cùng prepared dataset')
    manifest_path = interactions_path.parent / 'dataset_manifest.json'
    try:
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f'dataset manifest không đọc được: {manifest_path}') from exc
    if not isinstance(manifest, dict) or not isinstance(manifest.get('output_hashes'), dict):
        raise ValueError('dataset manifest thiếu output_hashes')
    if not isinstance(manifest.get('dataset_version'), str) or not manifest['dataset_version']:
        raise ValueError('dataset manifest thiếu dataset_version')
    for name, path in (('interactions.parquet', interactions_path),
                       ('courses.parquet', courses_path)):
        expected = manifest['output_hashes'].get(name)
        if not isinstance(expected, str) or len(expected) != 64:
            raise ValueError(f'dataset manifest thiếu SHA-256 của {name}')
        if _sha256(path) != expected:
            raise ValueError(f'dataset manifest không khớp {name}')
    return manifest, _sha256(manifest_path)


def _validated_time_basis(manifest):
    basis = manifest.get('time_basis')
    if not isinstance(basis, str) or not basis.strip():
        raise ValueError('dataset manifest thiếu time_basis hợp lệ')
    if basis != 'source_local_naive':
        try:
            ZoneInfo(basis)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f'dataset manifest time_basis không phải IANA key: {basis}') from exc
    return basis


def build_temporal_split(interactions_path, courses_path, output_dir, *, split_version,
                         seed) -> dict:
    """Publish train, held-out targets and separate warm validation/test cohorts.

    A user whose train/valid or valid/test boundary has equal timestamps is
    quarantined entirely. Course IDs never break a time tie for split membership.
    """
    import pyarrow as pa
    import pyarrow.parquet as pq

    if not isinstance(split_version, str) or not split_version.strip():
        raise ValueError('split_version phải là string không rỗng')
    if type(seed) is not int:
        raise ValueError('seed phải là integer')
    interactions_path, courses_path, output_dir = map(
        Path, (interactions_path, courses_path, output_dir))
    if output_dir.exists():
        raise ValueError(f'Output đã tồn tại: {output_dir}; dùng split version mới')
    dataset_manifest, dataset_hash = _dataset_identity(interactions_path, courses_path)
    time_basis = _validated_time_basis(dataset_manifest)
    input_hashes = {path.name: _sha256(path) for path in (interactions_path, courses_path)}
    try:
        interactions = pq.read_table(interactions_path)
        catalog = pq.read_table(courses_path, columns=['course_id'])
    except (OSError, pa.ArrowException) as exc:
        raise ValueError(f'Prepared Parquet không đọc được: {exc}') from exc
    required = {'user_id', 'course_id', 'event_time'}
    if not required <= set(interactions.column_names):
        raise ValueError('interactions.parquet thiếu user_id/course_id/event_time')
    event_type = interactions.schema.field('event_time').type
    expected_timezone = None if time_basis == 'source_local_naive' else 'UTC'
    if not pa.types.is_timestamp(event_type) or event_type.tz != expected_timezone:
        raise ValueError(
            f'dataset manifest time_basis={time_basis} không khớp event_time Arrow schema')
    catalog_ids = set(catalog.column('course_id').to_pylist())
    histories = defaultdict(list)
    for row in interactions.to_pylist():
        if (not row['user_id'] or not row['course_id'] or row['course_id'] not in catalog_ids
                or row['event_time'] is None):
            raise ValueError('Prepared interaction có user/course/time không hợp lệ')
        histories[row['user_id']].append(row)

    train, valid, test = [], [], []
    tie_users = tie_interactions = 0
    for user_id in sorted(histories):
        history = sorted(histories[user_id], key=lambda row: row['event_time'])
        if len(history) < 3 or len({row['course_id'] for row in history}) != len(history):
            raise ValueError(f'Prepared history không hợp lệ: {user_id}')
        if not (history[-3]['event_time'] < history[-2]['event_time']
                < history[-1]['event_time']):
            tie_users += 1
            tie_interactions += len(history)
            continue
        train.extend(history[:-2])
        valid.append(history[-2])
        test.append(history[-1])

    universe = sorted({row['course_id'] for row in train})
    universe_set = set(universe)
    target_schema = interactions.schema.append(pa.field('target_in_train', pa.bool_()))
    valid = [row | {'target_in_train': row['course_id'] in universe_set} for row in valid]
    test = [row | {'target_in_train': row['course_id'] in universe_set} for row in test]
    valid_cohort = [row for row in valid if row['target_in_train']]
    test_cohort = [row for row in test if row['target_in_train']]
    outputs = {
        'train': (train, interactions.schema),
        'valid': (valid, target_schema),
        'test': (test, target_schema),
        'valid_cohort': (valid_cohort, target_schema),
        'test_cohort': (test_cohort, target_schema),
        'candidate_universe': ([{'course_id': item} for item in universe],
                               pa.schema([('course_id', pa.string())])),
    }

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.split-', dir=output_dir.parent) as temporary:
        stage = Path(temporary) / 'split'
        stage.mkdir()
        for name in OUTPUT_NAMES:
            rows, schema = outputs[name]
            pq.write_table(pa.Table.from_pylist(rows, schema=schema), stage / f'{name}.parquet')
        for path in (interactions_path, courses_path):
            if _sha256(path) != input_hashes[path.name]:
                raise ValueError(f'Prepared input changed during split: {path.name}')
        manifest = dict(
            schema_version=1, split_version=split_version, protocol_id=PROTOCOL_ID,
            seed=seed, dataset_version=dataset_manifest['dataset_version'],
            dataset_hash=dataset_hash, input_hashes=input_hashes,
            time_basis=time_basis,
            selected_user_count=len(histories), split_user_count=len(valid),
            boundary_tie_user_count=tie_users,
            boundary_tie_interaction_count=tie_interactions,
            cold_target_counts={'valid': len(valid) - len(valid_cohort),
                                'test': len(test) - len(test_cohort)},
            warm_cohort_sizes={'valid': len(valid_cohort), 'test': len(test_cohort)},
            row_counts={name: len(outputs[name][0]) for name in OUTPUT_NAMES},
            output_hashes={f'{name}.parquet': _sha256(stage / f'{name}.parquet')
                           for name in OUTPUT_NAMES},
            boundary_rule='max(train time) < valid time < test time; ties exclude user',
            candidate_rule='sorted distinct course IDs from train only',
        )
        manifest['split_hash'] = hashlib.sha256(json.dumps(
            manifest, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
        ).hexdigest()
        (stage / 'split_manifest.json').write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        stage.rename(output_dir)
    return manifest
