"""Run four train-only models, select alpha on validation, then enforce a freeze.

Paths are relative to ``_base_dir`` (the CLI sets it to the YAML directory),
or to the current working directory for direct Python callers. Each invocation
publishes one new batch directory atomically. Freezing is a deliberate later
step: copy ``freeze_candidate`` from the validation experiment manifest, add
that file's SHA-256 as ``validation_manifest_sha256``, and set frozen/validation_dir.
The frozen test reuses the exact validation Content features and BPR checkpoint.
"""

from __future__ import annotations

import hashlib
import json
import platform
import shutil
import subprocess
import tempfile
from collections import defaultdict
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path
from time import perf_counter
from typing import Literal
from uuid import uuid4

import pandas as pd
import yaml
from scipy import sparse

from recsysedu.adapters.recbole import export_atomic_files, load_bpr_scorer, train_bpr
from recsysedu.contracts import RunIdentity
from recsysedu.data.split import PROTOCOL_ID, _dataset_identity
from recsysedu.evaluation.run import _sha256, _validate_split, evaluate_run
from recsysedu.models.content import ContentConfig, ContentModel, fit_content
from recsysedu.models.hybrid import HybridModel, _alpha, select_alpha
from recsysedu.models.popularity import fit_popularity


def _json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f'manifest cannot be read: {path}') from exc
    if not isinstance(value, dict):
        raise ValueError(f'manifest must be an object: {path}')
    return value


def _write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n',
                    encoding='utf-8')


def _config_hash(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _git_revision() -> str | None:
    try:
        return subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=Path(__file__).resolve().parents[3],
            stderr=subprocess.DEVNULL, text=True).strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def _git_dirty() -> bool | None:
    try:
        return bool(subprocess.check_output(
            ['git', 'status', '--porcelain'], cwd=Path(__file__).resolve().parents[3],
            stderr=subprocess.DEVNULL, text=True).strip())
    except (OSError, subprocess.CalledProcessError):
        return None


def _path(value, base: Path) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError('config paths must be non-empty strings')
    path = Path(value)
    return (base / path).resolve() if not path.is_absolute() else path.resolve()


def _section(config: dict, name: str, base: Path) -> dict:
    value = config.get(name, {})
    if not isinstance(value, dict):
        raise ValueError(f'{name} config must be an object')
    value = dict(value)
    config_path = value.pop('config_path', None)
    if config_path is None:
        return value
    path = _path(config_path, base)
    source = yaml.safe_load(path.read_text(encoding='utf-8-sig'))
    if not isinstance(source, dict):
        raise ValueError(f'{name} config must be an object: {path}')
    # Artifact paths inside a model YAML belong to that YAML, unlike overrides.
    if 'manifest_path' in source:
        source['manifest_path'] = str(_path(source['manifest_path'], path.parent))
    return source | value


