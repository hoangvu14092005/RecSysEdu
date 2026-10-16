# SDD ledger — plan: docs/superpowers/plans/2026-10-16-recsysedu-pipeline-first.md

## Pre-flight review

| Tasks / area | Producer -> consumer or shared file | Finding |
| --- | --- | --- |
| Task 0 | Current untracked base -> all later tasks/worktree | Conflict: a worktree from current HEAD would omit source. Ruling: execute approved Task 0 in the primary checkout, review it, then create the isolated worktree from the new baseline. Cost if wrong: baseline commit may include an unintended local file; mitigate with ignore checks and staged-file review. |
| 0 -> 1–13 | Baseline repository -> all implementation | Clean after the Task 0 ruling; later tasks receive tracked source. |
| 1 -> 4–10 | `ScoreResult`, `RankedItem`, `RunIdentity`, `Recommender` -> model/evaluator/demo | Clean; signatures are centralized in Task 1. |
| 1 / 2 / 6 / 7 | Sequential edits to `pyproject.toml` | Clean; each task adds only its direct dependency/marker and preserves earlier entries. |
| 2 -> 3 | Prepared Parquet/manifest -> temporal split | Clean; Task 3 consumes the exact Task 2 outputs. |
| 2 / 3 / 9 | Sequential edits to `src/recsysedu/cli.py` | Clean; commands are additive and each task reruns CLI tests. |
| 3 -> 4 / 7 / 9 | Split/cohort/universe -> evaluator, RecBole and runner | Clean; shared hashes and `leave_last_two_out_v1` bind consumers. |
| 4 -> 5–10 | Shared ranker/evaluator -> all model runs | Clean; models only score, evaluator owns mask/tie/metrics. |
| 5 -> 6 / 8 | Popularity fallback -> Content and Hybrid | Clean; Task 6 receives fallback via the Task 1 `Recommender` protocol. |
| 6 / 7 -> 8 | Content and BPR scores -> Hybrid | Clean; candidate order/length mismatch is an explicit test. |
| 7 -> 9 / 13 | BPR artifacts/checkpoint -> experiment runner and reproduction | Clean; adapter owns internal/source ID mapping. |
| 9 -> 10 / 11 / 13 | Run manifests -> snapshot, validation freeze and final test | Clean; mismatched hashes are rejected by runner/exporter tests. |
| 9 / 11 | Sequential edits to `configs/final_experiments.yaml` | Clean; Task 9 creates it, Task 11 writes selected values and `frozen: true`. |
| 10 -> 13 | Real snapshot exporter -> final demo | Clean; schema v1 and `paths=[]` remain fixed for P0. |
| 11 / 13 | Sequential edits to `tasks/todo.md` | Clean; only evidence-backed status updates are allowed. |
| 12 | P1 audit -> possible future P1 plan | Clean and isolated; no rerank/path implementation enters this P0 plan. |
| 13 | Frozen P0 -> test/reproduction/handoff | Clean; test is opened once after Task 11 freeze. |

Task 0: fix round 1/5 (2 addressed, 0 open; commits 8670d18..0a36d43)
Task 0: complete (commits db215ef..0a36d43, review clean)

Worktree: <CODEX_HOME>\worktrees\pipeline-first\RecSysEdu (detached HEAD at 0a36d43; native managed worktree)
Baseline verification: 28 pytest passed; Ruff passed.
Task 1: active
Task 1: fix round 1/5 (1 addressed, 0 open; commits 6f920c9..d5a677b)
Task 1: complete (commits 0a36d43..d5a677b, review clean)
Task 2: active
Task 2: minor (deferred): duplicate_interaction reject records normalized course ID instead of the losing raw enrollment ID; revisit in final whole-branch review.
Task 2: fix round 1/5 (1 addressed, 0 open; commits fed64a1..7f67b9c)
Task 2: complete (commits d5a677b..7f67b9c, review clean except 1 deferred minor)
Task 3: active
Task 3: fix round 1/5 (1 addressed, 0 open; commits cd46f28..ec1bdd8)
Task 3: complete (commits 7f67b9c..ec1bdd8, review clean)
Task 4: active
Task 4: fix round 1/5 (1 addressed, 0 open; commits 7ef6312..da702df; original implementer turn failed before changes, fresh fixer completed)
Task 4: complete (commits ec1bdd8..da702df, review clean)
Task 5: active
Task 5: minor (deferred): direct PopularityModel construction can silently truncate mismatched universe/counts via zip; fit_popularity path is valid.
Task 5: complete (commits da702df..a1d00c3, review clean except 1 deferred minor)
Task 6: active
Task 6: fix round 1/5 (1 addressed, 0 open; commits 256f51c..8f6ed43)
Task 6: complete (commits a1d00c3..8f6ed43, review clean)
Task 7: active
Task 7: complete (commits 8f6ed43..31abf2b, review clean)
Task 8: active
Task 8: complete (commits 31abf2b..a0f5445, review clean; reviewer focused tests 71 passed)
Task 9: active
Task 9: fix round 1/5 (1 Important addressed, 0 open; commits 1a1b254..a36ea25)
Task 9: complete (commits a0f5445..a36ea25, review clean)
Task 10: active
Task 10: complete (commits a36ea25..e7663cd, review clean; reviewer focused/integration tests 53 passed)
Task 11: active
Task 11: production scope correction (f8ca95b) and fix round 1/5 (e101b67), independently reviewed clean
Task 11: minor (deferred): validation_report early-stopping wording says consecutive decreases; RecBole counts values below best, ties reset counter.
Task 11: complete (evidence commit ae89581, review clean except 1 deferred documentation minor; real validation frozen, test unopened)
Task 12: complete (commit 68a373b, review clean; P1_STOP_INSUFFICIENT_EVIDENCE)
Task 13: active
Task 13: complete (commit 5773af4, review clean; frozen test once, clean-env reproduction and browser verification passed)
Final whole-branch review: fix wave 1/1 (Important stale onboarding docs fixed in 57d5b06; re-review APPROVE)
Deferred minors: Task 2 duplicate reject stores normalized course ID but retains source_record/raw source; Task 5 direct PopularityModel constructor can truncate mismatched arrays, supported fit_popularity path is valid.
Plan status: implementation and required reviews complete; integration, final verification and authorized GitHub push pending.
