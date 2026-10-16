import hashlib
import json
from pathlib import Path

import pandas as pd

root = Path(__file__).resolve().parents[2]
prepared = root / 'data/processed/mooccubex-pilot-v1'
repeat = root / 'data/processed/mooccubex-pilot-v1-repeat'
split = root / 'data/splits/mooccubex-pilot-v1-split-v1'
def digest(path):
    hasher = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            hasher.update(block)
    return hasher.hexdigest()
dataset = json.loads((prepared / 'dataset_manifest.json').read_text())
assert dataset == json.loads((repeat / 'dataset_manifest.json').read_text())
for name, entry in dataset['raw_files'].items():
    path = Path(entry['path'])
    assert path.stat().st_size == entry['bytes']
    assert digest(path) == entry['sha256']
for name, expected in dataset['output_hashes'].items():
    assert digest(prepared/name) == expected == digest(repeat/name)
manifest = json.loads((split/'split_manifest.json').read_text())
for name, expected in manifest['output_hashes'].items():
    assert digest(split/name) == expected
frames = {part: pd.read_parquet(split/f'{part}.parquet') for part in ('train', 'valid', 'test')}
pairs = {part: set(zip(frame.user_id, frame.course_id)) for part, frame in frames.items()}
assert not pairs['train'] & pairs['valid']
assert not pairs['train'] & pairs['test']
assert not pairs['valid'] & pairs['test']
train_times = frames['train'].groupby('user_id').event_time.max()
valid = frames['valid'].set_index('user_id')
test = frames['test'].set_index('user_id')
assert set(train_times.index) == set(valid.index) == set(test.index)
assert (train_times < valid.loc[train_times.index].event_time).all()
assert (valid.event_time < test.loc[valid.index].event_time).all()
universe = set(pd.read_parquet(split/'candidate_universe.parquet').course_id)
assert universe == set(frames['train'].course_id)
result = dict(raw_hashes_pass=True, repeat_exact=True, split_output_hashes_pass=True,
              pairs_disjoint=True, strict_temporal_order=True, train_universe_exact=True,
              temporal_users=len(train_times), test_scored=False)
(root/'results/local/data-audit-resume.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result))
