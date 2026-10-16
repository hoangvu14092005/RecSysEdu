"""Exact pre-split RecBole BPR training and source-ID scoring.

Atomic format: https://recbole.io/docs/user_guide/usage/running_new_dataset.html
Benchmark handling: RecBole v1.2.1 recbole/data/dataset/dataset.py, Dataset.build.
"""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np
import pyarrow.parquet as pq
import yaml

from recsysedu.contracts import ScoreResult


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def _token(value: object) -> bool:
    return (isinstance(value, str) and bool(value.strip()) and value != '[PAD]'
            and not any(char in value for char in '\t\r\n'))


def export_atomic_files(split_dir: Path, output_dir: Path) -> dict:
    """Export every Task 3 row, including cold held-out targets, without re-splitting."""
    split_dir, output_dir = Path(split_dir), Path(output_dir)
    if output_dir.exists():
        raise ValueError(f'Output exists: {output_dir}')
    manifest_path = split_dir / 'split_manifest.json'
    source = json.loads(manifest_path.read_text(encoding='utf-8'))
    source_identity = dict(source)
    split_hash = source_identity.pop('split_hash', None)
    actual_hash = hashlib.sha256(json.dumps(
        source_identity, ensure_ascii=False, sort_keys=True,
        separators=(',', ':')).encode('utf-8')).hexdigest()
    if split_hash != actual_hash:
        raise ValueError('split manifest hash mismatch')
    names = ('train', 'valid', 'test', 'candidate_universe')
    for name in names:
        path = split_dir / f'{name}.parquet'
        if _hash(path) != source['output_hashes'].get(path.name):
            raise ValueError(f'split file hash mismatch: {path.name}')
    tables = {name: pq.read_table(split_dir / f'{name}.parquet') for name in names}
    candidates = tables['candidate_universe']['course_id'].to_pylist()
    if (not candidates or len(set(candidates)) != len(candidates)
            or not all(_token(item) for item in candidates)):
        raise ValueError('invalid candidate universe')
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.atomic-', dir=output_dir.parent) as temporary:
        stage = Path(temporary) / 'export'
        dataset_dir = stage / 'recsysedu'
        dataset_dir.mkdir(parents=True)
        counts = {}
        for name in names[:3]:
            rows = tables[name].to_pylist()
            if len(rows) != source['row_counts'][name]:
                raise ValueError(f'split row count mismatch: {name}')
            path = dataset_dir / f'recsysedu.{name}.inter'
            with path.open('w', encoding='utf-8', newline='') as target:
                writer = csv.writer(target, delimiter='\t', lineterminator='\n')
                writer.writerow(['user_id:token', 'item_id:token', 'timestamp:float'])
                # Arrow conversion ignores the host timezone. Naive source times
                # retain their ordering; this does not assert UTC truth.
                timestamp = tables[name]['event_time'].cast('timestamp[us]').cast('int64')
                for row, micros in zip(rows, timestamp):
                    if not _token(row['user_id']) or not _token(row['course_id']):
                        raise ValueError('invalid source token or reserved padding token')
                    writer.writerow([row['user_id'], row['course_id'], micros.as_py() / 1_000_000])
            counts[name] = len(rows)
        if set(candidates) != set(tables['train']['course_id'].to_pylist()):
            raise ValueError('candidate universe differs from train IDs')
        manifest = dict(schema_version=1, dataset='recsysedu',
                        benchmark_filename=list(names[:3]), split_hash=split_hash,
                        dataset_hash=source['dataset_hash'], time_basis=source['time_basis'],
                        split_manifest_sha256=_hash(manifest_path), row_counts=counts,
                        candidate_ids=candidates,
                        output_hashes={p.name: _hash(p) for p in sorted(dataset_dir.iterdir())})
        _write_json(stage / 'export_manifest.json', manifest)
        stage.rename(output_dir)
    return manifest


class UnknownBPRUserError(ValueError):
    """BPR has no train embedding for the requested source user."""


