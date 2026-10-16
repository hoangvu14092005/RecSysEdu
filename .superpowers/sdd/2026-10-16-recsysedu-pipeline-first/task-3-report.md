# Task 3 report — temporal split and cohorts

Status: implemented and committed as `cd46f28` (`feat: create temporal recommendation split`) in `<CODEX_HOME>\worktrees\pipeline-first\RecSysEdu`.

## Delivered

- `build_temporal_split(interactions_path, courses_path, output_dir, *, split_version, seed)` reads Task 2 Parquet and verifies its input hashes against `dataset_manifest.json`.
- Each user is sorted by `event_time`. The penultimate event is valid, the last event is test, and all earlier events are train. A user is excluded entirely if either split boundary has equal timestamps; course IDs never decide temporal order.
- The global train course IDs form a sorted `candidate_universe.parquet`. Valid and test rows each carry `target_in_train`; `valid_cohort.parquet` and `test_cohort.parquet` independently contain only warm targets for that split.
- `split_manifest.json` records Task 2 dataset version and manifest SHA-256 as `dataset_hash`, input and output hashes, `split_hash`, protocol ID `leave_last_two_out_v1`, seed, tie/cold counts and warm cohort sizes. Six Parquet files and the manifest are published together by renaming a completed staging directory.
- Added `data split --config configs/split.yaml`. It reports the split version and both warm cohort sizes; malformed dataset manifests return exit code 1 without a traceback.

## Verification

- RED: `python -m pytest tests/test_split.py -q` failed during collection with `ModuleNotFoundError: recsysedu.data.split`.
- RED: after adding CLI tests, `python -m pytest tests/test_cli.py -q` reported 2 failures because `split` was not yet a command.
- GREEN: focused split/CLI/prepare regression: **37 passed**.
- Full suite: **87 passed** (`<REPO_ROOT>\.venv\Scripts\python.exe -m pytest -q`).
- Ruff: **All checks passed** (`<REPO_ROOT>\.venv\Scripts\python.exe -m ruff check .`).
- `git diff --cached --check` passed before commit. Worktree clean after commit.

## Limits and follow-up

- The checked-in default config points to `data/processed/mooccubex-pilot-v1`, which is absent in this worktree. The CLI was exercised on a prepared fixture, not on the full MOOCCubeX dataset. No evaluator or model behavior was implemented or validated.
- This implementation materializes the selected users' interactions in memory. Monitor peak memory when the 10,000-user pilot is prepared; switch to a streaming or external-sort implementation if that exceeds the available machine memory.
- `source_local_naive` timestamps are compared on their declared source clock, consistent with Task 2. The split does not establish a global cross-user chronology.

## Review fix round 1 — time basis contract

Commit: `ec1bdd8` (`fix: validate split time basis against Arrow timestamps`). Before publishing any output, split now requires `time_basis=source_local_naive` with an Arrow timestamp that has no timezone, or a valid IANA `ZoneInfo` key with an Arrow timestamp in `UTC`. Missing, empty, invalid, non-string and mismatched values raise a clear `ValueError`; the final split directory is not created.

Evidence: the new focused tests first failed in **6 cases** because the old code published splits for missing/invalid `time_basis` and for both timezone/schema mismatch directions. After the fix, split/CLI tests were **20 passed**; the full suite was **94 passed**; `ruff check .` reported **All checks passed**. Accepted naive and `Asia/Shanghai`/UTC datasets are covered. `git diff --cached --check` passed before commit; worktree was clean after commit.
