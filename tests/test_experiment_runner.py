"""Runner boundary tests use real Parquet, evaluator, and tiny RecBole training."""

import copy
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from recsysedu.data.prepare import prepare_dataset
from recsysedu.data.split import build_temporal_split
from recsysedu.experiments.runner import run_experiment


@pytest.fixture
def experiment_case(tmp_path):
    courses = tmp_path / 'course.json'
    users = tmp_path / 'user.json'
    courses.write_text(json.dumps([
        {'id': f'C_{i}', 'name': f'Computer science {i}', 'about': 'Programming algorithms'}
        for i in range(1, 4)]), encoding='utf-8')
    users.write_text(json.dumps([
        dict(id=f'U_{i}', course_order=order,
             enroll_time=['2020-01-01', '2020-02-01', '2020-03-01'])
        for i, order in enumerate(([1, 2, 3], [2, 3, 1], [3, 1, 2]))]), encoding='utf-8')
    prepared, split = tmp_path / 'prepared', tmp_path / 'split'
    prepare_dataset(courses, users, prepared, dataset_version='runner-fixture',
                    time_basis='source_local_naive', sample_users=0, seed=17)
    build_temporal_split(prepared / 'interactions.parquet', prepared / 'courses.parquet',
                         split, split_version='runner-split', seed=17)
    return dict(prepared_dir=str(prepared), split_dir=str(split), seed=17,
                frozen=False, release_mode=True,
                content={'analyzer': 'char', 'ngram_range': [2, 4], 'min_df': 1},
                bpr={'epochs': 1, 'embedding_size': 4,
                     'train_batch_size': 8, 'learning_rate': 0.001},
                hybrid={'alphas': [0, 0.5, 1]})


def _batch(root):
    batches = list(root.iterdir())
    assert len(batches) == 1
    return batches[0]


def _read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def _freeze(config, batch):
    result = copy.deepcopy(config)
    freeze = _read(batch / 'experiment_manifest.json')['freeze_candidate']
    freeze['validation_manifest_sha256'] = hashlib.sha256(
        (batch / 'experiment_manifest.json').read_bytes()).hexdigest()
    result.update(frozen=True, validation_dir=str(batch),
                  freeze=freeze)
    return result


def test_runner_refuses_test_before_config_is_marked_frozen(tmp_path, experiment_case):
    with pytest.raises(ValueError, match='frozen'):
        run_experiment(experiment_case, split='test', output_root=tmp_path / 'test')
    assert not (tmp_path / 'test').exists()


def test_default_bpr_settings_reject_early_stopped_artifact(tmp_path, experiment_case):
    from recsysedu.contracts import RunIdentity
    from recsysedu.experiments.runner import _bpr_identity, _settings

    parameters = _settings(experiment_case)[2]
    identity = RunIdentity('artifact-check', 'bpr', 'dataset', 'split',
                           'leave_last_two_out_v1', 17)
    manifest = dict(dataset_hash='dataset', split_hash='split', epochs_requested=1,
                    epochs_completed=1, validation_early_stopping=True, stopping_step=2,
                    embedding_size=4, train_batch_size=8, learning_rate=0.001, seed=17)
    path = tmp_path / 'manifest.json'
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='validation_early_stopping'):
        _bpr_identity(path, identity, parameters)
    assert parameters['validation_early_stopping'] is False
    assert parameters['stopping_step'] == 3
    # Legacy fixed-budget manifests had no early-stopping fields.
    del manifest['validation_early_stopping'], manifest['stopping_step']
    path.write_text(json.dumps(manifest))
    assert _bpr_identity(path, identity, parameters) == manifest


@pytest.mark.integration
def test_runner_accepts_early_stopped_checkpoint_budget(tmp_path, experiment_case):
    experiment_case['bpr'].update(epochs=8, validation_early_stopping=True, stopping_step=1)
    from recsysedu.experiments.runner import evaluate_model
    report = evaluate_model(experiment_case, model_id='bpr', split='valid',
                            output_root=tmp_path / 'early')
    batch = _batch(tmp_path / 'early')
    model = _read(batch / 'artifacts/bpr/bpr_manifest.json')
    assert model['epochs_requested'] == 8
    assert model['epochs_completed'] <= 8
    assert report['model_config']['validation_early_stopping'] is True
    assert report['metrics']['NDCG@10'] == pytest.approx(model['best_validation_ndcg_at_10'])


