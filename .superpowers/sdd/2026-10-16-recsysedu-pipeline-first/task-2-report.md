# Task 2 report — Prepare versioned Parquet dataset

Status: DONE — implemented and fixture/runtime-tested locally. Full raw preparation, temporal split, model training and measured recommendation quality were not run in this task.

Commit: `fed64a19421b953ccc7202aec4a1d2cf543736d7` — `feat: prepare versioned parquet dataset`.

Worktree: `<CODEX_HOME>\worktrees\pipeline-first\RecSysEdu`.
Base: `d5a677b`.
Interpreter: `<REPO_ROOT>\.venv\Scripts\python.exe`.
Working tree was clean after commit. No subagents were dispatched.

## Changes

- Added `src/recsysedu/data/prepare.py` with the required callable:
  `prepare_dataset(course_path, user_path, output_dir, *, dataset_version, time_basis, sample_users, seed) -> dict`.
- Added `configs/prepare.yaml`: `sample_users: 10000`, `seed: 20261016`, `time_basis: source_local_naive`, version `mooccubex-pilot-v1`, final output `data/processed/mooccubex-pilot-v1`.
- Added `data prepare --config ...` CLI. Missing/invalid config or time basis returns 1 with a readable error; success prints dataset version and final output path. Optional Parquet dependencies are imported only by preparation, preserving other CLI commands when the data extra is absent.
- Added direct project dependency `pandas>=2.2,<3`; DuckDB and PyArrow remain in the existing `data` extra. Installed verification runtime: pandas 2.3.3, DuckDB 1.5.6, PyArrow 25.0.1.
- Added 23 prepare test cases and two CLI tests; updated `docs/04_data_contract.md` to the implemented schema and stage boundary.

## Data behavior and decisions

1. Reuses streaming `iter_records` from `data.audit`, for JSON Lines and JSON arrays. Raw files are read only; SHA-256 is checked before and after processing, and a source change prevents publication.
2. ID rule remains exact catalog string or integer matching an existing `C_<digits>` ID. For example, integer 3 maps to catalog `C_003`; strings `"3"`, bools, floats and unknown integers do not invent IDs.
3. Duplicate user IDs retain the first source record, matching existing audit behavior. A user with invalid/mismatched history is quarantined; unequal arrays are never truncated/zipped partially.
4. Duplicate `(user_id, course_id)` enrollments retain the earliest valid event and its raw time/provenance. Equal times retain first source occurrence. Losing duplicates are recorded in rejects.
5. Parent-confirmed eligibility: at least three distinct valid catalog courses after cleaning. Invalid histories and insufficient cleaned histories are excluded before reservoir sampling. Timestamp-boundary ties remain eligible here; Task 3 decides split exclusion. All error counts, clean-pair counts and eligibility counts cover the full source before sampling.
6. `random.Random(seed)` reservoir sampling acts only on eligible users. `sample_users=0` streams all eligible users. Positive sample sizes retain at most the requested number of user histories in memory. Selected interactions include only selected eligible users; the catalog remains complete. Ineligible users never change the reservoir draws.
7. Output user groups retain source encounter order; each history is sorted by `(event_time, course_id)`. This is deterministic and supports direct all-user streaming. Documentation previously describing global `(user_id, timestamp, course_id)` sorting was updated to this actual order.
8. `source_local_naive` preserves naive source clock values in Arrow `timestamp[us]`, plus original `event_time_raw`; it never creates UTC values. Offset-bearing timestamps in this mode are rejected with `timestamp_awareness_mismatch`.
9. A valid IANA key localizes raw naive values then writes Arrow `timestamp[us, tz=UTC]`; original strings are retained. Explicit-offset input in IANA mode is converted from its existing instant. DST folds/gaps are quarantined as `ambiguous_local_time` / `nonexistent_local_time`; conversion overflow is `invalid_timestamp`. No machine timezone is inferred.
10. Invalid catalog IDs are quarantined; identical catalog duplicates are counted/gathered once. Conflicting catalog metadata or ambiguous numeric mappings block publication.
11. Parquet sinks buffer at most 4096 rows each. Catalog fingerprints and the set of previously encountered user IDs remain in memory, and reservoir memory also depends on selected history lengths. This is streaming records/output, not a claim of constant total memory.
12. Output writes to a temporary sibling directory; finished Parquet is checked by DuckDB for pair uniqueness, course references and cohort history length before the directory is renamed into the final location. Existing output directories are refused, preserving version immutability. Failed processing leaves no published partial dataset.

