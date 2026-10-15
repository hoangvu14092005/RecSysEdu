"""Stream raw records into an immutable, explicitly timed Parquet dataset."""

import hashlib
import json
import random
import re
import tempfile
from collections import Counter
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from recsysedu.data.audit import iter_records


class _TimeError(ValueError):
    pass


def _time_zone(time_basis):
    if time_basis == 'source_local_naive':
        return None
    if not isinstance(time_basis, str) or not time_basis:
        raise ValueError('time_basis phải là source_local_naive hoặc IANA timezone key')
    try:
        return ZoneInfo(time_basis)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(f'time_basis không hợp lệ: {time_basis}') from exc


def _event_time(raw, zone):
    try:
        if not isinstance(raw, str):
            raise ValueError()
        value = datetime.fromisoformat(raw.replace('Z', '+00:00'))
    except ValueError as exc:
        raise _TimeError('invalid_timestamp') from exc
    if zone is None:
        if value.tzinfo is not None:
            raise _TimeError('timestamp_awareness_mismatch')
        return value
    try:
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc)
        # A round trip catches DST gaps; distinct valid instants indicate a fold.
        candidates = set()
        for fold in (0, 1):
            utc = value.replace(tzinfo=zone, fold=fold).astimezone(timezone.utc)
            if utc.astimezone(zone).replace(tzinfo=None) == value:
                candidates.add(utc)
    except OverflowError as exc:
        raise _TimeError('invalid_timestamp') from exc
    if not candidates:
        raise _TimeError('nonexistent_local_time')
    if len(candidates) != 1:
        raise _TimeError('ambiguous_local_time')
    return candidates.pop()


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


class _ParquetSink:
    """Bound output buffering independently of raw dataset size."""

    def __init__(self, path, schema):
        import pyarrow.parquet as pq

        self.schema = schema
        self.writer = pq.ParquetWriter(path, schema, compression='zstd')
        self.buffer = []
        self.count = 0

    def add(self, row):
        self.buffer.append(row)
        self.count += 1
        if len(self.buffer) >= 4096:
            self.flush()

    def flush(self):
        import pyarrow as pa

        if self.buffer:
            self.writer.write_table(pa.Table.from_pylist(self.buffer, schema=self.schema))
            self.buffer.clear()

    def close(self):
        try:
            self.flush()
        finally:
            self.writer.close()


def _schemas(zone):
    import pyarrow as pa

    return {
        'courses': pa.schema([
            ('course_id', pa.string()), ('name', pa.string()), ('about', pa.string()),
            ('fields', pa.list_(pa.string())), ('prerequisite_text', pa.string()),
        ]),
        'interactions': pa.schema([
            ('user_id', pa.string()), ('course_id', pa.string()),
            ('event_time', pa.timestamp('us', tz='UTC' if zone else None)),
            ('event_time_raw', pa.string()), ('interaction', pa.int8()),
            ('source_record', pa.string()),
        ]),
        'rejects': pa.schema([
            ('reason_code', pa.string()), ('user_id', pa.string()),
            ('raw_course_id', pa.string()), ('event_time_raw', pa.string()),
            ('source_record', pa.string()), ('count', pa.int64()),
        ]),
        'cohort_users': pa.schema([('user_id', pa.string()), ('history_length', pa.int64())]),
    }


def _text(value):
    if value is None:
        return ''
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True)


def _catalog(path, courses_sink, reject, reader_errors):
    catalog = {}
    for index, course in enumerate(iter_records(path, reader_errors), 1):
        source = f'{path.name}:record:{index}'
        course_id = course.get('id')
        if not isinstance(course_id, str) or not course_id.strip():
            reject('invalid_course_id', source)
            continue
        fingerprint = json.dumps(course, ensure_ascii=False, sort_keys=True)
        if course_id in catalog:
            if catalog[course_id] != fingerprint:
                raise ValueError(f'Conflicting catalog course ID: {course_id}')
            reject('duplicate_course_id', source)
            continue
        catalog[course_id] = fingerprint
        fields = course.get('field') or []
        fields = fields if isinstance(fields, list) else [fields]
        courses_sink.add(dict(course_id=course_id, name=_text(course.get('name')),
                              about=_text(course.get('about')),
                              fields=sorted({_text(value) for value in fields if value}),
                              prerequisite_text=_text(course.get('prerequisites'))))
    numeric = {}
    for course_id in catalog:
        if re.fullmatch(r'C_[0-9]+', course_id):
            number = int(course_id[2:])
            if number in numeric and numeric[number] != course_id:
                raise ValueError('Catalog có mã số khóa học nhập nhằng')
            numeric[number] = course_id
    return catalog, numeric


