## Task 8: Implement Hybrid scoring and validation tuning

**Files:**
- Create: `src/recsysedu/models/hybrid.py`
- Create: `tests/test_hybrid.py`
- Create: `configs/hybrid.yaml`

**Interfaces:**
- Consumes: Content and BPR `Recommender` instances over identical candidate IDs
- Produces: `HybridModel(content, bpr, alpha, popularity).score(...) -> ScoreResult`; `select_alpha(validation_runs, alphas) -> float`

- [ ] **Step 1: Write failing Hybrid tests**

```python
def test_alpha_zero_and_one_equal_normalized_components(): ...
def test_constant_component_becomes_zero_vector_without_nan(): ...
def test_hybrid_rejects_candidate_order_or_length_mismatch(): ...
def test_missing_bpr_user_falls_back_to_content_then_popularity(): ...
def test_alpha_selection_uses_validation_ndcg_then_smallest_alpha_tie_break(): ...
```

- [ ] **Step 2: Verify failure**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_hybrid.py -q`

Expected: FAIL because Hybrid does not exist.

- [ ] **Step 3: Implement normalization, combination and fallback**

Per user/run, min–max each component over the same candidate list. Constant vectors become zero vectors. Validate alpha in `[0, 1]`; pilot grid is `[0, 0.25, 0.5, 0.75, 1]`.

- [ ] **Step 4: Run focused tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_hybrid.py tests/test_content.py tests/test_evaluation.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add configs/hybrid.yaml src/recsysedu/models/hybrid.py tests/test_hybrid.py
git commit -m "feat: add hybrid course ranking"
```

