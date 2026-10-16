# Task 4 implementation report

Status: complete; implemented and committed in the assigned worktree.

- Worktree: `<CODEX_HOME>\worktrees\pipeline-first\RecSysEdu`
- Starting HEAD: `ec1bdd8`
- Commit: `7ef6312ce79bcf1e8d77bd8af46a30b9287cd922` — `feat: add shared top-k evaluator`
- Interpreter: `<REPO_ROOT>\.venv\Scripts\python.exe`
- Scope: the four evaluation modules and the two requested test files only. No model, CLI, dataset, split producer, or UI changes.

## Implemented contracts

`rank_candidates(result, seen_ids, *, k) -> tuple[RankedItem, ...]`

- Revalidates `ScoreResult`, including finite scores for masked items.
- Filters seen source IDs, sorts score descending/course ID ascending, returns at most K items with contiguous one-based ranks.
- Rejects invalid K and non-`ScoreResult` output. Preserves legitimate overlap between user-ID and course-ID namespaces.

`metrics_at_k(ranked_ids, target_ids, universe_size, *, k) -> dict[str, float]`

- Canonical names in both this function and persisted artifacts: `NDCG@K`, `HitRate@K`, `Recall@K`, `Precision@K`, `Coverage@K`.
- Binary relevance, IDCG from the entire valid target set capped at K, Recall denominator is the target count, Precision denominator is K even for short lists.
- Truncates the ranking to K, rejects duplicate IDs/invalid cardinalities/empty ground truth, treats an empty recommendation list as a valid miss.
- Per-user Coverage describes that list; overall Coverage is recomputed from the union of recommended courses over the common universe.

`evaluate_run(model, split_dir, output_dir, identity, *, evaluation_split, k=10) -> dict`

- Uses Task 3 `valid_cohort.parquet` or `test_cohort.parquet`; cold targets remain reported outside the warm benchmark.
- Checks the `RunIdentity` dataset hash, split hash and protocol ID against the split manifest; rejects unsupported protocol/schema, recomputes the canonical split-manifest hash, and verifies all six split Parquet hashes.
- Checks the sorted candidate universe equals distinct train courses; verifies unique held-out targets, seen/target separation, warm cohort membership and size.
- Calls only `model.score(user_id, full_train_universe)`, one user at a time. Requires the complete, unchanged candidate order in `ScoreResult`.
- Valid masks train; test masks train plus valid. Evaluation never calls a model fitting method or passes valid/test history into a profile update.
- Streams source Parquet batches and JSONL; writes per-user metric rows in bounded batches of 1,024. It retains sparse histories and target maps, but never builds a dense users-by-courses score matrix.
- Writes all four artifacts in a sibling temporary directory, closes writers, rechecks input hashes, then publishes with one directory rename. Existing outputs are rejected. Failures remove the staging directory and leave no published run.
- The returned dictionary is exactly the serialized `run_manifest.json` contents.

## Persisted artifact contracts

`metrics.csv`: one summary row with all six RunIdentity fields, `evaluation_split`, `k`, `cohort_size`, and the five canonical metric columns.

`per_user_metrics.parquet`: `user_id`, `target_id`, `recommendation_count`, `train_history_count`, `fallback_status`, and the five canonical metric columns. Per-user Coverage is not the aggregate Coverage.

`recommendations.jsonl`: one record per evaluated user:

```json
{
  "user_id": "U_example",
  "target_ids": ["C_target"],
  "fallback_status": "none",
  "items": [
    {"course_id": "C_target", "rank": 1, "score": 0.5, "evidence": []}
  ]
}
```

Evidence is copied by ranked `course_id` from `ScoreResult.evidence`; missing evidence becomes `[]`. Sorting/masking cannot misalign it. No `reason_codes` are invented because the scoring contract does not define them. Task 10 can derive stable reason codes from model/fallback metadata while preserving the evidence array.

`run_manifest.json`: RunIdentity, schema version, evaluation split/K, primary metric, aggregate metrics, cohort/universe sizes, short-list/cold-target counts, fallback counts, candidate/profile/seen/tie-break policies, `history_mode="offline"`, `metric_status="measured"`, measured duration, split-manifest file hash, hashes of the three data artifacts, and the methodological limitations below. The manifest does not hash itself.

## TDD evidence

1. Wrote metric/ranking/evaluation tests before any evaluation module existed.
2. RED command: `python -m pytest tests/test_metrics.py tests/test_evaluation.py -q` produced two collection failures, both `ModuleNotFoundError: No module named 'recsysedu.evaluation'`, as the task brief expected. Repeated after canonical metric-name alignment; same expected RED.
3. Initial implementation: 39 passed and one test failed. The test fixture's expected aggregate Coverage had a hand-calculation error: its lists jointly contain `C_1`, `C_2`, and `C_3`, so Coverage is 3/3=1, whereas the mean per-user Coverage is 4/9. Corrected that literal expectation after independently enumerating the lists; no metric implementation change was made for that discrepancy.
4. Initial GREEN: 40 focused cases passed.
5. Added evidence-propagation and overlapping-ID regression cases before their fixes. RED: `test_evaluator_preserves_ranked_item_evidence_after_masking_and_sorting` failed with missing `evidence`; `test_source_user_and_course_ids_can_overlap` failed because a shared row-level duplicate check conflated two namespaces. Fixed evidence serialization and validated user/course IDs separately.
6. Additional behavioral checks cover 1,029-user output across batch boundaries, empty warm cohort rejection, and source mutation during scoring preventing publication.
7. Final GREEN: 45 focused cases passed.

