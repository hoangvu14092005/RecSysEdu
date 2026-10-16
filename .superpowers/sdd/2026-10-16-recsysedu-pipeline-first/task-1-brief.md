## Task 1: Define shared scoring and run contracts

**Files:**
- Create: `src/recsysedu/contracts.py`
- Create: `tests/test_contracts.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: source IDs as `str` and NumPy arrays of finite scores
- Produces: `ScoreResult`, `RankedItem`, `RunIdentity`, and `Recommender.score(user_id, candidate_ids)` used by Tasks 4–10

- [ ] **Step 1: Write failing contract tests**

Add tests asserting:

```python
def test_score_result_rejects_length_mismatch_and_non_finite_scores(): ...
def test_run_identity_requires_non_empty_matching_hash_fields(): ...
def test_ranked_item_requires_rank_from_one_and_finite_score(): ...
```

`ScoreResult(course_ids, scores, fallback_status, evidence)` must preserve candidate order and reject duplicate IDs, mismatched lengths, NaN and infinity.

- [ ] **Step 2: Verify the tests fail**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_contracts.py -q`

Expected: FAIL because `recsysedu.contracts` does not exist.

- [ ] **Step 3: Implement the interfaces**

Create:

```python
@dataclass(frozen=True)
class ScoreResult:
    course_ids: tuple[str, ...]
    scores: np.ndarray
    fallback_status: str = "none"
    evidence: Mapping[str, tuple[str, ...]] = field(default_factory=dict)

@dataclass(frozen=True)
class RankedItem:
    course_id: str
    rank: int
    score: float

@dataclass(frozen=True)
class RunIdentity:
    run_id: str
    model_id: str
    dataset_hash: str
    split_hash: str
    protocol_id: str
    seed: int | None

class Recommender(Protocol):
    def score(self, user_id: str, candidate_ids: Sequence[str]) -> ScoreResult: ...
```

Add direct dependency `numpy>=1.26,<3` because the shared scoring contract exposes NumPy arrays.

- [ ] **Step 4: Run the focused and base tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_contracts.py tests/test_demo_artifacts.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add pyproject.toml src/recsysedu/contracts.py tests/test_contracts.py
git commit -m "feat: define recommendation contracts"
```