@dataclass(frozen=True)
class BPRScorer:
    """Dot products of the actual trained RecBole BPR embeddings, in source order.

    Equivalent to BPR.predict in the pinned upstream source; avoids importing
    Torch/RecBole in unit scoring and the UI. Padding and cold items are excluded.
    """

    user_embeddings: np.ndarray
    item_embeddings: np.ndarray
    user_id_map: Mapping[str, int]
    item_id_map: Mapping[str, int]

    def __post_init__(self) -> None:
        for embeddings, mapping in ((self.user_embeddings, self.user_id_map),
                                    (self.item_embeddings, self.item_id_map)):
            if embeddings.ndim != 2 or not np.isfinite(embeddings).all():
                raise ValueError('invalid BPR embeddings')
            if any(not _token(token) or type(index) is not int or
                   index <= 0 or index >= len(embeddings) for token, index in mapping.items()):
                raise ValueError('invalid source mapping or padding index')
            if len(set(mapping.values())) != len(mapping):
                raise ValueError('duplicate internal IDs')
        if self.user_embeddings.shape[1] != self.item_embeddings.shape[1]:
            raise ValueError('BPR embedding dimensions differ')

    def score(self, user_id: str, candidate_ids: Sequence[str]) -> ScoreResult:
        candidates = tuple(candidate_ids)
        if not _token(user_id) or user_id not in self.user_id_map:
            raise UnknownBPRUserError('unknown user or padding token')
        if (len(set(candidates)) != len(candidates)
                or any(not _token(item) or item not in self.item_id_map for item in candidates)):
            raise ValueError('unknown, cold, duplicate or padding candidate IDs')
        indices = [self.item_id_map[item] for item in candidates]
        user = self.user_embeddings[self.user_id_map[user_id]]
        scores = (self.item_embeddings[indices] * user).sum(axis=1)
        return ScoreResult(candidates, scores)


def _build_train_loader(config, dataset, candidate_ids):
    """Use upstream alias sampling with exponent zero: uniform over train items.

    RecBole's default uniform sampler includes held-out-only items. Its default
    multi-phase sampler can also reject a user who consumed all items across
    train/valid/test. Constructing only the train phase avoids both problems.
    """
    from recbole.data.dataloader import TrainDataLoader
    from recbole.sampler import Sampler

    universe = set(dataset.token2id('item_id', list(candidate_ids)))
    positives = {}
    for user, item in zip(dataset.inter_feat['user_id'].numpy(),
                          dataset.inter_feat['item_id'].numpy()):
        positives.setdefault(int(user), set()).add(int(item))
    if any(items >= universe for items in positives.values()):
        raise ValueError('a train user has no unseen item in the train candidate universe')
    sampler = Sampler(['train'], [dataset], distribution='popularity', alpha=0.0)
    return TrainDataLoader(config, dataset, sampler.set_phase('train'), shuffle=True)


def _validation_ndcg(model, train, valid, candidate_ids, user_map, item_map):
    """Score exact warm validation targets with the shared source-ID ranking policy.

    RecBole's default full-sort includes cold items and breaks ties differently.
    Only train histories are masked here. Test interactions are never consulted.
    """
    from collections import defaultdict

    from recsysedu.evaluation.metrics import metrics_at_k
    from recsysedu.evaluation.ranking import rank_candidates

    inverse_users = {index: token for token, index in user_map.items()}
    inverse_items = {index: token for token, index in item_map.items()}
    histories = defaultdict(list)
    for user, item in zip(train.inter_feat['user_id'].tolist(),
                          train.inter_feat['item_id'].tolist()):
        histories[inverse_users[user]].append(inverse_items[item])
    scorer = BPRScorer(model.user_embedding.weight.detach().cpu().numpy(),
                       model.item_embedding.weight.detach().cpu().numpy(), user_map, item_map)
    values = []
    for user, target in zip(valid.inter_feat['user_id'].tolist(),
                            valid.inter_feat['item_id'].tolist()):
        if target not in inverse_items:
            continue
        source_user = inverse_users[user]
        ranked = rank_candidates(scorer.score(source_user, candidate_ids),
                                 histories[source_user], k=10)
        values.append(metrics_at_k([row.course_id for row in ranked], [inverse_items[target]],
                                   len(candidate_ids), k=10)['NDCG@10'])
    if not values:
        raise ValueError('early stopping requires a non-empty warm validation cohort')
    return float(np.mean(values))


