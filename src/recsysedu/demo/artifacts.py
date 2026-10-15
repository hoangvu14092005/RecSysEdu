"""Validate the shared snapshot before any UI attempts to display it."""

import json
import math
from pathlib import Path

MODEL_LABELS = {
    'popularity': 'MostPopular', 'content': 'Content-based',
    'bpr': 'BPR', 'hybrid': 'Hybrid', 'hybrid_prerequisite': 'Hybrid + tiền đề',
}
PREREQUISITE_LABELS = {
    'missing_exposure': 'Có tiền đề chưa có dấu hiệu tiếp xúc',
    'no_missing_exposure': 'Chưa phát hiện tiền đề cần ôn trong dữ liệu hiện có',
    'no_observed_prerequisite': 'Chưa thấy thông tin tiền đề trong graph',
    'unknown': 'Chưa đủ dữ liệu tiền đề',
}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _index(rows, key):
    _require(isinstance(rows, list), f'{key}: cần array')
    result = {}
    for row in rows:
        _require(isinstance(row, dict), f'{key}: record phải là object')
        value = row.get(key)
        _require(isinstance(value, str) and bool(value), f'{key}: cần string không rỗng')
        _require(value not in result, f'{key} trùng: {value}')
        result[value] = row
    return result


def _number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def validate_bundle(bundle: dict) -> dict:
    """Schema v1: references, seen mask, ranks, scores and run identity must agree."""
    _require(isinstance(bundle, dict), 'Bundle phải là object')
    meta = bundle.get('meta', {})
    _require(isinstance(meta, dict), 'meta phải là object')
    _require(type(meta.get('schema_version')) is int and meta['schema_version'] == 1,
             'schema_version chưa hỗ trợ')
    _require(meta.get('data_mode') in ('synthetic', 'real'), 'data_mode không hợp lệ')
    _require(meta.get('history_mode') in ('offline', 'demo'), 'history_mode không hợp lệ')
    for key in ('snapshot_id', 'dataset_version', 'dataset_hash', 'split_hash',
                'protocol_id', 'generated_at'):
        _require(isinstance(meta.get(key), str) and bool(meta[key]), f'meta thiếu {key}')
    courses = _index(bundle.get('courses'), 'course_id')
    users = _index(bundle.get('users'), 'user_id')
    runs = _index(bundle.get('runs'), 'run_id')
    for course in courses.values():
        _require(isinstance(course.get('name'), str), 'Tên khóa phải là string')
        _require(isinstance(course.get('fields'), list)
                 and all(isinstance(x, str) for x in course['fields']), 'fields không hợp lệ')
    for user in users.values():
        _require(isinstance(user.get('display_name'), str), 'Hồ sơ thiếu bí danh')
        for field in ('observed_course_ids', 'profile_course_ids'):
            values = user.get(field)
            _require(isinstance(values, list)
                     and all(isinstance(x, str) and x in courses for x in values),
                     f'{field} có ID không tồn tại')
            _require(len(values) == len(set(values)), f'{field} có ID trùng')
        _require(set(user['profile_course_ids']) <= set(user['observed_course_ids']),
                 'Profile chứa khóa chưa quan sát')
    for run in runs.values():
        _require(isinstance(run.get('model_id'), str) and run['model_id'] in MODEL_LABELS,
                 'model_id chưa hỗ trợ')
        for key in ('dataset_hash', 'split_hash', 'protocol_id'):
            _require(run.get(key) == meta[key], f'Run không khớp {key}')
        _require(run.get('evaluation_split') in ('valid', 'test', 'demo'), 'Split không hợp lệ')
        for key in ('cohort', 'candidate_policy', 'seen_policy', 'config_hash'):
            _require(isinstance(run.get(key), str) and bool(run[key]), f'Run thiếu {key}')
        _require(type(run.get('cohort_size')) is int and run['cohort_size'] >= 0,
                 'cohort_size không hợp lệ')
        _require('seed' in run and (run['seed'] is None or type(run['seed']) is int),
                 'seed không hợp lệ hoặc thiếu; dùng null khi không có seed')
        status, metrics = run.get('metric_status'), run.get('metrics')
        _require(status in ('measured', 'not_available'), 'metric_status không hợp lệ')
        if status == 'not_available':
            _require(metrics is None, 'Metric chưa chạy phải là null')
        else:
            _require(isinstance(metrics, dict) and bool(metrics)
                     and all(_number(value) for value in metrics.values()), 'Metric không hữu hạn')
        if meta['history_mode'] == 'demo' or run['evaluation_split'] == 'demo':
            _require(status == 'not_available', 'Demo live không có metric offline')
    recommendations = bundle.get('recommendations')
    _require(isinstance(recommendations, list), 'recommendations phải là array')
    keys = set()
    for rec in recommendations:
        _require(isinstance(rec, dict), 'Recommendation phải là object')
        user_id, run_id = rec.get('user_id'), rec.get('run_id')
        _require(isinstance(user_id, str) and user_id in users, 'User recommendation không tồn tại')
        _require(isinstance(run_id, str) and run_id in runs, 'Run recommendation không tồn tại')
        model_id = rec.get('model_id')
        _require(model_id == runs[run_id]['model_id'], 'Recommendation khác model của run')
        key = (user_id, model_id)
        _require(key not in keys, 'Danh sách recommendation trùng')
        keys.add(key)
        _require(isinstance(rec.get('fallback_status'), str), 'Thiếu fallback_status')
        items = rec.get('items')
        _require(isinstance(items, list) and len(items) <= 10, 'items phải là Top-10 tối đa')
        seen = set(users[user_id]['observed_course_ids'])
        returned = set()
        for rank, item in enumerate(items, 1):
            _require(isinstance(item, dict), 'Item phải là object')
            course_id = item.get('course_id')
            _require(isinstance(course_id, str) and course_id in courses, 'Course không tồn tại')
            _require(course_id not in seen and course_id not in returned, 'Course đã xem hoặc trùng')
            returned.add(course_id)
            _require(type(item.get('rank')) is int and item['rank'] == rank, 'Rank không liên tục')
            _require(_number(item.get('score')), 'Score không hữu hạn')
            _require(isinstance(item.get('prerequisite_status'), str)
                     and item['prerequisite_status'] in PREREQUISITE_LABELS, 'Trạng thái tiền đề lạ')
            for field in ('reason_codes', 'evidence'):
                _require(isinstance(item.get(field), list)
                         and all(isinstance(x, str) for x in item[field]), f'{field} phải là array')
    _require(isinstance(bundle.get('paths', []), list), 'paths phải là array')
    _require(not bundle.get('paths'), 'Base chưa hỗ trợ paths; để [] cho đến P1')
    return bundle


def load_bundle(path: Path) -> dict:
    def reject_constant(value):
        raise ValueError(f'JSON không cho phép {value}')
    bundle = json.loads(Path(path).read_text(encoding='utf-8-sig'), parse_constant=reject_constant)
    return validate_bundle(bundle)
