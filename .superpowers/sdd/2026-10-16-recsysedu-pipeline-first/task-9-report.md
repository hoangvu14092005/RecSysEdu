# Task 9 — Reproducible experiment commands and manifests

Status: DONE, ready for independent review.

Commit: `1a1b254` (`feat: orchestrate reproducible experiments`).

Base: `a0f54456a52d00d0e69a200eb2292c8727e385a2`.

Worktree: `C:\Users\Vu\.codex\worktrees\pipeline-first\RecSysEdu`.

## Delivered

- `run_experiment(config, *, split, output_root)` evaluates MostPopular, Content, BPR and Hybrid on the same dataset/split/protocol. It returns four evaluator manifests, choosing Hybrid by validation NDCG@10. Exact ties retain Task 8's smallest-alpha rule.
- Effective model parameters, seed, fixed protocol/K, normalization and alpha grid are canonically hashed. Per-run manifests add experiment ID, config hash, exact model configuration/hash, component artifact hashes, Git revision/dirty state and library versions.
- Validation evaluates every configured alpha against the same fitted Content/BPR components. Each trial records its actual alpha and the exact component manifest hashes. `alpha_selection.json` binds the selected alpha to the full validation manifests through canonical hashes.
- Each invocation generates a fresh UUID batch and per-model run IDs. The complete experiment (models, all trials, selected runs and manifests) is staged and published with one directory rename. Failed training/evaluation publishes no partial batch; prior results are retained.
- Checks prepared dataset hashes, split content and file hashes, supplied BPR dataset/split/protocol identity, seed and training parameters. Checks feature/checkpoint/ID-map files and completed evaluator artifacts again before publication.
- Test requires `frozen: true`, exact dataset/split/effective-config hashes and the validation experiment manifest SHA-256. It verifies the entire validation batch, requires a full four-model validation experiment and an output root outside the validation output root. It reuses the saved validation Content features, train-only profiles, exact BPR checkpoint and selected alpha; it never refits or selects on test. Validation artifacts are rechecked after scoring to reject mid-run changes.
- `evaluate_model` evaluates one requested model. A MostPopular-only evaluation does not import/train BPR or read a supplied BPR manifest. Frozen single-model tests still require a complete compatible validation freeze.
- `train_from_config` supports the CLI BPR command: validates and exports the exact temporal split, trains real RecBole BPR, enriches its manifest with protocol/config/Git provenance, then publishes a new model directory without overwrite.
- CLI now offers `train`, `evaluate`, `experiments`. `configs/final_experiments.yaml` explains path resolution, validation/test output roots and how to freeze. `configs/bpr.yaml` gained the split path required by `train`; this small addition outside the original Task 9 file list makes its mandated example command concrete.

## Verification and TDD evidence

- Initial runner tests failed because `recsysedu.experiments` did not exist.
- New CLI checks failed because train/evaluate/experiments were absent. Unsupported BPR and protocol-changing Hybrid settings were observed passing incorrectly, then their validation was implemented. Malformed output-root tests exposed an AttributeError and now return a clean CLI error.
- Self-review added failing regression tests for a moved source BPR manifest after validation, and validation artifact mutation during a frozen test. Both now pass: test uses the retained batch, and mutation prevents publication.
- Focused command: **37 passed, 36 upstream FutureWarnings in 14.28s**.
- Full project suite: **217 passed, 45 upstream FutureWarnings in 25.11s**.
- Ruff: **All checks passed**.
- CLI `--help` lists `data,demo,train,evaluate,experiments`.
- `git diff --check`: passed; Git only emitted normal LF/CRLF conversion warnings.
- Worktree clean after commit.

Commands, from the worktree:

```powershell
& 'D:\VuLapTrinh2\RecSysEdu\.venv\Scripts\python.exe' -m pytest tests/test_experiment_runner.py tests/test_cli.py -q
& 'D:\VuLapTrinh2\RecSysEdu\.venv\Scripts\python.exe' -m pytest -q
& 'D:\VuLapTrinh2\RecSysEdu\.venv\Scripts\python.exe' -m ruff check .
$env:PYTHONPATH='C:\Users\Vu\.codex\worktrees\pipeline-first\RecSysEdu\src'
& 'D:\VuLapTrinh2\RecSysEdu\.venv\Scripts\python.exe' -m recsysedu.cli --help
git diff --check
```