def _settings(config: dict):
    if not isinstance(config, dict):
        raise ValueError('experiment config must be an object')
    base = Path(config.get('_base_dir', '.')).resolve()
    seed = config.get('seed')
    if type(seed) is not int:
        raise ValueError('seed must be an integer')
    try:
        content = ContentConfig(**_section(config, 'content', base))
    except TypeError as exc:
        raise ValueError(f'invalid content configuration: {exc}') from exc
    bpr = _section(config, 'bpr', base)
    fixed = dict(benchmark_filename=['train', 'valid', 'test'], USER_ID_FIELD='user_id',
                 ITEM_ID_FIELD='item_id', TIME_FIELD='timestamp', use_gpu=False)
    allowed = {'seed', 'epochs', 'embedding_size', 'train_batch_size', 'learning_rate',
               'manifest_path', 'atomic_dir', 'split_dir', 'output_dir'} | fixed.keys()
    if set(bpr) - allowed:
        raise ValueError(f'unsupported BPR settings: {sorted(set(bpr) - allowed)}')
    for name, value in fixed.items():
        if name in bpr and (type(bpr[name]) is not type(value) or bpr[name] != value):
            raise ValueError(f'BPR {name} is owned by the adapter')
    seed_value = bpr.get('seed', seed)
    if type(seed_value) is not int or seed_value != seed:
        raise ValueError('BPR seed must match experiment seed')
    parameters = dict(seed=seed, epochs=bpr.get('epochs', 10),
                      embedding_size=bpr.get('embedding_size', 64),
                      train_batch_size=bpr.get('train_batch_size', 2048),
                      learning_rate=bpr.get('learning_rate', 0.001))
    for name in ('epochs', 'embedding_size', 'train_batch_size'):
        if type(parameters[name]) is not int or parameters[name] < 1:
            raise ValueError(f'BPR {name} must be a positive integer')
    if parameters['epochs'] > 100:
        raise ValueError('BPR epochs must be bounded from 1 to 100')
    rate = parameters['learning_rate']
    if type(rate) not in (int, float) or not 0 < rate < float('inf'):
        raise ValueError('BPR learning_rate must be positive and finite')
    hybrid = _section(config, 'hybrid', base)
    hybrid_fixed = dict(primary_metric='NDCG@10', selection_split='valid',
                        normalization='per_user_full_candidates_minmax_constant_zero',
                        fallback='content_then_popularity_for_unknown_bpr_user')
    if set(hybrid) - ({'alphas'} | hybrid_fixed.keys()):
        raise ValueError('unsupported hybrid settings')
    for name, value in hybrid_fixed.items():
        if name in hybrid and hybrid[name] != value:
            raise ValueError(f'hybrid {name} is fixed by the protocol')
    grid = hybrid.get('alphas', [0, 0.25, 0.5, 0.75, 1])
    if not isinstance(grid, (list, tuple)):
        raise ValueError('hybrid alphas must be a list')
    alphas = [_alpha(value) for value in grid]
    if not alphas or len(set(alphas)) != len(alphas):
        raise ValueError('hybrid alphas must be non-empty and unique')
    effective = dict(seed=seed, content=content.manifest_value(), bpr=parameters,
                     hybrid={'alphas': sorted(alphas),
                             'normalization': 'per_user_full_candidates_minmax_constant_zero',
                             'formula': 'alpha * normalized_bpr + (1 - alpha) * normalized_content'},
                     protocol_id=PROTOCOL_ID, k=10)
    artifact = _path(bpr['manifest_path'], base) if 'manifest_path' in bpr else None
    return base, content, parameters, sorted(alphas), effective, artifact


def _bpr_identity(path: Path, identity: RunIdentity, parameters: dict) -> dict:
    model = _json(path)
    for field in ('dataset_hash', 'split_hash'):
        if model.get(field) != getattr(identity, field):
            raise ValueError(f'BPR artifact {field} mismatch')
    # Task 7 manifests predate protocol_id. Their exact split_hash already binds
    # the complete protocol manifest; if explicitly present it must also match.
    if model.get('protocol_id', identity.protocol_id) != identity.protocol_id:
        raise ValueError('BPR artifact protocol_id mismatch')
    for key, value in parameters.items():
        field = 'epochs_completed' if key == 'epochs' else key
        if model.get(field) != value:
            raise ValueError(f'BPR artifact configuration mismatch: {key}')
    return model


def _verify_files(root: Path, hashes: dict) -> None:
    if not isinstance(hashes, dict) or not hashes:
        raise ValueError('artifact manifest missing output hashes')
    for name, expected in hashes.items():
        if not isinstance(name, str) or not isinstance(expected, str):
            raise ValueError('invalid artifact hash entry')
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()) or path == root.resolve():
            raise ValueError('artifact path must stay within its batch')
        try:
            digest = _sha256(path)
        except OSError as exc:
            raise ValueError(f'artifact hash input missing: {name}') from exc
        if digest != expected:
            raise ValueError(f'artifact hash mismatch: {name}')


