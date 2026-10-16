import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from recsysedu.adapters.recbole import load_bpr_scorer
from recsysedu.contracts import RunIdentity
from recsysedu.experiments.runner import _config_hash, _settings, _verify_files, _frozen_validation

root = Path(__file__).resolve().parents[2]
config = yaml.safe_load((root / 'configs/final_experiments.yaml').read_text())
base = root / 'configs'
batch = (base / config['validation_dir']).resolve()
manifest_path = batch / 'experiment_manifest.json'
manifest = json.loads(manifest_path.read_text())
hash_file = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
for name, digest in manifest['output_hashes'].items():
    assert hash_file(batch / name) == digest
reports = {name: json.loads((batch / path / 'run_manifest.json').read_text())
           for name, path in manifest['runs'].items()}
fields = ['dataset_hash', 'split_hash', 'protocol_id', 'cohort_size',
          'candidate_universe_size', 'seen_policy', 'profile_policy', 'tie_break_policy',
          'evaluation_split', 'config_hash', 'seed', 'candidate_policy', 'k',
          'history_mode', 'split_manifest_hash']
assert len({tuple(report[key] for key in fields) for report in reports.values()}) == 1
assert all(report['metric_status'] == 'measured' for report in reports.values())
def rankings(path):
    with path.open(encoding='utf-8') as stream:
        return {row['user_id']: [x['course_id'] for x in row['items']]
                for row in map(json.loads, stream)}
content = rankings(batch / manifest['runs']['content'] / 'recommendations.jsonl')
bpr = rankings(batch / manifest['runs']['bpr'] / 'recommendations.jsonl')
assert rankings(batch / manifest['alpha_trials']['0.0'] / 'recommendations.jsonl') == content
assert rankings(batch / manifest['alpha_trials']['1.0'] / 'recommendations.jsonl') == bpr
train = pd.read_parquet(root / 'data/splits/mooccubex-pilot-v1-split-v1/train.parquet')
seen = train.groupby('user_id').course_id.apply(set).to_dict()
universe = pd.read_parquet(root / 'data/splits/mooccubex-pilot-v1-split-v1/candidate_universe.parquet').course_id.tolist()
targets = pd.read_parquet(root / 'data/splits/mooccubex-pilot-v1-split-v1/valid_cohort.parquet').set_index('user_id').course_id.to_dict()
assert set(universe) == set(train.course_id)
assert set(content) == set(targets)
all_runs = manifest['runs'] | {f'alpha_{a}': p for a, p in manifest['alpha_trials'].items()}
assert set(manifest['alpha_trials']) == {'0.0', '0.25', '0.5', '0.75', '1.0'}
audit_rows = {}
for name, relative in all_runs.items():
    report = json.loads((batch / relative / 'run_manifest.json').read_text())
    assert tuple(report[key] for key in fields) == tuple(reports['content'][key] for key in fields)
    _verify_files(batch / relative, report['output_hashes'])
    ranking = rankings(batch / relative / 'recommendations.jsonl')
    with (batch / relative / 'recommendations.jsonl').open(encoding='utf-8') as stream:
        for row in map(json.loads, stream):
            items = row['items']
            assert [item['rank'] for item in items] == list(range(1, 11))
            assert all(math.isfinite(item['score']) for item in items)
            assert items == sorted(items, key=lambda item: (-item['score'], item['course_id']))
    assert set(ranking) == set(content)
    assert all(len(items) == 10 and len(set(items)) == 10 and not (set(items) & seen[user])
               for user, items in ranking.items())
    frame = pd.read_parquet(batch / relative / 'per_user_metrics.parquet')
    for key in ['NDCG@10', 'HitRate@10', 'Recall@10', 'Precision@10']:
        assert np.isclose(frame[key].mean(), report['metrics'][key], atol=1e-12)
    union = set().union(*map(set, ranking.values()))
    assert union <= set(universe)
    assert np.isclose(len(union)/len(universe), report['metrics']['Coverage@10'])
    # Recompute from saved target and ordered Top-K without calling evaluator metrics.
    totals = dict.fromkeys(['NDCG@10', 'HitRate@10', 'Recall@10', 'Precision@10'], 0.)
    by_user = frame.set_index('user_id')
    for user, items in ranking.items():
        position = items.index(targets[user]) + 1 if targets[user] in items else None
        hit = float(position is not None)
        calculated = {'NDCG@10': 1/math.log2(position+1) if position else 0.,
                      'HitRate@10': hit, 'Recall@10': hit, 'Precision@10': hit/10}
        assert by_user.loc[user, 'target_id'] == targets[user]
        for key, value in calculated.items():
            assert np.isclose(value, by_user.loc[user, key], rtol=0, atol=1e-12)
            totals[key] += value
    for key, value in totals.items():
        assert np.isclose(value/len(ranking), report['metrics'][key], rtol=0, atol=1e-12)
    audit_rows[name] = {'users': len(ranking), 'seen_violations': 0,
                        'independent_metrics_match': True}
model_path = batch / 'artifacts/bpr/bpr_manifest.json'
model = json.loads(model_path.read_text())
assert np.isclose(model['best_validation_ndcg_at_10'], reports['bpr']['metrics']['NDCG@10'])
first, second = load_bpr_scorer(model_path), load_bpr_scorer(model_path)
for user in list(content)[:5]:
    np.testing.assert_array_equal(first.score(user, universe).scores,
                                  second.score(user, universe).scores)
effective = _settings(config | {'_base_dir': str(base)})[4]
assert _config_hash(effective) == manifest['config_hash']
assert config['freeze'] == manifest['freeze_candidate'] | {
    'validation_manifest_sha256': hash_file(manifest_path)}
identity = RunIdentity('freeze-integrity-check', 'experiment', manifest['dataset_hash'],
                       manifest['split_hash'], manifest['protocol_id'], manifest['seed'])
_frozen_validation(config, base, identity, manifest['config_hash'],
                   (base / config['output_roots']['test']).resolve())
summary = dict(status='frozen_validation_only', test_evaluated=False,
               dataset_hash=manifest['dataset_hash'], split_hash=manifest['split_hash'],
               protocol_id=manifest['protocol_id'], seed=manifest['seed'],
               config_hash=manifest['config_hash'],
               validation_manifest_sha256=hash_file(manifest_path),
               validation_batch=batch.name, chosen_bpr=effective['bpr'],
               chosen_bpr_checkpoint_sha256=model['checkpoint_sha256'],
               chosen_bpr_id_maps_sha256=model['id_maps_sha256'],
               bpr_versions=model['versions'],
               selected_alpha=manifest['selected_alpha'], component_hashes=manifest['component_hashes'],
               versions=manifest['versions'], git_revision=manifest['git_revision'],
               metrics={name: report['metrics'] for name, report in reports.items()},
               audit=dict(four_model_compatibility=True, endpoint_rankings_match=True,
                          seen_mask_pass=True, checkpoint_reload_exact=True,
                          independent_per_user_metrics_pass=True,
                          four_model_and_five_alpha_runs_verified=True,
                          frozen_validation_guard_pass=True,
                          published_artifact_hashes_pass=True))
(root / 'artifacts').mkdir(exist_ok=True)
(root / 'artifacts/core_manifest.json').write_text(json.dumps(summary, indent=2))
(root / 'results/local/final-validation-audit.json').write_text(json.dumps(audit_rows, indent=2))
print(json.dumps(summary, indent=2))
