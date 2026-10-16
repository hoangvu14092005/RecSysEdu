import hashlib
import json

import pytest

from recsysedu.demo.artifacts import load_bundle


def export(*args):
    from recsysedu.demo.export import export_demo_bundle
    return export_demo_bundle(*args)


def rewrite_run(run, **updates):
    """Alter coherent producer output to exercise semantic compatibility checks."""
    path = run / 'run_manifest.json'
    manifest = json.loads(path.read_text('utf-8'))
    manifest.update(updates)
    path.write_text(json.dumps(manifest), encoding='utf-8')
    batch = run.parents[1]
    path = batch / 'experiment_manifest.json'
    manifest = json.loads(path.read_text('utf-8'))
    manifest.update({k: v for k, v in updates.items()
                     if k in ('dataset_hash', 'split_hash', 'protocol_id', 'evaluation_split')})
    manifest['output_hashes'][(run / 'run_manifest.json').relative_to(batch).as_posix()] = (
        hashlib.sha256((run / 'run_manifest.json').read_bytes()).hexdigest())
    path.write_text(json.dumps(manifest), encoding='utf-8')


def test_exporter_builds_real_bundle_from_compatible_runs(demo_runs, tmp_path):
    path = tmp_path / 'bundle.json'
    result = export(demo_runs, ['U_0', 'U_3'], path)
    assert load_bundle(path) == result
    assert result['meta']['data_mode'] == 'real'
    assert result['meta']['dataset_version'] == 'snapshot-test-fixture'
    assert result['meta']['evidence_level'] == 'offline_run'
    assert result['paths'] == []
    assert result['users'][0]['observed_course_ids'] == ['C_1']
    assert result['users'][0]['profile_course_ids'] == ['C_1']
    recs = {(r['user_id'], r['model_id']): r for r in result['recommendations']}
    assert recs['U_3', 'popularity']['items'][0]['course_id'] == 'C_1'
    assert recs['U_3', 'content']['items'][0]['course_id'] == 'C_5'
    assert all(len(r['items']) <= 10 for r in recs.values())
    assert all('C_4' != x['course_id'] for x in recs['U_3', 'content']['items'])
    assert all(r['metrics']['NDCG@10'] >= 0 for r in result['runs'])
    assert any('nội dung' in text for text in recs['U_3', 'content']['items'][0]['evidence'])


@pytest.mark.parametrize('field,value', [
    ('dataset_hash', 'other'), ('split_hash', 'other'), ('protocol_id', 'other'),
    ('history_mode', 'demo'), ('seen_policy', 'train_plus_valid'),
    ('evaluation_split', 'test'), ('config_hash', 'other'),
])
def test_exporter_rejects_mixed_identity_or_policy(demo_runs, tmp_path, field, value):
    rewrite_run(demo_runs[1], **{field: value})
    with pytest.raises(ValueError):
        export(demo_runs, ['U_0'], tmp_path / 'bundle.json')
    assert not (tmp_path / 'bundle.json').exists()


@pytest.mark.parametrize('fault', ['stale', 'missing', 'unknown_user', 'duplicate_model',
                                 'incomplete_batch_manifest'])
def test_exporter_rejects_stale_incomplete_or_ambiguous_input(demo_runs, tmp_path, fault):
    users = ['U_0']
    if fault == 'stale':
        with (demo_runs[0] / 'recommendations.jsonl').open('a') as stream:
            stream.write('{}\n')
    elif fault == 'missing':
        (demo_runs[0] / 'per_user_metrics.parquet').unlink()
    elif fault == 'unknown_user':
        users = ['unknown']
    elif fault == 'duplicate_model':
        demo_runs.append(demo_runs[0])
    else:
        batch = demo_runs[1].parents[1]
        path = batch / 'experiment_manifest.json'
        manifest = json.loads(path.read_text('utf-8'))
        del manifest['output_hashes']['artifacts/content/course_features.npz']
        path.write_text(json.dumps(manifest), encoding='utf-8')
        (batch / 'artifacts/content/course_features.npz').unlink()
    with pytest.raises(ValueError):
        export(demo_runs, users, tmp_path / 'bundle.json')


def test_exporter_marks_unavailable_metrics_without_inventing_zero(demo_runs, tmp_path):
    rewrite_run(demo_runs[0], metric_status='not_available', metrics=None)
    result = export(demo_runs, ['U_0'], tmp_path / 'bundle.json')
    run = next(r for r in result['runs'] if r['model_id'] == 'popularity')
    assert run['metric_status'] == 'not_available'
    assert run['metrics'] is None


