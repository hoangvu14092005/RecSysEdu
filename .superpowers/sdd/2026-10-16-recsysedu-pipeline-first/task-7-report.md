# Task 7 report — RecBole BPR

Status: **DONE**, with the non-blocking concerns below.

Commit: `31abf2b5166ef024707a54190f8ea6698a130946` — `feat: integrate recbole bpr`

Implementation checkout: `<CODEX_HOME>\worktrees\pipeline-first\RecSysEdu`
Base: `8f6ed43dbd861ee0bcea53a6419c52f888738a37`
Interpreter: `<REPO_ROOT>\.venv\Scripts\python.exe`
Working tree was clean after the commit. No subagents were dispatched.

## Delivered

- `export_atomic_files(split_dir, output_dir)` validates Task 3 split identity
  and input hashes, exports exact train/valid/test TSV rows with source IDs and
  timestamps, and publishes an export manifest atomically. Existing outputs
  are rejected. Cold held-out targets remain in the exact exported split.
- RecBole is configured with `benchmark_filename: [train, valid, test]`, the
  prescribed fields, CPU, fixed seed and bounded 1–100 epochs. Loaded counts
  **and ordered source user/item pairs** are checked against the atomic files.
- Real RecBole `BPR` and `Trainer.fit` train the model. The adapter constructs
  the train dataloader using upstream train-only `Sampler`, with popularity
  exponent zero giving uniform train-universe negative sampling. Only positive
  train interactions are excluded. Valid/test targets never change exclusions.
- `train_bpr(config_path, output_dir)` writes tensor-only checkpoint, source to
  internal ID maps, actual training losses/effective configuration, identities,
  hashes, versions, runtime and process memory estimate.
- `load_bpr_scorer(manifest_path)` verifies checkpoint/map hashes and loads with
  `weights_only=True`. `BPRScorer.score` uses the exact learned embeddings and
  returns Task 1 `ScoreResult` in source candidate order; padding, unknown,
  duplicate and cold candidates are rejected. There is no substitute model.
- `configs/bpr.yaml`, optional `bpr` dependencies, pytest integration marker,
  actual tested environment lock, and `results/bpr/runtime_spike.md` were added.
  `.gitignore` gained `/log_tensorboard/` for RecBole's fixed diagnostic location.

## TDD and self-review

The initial tests failed with the expected missing adapter import. Export and
mapping tests then passed after implementation. The train-only sampler test
failed with the expected missing sampler helper, then passed against the real
RecBole sampler.

Self-review checked data identity, exact split membership, source/internal token
mapping, negative sampling, configuration precedence, checkpoint integrity,
scope and dependency changes. It found two meaningful upstream integration
hazards and fixed both:

1. Default uniform sampling includes held-out-only items; default multi-phase
   sampler validation can reject all-warm users who consume all items across
   train/valid/test. Train-only upstream alias sampling now respects the project
   universe. Separate integration cases cover cold and all-warm fixtures, and
   the no-negative-candidate guard prevents an unbounded rejection loop.
2. RecBole normally gives `sys.argv` precedence over `config_dict`. A regression
   demonstrated that host flag `--epochs=3` overrode the validated YAML budget
   of two epochs (`assert 3 == 2` failed). The adapter's Config subclass ignores
   host command-line parsing; the regression now passes with exactly two epochs.

Restored upstream `BPR.predict` independently matches adapter scores at
`rtol=1e-6, atol=1e-7`. Repeated adapter reload is exactly equal. A modified
checkpoint copy is rejected. No unresolved self-review correctness issue remains.

## Verification

All commands ran in the implementation checkout with the interpreter above:

| Command arguments | Result |
| --- | --- |
| `-m pytest -m "not integration" tests/test_recbole_adapter.py -q` | 4 passed, 3 deselected |
| `-m pytest -m integration tests/test_recbole_adapter.py -q` | 3 passed, 4 deselected, 9 upstream warnings, 3.99 s |
| `-m pytest -m "not integration" -q` | 155 passed, 3 deselected, 12.69 s |
| `-m pytest -q` — final release run | 158 passed, 9 upstream warnings, 13.28 s |
| `-m ruff check src/recsysedu/adapters tests/test_recbole_adapter.py` | passed |
| `-m pip check` | exit 0, No broken requirements found; temporary-directory warning below |
| `git diff --check` and staged equivalent | passed |

The final release run includes all integration cases. Unit runs exclude them
explicitly. Runtime report documents these commands and evidence limits.

## Runtime spike and dependency freeze

Actual successful environment: Python 3.10.11, Torch 2.5.1+cpu, RecBole 1.2.1,
NumPy 1.26.4; pandas 2.3.3, SciPy 1.15.3, scikit-learn 1.7.2. Torch came from
the official PyTorch CPU index. No upstream package source was patched.

Fixture settings: seed 17, two epochs, embedding 8, batch 4, learning rate 0.001,
6/3/3 exact rows. The cold fixture measured 1.211996 s inside `train_bpr` after
imports and 380,387,328 bytes peak Windows process working set. A subsequent
all-warm fixture measured 0.061520 s and a 390,426,624-byte process high-water
mark. These are synthetic fixture/process measurements, not full-data estimates.
The lock was changed only after real training/reload passed.

## Concerns and explicit limits

- Real-data quality, validation tuning, full-dataset training time and a fresh
  environment installed from the lock remain later tasks; this task does not
  claim recommendation improvement or release readiness.
- RecBole emits pandas chained-assignment and Torch AMP deprecation warnings.
  They remain visible; pandas is pinned below 3.
- An overlapping pip resolver was stopped, then compatible versions were
  installed sequentially. Two abandoned pip temporary directories, `~ympy`
  and `~ympy-1.13.1.dist-info`, remain inside the existing `.venv`. Pip warns
  about them but reports no broken requirements. Automatic approval review
  rejected their explicitly bounded deletion with `blocked by policy`.
  The directories were retained; no cleanup workaround was attempted.
- Training artifacts/checkpoints and TensorBoard files are ignored, while the
  committed runtime report preserves measured evidence and reproduction commands.

The source audit and prior project guidance were used to enforce the existing
train-universe and source-ID contracts; all implementation/runtime claims above
were verified in this task.