@pytest.mark.integration
def test_runner_runs_four_models_on_one_shared_valid_protocol(tmp_path, experiment_case):
    root = tmp_path / 'valid'
    reports = run_experiment(experiment_case, split='valid', output_root=root)
    assert [r['model_id'] for r in reports] == ['popularity', 'content', 'bpr', 'hybrid']
    assert len({r['run_id'] for r in reports}) == 4
    assert len({(r['dataset_hash'], r['split_hash'], r['protocol_id'], r['cohort_size'])
                for r in reports}) == 1
    batch = _batch(root)
    manifest = _read(batch / 'experiment_manifest.json')
    assert manifest['output_root'] == '..'
    assert not Path(manifest['output_root']).is_absolute()
    assert manifest['git_revision'] and manifest['evaluation_split'] == 'valid'
    assert set(manifest['runs']) == {'popularity', 'content', 'bpr', 'hybrid'}
    for report in reports:
        saved = _read(batch / manifest['runs'][report['model_id']] / 'run_manifest.json')
        assert saved == report
        assert saved['config_hash'] == manifest['config_hash']
        assert saved['git_revision'] == manifest['git_revision']
    selection = _read(batch / 'alpha_selection.json')
    for trial in selection['validation_runs']:
        run = _read(batch / manifest['alpha_trials'][str(trial['alpha'])] / 'run_manifest.json')
        assert run['model_config']['alpha'] == trial['alpha']
        assert run['model_config']['components'] == manifest['component_hashes']
    for name, digest in manifest['output_hashes'].items():
        assert hashlib.sha256((batch / name).read_bytes()).hexdigest() == digest


@pytest.mark.integration
def test_runner_creates_distinct_run_ids_and_never_overwrites(tmp_path, experiment_case):
    root = tmp_path / 'valid'
    first = run_experiment(experiment_case, split='valid', output_root=root)
    before = {p: p.read_bytes() for p in root.rglob('*') if p.is_file()}
    second = run_experiment(experiment_case, split='valid', output_root=root)
    assert not {r['run_id'] for r in first} & {r['run_id'] for r in second}
    assert len(list(root.iterdir())) == 2
    assert all(p.read_bytes() == value for p, value in before.items())


@pytest.mark.integration
def test_frozen_test_reuses_selected_validation_checkpoint_and_alpha(tmp_path, experiment_case):
    valid_root = tmp_path / 'valid'
    run_experiment(experiment_case, split='valid', output_root=valid_root)
    batch = _batch(valid_root)
    frozen = _freeze(experiment_case, batch)
    reports = run_experiment(frozen, split='test', output_root=tmp_path / 'test')
    valid = _read(batch / 'experiment_manifest.json')
    test = _read(_batch(tmp_path / 'test') / 'experiment_manifest.json')
    assert test['component_hashes'] == valid['component_hashes']
    assert test['selected_alpha'] == valid['selected_alpha']
    assert test['validation_manifest_sha256'] == hashlib.sha256(
        (batch / 'experiment_manifest.json').read_bytes()).hexdigest()
    assert all(r['seen_policy'] == 'train_plus_valid' for r in reports)
    assert all(r['profile_policy'] == 'train_only' for r in reports)


@pytest.mark.parametrize('field', ['dataset_hash', 'split_hash', 'config_hash',
                                 'validation_manifest_sha256'])
@pytest.mark.integration
def test_runner_rejects_stale_freeze_hashes(tmp_path, experiment_case, field):
    root = tmp_path / 'valid'
    run_experiment(experiment_case, split='valid', output_root=root)
    config = _freeze(experiment_case, _batch(root))
    config['freeze'][field] = 'wrong'
    with pytest.raises(ValueError, match=field):
        run_experiment(config, split='test', output_root=tmp_path / 'test')
    assert not (tmp_path / 'test').exists()


@pytest.mark.integration
def test_runner_rejects_changed_configuration_or_validation_artifact(tmp_path, experiment_case):
    root = tmp_path / 'valid'
    run_experiment(experiment_case, split='valid', output_root=root)
    batch = _batch(root)
    config = _freeze(experiment_case, batch)
    config['content']['ngram_range'] = [1, 2]
    with pytest.raises(ValueError, match='config_hash'):
        run_experiment(config, split='test', output_root=tmp_path / 'changed')
    config = _freeze(experiment_case, batch)
    (batch / 'alpha_selection.json').write_text('{}', encoding='utf-8')
    with pytest.raises(ValueError, match='hash'):
        run_experiment(config, split='test', output_root=tmp_path / 'tampered')
    assert not (tmp_path / 'changed').exists()
    assert not (tmp_path / 'tampered').exists()