def test_exporter_preserves_existing_snapshot_on_failure(demo_runs, tmp_path):
    path = tmp_path / 'bundle.json'
    export(demo_runs, ['U_0'], path)
    before = path.read_bytes()
    with pytest.raises(ValueError):
        export(demo_runs, ['unknown'], path)
    assert path.read_bytes() == before


@pytest.mark.parametrize('same_batch', [False, pytest.param(True, marks=pytest.mark.integration)])
def test_exporter_detects_manifest_changed_while_reading(
        demo_runs, tmp_path, monkeypatch, same_batch):
    import recsysedu.demo.export as module

    if same_batch:
        from recsysedu.experiments.runner import run_experiment

        root = tmp_path / 'full-validation'
        run_experiment(dict(prepared_dir=str(tmp_path / 'prepared'),
                            split_dir=str(tmp_path / 'split'), seed=17,
                            bpr={'epochs': 1, 'embedding_size': 4, 'train_batch_size': 8},
                            hybrid={'alphas': [0, 1]}), split='valid', output_root=root)
        batch = next(root.iterdir())
        manifest = json.loads((batch / 'experiment_manifest.json').read_text('utf-8'))
        demo_runs = [batch / relative for relative in manifest['runs'].values()]
    original = module._verify
    batch = demo_runs[0].parents[1]
    changed = False

    def verify_then_change(root, hashes):
        nonlocal changed
        original(root, hashes)
        if root == batch and not changed:
            path = batch / 'experiment_manifest.json'
            path.write_bytes(path.read_bytes() + b'\n')
            changed = True

    monkeypatch.setattr(module, '_verify', verify_then_change)
    with pytest.raises(ValueError, match='changed'):
        export(demo_runs, ['U_0'], tmp_path / 'bundle.json')
    assert not (tmp_path / 'bundle.json').exists()


def test_exporter_requires_hash_bound_snapshot_sources(demo_runs, tmp_path):
    batch = demo_runs[0].parents[1]
    manifest_path = batch / 'experiment_manifest.json'
    manifest = json.loads(manifest_path.read_text('utf-8'))
    del manifest['output_hashes']['snapshot_inputs/courses.parquet']
    manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
    with pytest.raises(ValueError):
        export(demo_runs, ['U_0'], tmp_path / 'bundle.json')


def test_exporter_refuses_snapshot_inside_immutable_batch(demo_runs):
    with pytest.raises(ValueError, match='immutable'):
        export(demo_runs, ['U_0'], demo_runs[0] / 'snapshot.json')


@pytest.mark.integration
def test_test_snapshot_masks_valid_but_profile_remains_train_only(demo_runs, tmp_path):
    from recsysedu.experiments.runner import run_experiment

    config = dict(prepared_dir=str(tmp_path / 'prepared'), split_dir=str(tmp_path / 'split'),
                  seed=17, content={'analyzer': 'char', 'ngram_range': [2, 4], 'min_df': 1},
                  bpr={'epochs': 1, 'embedding_size': 4, 'train_batch_size': 8},
                  hybrid={'alphas': [0, 1]})
    root = tmp_path / 'four-model-valid'
    run_experiment(config, split='valid', output_root=root)
    batch = next(root.iterdir())
    path = batch / 'experiment_manifest.json'
    manifest = json.loads(path.read_text('utf-8'))
    config.update(frozen=True, validation_dir=str(batch), freeze=manifest['freeze_candidate'] | {
        'validation_manifest_sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    root = tmp_path / 'four-model-test'
    run_experiment(config, split='test', output_root=root)
    batch = next(root.iterdir())
    manifest = json.loads((batch / 'experiment_manifest.json').read_text('utf-8'))
    bundle = export([batch / relative for relative in manifest['runs'].values()],
                    ['U_0'], tmp_path / 'test-bundle.json')
    assert bundle['users'][0]['profile_course_ids'] == ['C_1']
    assert bundle['users'][0]['observed_course_ids'] == ['C_1', 'C_2']
    assert all(not {'C_1', 'C_2'} & {x['course_id'] for x in r['items']}
               for r in bundle['recommendations'])
    assert {r['model_id'] for r in bundle['runs']} == {'popularity', 'content', 'bpr', 'hybrid'}