def _frozen_validation(config, base, identity, config_hash, output_root):
    if config.get('frozen') is not True:
        raise ValueError('test requires frozen: true')
    validation_dir = _path(config.get('validation_dir'), base)
    path = validation_dir / 'experiment_manifest.json'
    valid = _json(path)
    freeze = config.get('freeze')
    if not isinstance(freeze, dict):
        raise ValueError('test requires exact freeze hashes')
    expected = dict(dataset_hash=identity.dataset_hash, split_hash=identity.split_hash,
                    config_hash=config_hash, validation_manifest_sha256=_sha256(path))
    for name, value in expected.items():
        if freeze.get(name) != value:
            raise ValueError(f'frozen {name} mismatch')
        if name != 'validation_manifest_sha256' and valid.get(name) != value:
            raise ValueError(f'validation {name} mismatch')
    if valid.get('evaluation_split') != 'valid' or valid.get('protocol_id') != PROTOCOL_ID:
        raise ValueError('freeze must reference compatible validation experiment')
    if set(valid.get('runs', {})) != {'popularity', 'content', 'bpr', 'hybrid'}:
        raise ValueError('freeze requires a complete four-model validation experiment')
    valid_root = Path(valid['output_root']).resolve()
    # Also reject nested test roots: they would mutate the immutable validation batch.
    if output_root == valid_root or output_root.is_relative_to(valid_root):
        raise ValueError('test requires a distinct output root outside validation output')
    _verify_files(validation_dir, valid.get('output_hashes'))
    return validation_dir, valid


def run_experiment(config: dict, *, split: Literal['valid', 'test'],
                   output_root: Path) -> list[dict]:
    """Publish compatible four-model runs; never choose parameters using test metrics."""
    return _run(config, split=split, output_root=output_root,
                model_ids=('popularity', 'content', 'bpr', 'hybrid'))


def evaluate_model(config: dict, *, model_id: str, split: Literal['valid', 'test'],
                   output_root: Path) -> dict:
    """Evaluate only one model; test still requires a full validation freeze."""
    if model_id not in ('popularity', 'content', 'bpr', 'hybrid'):
        raise ValueError('unsupported model_id')
    return _run(config, split=split, output_root=output_root, model_ids=(model_id,))[0]


def train_from_config(config_path: Path, *, output_dir: Path | None = None) -> dict:
    """CLI BPR training: validate the split and publish one new model directory."""
    config_path = Path(config_path).resolve()
    raw = yaml.safe_load(config_path.read_text(encoding='utf-8-sig'))
    if not isinstance(raw, dict):
        raise ValueError('BPR config must be an object')
    base = config_path.parent
    _, _, parameters, _, _, _ = _settings(dict(
        seed=raw.get('seed'), bpr=raw, _base_dir=str(base)))
    split_dir = _path(raw.get('split_dir'), base)
    split_manifest = _json(split_dir / 'split_manifest.json')
    identity = RunIdentity(f'train-{uuid4().hex}', 'bpr', split_manifest['dataset_hash'],
                           split_manifest['split_hash'], PROTOCOL_ID, parameters['seed'])
    _validate_split(split_dir, identity)
    if output_dir is None:
        output_dir = (_path(raw['output_dir'], base) if 'output_dir' in raw else
                      base / '../artifacts/models' / identity.run_id)
    output_dir = Path(output_dir).resolve()
    if output_dir.exists():
        raise ValueError(f'model output already exists: {output_dir}')
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.train-', dir=output_dir.parent) as temporary:
        stage = Path(temporary)
        export_atomic_files(split_dir, stage / 'atomic')
        temporary_config = stage / 'training.yaml'
        temporary_config.write_text(yaml.safe_dump(
            parameters | {'atomic_dir': str(stage / 'atomic')}), encoding='utf-8')
        report = train_bpr(temporary_config, stage / 'model')
        report.update(protocol_id=PROTOCOL_ID, config_hash=_config_hash(parameters),
                      model_config=parameters, git_revision=_git_revision(),
                      split_manifest_hash=_sha256(split_dir / 'split_manifest.json'))
        _validate_split(split_dir, identity)
        _write(stage / 'model/bpr_manifest.json', report)
        if output_dir.exists():
            raise ValueError(f'model output already exists: {output_dir}')
        (stage / 'model').rename(output_dir)
    return report | {'manifest_path': str(output_dir / 'bpr_manifest.json')}