@pytest.mark.integration
def test_runner_requires_distinct_test_output_root(tmp_path, experiment_case):
    root = tmp_path / 'valid'
    run_experiment(experiment_case, split='valid', output_root=root)
    with pytest.raises(ValueError, match='distinct'):
        run_experiment(_freeze(experiment_case, _batch(root)), split='test', output_root=root)


@pytest.mark.integration
@pytest.mark.parametrize('nested', [False, True])
def test_runner_protects_actual_validation_batch_after_it_is_moved(
        tmp_path, experiment_case, nested):
    original_root = tmp_path / 'valid'
    run_experiment(experiment_case, split='valid', output_root=original_root)
    moved_batch = tmp_path / 'moved-validation-batch'
    _batch(original_root).rename(moved_batch)
    frozen = _freeze(experiment_case, moved_batch)
    before = {p.relative_to(moved_batch): p.read_bytes()
              for p in moved_batch.rglob('*') if p.is_file()}
    output_root = moved_batch / 'test-output' if nested else moved_batch
    with pytest.raises(ValueError, match='distinct'):
        run_experiment(frozen, split='test', output_root=output_root)
    after = {p.relative_to(moved_batch): p.read_bytes()
             for p in moved_batch.rglob('*') if p.is_file()}
    assert after == before
    assert not (moved_batch / 'test-output').exists()
    assert not list(moved_batch.glob('test-*'))


@pytest.mark.parametrize('field', ['dataset_hash', 'split_hash', 'protocol_id'])
def test_runner_rejects_cross_dataset_or_cross_protocol_model_artifacts(
        tmp_path, experiment_case, field):
    split = _read(tmp_path / 'split/split_manifest.json')
    artifact = tmp_path / 'bpr_manifest.json'
    artifact.write_text(json.dumps(dict(dataset_hash=split['dataset_hash'],
                                       split_hash=split['split_hash'],
                                       protocol_id=split['protocol_id']) | {field: 'wrong'}),
                        encoding='utf-8')
    experiment_case['bpr']['manifest_path'] = str(artifact)
    with pytest.raises(ValueError, match=field):
        run_experiment(experiment_case, split='valid', output_root=tmp_path / 'valid')
    assert not (tmp_path / 'valid').exists()


def test_runner_rejects_tampered_prepared_metadata(tmp_path, experiment_case):
    path = tmp_path / 'prepared/courses.parquet'
    path.write_bytes(path.read_bytes() + b'changed')
    with pytest.raises(ValueError, match='courses.parquet'):
        run_experiment(experiment_case, split='valid', output_root=tmp_path / 'valid')
    assert not (tmp_path / 'valid').exists()


def test_runner_release_mode_requires_git_revision(tmp_path, experiment_case, monkeypatch):
    import recsysedu.experiments.runner as runner

    monkeypatch.setattr(runner, '_git_revision', lambda: None)
    with pytest.raises(ValueError, match='Git revision'):
        run_experiment(experiment_case, split='valid', output_root=tmp_path / 'valid')
    assert not (tmp_path / 'valid').exists()


def test_runner_failed_batch_publishes_no_partial_models(tmp_path, experiment_case, monkeypatch):
    import recsysedu.experiments.runner as runner

    def fail(*args, **kwargs):
        raise RuntimeError('bounded training failure')

    monkeypatch.setattr(runner, 'train_bpr', fail)
    with pytest.raises(RuntimeError, match='training failure'):
        run_experiment(experiment_case, split='valid', output_root=tmp_path / 'valid')
    assert list((tmp_path / 'valid').iterdir()) == []


def test_evaluate_one_popularity_model_does_not_require_training(tmp_path, experiment_case):
    from recsysedu.experiments.runner import evaluate_model

    experiment_case['bpr']['manifest_path'] = 'does-not-exist.json'
    report = evaluate_model(experiment_case, model_id='popularity', split='valid',
                            output_root=tmp_path / 'one')
    assert report['model_id'] == 'popularity'
    batch = _batch(tmp_path / 'one')
    manifest = _read(batch / 'experiment_manifest.json')
    assert set(manifest['runs']) == {'popularity'}
    assert not (batch / 'artifacts/bpr').exists()


