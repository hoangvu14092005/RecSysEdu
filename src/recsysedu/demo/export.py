"""Export a portable schema-v1 view of completed, compatible offline runs.

``run_dirs`` are selected run directories inside runner-produced experiment
batches (including the selected Hybrid alpha trial). The entire batch and
source copies are verified before export; no model is trained or scored here.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pandas as pd

from recsysedu.data.split import PROTOCOL_ID
from recsysedu.demo.artifacts import validate_bundle


def _read(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding='utf-8'), parse_constant=_reject_constant)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f'cannot read artifact: {path}') from exc
    if not isinstance(value, dict):
        raise ValueError(f'artifact must be an object: {path}')
    return value


def _reject_constant(value):
    raise ValueError(f'non-finite JSON value: {value}')


def _sha(path: Path) -> str:
    try:
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(block)
        return digest.hexdigest()
    except OSError as exc:
        raise ValueError(f'missing artifact: {path}') from exc


def _local(root: Path, value) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError('artifact path must be a non-empty relative path')
    path = (root / value).resolve()
    if Path(value).is_absolute() or path == root or not path.is_relative_to(root):
        raise ValueError('artifact path must stay inside the experiment batch')
    return path


def _verify(root: Path, hashes) -> None:
    if not isinstance(hashes, dict) or not hashes:
        raise ValueError('missing artifact output_hashes')
    for name, expected in hashes.items():
        if not isinstance(expected, str) or _sha(_local(root, name)) != expected:
            raise ValueError(f'artifact hash mismatch: {name}')


def _batch(run_dir: Path):
    for parent in run_dir.parents:
        if (parent / 'experiment_manifest.json').is_file():
            path = parent / 'experiment_manifest.json'
            manifest_hash = _sha(path)
            manifest = _read(path)
            if type(manifest.get('schema_version')) is not int or manifest['schema_version'] != 1:
                raise ValueError('unsupported experiment schema')
            _verify(parent, manifest.get('output_hashes'))
            inventory = {path.relative_to(parent).as_posix() for path in parent.rglob('*')
                         if path.is_file() and path != parent / 'experiment_manifest.json'}
            if inventory != set(manifest['output_hashes']):
                raise ValueError('experiment manifest has incomplete artifact inventory')
            components = manifest.get('component_hashes')
            if not isinstance(components, dict) or set(components) - {'content', 'bpr'}:
                raise ValueError('unsupported component manifest entries')
            for name, expected in components.items():
                filename = 'feature_manifest.json' if name == 'content' else 'bpr_manifest.json'
                path = parent / 'artifacts' / name / filename
                if _sha(path) != expected:
                    raise ValueError(f'component manifest hash mismatch: {name}')
                component = _read(path)
                if name == 'content':
                    hashes = component.get('output_hashes')
                else:
                    if not all(key in component for key in (
                            'checkpoint', 'checkpoint_sha256', 'id_maps', 'id_maps_sha256')):
                        raise ValueError('incomplete BPR component manifest')
                    hashes = {component[key]: component[f'{key}_sha256']
                              for key in ('checkpoint', 'id_maps')}
                _verify(path.parent, hashes)
            return parent, manifest, manifest_hash
    raise ValueError('run has no completed experiment manifest')


def _sources(root: Path, batch: dict, run: dict):
    inputs = batch.get('snapshot_inputs')
    if not isinstance(inputs, dict) or set(inputs) != {
            'dataset_manifest', 'split_manifest', 'courses', 'train', 'valid'}:
        raise ValueError('experiment lacks portable snapshot inputs; rerun the experiment')
    paths = {name: _local(root, value) for name, value in inputs.items()}
    if not all(path.relative_to(root).as_posix() in batch['output_hashes']
               for path in paths.values()):
        raise ValueError('snapshot inputs must be bound by batch output_hashes')
    dataset, split = _read(paths['dataset_manifest']), _read(paths['split_manifest'])
    if _sha(paths['dataset_manifest']) != run['dataset_hash']:
        raise ValueError('snapshot dataset_hash mismatch')
    if _sha(paths['split_manifest']) != run.get('split_manifest_hash'):
        raise ValueError('snapshot split manifest hash mismatch')
    content = {key: value for key, value in split.items() if key != 'split_hash'}
    digest = hashlib.sha256(json.dumps(content, ensure_ascii=False, sort_keys=True,
                                      separators=(',', ':')).encode()).hexdigest()
    if digest != run['split_hash'] or split.get('split_hash') != digest:
        raise ValueError('snapshot split_hash mismatch')
    if any(split.get(key) != run[key] for key in ('dataset_hash', 'protocol_id')):
        raise ValueError('snapshot split identity mismatch')
    for name in ('courses', 'train', 'valid'):
        source = dataset if name == 'courses' else split
        if _sha(paths[name]) != source.get('output_hashes', {}).get(paths[name].name):
            raise ValueError(f'snapshot source hash mismatch: {name}')
    version = dataset.get('dataset_version')
    if not isinstance(version, str) or not version:
        raise ValueError('snapshot missing dataset_version')
    return paths, version


def _item(item: dict, model: str, fallback: str) -> dict:
    """Describe only the executed scoring mechanism, preserving numeric evidence."""
    mechanisms = {
        'popularity': 'Xếp theo số lượt đăng ký khóa học trong tập train.',
        'content': 'So độ tương đồng nội dung tên/mô tả với hồ sơ từ các khóa trong train.',
        'bpr': 'Điểm xếp hạng BPR học từ các cặp người học–khóa học trong train.',
        'hybrid': 'Kết hợp điểm BPR và nội dung đã chuẩn hóa theo cấu hình của run.',
    }
    evidence = item.get('evidence')
    if not isinstance(evidence, list) or any(not isinstance(x, str) for x in evidence):
        raise ValueError('item evidence must be a string array')
    codes = [model + '_mechanism']
    if fallback != 'none':
        codes.append('fallback')
        text = f'Cơ chế dự phòng được ghi trong run: {fallback}.'
    else:
        text = mechanisms[model]
    return dict(item, prerequisite_status='unknown', reason_codes=codes,
                evidence=evidence + [text])


def export_demo_bundle(run_dirs: Sequence[Path], user_ids: Sequence[str],
                       output_path: Path) -> dict:
    """Validate completed runs, then atomically write an offline demo snapshot.

    ``real`` means rankings come from executed models. The displayed dataset
    version and ``offline_run`` evidence label do not certify pilot readiness,
    learning benefit or that a custom input dataset came from MOOCCubeX.
    """
    if (not run_dirs or not user_ids or isinstance(user_ids, (str, bytes))
            or any(not isinstance(user, str) or not user for user in user_ids)
            or len(set(user_ids)) != len(user_ids)):
        raise ValueError('provide runs and unique non-empty user IDs')
    runs, recommendations, batches, models = [], [], {}, set()
    common, source_paths, dataset_version = None, None, None
    identity_fields = ('dataset_hash', 'split_hash', 'protocol_id', 'history_mode',
                       'evaluation_split', 'candidate_policy', 'seen_policy', 'profile_policy',
                       'config_hash', 'cohort_size', 'split_manifest_hash')
    for directory in run_dirs:
        directory = Path(directory).resolve()
        root, batch, batch_hash = _batch(directory)
        if root in batches and batches[root][1] != batch_hash:
            raise ValueError('experiment manifest changed between snapshot runs')
        batches[root] = batch, batch_hash
        run = _read(directory / 'run_manifest.json')
        model = run.get('model_id')
        if not isinstance(model, str) or model not in ('popularity', 'content', 'bpr', 'hybrid'):
            raise ValueError('unsupported P0 model')
        if model in models:
            raise ValueError('only one run per model may enter a snapshot')
        models.add(model)
        selected = batch.get('runs')
        if not isinstance(selected, dict) or _local(root, selected.get(model)) != directory:
            raise ValueError('run is not a selected completed experiment run')
        relative = (directory / 'run_manifest.json').relative_to(root).as_posix()
        if relative not in batch['output_hashes']:
            raise ValueError('run manifest is not bound by experiment output_hashes')
        for key in ('dataset_hash', 'split_hash', 'protocol_id', 'evaluation_split', 'config_hash'):
            if run.get(key) != batch.get(key):
                raise ValueError(f'run/experiment {key} mismatch')
        if run.get('experiment_id') != batch.get('run_id'):
            raise ValueError('run belongs to another experiment')
        if (run.get('history_mode') != 'offline' or run.get('protocol_id') != PROTOCOL_ID
                or run.get('evaluation_split') not in ('valid', 'test')
                or run.get('candidate_policy') != 'full_train_universe'
                or run.get('profile_policy') != 'train_only' or run.get('k') != 10
                or run.get('seen_policy') != ('train' if run['evaluation_split'] == 'valid'
                                            else 'train_plus_valid')):
            raise ValueError('unsupported snapshot evaluation/history policy')
        current = tuple(run.get(key) for key in identity_fields)
        if common is not None and current != common:
            raise ValueError('mixed dataset/split/protocol/history/config/cohort runs')
        common = current
        _verify(directory, run.get('output_hashes'))
        if not {'recommendations.jsonl', 'per_user_metrics.parquet', 'metrics.csv'} <= set(
                run['output_hashes']):
            raise ValueError('incomplete evaluator run')
        paths, version = _sources(root, batch, run)
        if source_paths is None:
            source_paths, dataset_version = paths, version
        runs.append({key: run.get(key) for key in (
            'run_id', 'model_id', 'dataset_hash', 'split_hash', 'protocol_id', 'evaluation_split',
            'cohort_size', 'candidate_policy', 'seen_policy', 'config_hash', 'seed',
            'metric_status', 'metrics', 'git_revision', 'git_dirty', 'limitations',
            'history_mode', 'profile_policy')}
            | {'cohort': 'warm', 'evidence_level': 'offline_run'})
        seen_users, selected_users = set(), set()
        try:
            with (directory / 'recommendations.jsonl').open(encoding='utf-8') as stream:
                for line in stream:
                    row = json.loads(line, parse_constant=_reject_constant)
                    user = row.get('user_id')
                    if not isinstance(user, str) or user in seen_users:
                        raise ValueError('duplicate or invalid recommendation user')
                    seen_users.add(user)
                    if user not in user_ids:
                        continue
                    selected_users.add(user)
                    items = row.get('items')
                    if not isinstance(items, list):
                        raise ValueError('recommendation items must be an array')
                    recommendations.append(dict(
                        user_id=user, model_id=model, run_id=run['run_id'],
                        fallback_status=row.get('fallback_status'),
                        items=[_item(item, model, row.get('fallback_status')) for item in items]))
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError, AttributeError) as exc:
            raise ValueError('invalid recommendations artifact') from exc
        if len(seen_users) != run.get('cohort_size') or selected_users != set(user_ids):
            raise ValueError('recommendations incomplete or selected user absent from run cohort')

    train = pd.read_parquet(source_paths['train'], columns=['user_id', 'course_id'])
    valid = pd.read_parquet(source_paths['valid'], columns=['user_id', 'course_id'])
    histories, seen = defaultdict(set), defaultdict(set)
    for user, course in train.itertuples(index=False, name=None):
        if user in user_ids:
            histories[user].add(course)
            seen[user].add(course)
    if runs[0]['evaluation_split'] == 'test':
        for user, course in valid.itertuples(index=False, name=None):
            if user in user_ids:
                seen[user].add(course)
    users = [dict(user_id=user, display_name=f'Hồ sơ {number}',
                  observed_course_ids=sorted(seen[user]), profile_course_ids=sorted(histories[user]))
             for number, user in enumerate(user_ids, 1)]
    needed = set().union(*seen.values(), *histories.values())
    needed.update(item.get('course_id') for rec in recommendations for item in rec['items'])
    courses = pd.read_parquet(source_paths['courses']).to_dict(orient='records')
    catalog = [dict(course_id=row['course_id'], name=row['name'], fields=list(row['fields']))
               for row in courses if row['course_id'] in needed]
    first = runs[0]
    bundle = dict(
        meta=dict(schema_version=1, snapshot_id=f'snapshot-{uuid4().hex}',
                  data_mode='real', history_mode='offline', evidence_level='offline_run',
                  dataset_version=dataset_version,
                  generated_at=datetime.now(timezone.utc).isoformat(),
                  **{key: first[key] for key in ('dataset_hash', 'split_hash', 'protocol_id')}),
        users=users, courses=catalog, runs=runs, recommendations=recommendations, paths=[])
    validate_bundle(bundle)
    # Recheck after reading, so an input changed mid-export is never published.
    for root, (batch, digest) in batches.items():
        if _sha(root / 'experiment_manifest.json') != digest:
            raise ValueError('experiment manifest changed during snapshot export')
        _verify(root, batch['output_hashes'])
    output_path = Path(output_path)
    if any(output_path.resolve().is_relative_to(root) for root in batches):
        raise ValueError('snapshot output must stay outside immutable experiment batches')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.snapshot-', dir=output_path.parent) as temporary:
        staged = Path(temporary) / 'bundle.json'
        staged.write_text(json.dumps(bundle, ensure_ascii=False, indent=2, allow_nan=False) + '\n',
                          encoding='utf-8')
        os.replace(staged, output_path)
    return bundle
