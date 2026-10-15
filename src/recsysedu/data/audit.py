"""Inspect raw data without converting unresolved source timezones."""

import json
import re
import time
from collections import Counter
from datetime import datetime, timezone
from itertools import islice
from pathlib import Path

import ijson


def iter_records(path: Path, issues: Counter | None = None):
    """Stream JSON Lines or a JSON array; optionally count invalid line records."""
    with Path(path).open('rb') as stream:
        prefix = stream.peek(4096).removeprefix(b'\xef\xbb\xbf').lstrip()
        if prefix.startswith(b'['):
            if stream.peek(3).startswith(b'\xef\xbb\xbf'):
                stream.read(3)
            records = ijson.items(stream, 'item', use_float=True)
        else:
            def lines():
                for line_number, line in enumerate(stream, 1):
                    if not line.strip():
                        continue
                    try:
                        yield json.loads(line.decode('utf-8-sig'))
                    except (ValueError, UnicodeError) as exc:
                        if issues is None:
                            raise ValueError(f'JSON lỗi tại {path.name}:{line_number}') from exc
                        issues['invalid_json'] += 1
            records = lines()
        try:
            for record in records:
                if not isinstance(record, dict):
                    if issues is None:
                        raise ValueError(f'Bản ghi không phải object: {path.name}')
                    issues['invalid_record'] += 1
                    continue
                yield record
        except ijson.JSONError as exc:
            raise ValueError(f'JSON array lỗi hoặc tải thiếu: {path.name}') from exc


def audit_dataset(course_path: Path, user_path: Path, *, max_users: int = 0) -> dict:
    """Aggregate quality counts. No user names or IDs are written to the report.

    A parseable naive datetime is not a confirmed timezone or a released split.
    """
    if max_users < 0:
        raise ValueError('max_users phải từ 0; 0 là quét toàn bộ')
    started = time.monotonic()
    errors = Counter()
    courses = {}
    course_rows = 0
    field_types = Counter()
    fields_present = 0
    for course in iter_records(course_path, errors):
        course_rows += 1
        course_id = course.get('id')
        if not isinstance(course_id, str) or not course_id:
            errors['invalid_course_id'] += 1
            continue
        fingerprint = json.dumps(course, ensure_ascii=False, sort_keys=True)
        if course_id in courses:
            errors['duplicate_course_id'] += 1
            if courses[course_id] != fingerprint:
                errors['conflicting_course_id'] += 1
        courses[course_id] = fingerprint
        field = course.get('field')
        field_types[type(field).__name__] += 1
        fields_present += bool(field)
    numeric_catalog = {}
    for course_id in courses:
        if re.fullmatch(r'C_[0-9]+', course_id):
            number = int(course_id[2:])
            if number in numeric_catalog and numeric_catalog[number] != course_id:
                raise ValueError('Catalog có mã số khóa học nhập nhằng')
            numeric_catalog[number] = course_id
    resolution = Counter()
    user_ids = set()
    users_scanned = 0
    valid_enrollments = 0
    known_unique_pairs = 0
    eligible = 0
    strict = 0
    raw_slots = 0
    history_histogram = Counter()
    awareness = Counter()
    timestamp_ranges = {}
    rows = iter_records(user_path, errors)
    for user in islice(rows, max_users or None):
        users_scanned += 1
        user_id = user.get('id')
        if not isinstance(user_id, str) or not user_id:
            errors['invalid_user_id'] += 1
            continue
        if user_id in user_ids:
            errors['duplicate_user_id'] += 1
            continue
        user_ids.add(user_id)
        order, times = user.get('course_order'), user.get('enroll_time')
        if not isinstance(order, list) or not isinstance(times, list):
            errors['invalid_history_type'] += 1
            continue
        raw_slots += len(order)
        if len(order) != len(times):
            errors['array_length_mismatch'] += 1
            continue
        history = {}
        user_awareness = set()
        for raw_course_id, stamp in zip(order, times):
            course_id = None
            if isinstance(raw_course_id, str) and raw_course_id in courses:
                course_id = raw_course_id
                resolution['exact_string_match'] += 1
            elif type(raw_course_id) is int and raw_course_id in numeric_catalog:
                course_id = numeric_catalog[raw_course_id]
                resolution['numeric_catalog_match'] += 1
            if course_id is None:
                errors['unknown_course_id'] += 1
            try:
                if not isinstance(stamp, str):
                    raise ValueError('Timestamp không phải string')
                parsed = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                errors['invalid_timestamp'] += 1
                continue
            kind = 'with_offset' if parsed.tzinfo is not None else 'naive'
            awareness[kind] += 1
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone(timezone.utc)
            bounds = timestamp_ranges.setdefault(kind, [parsed, parsed])
            bounds[0], bounds[1] = min(bounds[0], parsed), max(bounds[1], parsed)
            if course_id is None:
                continue
            user_awareness.add(kind)
            valid_enrollments += 1
            if course_id in history:
                errors['duplicate_interaction'] += 1
                old = history[course_id]
                if (old.tzinfo is None) == (parsed.tzinfo is None):
                    history[course_id] = min(old, parsed)
            else:
                history[course_id] = parsed
        known_unique_pairs += len(history)
        history_histogram[len(history)] += 1
        if len(history) >= 3:
            eligible += 1
            if len(user_awareness) > 1:
                errors['mixed_timestamp_awareness'] += 1
            else:
                stamps = sorted(history.values())
                if stamps[-3] < stamps[-2] < stamps[-1]:
                    strict += 1
                else:
                    errors['holdout_timestamp_tie'] += 1
    return {
        'schema_version': 1,
        'scope': 'limited' if max_users else 'full',
        'max_users': max_users,
        'course_records': course_rows,
        'unique_course_ids': len(courses),
        'courses_with_fields_records': fields_present,
        'course_field_types': dict(field_types),
        'users_scanned': users_scanned,
        'unique_user_ids': len(user_ids),
        'raw_enrollment_slots': raw_slots,
        'valid_known_enrollments_before_dedup': valid_enrollments,
        'known_unique_pairs': known_unique_pairs,
        'course_id_resolution': dict(resolution),
        'course_id_rule': 'exact string or integer matched to an existing C_<digits> catalog ID',
        'users_with_3_known_unique_courses': eligible,
        'users_with_strict_holdout_boundaries': strict,
        'clean_history_length_histogram': dict(sorted(history_histogram.items())),
        'errors': dict(errors),
        'timestamp_awareness': dict(awareness),
        'timestamp_ranges': {
            kind: [value.isoformat() for value in bounds]
            for kind, bounds in timestamp_ranges.items()
        },
        'timezone_status': ('unresolved' if awareness['naive'] else
                            'explicit_offsets' if awareness['with_offset'] else 'no_valid_times'),
        'temporal_dataset_ready': False,
        'elapsed_seconds': round(time.monotonic() - started, 2),
        'note': 'Chỉ audit raw; chưa chuẩn hóa, phát hành split hoặc huấn luyện.',
    }