@pytest.mark.parametrize('key,value', [('embedding_size', 0), ('learning_rate', float('nan')),
                                     ('seed', 19), ('reg_weight', 100), ('use_gpu', True)])
def test_runner_rejects_unsupported_or_invalid_bpr_settings(
        tmp_path, experiment_case, key, value):
    experiment_case['bpr'][key] = value
    with pytest.raises(ValueError):
        run_experiment(experiment_case, split='valid', output_root=tmp_path / 'bad')
    assert not (tmp_path / 'bad').exists()


@pytest.mark.parametrize('key,value', [('selection_split', 'test'),
                                     ('primary_metric', 'Recall@20'),
                                     ('normalization', 'none')])
def test_runner_rejects_hybrid_settings_that_change_the_protocol(
        tmp_path, experiment_case, key, value):
    experiment_case['hybrid'][key] = value
    with pytest.raises(ValueError):
        run_experiment(experiment_case, split='valid', output_root=tmp_path / 'bad')
    assert not (tmp_path / 'bad').exists()


@pytest.mark.integration
def test_cli_train_and_experiments_consume_relative_configuration_paths(
        tmp_path, experiment_case, capsys):
    from recsysedu.cli import main

    config_dir = tmp_path / 'configs'
    config_dir.mkdir()
    bpr = config_dir / 'bpr.yaml'
    bpr.write_text(yaml.safe_dump(experiment_case['bpr'] | {
        'seed': 17, 'split_dir': '../split', 'output_dir': '../trained'}), encoding='utf-8')
    assert main(['train', '--model', 'bpr', '--config', str(bpr)]) == 0
    capsys.readouterr()
    manifest = _read(tmp_path / 'trained/bpr_manifest.json')
    assert manifest['epochs_completed'] == 1
    assert manifest['protocol_id'] == 'leave_last_two_out_v1'
    assert manifest['git_revision']
    before = (tmp_path / 'trained/bpr.pth').read_bytes()
    assert main(['train', '--model', 'bpr', '--config', str(bpr)]) == 1
    assert (tmp_path / 'trained/bpr.pth').read_bytes() == before
    capsys.readouterr()
    config = experiment_case | dict(
        prepared_dir='../prepared', split_dir='../split',
        bpr={'config_path': 'bpr.yaml', 'manifest_path': '../trained/bpr_manifest.json'},
        output_roots={'valid': '../cli-valid'})
    path = config_dir / 'experiments.yaml'
    path.write_text(yaml.safe_dump(config), encoding='utf-8')
    assert main(['experiments', '--split', 'valid', '--config', str(path)]) == 0
    assert 'NDCG@10' in capsys.readouterr().out
    batch = _batch(tmp_path / 'cli-valid')
    assert len(_read(batch / 'experiment_manifest.json')['runs']) == 4
    assert main(['evaluate', '--model', 'popularity', '--split', 'valid',
                 '--config', str(path), '--output', str(tmp_path / 'cli-one')]) == 0
    assert set(_read(_batch(tmp_path / 'cli-one') / 'experiment_manifest.json')['runs']) == {
        'popularity'}
    # The frozen test is self-contained in the validation batch. The original
    # separately-trained source may be moved after validation publication.
    (tmp_path / 'trained/bpr_manifest.json').unlink()
    frozen = _freeze(config | {'_base_dir': str(config_dir)}, batch)
    reports = run_experiment(frozen, split='test', output_root=tmp_path / 'cli-test')
    assert len(reports) == 4


@pytest.mark.integration
def test_validation_mutation_during_test_prevents_batch_publication(
        tmp_path, experiment_case, monkeypatch):
    import recsysedu.experiments.runner as runner

    root = tmp_path / 'valid'
    run_experiment(experiment_case, split='valid', output_root=root)
    batch = _batch(root)
    frozen = _freeze(experiment_case, batch)
    evaluate = runner.evaluate_run

    def mutate_after_evaluation(*args, **kwargs):
        report = evaluate(*args, **kwargs)
        (batch / 'alpha_selection.json').write_text('{}', encoding='utf-8')
        return report

    monkeypatch.setattr(runner, 'evaluate_run', mutate_after_evaluation)
    with pytest.raises(ValueError, match='hash'):
        run_experiment(frozen, split='test', output_root=tmp_path / 'test')
    assert list((tmp_path / 'test').iterdir()) == []