## Output contract for downstream tasks

`output_dir` is the final version directory, not a parent to which the function appends another dataset version.

| File | Columns |
| --- | --- |
| `courses.parquet` | `course_id: string`, `name: string`, `about: string`, `fields: list[string]`, `prerequisite_text: string` |
| `interactions.parquet` | `user_id: string`, `course_id: string`, `event_time: timestamp[us]` or `timestamp[us, UTC]`, `event_time_raw: string`, `interaction: int8`, `source_record: string` |
| `cohort_users.parquet` | `user_id: string`, `history_length: int64` |
| `rejects.parquet` | `reason_code: string`, `user_id: string?`, `raw_course_id: string?`, `event_time_raw: string?`, `source_record: string`, `count: int64` |

`source_record` for valid source objects is `<filename>:record:<1-based valid-object ordinal>`, with `:slot:<0-based index>` for history events. This is an object ordinal, not a physical JSON Lines number. `raw_course_id` uses JSON encoding to preserve the original ID type. `iter_records` exposes aggregate parser counts without offsets; malformed JSON/non-object records therefore get aggregate per-file rejects with `count`. Every reject count is included in manifest `error_counts`; `row_counts.rejects` counts rows rather than summing their multiplicity.

`dataset_manifest.json` contains:

- `schema_version`, `dataset_version`, `time_basis`, `seed`.
- `requested_user_count`, `selected_user_count`, `users_scanned`, `eligible_user_count`.
- `raw_enrollment_slots`, `valid_enrollments_before_dedup`, `clean_interaction_count_before_sampling` (including clean pairs belonging to insufficient histories).
- `raw_files` keyed by filename, each with resolved local `path`, `bytes`, `sha256`.
- `row_counts` keyed by table stem; `error_counts` keyed by reason.
- `schemas` keyed by table stem, listing each Arrow field name/type/nullability.
- `output_hashes` keyed by the four Parquet filenames with SHA-256 values.
- `course_id_rule`, `eligibility_rule`, `sampling_rule`, `output_order`, `fields_source`.
- `temporal_dataset_ready: false`.

There is no self-referential manifest hash. A downstream stage can compute SHA-256 of the saved manifest as dataset identity. Identical raw/config/library versions produce matching Parquet hashes in tests; cross-PyArrow-version byte identity is not promised.

## RED / GREEN evidence

Initial required tests were written before production code. RED command:

```powershell
& '<REPO_ROOT>\.venv\Scripts\python.exe' -m pytest tests/test_prepare.py -q
```

Observed exit 1, collection failure because `recsysedu.data.prepare` did not exist (`ModuleNotFoundError`). This is the missing-module failure specified by the brief.

Initial GREEN after implementation:

```text
pytest tests/test_prepare.py tests/test_cli.py -q
23 passed in 8.93s
```

Additional characterization checks exercised all/limited sampling, seed changes, selection beyond the prefix, ineligible-user invariance, preserved timestamp ties, JSON arrays, identical catalog duplicates and atomic cleanup on truncated arrays. They passed before further changes; they characterize already implemented behavior rather than being described as independently RED.

A second RED/GREEN cycle found UTC underflow for both naive and explicit-offset year-1 timestamps:

```text
pytest tests/test_prepare.py -q -k overflows
RED: 2 failed, 21 deselected; OverflowError: date value out of range
GREEN after conversion quarantine: 2 passed, 21 deselected in 0.55s
```

Final focused/regression command:

```powershell
& '<REPO_ROOT>\.venv\Scripts\python.exe' -m pytest tests/test_prepare.py tests/test_cli.py tests/test_audit.py -q
```

