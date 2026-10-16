# RecBole BPR CPU runtime spike — 2026-10-16

Evidence level: **runtime-tested on a tiny synthetic fixture**. This confirms
dependency/import/training/checkpoint/scoring compatibility, not recommendation
quality, full MOOCCubeX runtime, or clean-machine reproduction.

## Environment that passed

| Component | Actual version/value |
| --- | --- |
| Python | 3.10.11, Windows x64 |
| Torch | 2.5.1+cpu, official PyTorch CPU wheel |
| RecBole | 1.2.1 |
| NumPy | 1.26.4 |
| pandas / SciPy / scikit-learn | 2.3.3 / 1.15.3 / 1.7.2 |
| Device / workers | CPU / 0 |
| Seed / epochs / embedding / batch / learning rate | 17 / 2 / 8 / 4 / 0.001 |
| Exact train / valid / test rows | 6 / 3 / 3 |

The tested pins, including transitive dependencies, are frozen in
`requirements-win-py310.lock.txt`. Its extra index serves the CPU Torch wheel;
the `bpr` optional dependency group constrains the compatible main packages.
NumPy is pinned below 2 because RecBole 1.2.1 config uses NumPy scalar aliases
removed in NumPy 2. No third-party source files were patched.

## Measured results

The fixture with a held-out-only cold item trained in **1.211996 s** inside
`train_bpr`, after imports, including dataset/config/trainer/checkpoint work.
The process peak working set was **380,387,328 bytes (362.77 MiB)**. A subsequent
all-warm fixture in the same process took **0.061520 s** and the process peak
increased to **390,426,624 bytes (372.34 MiB)**. These are Windows `peak_wset`
process high-water marks, not incremental model memory. On other platforms the
manifest uses end-of-run RSS as an estimate. Do not extrapolate these fixture
numbers to the real dataset.

The integration command completed **3 checks in 4.37 s**, with 9 upstream
deprecation warnings. Both tiny models completed exactly two epochs. Cold-item
fixture losses were `1.4627221823, 1.3680561185`; all-warm losses were
`1.8030905128, 1.6740387082`. These losses are training diagnostics.

Checkpoint reload produced finite, non-constant scores in requested source-ID
order. The adapter's learned-embedding dot products matched the restored
upstream `BPR.predict` at `rtol=1e-6, atol=1e-7`. Reloading the same checkpoint
twice produced identical adapter scores. A deliberately modified checkpoint
copy was rejected by SHA-256 verification.

## Data and sampler decisions

The exporter validates the Task 3 split manifest identity and source Parquet
hashes, exports every row with tabs and source IDs, and records exact counts.
`benchmark_filename: [train, valid, test]` bypasses RecBole splitting. The adapter
also compares each loaded user/item pair in each split with the atomic input;
matching counts alone are not sufficient.
The adapter isolates RecBole configuration from the host application's
`sys.argv`, which upstream otherwise gives precedence over the validated YAML.
A regression reproduced `--epochs=3` silently overriding a two-epoch budget;
the adapter now preserves the validated budget and CPU/split settings.

RecBole's default uniform sampler draws from its global token map, which includes
held-out-only items. Its multi-phase sampler can reject users who consumed all
items across train/valid/test even when the train history has valid negatives.
The adapter therefore builds the exact benchmark datasets and constructs the
upstream sampler for **train only**, using `popularity` with exponent `alpha=0`.
This is a uniform distribution over distinct train items. Only positive train
items are excluded; valid/test targets do not alter those exclusions. A user
with no unseen train candidate causes a clear error rather than an infinite
rejection-sampling loop or silent filtering.

The adapter trains for the configured bounded epochs without RecBole validation
or test metrics; the shared project evaluator owns cohort/universe/seen masking
and model selection. Cold and padding item IDs never enter `BPRScorer.score`.
The tensor-only checkpoint uses `torch.load(..., weights_only=True)`.
Training losses, effective parameters, seed, versions, identities, counts and
artifact hashes are saved in `bpr_manifest.json`; source/internal maps are in
`id_maps.json`. RecBole's own TensorBoard diagnostics use ignored
`log_tensorboard/`; checkpoints and their small manifests are output artifacts.

## Commands

Run from the implementation checkout, using its source via pytest `pythonpath`:

```powershell
$python = '<REPO_ROOT>\.venv\Scripts\python.exe'
# Unit command: explicitly excludes training.
& $python -m pytest -m "not integration" -q
# Bounded real-library integration checks.
& $python -m pytest -m integration tests/test_recbole_adapter.py -q
# Release command: includes all registered integration checks.
& $python -m pytest -q
& $python -m ruff check src/recsysedu/adapters tests/test_recbole_adapter.py
& $python -m pip check
```

The initial red test failed because `recsysedu.adapters` did not exist; the
sampler regression then failed because `_build_train_loader` did not exist.
Focused unit tests passed 4/4; the full unit suite passed 155 with 3 integration
cases deselected. `pip check` reported **No broken requirements found**.
The release command, including integration, passed **158 tests**; the final
focused integration rerun passed 3 tests in 3.99 s. Ruff and `git diff --check`
also passed.

## Remaining limitations and environment notes

- RecBole emits pandas chained-assignment and Torch AMP deprecation warnings;
  they are reported, not suppressed. pandas remains pinned below 3.
- The first overlapping pip resolver was stopped, then the compatible pins were
  installed sequentially. Two abandoned `~ympy` temporary directories remain
  in the existing virtual environment. Pip warns about these invalid temporary
  distributions while reporting no broken requirements. Automatic approval
  review rejected their bounded deletion with `blocked by policy`; no deletion
  or alternative cleanup was performed.
- This is an existing-environment runtime check. A new environment from the
  committed lock and a real-data benchmark remain later release work.

## Primary sources audited

- [Atomic files and dataset naming](https://recbole.io/docs/user_guide/usage/running_new_dataset.html)
- [RecBole v1.2.1 benchmark build and token maps](https://github.com/RUCAIBox/RecBole/blob/v1.2.1/recbole/data/dataset/dataset.py)
- [RecBole v1.2.1 Sampler and alias probabilities](https://github.com/RUCAIBox/RecBole/blob/v1.2.1/recbole/sampler/sampler.py)
- [RecBole v1.2.1 BPR loss and predict](https://github.com/RUCAIBox/RecBole/blob/v1.2.1/recbole/model/general_recommender/bpr.py)
- [RecBole v1.2.1 Trainer.fit](https://github.com/RUCAIBox/RecBole/blob/v1.2.1/recbole/trainer/trainer.py)
