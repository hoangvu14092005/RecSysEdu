## Task 6: Implement Content TF-IDF

**Files:**
- Create: `src/recsysedu/models/content.py`
- Create: `tests/test_content.py`
- Create: `configs/content.yaml`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: course metadata, train interactions and `ContentConfig(analyzer, ngram_range, min_df)`
- Produces: `fit_content(courses: pd.DataFrame, train: pd.DataFrame, config: ContentConfig, artifact_dir: Path, fallback: Recommender) -> ContentModel`; `ContentModel.score(...) -> ScoreResult`

- [ ] **Step 1: Write failing content tests**

```python
def test_content_profile_uses_train_courses_only(): ...
def test_content_prefers_course_with_shared_character_ngrams(): ...
def test_content_empty_profile_returns_popularity_fallback_status(): ...
def test_content_feature_manifest_preserves_course_order_and_config_hash(): ...
```

- [ ] **Step 2: Verify failure**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_content.py -q`

Expected: FAIL because Content module/config do not exist.

- [ ] **Step 3: Implement TF-IDF and persisted artifacts**

Join normalized `name` and `about`; default pilot uses `analyzer="char"`, `ngram_range=(2, 4)`. Fit vectorizer only on the fixed course universe, create user profiles only from train, save vectorizer/sparse matrix/course order/feature manifest.

Inject the Task 5 popularity model for empty-profile fallback; preserve `fallback_status="popularity_empty_profile"`.

- [ ] **Step 4: Run focused tests and lint**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_content.py tests/test_popularity.py -q`

Run: `.\.venv\Scripts\python.exe -m ruff check src tests`

Expected: both PASS.

- [ ] **Step 5: Commit**

```powershell
git add pyproject.toml configs/content.yaml src/recsysedu/models/content.py tests/test_content.py
git commit -m "feat: add tf-idf course recommender"
```