def _clean_users(path, catalog, numeric, zone, reject, reader_errors, stats):
    seen = set()
    for index, user in enumerate(iter_records(path, reader_errors), 1):
        stats['users_scanned'] += 1
        source = f'{path.name}:record:{index}'
        user_id = user.get('id')
        if not isinstance(user_id, str) or not user_id.strip():
            reject('invalid_user_id', source)
            continue
        if user_id in seen:
            reject('duplicate_user_id', source, user_id)
            continue
        seen.add(user_id)
        order, times = user.get('course_order'), user.get('enroll_time')
        if not isinstance(order, list) or not isinstance(times, list):
            reject('invalid_history_type', source, user_id)
            continue
        stats['raw_enrollment_slots'] += len(order)
        if len(order) != len(times):
            reject('array_length_mismatch', source, user_id)
            continue
        history = {}
        for slot, (raw_id, stamp) in enumerate(zip(order, times)):
            event_source = f'{source}:slot:{slot}'
            course_id = (raw_id if isinstance(raw_id, str) and raw_id in catalog
                         else numeric.get(raw_id) if type(raw_id) is int else None)
            if course_id is None:
                reject('unknown_course_id', event_source, user_id, raw_id, stamp)
            try:
                parsed = _event_time(stamp, zone)
            except _TimeError as exc:
                reject(str(exc), event_source, user_id, raw_id, stamp)
                continue
            if course_id is None:
                continue
            stats['valid_enrollments_before_dedup'] += 1
            row = dict(user_id=user_id, course_id=course_id, event_time=parsed,
                       event_time_raw=stamp, interaction=1, source_record=event_source)
            if course_id in history:
                old = history[course_id]
                loser = old if parsed < old['event_time'] else row
                reject('duplicate_interaction', loser['source_record'], user_id,
                       course_id, loser['event_time_raw'])
                if parsed < old['event_time']:
                    history[course_id] = row
            else:
                history[course_id] = row
        stats['clean_interaction_count_before_sampling'] += len(history)
        if len(history) < 3:
            reject('insufficient_history', source, user_id)
            continue
        stats['eligible_user_count'] += 1
        yield index, user_id, sorted(history.values(), key=lambda row: (
            row['event_time'], row['course_id']))


def _validate_output(stage):
    """DuckDB reads only finished Parquet; it never transforms raw data."""
    import duckdb

    with duckdb.connect() as connection:
        for name in ('courses', 'interactions', 'cohort_users'):
            connection.read_parquet(str(stage / f'{name}.parquet')).create_view(name)
        duplicates = connection.sql('''
            SELECT COUNT(*) FROM (
                SELECT user_id, course_id FROM interactions GROUP BY ALL HAVING COUNT(*) > 1
            )
        ''').fetchone()[0]
        orphans = connection.sql('''
            SELECT COUNT(*) FROM interactions i ANTI JOIN courses c USING (course_id)
        ''').fetchone()[0]
        invalid_cohort = connection.sql('''
            SELECT COUNT(*) FROM (
                SELECT u.user_id FROM cohort_users u LEFT JOIN interactions i USING (user_id)
                GROUP BY u.user_id, u.history_length
                HAVING COUNT(i.course_id) != u.history_length OR u.history_length < 3
            )
        ''').fetchone()[0]
        if duplicates or orphans or invalid_cohort:
            raise ValueError('Parquet validation failed: duplicate, orphan or invalid cohort')


