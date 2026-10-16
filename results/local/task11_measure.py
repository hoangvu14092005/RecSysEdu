import json
import os
from pathlib import Path
import subprocess
import sys
import time

import psutil

root = Path(__file__).resolve().parents[2]
env = os.environ | {'PYTHONPATH': str(root / 'src'), 'OMP_NUM_THREADS': '2',
                    'MKL_NUM_THREADS': '2', 'OPENBLAS_NUM_THREADS': '2'}
label = sys.argv[1]
start = time.perf_counter()
with (root / f'results/local/{label}.log').open('w', encoding='utf-8') as log:
    proc = subprocess.Popen([sys.executable, '-m', 'recsysedu.cli', *sys.argv[2:]],
                            cwd=root, env=env, stdout=log, stderr=log)
    peak = 0
    while proc.poll() is None:
        try:
            parent = psutil.Process(proc.pid)
            peak = max(peak, sum(p.memory_info().rss for p in [parent, *parent.children(recursive=True)]))
        except psutil.NoSuchProcess:
            pass
        time.sleep(0.2)
    result = dict(label=label, args=sys.argv[2:], exit_code=proc.returncode,
                  seconds=time.perf_counter() - start, sampled_peak_rss_bytes=peak,
                  peak_sampling_interval_seconds=0.2)
    (root / f'results/local/{label}.measurement.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result))
raise SystemExit(proc.returncode)