def train_bpr(config_path: Path, output_dir: Path) -> dict:
    """Train real RecBole BPR on the exact export; project evaluator owns metrics.

    The configuration accepts atomic_dir, seed, epochs, embedding_size,
    train_batch_size and learning_rate. Dataset/split/filter/device settings
    are owned by this adapter and cannot silently alter the Task 3 split.
    """
    import psutil
    import recbole
    import torch
    from recbole.config import Config
    from recbole.data import create_dataset
    from recbole.model.general_recommender.bpr import BPR
    from recbole.trainer import Trainer
    from recbole.utils import init_seed

    started = time.perf_counter()
    config_path, output_dir = Path(config_path), Path(output_dir)
    raw = yaml.safe_load(config_path.read_text(encoding='utf-8'))
    if output_dir.exists():
        raise ValueError(f'Output exists: {output_dir}')
    atomic_dir = Path(raw['atomic_dir'])
    if not atomic_dir.is_absolute():
        atomic_dir = config_path.parent / atomic_dir
    exported = json.loads((atomic_dir / 'export_manifest.json').read_text(encoding='utf-8'))
    for name, expected in exported['output_hashes'].items():
        if _hash(atomic_dir / exported['dataset'] / name) != expected:
            raise ValueError(f'atomic file hash mismatch: {name}')
    if exported['benchmark_filename'] != ['train', 'valid', 'test']:
        raise ValueError('benchmark files must be train/valid/test')
    parameters = {name: raw[name] for name in (
        'seed', 'epochs', 'embedding_size', 'train_batch_size', 'learning_rate') if name in raw}
    if type(parameters.get('epochs')) is not int or not 1 <= parameters['epochs'] <= 100:
        raise ValueError('epochs must be bounded from 1 to 100')
    if type(parameters.get('seed')) is not int:
        raise ValueError('seed must be an integer')
    early = raw.get('validation_early_stopping', False)
    patience = raw.get('stopping_step', 3)
    if type(early) is not bool or type(patience) is not int or patience < 1:
        raise ValueError('validation_early_stopping must be bool; stopping_step positive integer')
    parameters.update(
        data_path=str(atomic_dir.resolve()), benchmark_filename=['train', 'valid', 'test'],
        USER_ID_FIELD='user_id', ITEM_ID_FIELD='item_id', TIME_FIELD='timestamp',
        field_separator='\t', load_col={'inter': ['user_id', 'item_id', 'timestamp']},
        use_gpu=False, worker=0, reproducibility=True, show_progress=False,
        save_dataset=False, save_dataloaders=False,
        user_inter_num_interval='[0,inf)', item_inter_num_interval='[0,inf)',
        eval_args={'split': None, 'order': 'TO', 'group_by': 'user', 'mode': 'full'},
        train_neg_sample_args={'distribution': 'popularity', 'sample_num': 1, 'alpha': 0.0},
        metrics=['NDCG'], topk=[10], valid_metric='NDCG@10', enable_amp=False,
        eval_step=1, stopping_step=patience)
    class AdapterConfig(Config):
        # RecBole normally lets sys.argv override config_dict. The embedding
        # application's flags must not bypass our CPU/split/epoch constraints.
        def _load_cmd_line(self):
            return {}

    config = AdapterConfig(model='BPR', dataset='recsysedu', config_dict=parameters)
    init_seed(config['seed'], True)
    dataset = create_dataset(config)
    train, valid, test = dataset.build()
    loaded_counts = {name: len(data) for name, data in
                     zip(('train', 'valid', 'test'), (train, valid, test))}
    if loaded_counts != exported['row_counts']:
        raise ValueError('RecBole changed split row counts')
    for name, subset in zip(('train', 'valid', 'test'), (train, valid, test)):
        original = atomic_dir / 'recsysedu' / f'recsysedu.{name}.inter'
        with original.open(encoding='utf-8', newline='') as source:
            expected_pairs = [(r['user_id:token'], r['item_id:token']) for r in
                              csv.DictReader(source, delimiter='\t')]
        interaction = subset.inter_feat
        pairs = list(zip(dataset.id2token('user_id', interaction['user_id'].numpy()),
                         dataset.id2token('item_id', interaction['item_id'].numpy())))
        if pairs != expected_pairs:
            raise ValueError(f'RecBole changed split membership/order: {name}')
    user_map = {str(token): int(index) for token, index in
                dataset.field2token_id['user_id'].items() if index != 0}
    item_map = {token: int(dataset.token2id('item_id', token))
                for token in exported['candidate_ids']}
    train_loader = _build_train_loader(config, train, exported['candidate_ids'])
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.bpr-', dir=output_dir.parent) as temporary:
        stage = Path(temporary) / 'model'
        stage.mkdir()
        config['checkpoint_dir'] = str(stage)
        model = BPR(config, train).to('cpu')
        best_state, validation_history = {}, []

        class ValidationTrainer(Trainer):
            def _valid_epoch(self, valid_data, show_progress=False):
                self.model.eval()
                value = _validation_ndcg(self.model, train, valid_data,
                                         exported['candidate_ids'], user_map, item_map)
                validation_history.append(value)
                # Match RecBole's >= update rule, including exact ties.
                if value >= self.best_valid_score:
                    best_state.clear()
                    best_state.update({key: tensor.detach().clone() for key, tensor in
                                       self.model.state_dict().items()})
                return value, {'ndcg@10': value}

        trainer = (ValidationTrainer if early else Trainer)(config, model)
        try:
            trainer.fit(train_loader, valid_data=valid if early else None, verbose=False,
                        saved=False, show_progress=False)
        finally:
            trainer.tensorboard.close()
        if early:
            model.load_state_dict(best_state)
        checkpoint = stage / 'bpr.pth'
        torch.save(model.state_dict(), checkpoint)
        _write_json(stage / 'id_maps.json', {'user_id_map': user_map, 'item_id_map': item_map})
        manifest = dict(schema_version=1, model_id='recbole-bpr', device='cpu',
                        seed=config['seed'], epochs_completed=len(trainer.train_loss_dict),
                        epochs_requested=parameters['epochs'],
                        validation_early_stopping=early, stopping_step=patience,
                        best_epoch=(max(i + 1 for i, value in enumerate(validation_history)
                                        if value == max(validation_history)) if early else None),
                        best_validation_ndcg_at_10=(max(validation_history) if early else None),
                        validation_ndcg_history=validation_history,
                        embedding_size=config['embedding_size'],
                        train_batch_size=config['train_batch_size'],
                        learning_rate=config['learning_rate'],
                        training_losses=list(trainer.train_loss_dict.values()),
                        negative_sampling={'distribution': 'uniform_over_train_items',
                                           'implementation': 'RecBole popularity alias, alpha=0',
                                           'positive_exclusion': 'train only', 'sample_num': 1},
                        split_hash=exported['split_hash'], dataset_hash=exported['dataset_hash'],
                        export_manifest_sha256=_hash(atomic_dir / 'export_manifest.json'),
                        loaded_row_counts=loaded_counts, checkpoint='bpr.pth', id_maps='id_maps.json',
                        checkpoint_sha256=_hash(checkpoint), id_maps_sha256=_hash(stage / 'id_maps.json'),
                        versions={'python': platform.python_version(), 'torch': torch.__version__,
                                  'recbole': recbole.__version__, 'numpy': np.__version__},
                        elapsed_seconds=time.perf_counter() - started,
                        peak_working_set_bytes=getattr(psutil.Process().memory_info(),
                                                      'peak_wset',
                                                      psutil.Process().memory_info().rss),
                        evaluation='project evaluator required; no quality claim')
        _write_json(stage / 'bpr_manifest.json', manifest)
        stage.rename(output_dir)
    return manifest


def load_bpr_scorer(manifest_path: Path) -> BPRScorer:
    """Load a trusted local tensor-only checkpoint after validating artifact hashes."""
    import torch

    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    for key in ('checkpoint', 'id_maps'):
        if Path(manifest[key]).name != manifest[key]:
            raise ValueError('artifact filenames must be local basenames')
        if _hash(manifest_path.parent / manifest[key]) != manifest[f'{key}_sha256']:
            raise ValueError(f'{key} hash mismatch')
    state = torch.load(manifest_path.parent / manifest['checkpoint'],
                       map_location='cpu', weights_only=True)
    maps = json.loads((manifest_path.parent / manifest['id_maps']).read_text(encoding='utf-8'))
    return BPRScorer(state['user_embedding.weight'].numpy(),
                     state['item_embedding.weight'].numpy(), **maps)