Hand-calculated metric cases include rank 1 NDCG=1, rank 2 approximately 0.6309297536, miss/outside Top-10 NDCG=0, one-target Recall=HitRate, Precision=HitRate/10 on short lists, and a multi-target case with NDCG approximately 0.7039180890.

## Final verification

All commands ran from the assigned worktree using the specified interpreter before commit:

| Command | Result |
| --- | --- |
| `python -m pytest tests/test_metrics.py tests/test_evaluation.py -q` | 45 passed in 3.40s |
| `python -m pytest tests/test_split.py tests/test_contracts.py -q` | 37 passed in 1.47s |
| `python -m pytest -q` | 139 passed in 8.38s |
| `python -m ruff check .` | All checks passed |
| `git diff --cached --check` | Exit 0, no whitespace errors |
| `git status --short` after commit | Empty; worktree clean |

Static review covered metric denominators/IDCG, full-ranking alignment, finite-score enforcement before seen filtering, exact warm cohort matching, evidence alignment, bounded output buffers, failure cleanup, hash revalidation, and overwrite preservation. No new dependencies were introduced. No unresolved failures were observed in the final focused, regression, full-suite or Ruff runs.

## Concerns and boundaries

- These are runtime tests of the evaluator with controlled fixture data and test-only static score providers. They are not recommender training, pilot benchmark metrics, or evidence that any real model is ready.
- The `Recommender` contract exposes only `score`; evaluator cannot inspect the provenance of a supplied model's internal training data. It enforces score-only/frozen evaluation, candidate and mask rules, while model construction/loading must still ensure train-only provenance.
- Empty warm cohorts raise `ValueError` instead of creating apparently measured zero-user metrics.
- Sparse train histories and user target maps are retained in memory; score storage is bounded to a single user's universe. This task has not measured performance on a full real-data run.
- Per-user temporal splits can include other users' later interactions in train; static catalog availability is not time-aware. Enrollment ranking does not measure mastery or learning gain. These limits are written into each run manifest.
- Duration is measured and intentionally varies between repeated runs; run manifests are not claimed byte-identical.
- Publication uses an atomic directory rename on the same filesystem; power-loss durability/fsync guarantees are outside this task.
- Protocol is validated using the defined `protocol_id` plus the canonical split hash; the Task 1 identity has no separate `protocol_hash` field.

## Memory provenance

The memory quick pass confirmed the prior preference for evaluator/data contracts before UI and the existing NDCG/temporal-mask methodology. All implementation decisions were checked against the current task brief, current contracts, split producer and repository documentation. Relevant memory references: `MEMORY.md:119-125` and `rollout_summaries/2026-10-09T09-56-52-4uA5-recsysedu_documentation_methodology_roadmap.md:15-24`; rollout ID `01a12018-1a34-78f0-b32b-c268601075e5`.

## Fix round 1: enforce the approved K at publication

- Finding: `evaluate_run(..., k=1)` could publish a measured run with `NDCG@1` while retaining protocol `leave_last_two_out_v1`, whose approved K is 10.
- Change: `evaluate_run` now raises `ValueError('evaluate_run requires k=10 for leave_last_two_out_v1')` immediately after generic K validation and before output path setup or staging. Generic ranking and metric helpers remain configurable.
- Regression: `test_evaluator_rejects_non_protocol_k_before_creating_output` asserts `k=1` fails with no output or staging directory, then runs `k=10` successfully and checks the returned K.
- Exact changed files: `src/recsysedu/evaluation/run.py`; `tests/test_evaluation.py`.
- Focused command: `& '<REPO_ROOT>\.venv\Scripts\python.exe' -m pytest tests/test_metrics.py tests/test_evaluation.py -q`
- Focused output: `46 passed in 3.61s`.
- Full-suite command: `& '<REPO_ROOT>\.venv\Scripts\python.exe' -m pytest -q`
- Full-suite output: `140 passed in 9.00s`.
- Ruff command: `& '<REPO_ROOT>\.venv\Scripts\python.exe' -m ruff check .`
- Ruff output: `All checks passed!`.
- Diff check: `git diff --check` exited 0 with no whitespace errors; Git emitted only line-ending conversion warnings for the two edited files.
- Commit: `da702dff2f5f6ad94f3e7a90dc53862dc1bd3a40` — `fix: enforce evaluation protocol K`.
- Post-commit `git status --short`: empty.
