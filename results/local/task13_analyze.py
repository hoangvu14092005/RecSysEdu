import hashlib
import json
from pathlib import Path
import pandas as pd
from recsysedu.demo.export import export_demo_bundle
from recsysedu.demo.artifacts import load_bundle

root = Path(__file__).resolve().parents[2]
batch, = (root / 'results/local/pilot-final/test').glob('test-*')
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
manifest = read(batch / 'experiment_manifest.json')
assert manifest['evaluation_split'] == 'test'
for name, digest in manifest['output_hashes'].items():
    assert sha(batch / name) == digest, name
reports, cohort = {}, {}
universe = set(pd.read_parquet(root / 'data/splits/mooccubex-pilot-v1-split-v1/candidate_universe.parquet').course_id)
train = pd.read_parquet(root / 'data/splits/mooccubex-pilot-v1-split-v1/train.parquet')
valid = pd.read_parquet(root / 'data/splits/mooccubex-pilot-v1-split-v1/valid.parquet')
seen = train.groupby('user_id').course_id.agg(set).to_dict()
for u, c in valid[['user_id', 'course_id']].itertuples(index=False, name=None): seen[u].add(c)
for model, rel in manifest['runs'].items():
    directory = batch / rel
    report = read(directory / 'run_manifest.json')
    frame = pd.read_parquet(directory / 'per_user_metrics.parquet')
    metric_cols = ['NDCG@10', 'HitRate@10', 'Recall@10', 'Precision@10']
    groups = {'low_1_4': set(frame.loc[frame.train_history_count <= 4, 'user_id']),
              'middle_5_19': set(frame.loc[frame.train_history_count.between(5,19), 'user_id']),
              'high_20_plus': set(frame.loc[frame.train_history_count >= 20, 'user_id'])}
    unions = {group: set() for group in groups}
    all_items = set()
    by_user = frame.set_index('user_id')
    misses = 0
    for line in (directory / 'recommendations.jsonl').open(encoding='utf-8'):
        row = json.loads(line)
        ids = [item['course_id'] for item in row['items']]
        assert len(ids) == len(set(ids)) == 10
        assert set(ids) <= universe and not set(ids) & seen[row['user_id']]
        assert [item['rank'] for item in row['items']] == list(range(1,11))
        assert row['items'] == sorted(row['items'], key=lambda item: (-item['score'], item['course_id']))
        target, = row['target_ids']
        hit = float(target in ids)
        import math
        ndcg = 1 / math.log2(ids.index(target)+2) if hit else 0.
        expected = [ndcg, hit, hit, hit / 10]
        for name, value in zip(metric_cols, expected):
            assert abs(by_user.loc[row['user_id'], name] - value) < 1e-12
        misses += not hit
        all_items.update(ids)
        for group, users in groups.items():
            if row['user_id'] in users: unions[group].update(ids)
    for name in metric_cols: assert abs(frame[name].mean()-report['metrics'][name]) < 1e-12
    assert abs(len(all_items)/len(universe)-report['metrics']['Coverage@10']) < 1e-12
    reports[model] = {k: report[k] for k in ('metrics','duration_seconds','cohort_size','fallback_counts','short_list_user_count','cold_target_count')}
    reports[model]['misses'] = misses
    cohort[model] = {group: {'n':len(users), **frame.loc[frame.user_id.isin(users),metric_cols].mean().to_dict(),
                              'Coverage@10':len(unions[group])/len(universe)} for group,users in groups.items()}
    if model == 'popularity':
        ordered = frame.sort_values(['train_history_count','user_id'])
        selected = [ordered.iloc[i].user_id for i in (0,len(ordered)//2,len(ordered)-1)]
        profile_histories = [int(by_user.loc[u,'train_history_count']) for u in selected]
bundle_path = root / 'artifacts/demo/v1/demo_bundle.json'
bundle = export_demo_bundle([batch/rel for rel in manifest['runs'].values()], selected, bundle_path)
assert load_bundle(bundle_path) == bundle
summary = {'batch': batch.name, 'manifest_sha256':sha(batch/'experiment_manifest.json'),
           'bundle_sha256':sha(bundle_path), 'bundle_bytes':bundle_path.stat().st_size,
           'profiles_train_history_counts':profile_histories, 'reports':reports, 'cohorts':cohort,
           'validation_manifest_sha256':manifest['validation_manifest_sha256'],
           'component_hashes':manifest['component_hashes'], 'selected_alpha':manifest['selected_alpha']}
(root/'results/local/task13-summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))
