import json
from pathlib import Path

import numpy as np
import torch
from recbole.config import Config
from recbole.data import create_dataset
from recbole.data.interaction import Interaction
from recbole.model.general_recommender.bpr import BPR

from recsysedu.adapters.recbole import load_bpr_scorer

root = Path(__file__).resolve().parents[2]
batch = root / 'results/local/pilot-search/bpr-3/valid-cbcf720e67144f10a735e06b0a717763'
path = batch / 'artifacts/bpr/bpr_manifest.json'
manifest = json.loads(path.read_text())
scorer = load_bpr_scorer(path)
config = Config(model='BPR', dataset='recsysedu', config_dict={
    'data_path': str(batch / 'artifacts/atomic'),
    'benchmark_filename': ['train', 'valid', 'test'], 'use_gpu': False,
    'embedding_size': manifest['embedding_size']})
upstream = BPR(config, create_dataset(config))
upstream.load_state_dict(torch.load(path.parent / 'bpr.pth', weights_only=True))
np.testing.assert_array_equal(scorer.user_embeddings, upstream.user_embedding.weight.detach().numpy())
np.testing.assert_array_equal(scorer.item_embeddings, upstream.item_embedding.weight.detach().numpy())
candidate_ids = list(scorer.item_id_map)
maximum = 0.0
oracle_maximum = 0.0
ranking_equal = True
for user in list(scorer.user_id_map)[:5]:
    interaction = Interaction({'user_id': torch.tensor([scorer.user_id_map[user]] * len(candidate_ids)),
                               'item_id': torch.tensor([scorer.item_id_map[item] for item in candidate_ids])})
    expected = upstream.predict(interaction).detach().numpy()
    actual = scorer.score(user, candidate_ids).scores
    maximum = max(maximum, float(np.abs(expected - actual).max()))
    # Float32 NumPy and Torch reduction trees need not round identically.
    # Check both against an independently accumulated float64 dot product.
    oracle = (scorer.item_embeddings[[scorer.item_id_map[item] for item in candidate_ids]].astype(np.float64)
              * scorer.user_embeddings[scorer.user_id_map[user]].astype(np.float64)).sum(axis=1)
    oracle_maximum = max(oracle_maximum, float(np.abs(actual - oracle).max()),
                         float(np.abs(expected - oracle).max()))
    np.testing.assert_allclose(actual, expected, rtol=1e-6, atol=2e-6)
    np.testing.assert_allclose(actual, oracle, rtol=1e-6, atol=2e-6)
    np.testing.assert_allclose(expected, oracle, rtol=1e-6, atol=2e-6)
    ranking_equal &= sorted(candidate_ids, key=lambda item: (-float(actual[candidate_ids.index(item)]), item)) == sorted(
        candidate_ids, key=lambda item: (-float(expected[candidate_ids.index(item)]), item))
print(json.dumps(dict(known_users=5, candidates_per_user=len(candidate_ids),
                     restored_upstream_predict_matches=True, max_absolute_difference=maximum,
                     float64_oracle_max_absolute_difference=oracle_maximum,
                     tolerance=dict(rtol=1e-6, atol=2e-6), full_rankings_equal=ranking_equal)))
