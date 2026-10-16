import hashlib
import json
import math
import time
from pathlib import Path
import numpy as np
import pandas as pd
from recsysedu.adapters.recbole import load_bpr_scorer
from recsysedu.demo.artifacts import load_bundle
from recsysedu.evaluation.ranking import rank_candidates

started = time.perf_counter()
root = Path(__file__).resolve().parents[2]
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
bundle_path = root / 'artifacts/demo/v1/demo_bundle.json'
bundle = load_bundle(bundle_path)
batch, = (root / 'results/local/pilot-final/test').glob('test-*')
manifest = read(batch/'experiment_manifest.json')
model_manifest = batch/'artifacts/bpr/bpr_manifest.json'
model = load_bpr_scorer(model_manifest)
other = load_bpr_scorer(model_manifest)
universe = tuple(pd.read_parquet(root/'data/splits/mooccubex-pilot-v1-split-v1/candidate_universe.parquet').course_id)
rec_by_user = {r['user_id']:r for r in bundle['recommendations'] if r['model_id']=='bpr'}
results = []
users = list(bundle['users'])
per_user = pd.read_parquet(batch/manifest['runs']['bpr']/'per_user_metrics.parquet')
positive_id = per_user.loc[per_user['NDCG@10']>0,'user_id'].iloc[0]
train = pd.read_parquet(root/'data/splits/mooccubex-pilot-v1-split-v1/train.parquet')
valid = pd.read_parquet(root/'data/splits/mooccubex-pilot-v1-split-v1/valid.parquet')
history = train.loc[train.user_id==positive_id,'course_id'].tolist()
observed = history + valid.loc[valid.user_id==positive_id,'course_id'].tolist()
users.append({'user_id':positive_id,'profile_course_ids':history,'observed_course_ids':observed})
for line in (batch/manifest['runs']['bpr']/'recommendations.jsonl').open(encoding='utf-8'):
    row=json.loads(line)
    if row['user_id']==positive_id: rec_by_user[positive_id]=row
for user in users:
    first = model.score(user['user_id'],universe)
    second = other.score(user['user_id'],universe)
    assert np.array_equal(first.scores,second.scores)
    ranked = rank_candidates(first,set(user['observed_course_ids']),k=10)
    stored = rec_by_user[user['user_id']]['items']
    assert [r.course_id for r in ranked] == [r['course_id'] for r in stored]
    assert np.array_equal(np.array([r.score for r in ranked]), np.array([r['score'] for r in stored]))
    target = pd.read_parquet(root/'data/splits/mooccubex-pilot-v1-split-v1/test.parquet').set_index('user_id').loc[user['user_id'],'course_id']
    ids = [r.course_id for r in ranked]
    ndcg = 1/math.log2(ids.index(target)+2) if target in ids else 0.
    measured = pd.read_parquet(batch/manifest['runs']['bpr']/'per_user_metrics.parquet').set_index('user_id').loc[user['user_id'],'NDCG@10']
    assert abs(ndcg-measured)<1e-12
    results.append({'history_count':len(user['profile_course_ids']),'ndcg':ndcg,'rankings_exact':True,'scores_exact':True})
result = {'seconds':time.perf_counter()-started,'checkpoint_sha256':read(model_manifest)['checkpoint_sha256'],
          'bundle_sha256':sha(bundle_path),'lock_sha256':sha(root/'requirements-win-py310.lock.txt'),
          'cases':results,'fixture_metrics_tolerance':1e-12,'bpr_numpy_repeat_tolerance':0}
(root/'results/local/task13-clean-reproduce.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
