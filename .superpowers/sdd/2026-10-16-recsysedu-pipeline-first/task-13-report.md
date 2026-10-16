# Task 13 — Final test, reproduction and handoff

Status: DONE, pending independent task/whole-branch review.
Commit: `5773af4a04e7da4a52d29c18c49d05f35753909e`.
Base: `ae8958107820cb0c25a56d1cf09f4c62982952e7`.
Managed worktree clean after commit. No subagents spawned.

Only seven owned documentation files committed: README, runbook, todo,
final/reproduction/acceptance reports and validation-report minor clarification.
Fixed deferred early-stopping wording precisely: below best achieved, ties reset.
Added historical-state crosslink from freeze report to final test.

## Single frozen full test

Executed exactly once from worktree with explicit worktree src PYTHONPATH:
`<REPO_ROOT>\.venv\Scripts\python.exe results/local/task11_measure.py final-test-once experiments --split test --config configs/final_experiments.yaml`.
Wrapper sets OMP/MKL/OPENBLAS threads2 and calls CLI experiments test with exact
committed frozen config. No code/artifact failure, no full-test retry or tuning.
Exit0,520.1935353s,process-tree RSS sampled peak388657152 bytes/interval0.2s.
Install/tests running concurrently; not isolated performance benchmark.

Published test batch:
`results/local/pilot-final/test/test-b36cb3e524a346c8bb6a9935da76406a/`.
30 files,65591620 bytes. Manifest SHA256
`d4eb81744e8dc962d09624c7d40286e491ec93f83358e2fcd8322d795622d08d`.
9,858 warm users,107 cold targets excluded/reported,2,586 train candidates,K10,
seed17,train-only model/profile,train+valid seen,alpha.25. Component hashes and
validation manifest digest unchanged; no retraining. Git revision ae89581,
git_dirty true only because validation documentation wording was edited first.

| Model | NDCG@10 | HR/Recall@10 | Precision@10 | Coverage@10 | evaluator seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| popularity | .047042649608172046 | .0801379590180564 | .008013795901805619 | .01237432327919567 |15.8952336|
| content | .05765705741489261 | .09870156218299858 | .00987015621829973 | .9238205723124516 |192.5525233|
| bpr | .05729389792191103 | .10590383444917834 | .010590383444917665 | .6782675947409126 |28.7110019|
| hybrid | .07737278190883444 | .13643741123960235 | .013643741123959895 | .8395204949729311 |279.3437266|

Full independent local `task13_analyze.py` audit passed: every experiment output
hash; each ranking continuous1..10,unique,finite/score-ID order,in-universe,
zero train+valid seen. Every per-user NDCG/hit/recall/precision recomputed from
target/rank and compared Parquet+aggregate at1e-12; coverage by union. Group
thresholds descriptive after test, not model selection:low1-4/history6110,
middle5-19/2285,high20+/1463. All five metrics per model/group in final report.
BPR high-history NDCG.01627407 exceeds Hybrid.01570154; no universal-win claim.
Miss counts popularity9068,content8885,bpr8814,hybrid8513. No actual fallback
or short lists in warm cohort; not evidence for cold-start quality.

## Real snapshot

Exporter selected min/median/max train-history profiles by history length and
ID, not hit result:1,3,1109. All three BPR misses retained, not cherry-picked.
Snapshot `artifacts/demo/v1/demo_bundle.json`,246003 bytes,real/schema1,
3 profiles ×4 models,paths=[],exporter+loader validated.
SHA256 `3e80b5e90db8f2776ff7f5e58915696f45f9b552ee8b7f0fe2219ae20577e56e`.
Snapshot remains ignored, contains learner IDs and must be copied separately.

## Automated gate and clean environment

Shared env explicit worktree PYTHONPATH:
- Full pytest262 passed,64 upstream warnings,40.82s.
- Ruff src/app/tests pass; git diff --check pass.
- Pip check No broken requirements; old env warns invalid distribution -ympy.
  Did not modify/delete the old environment to hide this.

Created actual new `.venv-repro` via py-3.10-mvenv,Python3.10.11,
include-system-site-packages=false. Installed committed lock + editable package
with no dependencies. Install exit0; clean pip check No broken requirements
without old-env warning.78 pinned runtime versions match PEP440. A diagnostic
raw-string assertion initially failed because thop reports0.1.1-2209072238
vs lock0.1.1.post2209072238; normalized Version comparison proves equivalent.
No lock edit or dependency substitution. Install log write span447.036s is
explicitly labeled as log-span rather than stopwatch for venv+installation.

Exact clean fixture command:
`.venv-repro/Scripts/python.exe -m pytest tests/test_experiment_runner.py::test_frozen_test_reuses_selected_validation_checkpoint_and_alpha tests/test_demo_export.py::test_exporter_builds_real_bundle_from_compatible_runs -q`.
2 passed,3 upstream warnings,9.79s; actual prepare/split/train/valid/freeze/test
and snapshot fixture execution.

Clean `task13_reproduce.py`:load selected BPR tensor checkpoint twice,score full
universe for snapshot3,compare full Top10 score/order exactly,independent NDCG
vs frozen per-user Parquet. First3 cases pass1.356s. Expanded with one diagnostic
positive hit(history7,NDCG.5) and reran only4 case verification1.486982s; all
rankings/scores exact,metrics tolerance1e-12. This is NOT full-test repetition.
Real demo validate CLI passed. All source IDs in ignored helper only.
Lock SHA256 `1ea4c9807f56d9563e92a90431c59dcb76bc0e768c4a074121157e126a49e8d5`.
Checkpoint SHA256 unchanged`c4dbd2d88e71689b1d447f314fe6b9dc1a90af95499d2cafdba5eec03b36720a`.

