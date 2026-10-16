import csv
import json
import shutil
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import pytest
import yaml

from recsysedu.adapters.recbole import (
    BPRScorer, export_atomic_files, load_bpr_scorer, train_bpr,
)
from recsysedu.contracts import ScoreResult
from recsysedu.data.prepare import prepare_dataset
from recsysedu.data.split import build_temporal_split


@pytest.fixture
def split_dir(tmp_path):
    return _make_split(tmp_path)


def _make_split(tmp_path, *, cold=True):
    tmp_path.mkdir(parents=True, exist_ok=True)
    courses = ['C_01', 'C_2', 'C_3', 'C_4', 'C_cold']
    (tmp_path / 'course.json').write_text(
        '\n'.join(json.dumps({'id': item}) for item in courses), encoding='utf-8')
    histories = [('U_01', ['C_01', 'C_2', 'C_3', 'C_cold' if cold else 'C_4']),
                 ('U_2', ['C_3', 'C_4', 'C_01', 'C_2']),
                 ('U_3', ['C_2', 'C_01', 'C_4', 'C_3'])]
    (tmp_path / 'user.json').write_text('\n'.join(
        json.dumps({'id': user, 'course_order': items,
                    'enroll_time': ['2020-01-01', '2020-02-01',
                                    '2020-03-01', '2020-04-01']})
        for user, items in histories), encoding='utf-8')
    prepared, split = tmp_path / 'prepared', tmp_path / 'split'
    prepare_dataset(tmp_path / 'course.json', tmp_path / 'user.json', prepared,
                    dataset_version='tiny', time_basis='source_local_naive',
                    sample_users=0, seed=17)
    build_temporal_split(prepared / 'interactions.parquet', prepared / 'courses.parquet',
                         split, split_version='tiny', seed=17)
    return split


def test_atomic_export_uses_tabs_source_ids_and_exact_split_counts(split_dir, tmp_path):
    output = tmp_path / 'atomic'
    manifest = export_atomic_files(split_dir, output)
    for name, count in [('train', 6), ('valid', 3), ('test', 3)]:
        path = output / 'recsysedu' / f'recsysedu.{name}.inter'
        assert path.read_text(encoding='utf-8').splitlines()[0] == (
            'user_id:token\titem_id:token\ttimestamp:float')
        with path.open(encoding='utf-8', newline='') as source:
            rows = list(csv.DictReader(source, delimiter='\t'))
        expected = pq.read_table(split_dir / f'{name}.parquet').to_pylist()
        assert [(r['user_id:token'], r['item_id:token']) for r in rows] == [
            (r['user_id'], r['course_id']) for r in expected]
        assert len(rows) == manifest['row_counts'][name] == count
        assert float(rows[0]['timestamp:float']) == {
            'train': 1577836800, 'valid': 1583020800, 'test': 1585699200}[name]
    assert 'C_cold' in (output / 'recsysedu/recsysedu.test.inter').read_text()


def test_atomic_export_declares_benchmark_files_and_never_resplits(split_dir, tmp_path):
    manifest = export_atomic_files(split_dir, tmp_path / 'atomic')
    assert manifest['benchmark_filename'] == ['train', 'valid', 'test']
    source = json.loads((split_dir / 'split_manifest.json').read_text())
    assert manifest['split_hash'] == source['split_hash']
    assert manifest['candidate_ids'] == ['C_01', 'C_2', 'C_3', 'C_4']
    with pytest.raises(ValueError, match='exists'):
        export_atomic_files(split_dir, tmp_path / 'atomic')


def test_export_rejects_modified_split_before_publishing(split_dir, tmp_path):
    table = pq.read_table(split_dir / 'train.parquet').slice(1)
    pq.write_table(table, split_dir / 'train.parquet')
    with pytest.raises(ValueError, match='hash'):
        export_atomic_files(split_dir, tmp_path / 'atomic')
    assert not (tmp_path / 'atomic').exists()


def test_bpr_scorer_maps_source_ids_and_rejects_padding_or_unknown_ids():
    scorer = BPRScorer(
        user_embeddings=np.array([[0., 0.], [2., 3.]]),
        item_embeddings=np.array([[0., 0.], [4., 5.], [6., 7.]]),
        user_id_map={'U_01': 1}, item_id_map={'C_01': 2, 'C_2': 1})
    result = scorer.score('U_01', ['C_2', 'C_01'])
    assert isinstance(result, ScoreResult)
    assert result.course_ids == ('C_2', 'C_01')
    np.testing.assert_array_equal(result.scores, [23., 33.])
    assert result.fallback_status == 'none'
    assert scorer.score('U_01', []).course_ids == ()
    for user, items in [('[PAD]', ['C_2']), ('unknown', ['C_2']),
                        ('U_01', ['[PAD]']), ('U_01', ['C_cold']),
                        ('U_01', ['C_2', 'C_2'])]:
        with pytest.raises(ValueError):
            scorer.score(user, items)
    with pytest.raises(ValueError, match='padding'):
        BPRScorer(np.zeros((2, 2)), np.zeros((2, 2)), {'U_01': 0}, {'C_2': 1})


