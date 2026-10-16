# Task 10 — Real recommendation snapshots

Status: DONE, ready for independent review.

Base: `a36ea25d220c244bfb82b24af12c413939fd6bb1`.

Commit: `e7663cdcc45cdb02344d5fc54ae37de608b504fb` (`feat: export real recommendation snapshots`).

Worktree: `C:\Users\Vu\.codex\worktrees\pipeline-first\RecSysEdu` (clean after commit).

## Delivered

- `export_demo_bundle(run_dirs, user_ids, output_path)` consumes selected completed runner-produced runs, including the selected Hybrid alpha trial, and writes a schema-v1 snapshot with `data_mode=real`, `history_mode=offline`, `evidence_level=offline_run`, and `paths=[]`.
- Exports a small catalog, pseudonymous display names, selected users, per-model rankings, actual metrics/status, IDs/hashes/seed, Git metadata and mechanism evidence. It preserves saved ranks/scores; it never retrains, scores, invents neighbors, or fills short lists.
- Rejects mixed dataset, split, protocol, config, cohort, evaluation split, history/profile/candidate/seen policy; rejects duplicate model selection and users missing from any selected warm cohort. Source rankings containing seen courses, invalid IDs, non-finite scores, non-contiguous ranks or more than 10 entries are rejected by the shared loader before publication.
- Verifies the complete batch file inventory and SHA-256 hashes, component manifests/features/checkpoints, selected-run membership and per-run output hashes. The copied dataset/split manifests bind catalog and histories to the same source dataset/split. Changes during export, including changes between two runs from one batch, prevent publication.
- Snapshot publication uses a temporary file and `os.replace`; a failing export preserves an existing snapshot. Output cannot be inside an immutable input experiment batch.
- `metric_status=not_available` remains `metrics=null`, never zero. `measured` still requires actual finite metrics in the shared loader.
- Real loader requires an explicit offline evidence label and compatible policies, one selected run per model, and a ranking for every selected user/model pair. Synthetic fixture behavior remains supported.
- Streamlit shows dataset, snapshot, history, protocol and selected run ID. Real mode explicitly says an offline pipeline result does not establish a completed pilot or learning benefit. A broken explicit real bundle displays an error and does not fall back to fixture data.
- CLI: `python -m recsysedu.cli demo export --run-dir <selected-run> [--run-dir ...] --user-id <cohort-user> [--user-id ...] --output <snapshot.json>`.

## Necessary producer adjustment

The Task 9 artifact format contained rankings and hashes but lacked the catalog and source histories required by the approved three-argument exporter interface. The runner now copies five small inputs into each immutable batch and lists them under `snapshot_inputs`: dataset manifest, split manifest, course catalog, train interactions, validation interactions. The existing complete batch hash map covers these files. It does not copy raw logs, the entire prepared interactions file, user names, or held-out test targets.

This keeps exports portable after the source prepared/split directories move. Older experiment batches without `snapshot_inputs` must be rerun before exporting; the exporter reports this rather than guessing source paths. Controller was informed of this interface gap and resolution.

## Verification

Environment: shared `D:\VuLapTrinh2\RecSysEdu\.venv\Scripts\python.exe`, current worktree `src` selected by pytest and explicit `PYTHONPATH` for the browser subprocess.

- Initial RED: `pytest tests/test_demo_export.py tests/test_app.py -q`: 15 expected failures from the missing exporter; existing synthetic/error behavior passed.
- Further RED cycles exercised missing mechanism evidence, absent real evidence label, incompatible loader policy, missing user/model ranking, absent CLI command, a missing component removed from the outer hash inventory, and manifest changes during export. Each failed before its implementation/fix.
- Final full suite: `python -m pytest -q`: **245 passed, 57 warnings, 35.69 seconds**. Warnings are upstream RecBole pandas chained-assignment and Torch GradScaler deprecations; no tests failed.
- `python -m ruff check .`: passed.
- `git diff --check`: passed.
- Integration test runs real tiny RecBole BPR, all four validation models, frozen test reuse, then exports all four test runs. It confirms test observed history is `C_1,C_2`, content profile remains train-only `C_1`, and neither observed course appears in any ranking.
- AppTest checks real snapshot provenance, switching profiles/models, displayed run metadata, and broken bundle error behavior.

## Practical browser smoke

Started an owned hidden Streamlit subprocess at `http://127.0.0.1:8502/` with a generated executed-pipeline test fixture; health endpoint returned `ok`. Chrome DevTools MCP is unavailable, so CUA's in-app browser was used. Observed:

1. Explicit `snapshot-test-fixture` dataset and offline evidence limitation rendered; no synthetic warning.
2. Selecting profile 2 changed history to `History ancient` and MostPopular first result to `Python basic`.
3. Selecting Content changed first result to `History modern`.
4. Expanding the first item showed the train-only content mechanism and a score explicitly identified as a ranking score.
5. Model Lab showed valid/warm/full_train_universe/train policy and actual MostPopular/Content run rows.
6. Browser warning/error log query returned `[]`; screenshots were visually inspected. Server stderr contains startup only.

The temporary browser tab and owned server process were closed after the smoke. Logs are in this SDD workspace as `task10-streamlit.stdout.log` and `task10-streamlit.stderr.log`. This is a fixture-based browser/runtime check, not a real MOOCCubeX pilot claim.

## Self-review and limits

- Exporter intentionally accepts only users already ranked in each selected offline warm cohort. It cannot create a new-user ranking because it consumes artifacts without scoring a model.
- Exactly one selected run per model may appear in a snapshot. Compatible runs from separate experiment batches are permitted, but every batch must be complete and hash-consistent.
- Complete experiment directories are immutable inputs. Extra files or removed hash entries are rejected; put snapshots/notes outside these directories.
- This task implements the export/UI boundary and fixture verification. Actual pilot data, validation/freeze reporting and final handoff remain Tasks 11–13.
- No known Important/Critical issues remain from self-review. No subagents were spawned.