Observed: **32 passed in 1.56s**, exit 0.

Final full suite:

```powershell
& '<REPO_ROOT>\.venv\Scripts\python.exe' -m pytest -q
```

Observed: **78 passed in 7.19s**, exit 0. No test failures were omitted.

Lint and patch validation:

```powershell
& '<REPO_ROOT>\.venv\Scripts\python.exe' -m ruff check .
git diff --check
git diff --cached --check
```

Observed: **All checks passed!**, exit 0; both Git whitespace checks clean. Git emitted only the repository's LF-to-CRLF normalization notices for new files during staging.

## Concerns / limits

- Evidence is fixture/runtime-tested preparation and existing regression coverage, not full MOOCCubeX execution, measured memory performance, a released temporal split or model readiness.
- Source timezone remains unconfirmed. Pilot uses the explicit source-local-naive assumption; no UTC claim is made.
- Parser quarantine preserves per-file counts for malformed/non-object input but cannot recover exact raw line offsets through the existing `iter_records` interface.
- Full-mode deduplication retains a set of all source user IDs. Full-data peak memory and duration should be measured in the later real pilot task.
- Full catalog conflict or malformed JSON-array input intentionally blocks publication. Existing version directories are never overwritten; reruns need a fresh output directory/version.
- No train/valid/test split, cold-target logic, model code or demo exporter was implemented.

Next step: independent parent review, then Task 3 consumes `event_time`, selected user histories and the manifest to implement temporal split/cohort rules.

## Fix round 1/5 — Exact positive sample count

Fix commit: `7f67b9cb0c650d09edb99c31a4ecb6efa7766edf` — `fix: require exact requested eligible user sample`.

Important finding addressed: preparation previously published fewer selected users when a positive request exceeded the number of eligible users. The approved pilot must contain exactly 10,000 eligible users for `sample_users=10000`.

Change: after scanning/cleaning the full input and before writing sampled users or publishing the dataset, preparation now raises a clear `ValueError` whenever `sample_users > 0` and `eligible_user_count < sample_users`. The message contains both counts, for example `Không đủ user hợp lệ: sample_users=2, eligible_user_count=1`. Temporary output is cleaned and no final output directory is published. `sample_users=0` retains all eligible users, including a cohort smaller than a positive pilot request. The documented positive-sample contract was corrected to require the exact count; the earlier description of a maximum-only limit is superseded by this fix.

Regression tests added:

- `test_prepare_requires_exact_positive_sample_count_before_publication`: one eligible user plus one insufficient-history user, request two, assert `ValueError` with both counts, no final directory, no leftover staging directory, then confirm all-user mode succeeds with one selected user.
- `test_prepare_cli_refuses_short_sample_without_publication`: request two with one eligible user, assert exit 1, both counts in the readable error, no traceback and no final directory.

RED command and exact result:

```powershell
& '<REPO_ROOT>\.venv\Scripts\python.exe' -m pytest tests/test_prepare.py tests/test_cli.py -q -k 'exact_positive_sample or short_sample'
```

Observed exit 1: **2 failed, 28 deselected in 0.64s**. The prepare regression failed with `DID NOT RAISE ValueError`; CLI regression failed because the command returned 0 and published only one user.

GREEN focused command:

```powershell
& '<REPO_ROOT>\.venv\Scripts\python.exe' -m pytest tests/test_prepare.py tests/test_cli.py -q
```

Observed exit 0: **30 passed in 1.63s**.

Full suite and quality checks:

```powershell
& '<REPO_ROOT>\.venv\Scripts\python.exe' -m pytest -q
& '<REPO_ROOT>\.venv\Scripts\python.exe' -m ruff check .
git diff --check
git diff --cached --check
```

Observed: **80 passed in 4.55s**, Ruff **All checks passed!**, Git whitespace checks clean; all commands exited 0. Only standard LF-to-CRLF staging notices appeared.

The reviewer's Minor raw duplicate-ID observation was not changed in this round, as instructed. Full-raw execution and timezone confirmation remain pending as described above.
