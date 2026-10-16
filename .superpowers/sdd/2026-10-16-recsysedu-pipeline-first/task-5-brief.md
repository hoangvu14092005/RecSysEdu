## Task 5: Implement MostPopular baseline

**Files:**
- Create: `src/recsysedu/models/__init__.py`
- Create: `src/recsysedu/models/popularity.py`
- Create: `tests/test_popularity.py`
- Create: `configs/popularity.yaml`

**Interfaces:**
- Consumes: train interactions and sorted candidate universe
- Produces: `fit_popularity(train: pd.DataFrame, universe: Sequence[str]) -> PopularityModel`; `PopularityModel.score(...) -> ScoreResult`

- [ ] **Step 1: Write the failing tests**

```python
def test_popularity_counts_train_only_and_scores_unseen_candidates(): ...
def test_popularity_ties_are_resolved_by_shared_ranker(): ...
def test_popularity_never_reads_valid_or_test_targets(): ...
```

- [ ] **Step 2: Verify failure**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_popularity.py -q`

Expected: FAIL because the model does not exist.

- [ ] **Step 3: Implement the model**

Scores are train enrollment counts as floats. Unknown candidate IDs raise `ValueError`; user ID does not change popularity scores.

- [ ] **Step 4: Run model and evaluator tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_popularity.py tests/test_evaluation.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/recsysedu/models configs/popularity.yaml tests/test_popularity.py
git commit -m "feat: add most-popular baseline"
```

