"""Stream one user's full-ranking scores at a time and publish a run atomically."""

from __future__ import annotations

import csv
import hashlib
import json
import tempfile
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path
from time import perf_counter

from recsysedu.contracts import Recommender, RunIdentity, ScoreResult
from recsysedu.data.split import OUTPUT_NAMES, PROTOCOL_ID
from recsysedu.evaluation.metrics import _ids, _validate_k, metrics_at_k
from recsysedu.evaluation.ranking import rank_candidates


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _validate_split(split_dir: Path, identity: RunIdentity) -> dict:
    try:
        manifest = json.loads((split_dir / 'split_manifest.json').read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('split manifest cannot be read') from exc
    if not isinstance(manifest, dict) or manifest.get('schema_version') != 1:
        raise ValueError('unsupported split manifest schema')
    for name in ('dataset_hash', 'split_hash', 'protocol_id'):
        if manifest.get(name) != getattr(identity, name):
            raise ValueError(f'{name} mismatch between split and run identity')
    if manifest['protocol_id'] != PROTOCOL_ID:
        raise ValueError('unsupported protocol_id')
    content = {name: value for name, value in manifest.items() if name != 'split_hash'}
    digest = hashlib.sha256(json.dumps(
        content, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')
    ).hexdigest()
    if manifest['split_hash'] != digest:
        raise ValueError('split_hash does not match split manifest contents')
    hashes = manifest.get('output_hashes')
    if not isinstance(hashes, dict):
        raise ValueError('split manifest missing output_hashes')
    for name in OUTPUT_NAMES:
        filename = f'{name}.parquet'
        try:
            matches = _sha256(split_dir / filename) == hashes.get(filename)
        except OSError as exc:
            raise ValueError(f'split hash input cannot be read: {filename}') from exc
        if not matches:
            raise ValueError(f'split output hash mismatch: {filename}')
    return manifest


def _rows(path: Path, columns: list[str]):
    import pyarrow as pa
    import pyarrow.parquet as pq

    try:
        source = pq.ParquetFile(path)
        if not set(columns) <= set(source.schema_arrow.names):
            raise ValueError(f'{path.name} missing required columns')
        for batch in source.iter_batches(batch_size=1024, columns=columns):
            yield from batch.to_pylist()
    except (OSError, pa.ArrowException) as exc:
        raise ValueError(f'split Parquet cannot be read: {path.name}') from exc


def _inputs(split_dir: Path, evaluation_split: str, manifest: dict):
    universe = _ids((row['course_id'] for row in _rows(
        split_dir / 'candidate_universe.parquet', ['course_id'])), 'candidate_universe')
    if not universe or universe != tuple(sorted(universe)):
        raise ValueError('candidate universe must be non-empty and sorted')
    universe_set = set(universe)
    train_seen = defaultdict(set)
    for row in _rows(split_dir / 'train.parquet', ['user_id', 'course_id']):
        _ids([row['user_id']], 'train user')
        _ids([row['course_id']], 'train course')
        if row['course_id'] not in universe_set:
            raise ValueError('train course outside candidate universe')
        train_seen[row['user_id']].add(row['course_id'])
    if set().union(*train_seen.values()) != universe_set:
        raise ValueError('candidate universe must equal distinct train courses')
    valid_targets = {}
    for row in _rows(split_dir / 'valid.parquet', ['user_id', 'course_id']):
        user_id, course_id = row['user_id'], row['course_id']
        if user_id not in train_seen or user_id in valid_targets:
            raise ValueError('valid target must be unique and belong to a train user')
        _ids([course_id], 'valid target')
        if course_id in train_seen[user_id]:
            raise ValueError('valid target overlaps train seen')
        valid_targets[user_id] = course_id
    targets = valid_targets
    if evaluation_split == 'test':
        targets = {}
        for row in _rows(split_dir / 'test.parquet', ['user_id', 'course_id']):
            user_id, course_id = row['user_id'], row['course_id']
            if user_id not in valid_targets or user_id in targets:
                raise ValueError('test target must be unique and belong to a valid user')
            _ids([course_id], 'test target')
            if course_id in train_seen[user_id] or course_id == valid_targets[user_id]:
                raise ValueError('test target overlaps train/valid seen')
            targets[user_id] = course_id
    expected = {user_id: target for user_id, target in targets.items() if target in universe_set}
    if not expected:
        raise ValueError('cannot evaluate an empty warm cohort')
    if len(expected) != manifest['warm_cohort_sizes'][evaluation_split]:
        raise ValueError('warm cohort size mismatch')
    return universe, train_seen, valid_targets, expected


def evaluate_run(model: Recommender, split_dir, output_dir, identity: RunIdentity, *,
                 evaluation_split: str, k: int = 10) -> dict:
    """Evaluate a frozen train-only model on the declared warm valid/test cohort.

    The model receives the complete train universe in source-ID order. Only the
    evaluator masks seen courses. A new output directory is published by a single
    rename after every artifact is complete; an existing run is never overwritten.
    """
    import pyarrow as pa
    import pyarrow.parquet as pq

    _validate_k(k)
    if k != 10:
        raise ValueError('evaluate_run requires k=10 for leave_last_two_out_v1')
    if evaluation_split not in ('valid', 'test'):
        raise ValueError('evaluation_split must be valid or test')
    if not isinstance(identity, RunIdentity):
        raise ValueError('identity must be RunIdentity')
    split_dir, output_dir = Path(split_dir), Path(output_dir)
    if output_dir.exists():
        raise ValueError(f'output already exists: {output_dir}')
    started = perf_counter()
    split_manifest = _validate_split(split_dir, identity)
    manifest_hash = _sha256(split_dir / 'split_manifest.json')
    universe, train_seen, valid_targets, expected = _inputs(
        split_dir, evaluation_split, split_manifest)
    metric_names = [f'{name}@{k}' for name in
                    ('NDCG', 'HitRate', 'Recall', 'Precision', 'Coverage')]
    schema = pa.schema([('user_id', pa.string()), ('target_id', pa.string()),
                        ('recommendation_count', pa.int64()), ('train_history_count', pa.int64()),
                        ('fallback_status', pa.string())] +
                       [(name, pa.float64()) for name in metric_names])
    sums = dict.fromkeys(metric_names, 0.0)
    recommended, evaluated = set(), set()
    fallback_counts = Counter()
    short_lists = 0
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.evaluation-', dir=output_dir.parent) as temporary:
        stage = Path(temporary) / 'run'
        stage.mkdir()
        with pq.ParquetWriter(stage / 'per_user_metrics.parquet', schema) as writer, (
                stage / 'recommendations.jsonl').open('w', encoding='utf-8', newline='\n') as recs:
            buffer = []
            for row in _rows(split_dir / f'{evaluation_split}_cohort.parquet',
                             ['user_id', 'course_id', 'target_in_train']):
                user_id, target = row['user_id'], row['course_id']
                if (user_id in evaluated or expected.get(user_id) != target
                        or row['target_in_train'] is not True):
                    raise ValueError('warm cohort does not match split targets')
                seen = train_seen[user_id]
                if evaluation_split == 'test':
                    seen = seen | {valid_targets[user_id]}
                result = model.score(user_id, universe)
                if not isinstance(result, ScoreResult) or result.course_ids != universe:
                    raise ValueError('model scores must preserve the complete candidate universe')
                ranked = rank_candidates(result, seen, k=k)
                values = metrics_at_k([item.course_id for item in ranked], [target],
                                      len(universe), k=k)
                buffer.append(dict(user_id=user_id, target_id=target,
                                   recommendation_count=len(ranked),
                                   train_history_count=len(train_seen[user_id]),
                                   fallback_status=result.fallback_status) | values)
                if len(buffer) >= 1024:
                    writer.write_table(pa.Table.from_pylist(buffer, schema=schema))
                    buffer.clear()
                recs.write(json.dumps(dict(user_id=user_id, target_ids=[target],
                                           fallback_status=result.fallback_status,
                                           items=[asdict(item) | {'evidence': list(
                                               result.evidence.get(item.course_id, ()))}
                                                  for item in ranked]),
                                      ensure_ascii=False, allow_nan=False) + '\n')
                evaluated.add(user_id)
                recommended.update(item.course_id for item in ranked)
                fallback_counts[result.fallback_status] += 1
                short_lists += len(ranked) < k
                for name in metric_names:
                    sums[name] += values[name]
            if buffer:
                writer.write_table(pa.Table.from_pylist(buffer, schema=schema))
        if evaluated != set(expected):
            raise ValueError('warm cohort is missing expected users')
        count = len(evaluated)
        metrics = {name: total / count for name, total in sums.items()}
        metrics[f'Coverage@{k}'] = len(recommended) / len(universe)
        summary = asdict(identity) | dict(evaluation_split=evaluation_split, k=k,
                                          cohort_size=count) | metrics
        with (stage / 'metrics.csv').open('w', encoding='utf-8', newline='') as stream:
            writer_csv = csv.DictWriter(stream, fieldnames=list(summary))
            writer_csv.writeheader()
            writer_csv.writerow(summary)
        # Detect input mutation during scoring before publishing any run artifacts.
        _validate_split(split_dir, identity)
        if _sha256(split_dir / 'split_manifest.json') != manifest_hash:
            raise ValueError('split manifest hash changed during evaluation')
        report = asdict(identity) | dict(
            schema_version=1, evaluation_split=evaluation_split, k=k,
            primary_metric=f'NDCG@{k}', metrics=metrics, cohort_size=count,
            candidate_universe_size=len(universe), short_list_user_count=short_lists,
            cold_target_count=split_manifest['cold_target_counts'][evaluation_split],
            fallback_counts=dict(sorted(fallback_counts.items())),
            candidate_policy='full_train_universe', profile_policy='train_only',
            seen_policy='train' if evaluation_split == 'valid' else 'train_plus_valid',
            tie_break_policy='score_desc_course_id_asc', history_mode='offline',
            metric_status='measured', duration_seconds=perf_counter() - started,
            split_manifest_hash=manifest_hash,
            output_hashes={name: _sha256(stage / name) for name in
                           ('metrics.csv', 'per_user_metrics.parquet', 'recommendations.jsonl')},
            limitations=[
                'Per-user temporal split allows cross-user future interactions in train.',
                'Static catalog has no time-dependent course availability.',
                'Offline enrollment ranking does not measure mastery or learning gain.',
            ],
        )
        (stage / 'run_manifest.json').write_text(
            json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n',
            encoding='utf-8')
        stage.rename(output_dir)
    return report
