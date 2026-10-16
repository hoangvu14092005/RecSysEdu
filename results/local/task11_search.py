import json
from pathlib import Path
import subprocess
import sys

import yaml

root = Path(__file__).resolve().parents[2]
scratch = root / 'results/local'
base = yaml.safe_load((root / 'configs/final_experiments.yaml').read_text())
base.update(prepared_dir=str(root / 'data/processed/mooccubex-pilot-v1'),
            split_dir=str(root / 'data/splits/mooccubex-pilot-v1-split-v1'),
            content={'config_path': str(root / 'configs/content.yaml')},
            hybrid={'config_path': str(root / 'configs/hybrid.yaml')})
attempts = []
# Predeclared small search; one seed, max 3 configurations, max 10 epochs each.
for i, (dim, rate) in enumerate([(32, 0.001), (64, 0.001), (32, 0.01)], 1):
    label = f'bpr-{i}'
    parameters = dict(seed=17, epochs=10, embedding_size=dim, train_batch_size=2048,
                      learning_rate=rate, validation_early_stopping=True, stopping_step=2)
    config = base | {'bpr': parameters}
    path = scratch / f'{label}.yaml'
    path.write_text(yaml.safe_dump(config))
    result = subprocess.run([sys.executable, str(scratch / 'task11_measure.py'), label,
                             'evaluate', '--model', 'bpr', '--split', 'valid', '--config',
                             str(path), '--output', f'results/local/pilot-search/{label}'])
    attempt = dict(label=label, parameters=parameters, exit_code=result.returncode)
    if result.returncode == 0:
        batch = next((scratch / f'pilot-search/{label}').iterdir())
        run = json.loads((batch / 'runs/bpr/run_manifest.json').read_text())
        model = json.loads((batch / 'artifacts/bpr/bpr_manifest.json').read_text())
        attempt.update(metrics=run['metrics'], batch=str(batch),
                       best_epoch=model['best_epoch'], epochs_completed=model['epochs_completed'],
                       validation_ndcg_history=model['validation_ndcg_history'])
    attempts.append(attempt)
    (scratch / 'bpr-search.json').write_text(json.dumps(attempts, indent=2))
    print(json.dumps(attempt), flush=True)