@pytest.mark.integration
@pytest.mark.parametrize('all_warm', [False, True])
def test_tiny_bpr_checkpoint_reloads_and_scores_known_user_items(
        split_dir, tmp_path, all_warm, monkeypatch):
    if all_warm:
        # Every user consumed the whole train universe across the three splits.
        # This must not make the train-only negative sampler reject the dataset.
        split_dir = _make_split(tmp_path / 'warm', cold=False)
    atomic = tmp_path / 'atomic'
    export_atomic_files(split_dir, atomic)
    config = yaml.safe_load((Path(__file__).parents[1] / 'configs/bpr.yaml').read_text())
    config.update(atomic_dir=str(atomic), epochs=2, embedding_size=8, train_batch_size=4)
    config_path = tmp_path / 'bpr.yaml'
    config_path.write_text(yaml.safe_dump(config), encoding='utf-8')
    # The host application's flags must not override the validated YAML budget.
    monkeypatch.setattr('sys.argv', ['host-app', '--epochs=3'])
    trained = train_bpr(config_path, tmp_path / 'model')
    assert trained['loaded_row_counts'] == {'train': 6, 'valid': 3, 'test': 3}
    assert trained['device'] == 'cpu'
    assert trained['epochs_completed'] == 2
    scorer = load_bpr_scorer(tmp_path / 'model/bpr_manifest.json')
    result = scorer.score('U_01', ['C_4', 'C_01', 'C_2'])
    assert result.course_ids == ('C_4', 'C_01', 'C_2')
    assert np.isfinite(result.scores).all()
    assert len(set(result.scores)) > 1
    restored = load_bpr_scorer(tmp_path / 'model/bpr_manifest.json')
    np.testing.assert_array_equal(restored.score('U_01', result.course_ids).scores,
                                  result.scores)
    with pytest.raises(ValueError):
        scorer.score('U_01', ['C_cold'])

    # Restore with the real upstream class and compare inference, independently
    # of the adapter's NumPy implementation.
    import torch
    from recbole.config import Config
    from recbole.data import create_dataset
    from recbole.data.interaction import Interaction
    from recbole.model.general_recommender.bpr import BPR

    upstream_config = Config(model='BPR', dataset='recsysedu', config_dict={
        'data_path': str(atomic), 'benchmark_filename': ['train', 'valid', 'test'],
        'use_gpu': False, 'embedding_size': 8})
    upstream = BPR(upstream_config, create_dataset(upstream_config))
    upstream.load_state_dict(torch.load(tmp_path / 'model/bpr.pth', weights_only=True))
    interaction = Interaction({
        'user_id': torch.tensor([scorer.user_id_map['U_01']] * 3),
        'item_id': torch.tensor([scorer.item_id_map[item] for item in result.course_ids])})
    np.testing.assert_allclose(upstream.predict(interaction).detach().numpy(), result.scores,
                               rtol=1e-6, atol=1e-7)

    # A modified tensor artifact must never be silently loaded.
    shutil.copytree(tmp_path / 'model', tmp_path / 'tampered')
    with (tmp_path / 'tampered/bpr.pth').open('ab') as target:
        target.write(b'changed')
    with pytest.raises(ValueError, match='hash'):
        load_bpr_scorer(tmp_path / 'tampered/bpr_manifest.json')


@pytest.mark.integration
def test_training_sampler_uses_train_universe_without_excluding_heldout_positives(
        split_dir, tmp_path):
    from recbole.config import Config
    from recbole.data import create_dataset
    from recsysedu.adapters.recbole import _build_train_loader

    np.random.seed(17)
    atomic = tmp_path / 'atomic'
    exported = export_atomic_files(split_dir, atomic)
    config = Config(model='BPR', dataset='recsysedu', config_dict={
        'data_path': str(atomic), 'benchmark_filename': ['train', 'valid', 'test'],
        'use_gpu': False, 'worker': 0, 'train_batch_size': 4,
        'train_neg_sample_args': {'distribution': 'popularity', 'sample_num': 1, 'alpha': 0.0}})
    dataset = create_dataset(config)
    train, _, _ = dataset.build()
    loader = _build_train_loader(config, train, exported['candidate_ids'])
    samples = []
    for _ in range(20):
        for batch in loader:
            users = dataset.id2token('user_id', batch['user_id'].numpy())
            negatives = dataset.id2token('item_id', batch['neg_item_id'].numpy())
            samples.extend(zip(users, negatives))
    assert {item for _, item in samples} <= {'C_01', 'C_2', 'C_3', 'C_4'}
    train_pairs = {(r['user_id'], r['course_id']) for r in
                   pq.read_table(split_dir / 'train.parquet').to_pylist()}
    assert not (set(samples) & train_pairs)
    assert ('U_01', 'C_3') in samples  # validation positive is not a sampler exclusion
    with pytest.raises(ValueError, match='no unseen item'):
        _build_train_loader(config, dataset, exported['candidate_ids'])