def _run(config, *, split, output_root, model_ids):
    started = perf_counter()
    if split not in ('valid', 'test'):
        raise ValueError('split must be valid or test')
    if split == 'test' and (not isinstance(config, dict) or config.get('frozen') is not True):
        raise ValueError('test requires frozen: true')
    base, content_config, bpr_config, alphas, effective, supplied_bpr = _settings(config)
    config_hash = _config_hash(effective)
    prepared = _path(config.get('prepared_dir'), base)
    split_dir = _path(config.get('split_dir'), base)
    output_root = Path(output_root).resolve()
    _, dataset_hash = _dataset_identity(prepared / 'interactions.parquet',
                                        prepared / 'courses.parquet')
    source = _json(split_dir / 'split_manifest.json')
    batch_id = f'{split}-{uuid4().hex}'
    identity = RunIdentity(batch_id, 'experiment', dataset_hash, source['split_hash'],
                           PROTOCOL_ID, effective['seed'])
    _validate_split(split_dir, identity)
    revision = _git_revision()
    dirty = _git_dirty()
    versions = {'python': platform.python_version()} | {
        name: version(name) for name in ('numpy', 'pandas', 'scikit-learn', 'pyarrow')}
    if config.get('release_mode', False) and revision is None:
        raise ValueError('release mode requires a Git revision')
    validation_dir, validation = None, None
    if split == 'test':
        validation_dir, validation = _frozen_validation(
            config, base, identity, config_hash, output_root)
    need_bpr = bool({'bpr', 'hybrid'} & set(model_ids))
    need_content = bool({'content', 'hybrid'} & set(model_ids))
    if supplied_bpr is not None and need_bpr and validation is None:
        _bpr_identity(supplied_bpr, identity, bpr_config)
    train = pd.read_parquet(split_dir / 'train.parquet')
    universe = pd.read_parquet(split_dir / 'candidate_universe.parquet')['course_id'].tolist()
    popularity = fit_popularity(train, universe)
    output_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.experiments-', dir=output_root) as temporary:
        stage = Path(temporary) / batch_id
        artifacts = stage / 'artifacts'
        artifacts.mkdir(parents=True)
        content, bpr = None, None
        if validation is None:
            if need_content:
                content = fit_content(pd.read_parquet(prepared / 'courses.parquet'), train,
                                      content_config, artifacts / 'content', popularity)
            if need_bpr and supplied_bpr is None:
                export_atomic_files(split_dir, artifacts / 'atomic')
                temporary_config = stage / 'training.yaml'
                temporary_config.write_text(yaml.safe_dump(
                    bpr_config | {'atomic_dir': str((artifacts / 'atomic').resolve())}),
                    encoding='utf-8')
                train_bpr(temporary_config, artifacts / 'bpr')
                temporary_config.unlink()
            elif need_bpr:
                # Copy only adapter-owned artifacts, never a caller's unrelated files.
                model = _json(supplied_bpr)
                target = artifacts / 'bpr'
                target.mkdir()
                for key in ('checkpoint', 'id_maps'):
                    name = model[key]
                    if Path(name).name != name:
                        raise ValueError('BPR artifact filenames must be local basenames')
                    shutil.copyfile(supplied_bpr.parent / name, target / name)
                shutil.copyfile(supplied_bpr, target / 'bpr_manifest.json')
        else:
            for name in ([name for name, needed in (('content', need_content), ('bpr', need_bpr))
                          if needed]):
                shutil.copytree(validation_dir / 'artifacts' / name, artifacts / name)
            if need_content:
                features = artifacts / 'content'
                course_ids = tuple(json.loads((features / 'course_order.json').read_text('utf-8')))
                index = {course: position for position, course in enumerate(course_ids)}
                histories = defaultdict(list)
                for user, course in zip(train['user_id'], train['course_id']):
                    histories[user].append(index[course])
                content = ContentModel(
                    course_ids, sparse.load_npz(features / 'course_features.npz'),
                    {user: tuple(rows) for user, rows in histories.items()}, popularity)
        bpr_path = artifacts / 'bpr/bpr_manifest.json'
        components = {}
        if need_bpr:
            _bpr_identity(bpr_path, identity, bpr_config)
            bpr = load_bpr_scorer(bpr_path)
            components['bpr'] = _sha256(bpr_path)
        if need_content:
            components['content'] = _sha256(artifacts / 'content/feature_manifest.json')
        if validation is not None:
            for name, digest in components.items():
                if validation['component_hashes'].get(name) != digest:
                    raise ValueError('frozen component artifact hashes mismatch')
        reports, paths, completed_runs = {}, {}, {}

        def evaluate(model_id, model, relative, model_config):
            run_identity = RunIdentity(f'{batch_id}-{uuid4().hex}', model_id,
                                       identity.dataset_hash, identity.split_hash,
                                       identity.protocol_id, identity.seed)
            report = evaluate_run(model, split_dir, stage / relative, run_identity,
                                  evaluation_split=split)
            report.update(config_hash=config_hash, model_config=model_config,
                          model_config_hash=_config_hash(model_config), git_revision=revision,
                          git_status='revision_available' if revision else 'no_revision',
                          git_dirty=dirty, versions=versions,
                          experiment_id=batch_id, component_hashes=components)
            _write(stage / relative / 'run_manifest.json', report)
            completed_runs[relative] = report
            return report

        for model_id, model, parameters in (
                ('popularity', popularity, {'count_scope': 'train_only'}),
                ('content', content, content_config.manifest_value()),
                ('bpr', bpr, bpr_config)):
            if model_id not in model_ids:
                continue
            paths[model_id] = f'runs/{model_id}'
            reports[model_id] = evaluate(model_id, model, paths[model_id], parameters)
        trials = {}
        selected_alpha = None
        if validation is None and 'hybrid' in model_ids:
            trial_reports = {}
            for alpha in alphas:
                relative = f'alpha_trials/{alpha}'
                trials[str(alpha)] = relative
                trial_reports[alpha] = evaluate(
                    'hybrid', HybridModel(content, bpr, alpha, popularity), relative,
                    {'alpha': alpha, 'components': components})
            selected_alpha = select_alpha(trial_reports, alphas,
                                          artifact_path=stage / 'alpha_selection.json')
            paths['hybrid'] = trials[str(selected_alpha)]
            reports['hybrid'] = trial_reports[selected_alpha]
        elif 'hybrid' in model_ids:
            selected_alpha = validation['selected_alpha']
            if selected_alpha not in alphas:
                raise ValueError('frozen alpha is outside configuration grid')
            paths['hybrid'] = 'runs/hybrid'
            reports['hybrid'] = evaluate(
                'hybrid', HybridModel(content, bpr, selected_alpha, popularity), paths['hybrid'],
                {'alpha': selected_alpha, 'components': components})
            shutil.copyfile(validation_dir / 'alpha_selection.json', stage / 'alpha_selection.json')
        # Detect prepared input mutation as well as split mutation before batch publication.
        _, after_hash = _dataset_identity(prepared / 'interactions.parquet',
                                          prepared / 'courses.parquet')
        if after_hash != dataset_hash:
            raise ValueError('dataset_hash changed during experiment')
        _validate_split(split_dir, identity)
        if validation is not None:
            _frozen_validation(config, base, identity, config_hash, output_root)
        for name, digest in components.items():
            manifest_path = (artifacts / 'content/feature_manifest.json' if name == 'content'
                             else bpr_path)
            if _sha256(manifest_path) != digest:
                raise ValueError(f'component manifest hash changed: {name}')
            component = _json(manifest_path)
            hashes = (component['output_hashes'] if name == 'content' else
                      {component[key]: component[f'{key}_sha256']
                       for key in ('checkpoint', 'id_maps')})
            _verify_files(manifest_path.parent, hashes)
        for relative, report in completed_runs.items():
            if _json(stage / relative / 'run_manifest.json') != report:
                raise ValueError(f'run manifest changed during experiment: {relative}')
            _verify_files(stage / relative, report['output_hashes'])
        manifest = asdict(identity) | dict(
            schema_version=1, evaluation_split=split, config_hash=config_hash,
            effective_config=effective, git_revision=revision,
            git_status='revision_available' if revision else 'no_revision',
            git_dirty=dirty, versions=versions, duration_seconds=perf_counter() - started,
            output_root=str(output_root), runs=paths, alpha_trials=trials,
            selected_alpha=selected_alpha, component_hashes=components,
            freeze_candidate=dict(dataset_hash=dataset_hash, split_hash=identity.split_hash,
                                  config_hash=config_hash),
            output_hashes={p.relative_to(stage).as_posix(): _sha256(p)
                           for p in sorted(stage.rglob('*')) if p.is_file()})
        if validation is not None:
            manifest['validation_manifest_sha256'] = _sha256(
                validation_dir / 'experiment_manifest.json')
        _write(stage / 'experiment_manifest.json', manifest)
        target = output_root / batch_id
        if target.exists():
            raise ValueError(f'experiment output already exists: {target}')
        stage.rename(target)
    return [reports[name] for name in model_ids]