Clean environment left local at worktree`.venv-repro/`. Added only local
common Git info/exclude pattern`/.venv-repro/`; no tracked ignore modification.
Do not commit or copy environment as reproducibility substitute.

## Browser evidence performed by root

Subagent CUA create tab blocked('IAB visibility is not supported in a subagent
thread',bothtrue/false). Root completed real browser work at my request:
- real8513:all12 profile/model combinations rendered10 ranked rows with distinct
  correct run IDs and varied tops. Offline/dataset/protocol/P1-limit visible.
- ModelLab test/warm/full_train_universe/train_plus_valid + metadata visible;
  actual CSV download success. I independently read downloaded CSV:pandas4rows,
  cohort9858,run IDs/config hashes/metrics match real snapshot tolerance1e-12.
  CSV digest`ca9bf2d2587c4756f04449dd618905861a7713a575db35b4ff7a13f2a5eda406`.
- synthetic fixture8514 explicit label,3-item short rankings,new-user fallback.
- separately copied synthetic variant8516 new-user empty0/no-history/fallback/
  no-course messages; authoritative real snapshot unchanged.
- invalid8515 only schema error,no recommendation/synthetic fallback.
- browser warning/error logs empty. Real tab kept; temporary tabs closed.
Visual evidence is UI correctness,not independent ranking/model quality.

## Handoff and self-review

Public docs have no learner IDs/local absolute paths/secrets/large artifacts.
Seven files exactly staged;58 internal file links checked,all exist;
staged whitespace check pass. P0 achieved bounded offline scope,P1 stop;
same-machine clean env distinguished from new physical-machine/full training
reproduction. One seed/limited BPR budget/no statistical claims retained.
Runbook distinguishes executed records vs examples and documents artifact-copy,
no manifest rewrite,new-validation/new-freeze requirements after changes.
Task13 commit leaves all source/config frozen values untouched.

Preserve/copy before managed worktree archive:
- Prior Task11 required data/split/valid/search inventory.
- ENTIRE new test batch at relative path above (30files65591620bytes).
- `artifacts/demo/v1/demo_bundle.json`(246003bytes).
- `results/local/final-test-once.{log,measurement.json}`,task13-analyze.log,
  task13-summary.json,task13-clean-reproduce.json,clean-install/editable/
  pip-check/fixture/real/lock-check logs,clean-freeze.txt,task13_* helper scripts.
- Browser downloaded CSV currently`<DOWNLOADS_DIR>\learnpath_test_runs.csv`.
Keep real server8513 alive for deliverable;root may stop temporary8514/8515/8516
after review. Their launcher PIDs recorded in tool outputs,Python children exist.

Concerns: no block. GitHub push and whole-branch review pending controller.
Task11 core_manifest remains deliberately validation-only historical freeze
authority;final report is final-test authority. No production source changes.

## Final whole-branch fix wave — onboarding documentation

Important reviewer issue addressed in commit
`57d5b06874b0bd13c2f79efb5864bf211b19d17b`, base `5773af4`.
Only four requested onboarding docs changed: docs/README.md,
docs/03_architecture.md,docs/04_data_contract.md,docs/05_evaluation.md.
No production code, frozen config, model or real artifact modified; no subagent.

- Replaced stale pre-implementation status with implemented/real-data P0
  evidence and direct links to final/validation/reproduction/acceptance.
  Identified base reports/six-week dates and retained P1 ideas as historical.
- Updated model interface to score(user_id,candidate_ids)->ScoreResult with
  course_ids,scores,fallback_status,evidence, exact source ordering, finite
  NumPy scores and evaluator-owned mask/rank/tie responsibilities.
- Corrected actual module paths (ranking,runner,export,knowledge/audit) and
  directory structure (separate data/splits, batch artifacts/runs/snapshot_inputs,
  RecBole recsysedu.<split>.inter, checkpoint/ID-map/feature manifest names).
- Replaced obsolete per_user_metrics.csv by actual per_user_metrics.parquet;
  verified all four real run directories contain the Parquet file.
- Separated mandatory warm/full-universe/train-only/seen/K10 protocol from
  post-test descriptive history groups1-4,5-19,20+, counts6110/2285/1463.
  Old1-3/from4 proposal explicitly historical and not applied/tuned on test.
- Clarified real exporter constraints/schema1/evidence_level/offline/P0 model
  set,paths=[] and prerequisite unknown. P1 audit is implemented but real
  sources absent; graph/path/penalty contract remains unimplemented.

Verification after final edits:4 docs,42 internal file links all exist;
code fences balanced; all14 listed implementation paths exist; actual
Recommender signature/dataclass fields match doc; history subgroup counts
match saved Task13 summary. RG stale-claim/API/path/CSV patterns returned
no matches. Git diff/staged diff --check passed. Only these4 docs staged.
No pytest/Ruff rerun:documentation-only change, no Python/config/artifact
diff; previous262-pass gate remains recorded, not falsely rerun.
Self-review checked current vs historical wording, P1 limits, exact artifact
names and evaluation-vs-descriptive-group distinction. Worktree clean after
commit; ready for controller final verification/integration/push.