def prepare_dataset(course_path, user_path, output_dir, *, dataset_version, time_basis,
                    sample_users, seed) -> dict:
    """Publish selected users with >=3 cleaned courses, without creating a split.

    The reservoir is bounded by sample_users. Zero streams every eligible user.
    Output users retain source encounter order; each history is time/ID sorted.
    """
    zone = _time_zone(time_basis)
    if not isinstance(dataset_version, str) or not dataset_version.strip():
        raise ValueError('dataset_version phải là string không rỗng')
    if type(sample_users) is not int or sample_users < 0:
        raise ValueError('sample_users phải là integer từ 0; 0 là toàn bộ')
    if type(seed) is not int:
        raise ValueError('seed phải là integer')
    course_path, user_path, output_dir = map(Path, (course_path, user_path, output_dir))
    if output_dir.exists():
        raise ValueError(f'Output đã tồn tại: {output_dir}; dùng dataset version mới')
    raw_files = {path.name: dict(path=str(path.resolve()), bytes=path.stat().st_size,
                                sha256=_sha256(path)) for path in (course_path, user_path)}
    schemas = _schemas(zone)
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.prepare-', dir=output_dir.parent) as temporary:
        stage = Path(temporary) / 'dataset'
        stage.mkdir()
        errors, stats = Counter(), Counter()
        with ExitStack() as stack:
            sinks = {}
            for name, schema in schemas.items():
                sink = _ParquetSink(stage / f'{name}.parquet', schema)
                stack.callback(sink.close)
                sinks[name] = sink

            def reject(reason, source, user_id=None, raw_id=None, stamp=None, count=1):
                errors[reason] += count
                sinks['rejects'].add(dict(
                    reason_code=reason, user_id=user_id,
                    raw_course_id=None if raw_id is None else json.dumps(raw_id, ensure_ascii=False),
                    event_time_raw=None if stamp is None else _text(stamp),
                    source_record=source, count=count))

            def emit_reader_errors(path, issues):
                # iter_records counts malformed lines/objects without exposing their offsets.
                for reason, count in sorted(issues.items()):
                    reject(reason, path.name, count=count)

            reader_errors = Counter()
            catalog, numeric = _catalog(course_path, sinks['courses'], reject, reader_errors)
            emit_reader_errors(course_path, reader_errors)
            reader_errors = Counter()
            randomizer, reservoir = random.Random(seed), []

            def write_user(candidate):
                _, user_id, history = candidate
                sinks['cohort_users'].add(dict(user_id=user_id, history_length=len(history)))
                for row in history:
                    sinks['interactions'].add(row)

            for candidate in _clean_users(user_path, catalog, numeric, zone, reject,
                                          reader_errors, stats):
                if sample_users == 0:
                    write_user(candidate)
                elif len(reservoir) < sample_users:
                    reservoir.append(candidate)
                else:
                    slot = randomizer.randrange(stats['eligible_user_count'])
                    if slot < sample_users:
                        reservoir[slot] = candidate
            emit_reader_errors(user_path, reader_errors)
            for candidate in sorted(reservoir, key=lambda candidate: candidate[0]):
                write_user(candidate)
        _validate_output(stage)
        for path in (course_path, user_path):
            if _sha256(path) != raw_files[path.name]['sha256']:
                raise ValueError(f'Raw input changed during prepare: {path.name}')
        manifest = dict(
            schema_version=1, dataset_version=dataset_version, time_basis=time_basis, seed=seed,
            requested_user_count=sample_users,
            selected_user_count=sinks['cohort_users'].count,
            users_scanned=stats['users_scanned'], eligible_user_count=stats['eligible_user_count'],
            raw_enrollment_slots=stats['raw_enrollment_slots'],
            valid_enrollments_before_dedup=stats['valid_enrollments_before_dedup'],
            clean_interaction_count_before_sampling=stats['clean_interaction_count_before_sampling'],
            raw_files=raw_files, row_counts={name: sink.count for name, sink in sinks.items()},
            error_counts=dict(sorted(errors.items())),
            schemas={name: [dict(name=field.name, type=str(field.type), nullable=field.nullable)
                            for field in schema] for name, schema in schemas.items()},
            output_hashes={f'{name}.parquet': _sha256(stage / f'{name}.parquet') for name in schemas},
            course_id_rule='exact string or integer matched to an existing C_<digits> catalog ID',
            eligibility_rule='at least 3 distinct valid catalog courses after cleaning',
            sampling_rule='seeded reservoir over eligible users in source encounter order; 0=all',
            output_order='source user encounter order; event_time, course_id within each user',
            fields_source='course.json:field', temporal_dataset_ready=False,
        )
        (stage / 'dataset_manifest.json').write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        stage.rename(output_dir)
    return manifest
