## Task 4: Implement common ranking and evaluator

**Files:**
- Create: `src/recsysedu/evaluation/__init__.py`
- Create: `src/recsysedu/evaluation/metrics.py`
- Create: `src/recsysedu/evaluation/ranking.py`
- Create: `src/recsysedu/evaluation/run.py`
- Create: `tests/test_metrics.py`
- Create: `tests/test_evaluation.py`

**Interfaces:**
- Consumes: `Recommender`, split Parquet and `RunIdentity`
- Produces: `rank_candidates(result, seen_ids, *, k) -> tuple[RankedItem, ...]`, `metrics_at_k(ranked_ids, target_ids, universe_size, *, k) -> dict[str, float]`, `evaluate_run(model, split_dir, output_dir, identity, *, evaluation_split, k=10) -> dict`

- [ ] **Step 1: Write failing metric tests using hand-calculated cases**

Assert NDCG is `1.0` at rank 1, approximately `0.6309297536` at rank 2 and `0.0` on miss. With one target, assert Recall equals HitRate and Precision equals HitRate/10.

- [ ] **Step 2: Write failing ranking/evaluator tests**

```python
def test_ranking_masks_seen_and_breaks_equal_scores_by_course_id(): ...
def test_ranking_rejects_nan_instead_of_silently_sorting_it(): ...
def test_valid_uses_train_seen_while_test_masks_train_plus_valid(): ...
def test_evaluator_rejects_mismatched_dataset_split_or_protocol_hash(): ...
```

- [ ] **Step 3: Verify the tests fail**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_metrics.py tests/test_evaluation.py -q`

Expected: FAIL because evaluation modules do not exist.

- [ ] **Step 4: Implement metrics, ranking and streaming evaluation**

Evaluate one user at a time so full-ranking scores are not stored as a dense user-by-course matrix. Write `metrics.csv`, `per_user_metrics.parquet`, `recommendations.jsonl` and `run_manifest.json` atomically.

- [ ] **Step 5: Run focused tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_metrics.py tests/test_evaluation.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add src/recsysedu/evaluation tests/test_metrics.py tests/test_evaluation.py
git commit -m "feat: add shared top-k evaluator"
```