The shared virtual environment is editable-installed from the primary checkout. Pytest already sets the worktree's src on its import path. CLI subprocess tests now explicitly set their checkout's `src` as PYTHONPATH, so they verify the changed source rather than the older primary checkout. The manual worktree CLI check used the same setting. After integration, the primary installation will point at the integrated source normally.

Warnings are pinned upstream RecBole pandas chained assignments and Torch AMP deprecation; no project warnings or test failures remain.

## Integration notes for Tasks 10–13

1. Paths in experiment/model YAML are relative to the YAML containing them. Direct Python callers can set `_base_dir` or supply absolute paths. CLI `--output` follows the shell's current directory. Dataset prepare/split command path semantics were preserved.
2. `output_root/<valid-or-test>-<UUID>/experiment_manifest.json` contains `runs`, a map of the four model IDs to relative run directories. On validation, `runs.hybrid` points to the chosen `alpha_trials/<alpha>` directory rather than duplicating that run. Each run directory contains the existing evaluator's CSV, Parquet, JSONL and extended `run_manifest.json`.
3. `alpha_trials` maps stringified float alphas (`"0.0"`, `"0.5"`, etc.) to the corresponding trial directories. Every trial's `model_config.alpha` and `model_config.components` explicitly bind what was scored.
4. To freeze after Task 11 review, copy `freeze_candidate` from the chosen validation experiment manifest into final config's `freeze`, add the SHA-256 of that experiment manifest as `validation_manifest_sha256`, set `validation_dir` and `frozen: true`. The manifest cannot embed its own hash; compute it after publication. Leave effective Content/BPR/alpha-grid settings unchanged. Test loads the checkpoint/features from this validation batch even if an original external model source has moved.
5. BPR search is intentionally still Task 11. Use `train --output <fresh directory>` and `evaluate --model bpr` to compare candidate configurations on validation. Set `bpr.manifest_path` to reuse the selected checkpoint when running the final four-model validation comparison.
6. Task 7 BPR manifests have no protocol_id. The runner accepts them only when their exact dataset_hash and split_hash match the fully validated current split; that split hash itself binds protocol_id. An explicit protocol_id, if present, must match. CLI-trained manifests now record it directly.
7. Release mode requires an available Git revision. Dirty state is recorded explicitly rather than falsely claiming current uncommitted source is contained in that revision.

## Limits

All metrics here are fixture/tiny-library compatibility evidence. No 10,000-user pilot, BPR search winner, real-data alpha or final test quality is claimed. Those remain Tasks 11/13. Config remains `frozen: false` intentionally. No substantive unresolved self-review concern remains; independent review is required.

## Fix round 1 — Protect relocated validation batches

The reviewer identified an Important issue: the test-output separation guard trusted only the recorded validation output root. Moving a validation batch made that stored path stale and allowed test output inside the actual batch.

- Added a real regression test that creates a validation batch, moves it outside its original root, then attempts test output both directly at the moved batch and inside a nested directory. Both cases were observed failing before the fix (`DID NOT RAISE`).
- `_frozen_validation` now protects both the recorded output root and the actual resolved validation directory. Equal or nested test roots fail before any output publication.
- Regression assertions confirm the moved batch's file set/content stays byte-for-byte unchanged and no nested test output is created.
- Focused suite: **39 passed, 42 upstream FutureWarnings in 15.86s**.
- Full suite: **219 passed, 51 upstream FutureWarnings in 26.45s**.
- Ruff and `git diff --check`: passed; only normal CRLF conversion warnings.
- Fix commit: `a36ea25d220c244bfb82b24af12c413939fd6bb1` (`fix: protect relocated validation batches`); worktree clean. The fix preserves the original separation check and adds the requested actual-location check. No new self-review concern found.
