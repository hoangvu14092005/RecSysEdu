# RecSysEdu Pipeline-first Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Xây pipeline có thể chạy lại từ MOOCCubeX raw đến bốn mô hình, đánh giá offline, snapshot thật và demo Streamlit trong sáu tuần.

**Architecture:** Mỗi giai đoạn đọc artifact versioned và ghi artifact mới kèm manifest/hash. Model dùng chung giao diện chấm điểm; evaluator chịu trách nhiệm candidate universe, seen mask, Top-K và metric. UI chỉ đọc `demo_bundle.json`, không gọi training.

**Tech Stack:** Python 3.10+, PyArrow/Parquet, DuckDB, pandas, NumPy, scikit-learn, RecBole/PyTorch, PyYAML, pytest, Ruff và Streamlit.

**Spec:** `docs/superpowers/specs/2026-10-16-recsysedu-pipeline-first-design.md`

## Global Constraints

- P0 gồm MostPopular, Content TF-IDF, BPR, Hybrid, evaluator, snapshot thật và Streamlit tối thiểu.
- P1 graph chỉ đi qua audit/cổng quyết định trong plan này; rerank/path cần plan riêng nếu dữ liệu đạt.
- Bắt đầu với 10.000 user đủ điều kiện, seed cố định; chỉ tăng đến khoảng 30.000 sau khi đo RAM, dung lượng và thời gian.
- Raw giữ nguyên ngoài Git; processed chính dùng Parquet và truy vấn bằng DuckDB.
- Timestamp không được gắn UTC giả. Split chỉ phát hành khi có nguồn timezone hoặc config ghi `source_local_naive` và chỉ dùng thứ tự trong từng user.
- Valid dùng profile/model từ train và mask train. Test vẫn dùng profile/model từ train, mask train + valid; không retrain ngầm.
- Candidate universe là các khóa có tương tác train; mọi model dùng cùng cohort, universe, seen mask và tie-break `course_id` tăng dần.
- K = 10; NDCG@10 là metric chính. Test chỉ mở sau khi khóa dataset, protocol, seed và tham số.
- UI không train khi click, không tự chuyển sang fixture nếu snapshot thật lỗi, và không trình bày enrollment như mastery.
- Python tối thiểu 3.10; không ghi đường dẫn ổ đĩa tuyệt đối vào code/config được commit.
- Mỗi task chỉ commit file thuộc task; raw, processed Parquet, checkpoint lớn, `.venv`, `.archify` và `results/local` không vào Git.

## Review Focus

1. **Timestamp naive hoặc hòa ranh giới:** Task 2 phải từ chối mode thời gian không khai báo và Task 3 phải cách ly user có ba mốc cuối không tăng nghiêm ngặt.
2. **ID số không có trong catalog:** Task 2 phải cách ly thay vì tạo `C_<số>` mới.
3. **Target/seen leakage:** Task 3 và Task 4 phải chứng minh valid/test target không vào profile và seen item không vào Top-K.
4. **Score hằng, NaN hoặc model không áp dụng:** Task 4, 6 và 8 phải xử lý xác định, dùng fallback có nhãn và không tạo ranking từ score lỗi.
5. **Artifact khác dataset/split/protocol:** Task 9 và Task 10 phải chặn ghép run/snapshot có hash không khớp.

---

## File Map

### File hiện có sẽ sửa

- `.gitignore`: bỏ qua artifact sinh ra, `.archify/` và cache local.
- `pyproject.toml`, `requirements-win-py310.lock.txt`: dependency data/model đã chạy được.
- `configs/data.yaml`: nguồn raw và chính sách thời gian.
- `src/recsysedu/cli.py`: thêm command prepare, split, train, evaluate, experiments và demo export.
- `src/recsysedu/demo/artifacts.py`: giữ validation v1 và hỗ trợ snapshot thật do exporter tạo.
- `app/streamlit_app.py`: chỉ sửa phần đọc/hiển thị metadata cần cho artifact thật.
- `docs/04_data_contract.md`, `docs/05_evaluation.md`, `docs/09_runbook.md`: đồng bộ contract và lệnh đã chạy.
- `tasks/todo.md`: cập nhật chỉ khi có bằng chứng.

### File mới

- `src/recsysedu/data/prepare.py`: làm sạch raw và ghi dataset Parquet/manifest.
- `src/recsysedu/data/split.py`: tạo temporal split/cohort/manifest.
- `src/recsysedu/contracts.py`: dataclass/protocol dùng chung cho scoring và run identity.
- `src/recsysedu/evaluation/metrics.py`: metric Top-K thuần, kiểm bằng ví dụ tính tay.
- `src/recsysedu/evaluation/ranking.py`: candidate, seen mask, tie-break và Top-K.
- `src/recsysedu/evaluation/run.py`: chạy evaluator và ghi artifact.
- `src/recsysedu/models/popularity.py`: baseline popularity.
- `src/recsysedu/models/content.py`: TF-IDF, profile và content scorer.
- `src/recsysedu/adapters/recbole.py`: atomic export, BPR train/load và ID mapping.
- `src/recsysedu/models/hybrid.py`: chuẩn hóa score và ghép trọng số.
- `src/recsysedu/experiments/runner.py`: điều phối run bằng config đã khóa.
- `src/recsysedu/demo/export.py`: xuất `demo_bundle.json` từ run artifact.
- `src/recsysedu/knowledge/audit.py`: P1 chỉ audit mapping/edge/coverage.
- `configs/prepare.yaml`, `configs/split.yaml`, `configs/popularity.yaml`, `configs/content.yaml`, `configs/bpr.yaml`, `configs/hybrid.yaml`, `configs/final_experiments.yaml`.
- Các test cùng tên trách nhiệm dưới `tests/`.

## Task 0: Establish the repository baseline

**Files:**
- Modify: `.gitignore`
- Track: source, tests, configs, docs, task files, small fixtures and non-sensitive reports currently untracked
- Exclude: `.archify/`, `data/`, `artifacts/`, `.venv/`, caches and `results/local/`

**Interfaces:**
- Consumes: working tree hiện tại và commit spec `7f2cb19`
- Produces: một baseline commit chứa đúng trạng thái base đã được báo cáo, để worktree/branch mới có đủ source

- [ ] **Step 1: Audit files before staging**

Run: `git status --short` and `git check-ignore -v data/raw/course.json data/raw/user.json results/local/data_audit.json .venv/pyvenv.cfg`

Expected: raw, local result và virtual environment đều bị ignore; danh sách untracked không chứa credential hoặc dữ liệu người học cần loại thêm.

- [ ] **Step 2: Add `.archify/` and generated caches to `.gitignore`**

Keep `.streamlit/config.toml`, tests fixtures and Markdown reports because they are small project inputs/evidence.

- [ ] **Step 3: Verify the current base before recording it**

Run: `.\.venv\Scripts\python.exe -m pytest -q`

Expected: existing base suite passes.

Run: `.\.venv\Scripts\python.exe -m ruff check src app tests`

Expected: `All checks passed`.

- [ ] **Step 4: Stage and inspect the exact baseline**

Run: `git add .gitignore .streamlit CONTRIBUTING.md README.md app configs docs pyproject.toml requirements-win-py310.lock.txt results src tasks tests`

Run: `git diff --cached --name-only` and `git diff --cached --check`

Expected: no raw/processed/checkpoint/local result/`.archify` path; no whitespace error.

- [ ] **Step 5: Commit**

```powershell
git commit -m "chore: establish RecSysEdu base"
```

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

## Task 2: Prepare a versioned Parquet dataset

**Files:**
- Create: `src/recsysedu/data/prepare.py`
- Create: `tests/test_prepare.py`
- Create: `configs/prepare.yaml`
- Modify: `src/recsysedu/cli.py`
- Modify: `docs/04_data_contract.md`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: raw `course.json`, `user.json`; `prepare_dataset(course_path, user_path, output_dir, *, dataset_version, time_basis, sample_users, seed) -> dict`
- Produces: `courses.parquet`, `interactions.parquet`, `rejects.parquet`, `cohort_users.parquet`, `dataset_manifest.json`

- [ ] **Step 1: Write failing prepare tests**

Add fixture records covering exact string ID, numeric catalog match, unknown numeric ID, duplicate enrollment, invalid timestamp, array mismatch and naive timestamps. Assert:

```python
def test_prepare_maps_only_catalog_ids_and_keeps_earliest_duplicate(): ...
def test_prepare_rejects_unknown_ids_and_bad_histories_with_reason_codes(): ...
def test_prepare_requires_declared_time_basis_and_is_seed_reproducible(): ...
```

`time_basis` accepts exactly `source_local_naive` or a valid IANA timezone key. For `source_local_naive`, write Arrow `event_time` as timezone-free timestamp and `event_time_raw` as source string; do not create UTC values. For an IANA key, localize the raw naive value with that key and write UTC plus the original string.

- [ ] **Step 2: Verify the tests fail**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_prepare.py -q`

Expected: FAIL because `prepare_dataset` does not exist.

- [ ] **Step 3: Implement streaming preparation**

Use `iter_records` from `data.audit`, deterministic reservoir sampling over eligible users, PyArrow for Parquet and DuckDB only for post-write validation. `sample_users=0` means all eligible users; pilot config uses `10000`, seed `20261016`.

Add direct data dependency `pandas>=2.2,<3`; keep DuckDB and PyArrow in the existing `data` extra.

Manifest fields must include raw file hashes, dataset version, time basis, seed, requested/selected user counts, row counts, error counts, schemas and output hashes.

- [ ] **Step 4: Add `data prepare` CLI and config**

Command:

```powershell
python -m recsysedu.cli data prepare --config configs/prepare.yaml
```

CLI exits 1 without traceback on invalid config/time basis and prints dataset version/output path on success.

- [ ] **Step 5: Run focused tests and Parquet schema check**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_prepare.py tests/test_cli.py -q`

Expected: PASS; fixture output has unique `(user_id, course_id)` and no orphan course ID.

- [ ] **Step 6: Commit**

```powershell
git add pyproject.toml configs/prepare.yaml src/recsysedu/data/prepare.py src/recsysedu/cli.py tests/test_prepare.py tests/test_cli.py docs/04_data_contract.md
git commit -m "feat: prepare versioned parquet dataset"
```

## Task 3: Build the temporal split and cohorts

**Files:**
- Create: `src/recsysedu/data/split.py`
- Create: `tests/test_split.py`
- Create: `configs/split.yaml`
- Modify: `src/recsysedu/cli.py`

**Interfaces:**
- Consumes: Task 2 Parquet; `build_temporal_split(interactions_path, courses_path, output_dir, *, split_version, seed) -> dict`
- Produces: `train.parquet`, `valid.parquet`, `test.parquet`, `valid_cohort.parquet`, `test_cohort.parquet`, `candidate_universe.parquet`, `split_manifest.json`

- [ ] **Step 1: Write failing split tests**

```python
def test_split_uses_last_two_strict_times_and_never_overlaps(): ...
def test_split_quarantines_boundary_ties_without_course_id_ordering(): ...
def test_split_marks_cold_targets_and_builds_warm_cohorts_from_train_universe(): ...
def test_split_repeats_byte_identical_outputs_for_same_input_and_seed(): ...
```

- [ ] **Step 2: Verify the tests fail**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_split.py -q`

Expected: FAIL because the split module does not exist.

- [ ] **Step 3: Implement split and manifest**

Sort within user by `event_time`; require the final three distinct course events to have strictly increasing timestamps. Valid target is penultimate, test target is last, earlier interactions are train. Candidate universe is sorted course IDs with at least one train interaction.

Manifest records dataset hash, output hashes, tie/cold counts, cohort sizes, seed and protocol ID `leave_last_two_out_v1`.

- [ ] **Step 4: Add `data split` CLI**

Run: `python -m recsysedu.cli data split --config configs/split.yaml`

Expected: success message includes split version and warm cohort sizes; malformed manifest exits 1 without traceback.

- [ ] **Step 5: Run focused tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_split.py tests/test_cli.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add configs/split.yaml src/recsysedu/data/split.py src/recsysedu/cli.py tests/test_split.py tests/test_cli.py
git commit -m "feat: create temporal recommendation split"
```

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

## Task 7: Integrate RecBole BPR

**Files:**
- Create: `src/recsysedu/adapters/__init__.py`
- Create: `src/recsysedu/adapters/recbole.py`
- Create: `tests/test_recbole_adapter.py`
- Create: `configs/bpr.yaml`
- Modify: `pyproject.toml`
- Modify: `requirements-win-py310.lock.txt`

**Interfaces:**
- Consumes: the exact Task 3 split; `export_atomic_files(split_dir: Path, output_dir: Path) -> dict`; `train_bpr(config_path: Path, output_dir: Path) -> dict`; `load_bpr_scorer(manifest_path: Path) -> BPRScorer`
- Produces: RecBole train/valid/test TSV, export manifest, checkpoint, source/internal ID maps and `BPRScorer.score(...) -> ScoreResult`

- [ ] **Step 1: Write failing exporter and mapping tests**

```python
def test_atomic_export_uses_tabs_source_ids_and_exact_split_counts(): ...
def test_atomic_export_declares_benchmark_files_and_never_resplits(): ...
def test_bpr_scorer_maps_source_ids_and_rejects_padding_or_unknown_ids(): ...
```

- [ ] **Step 2: Verify failure**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_recbole_adapter.py -q`

Expected: FAIL because the adapter does not exist.

- [ ] **Step 3: Run the dependency/runtime spike before changing the lock**

In the project Python 3.10 environment, install compatible `torch<3` and `recbole<2`, then run import and one tiny CPU BPR training job. Record Python, Torch, RecBole, NumPy, device, elapsed time and peak working-set estimate in `results/bpr/runtime_spike.md`.

If the tiny job fails, fix the environment in this task before proceeding; do not substitute another model and call BPR complete.

- [ ] **Step 4: Implement export, train/load and ID restoration**

RecBole config must use `benchmark_filename: [train, valid, test]`, `USER_ID_FIELD: user_id`, `ITEM_ID_FIELD: item_id`, `TIME_FIELD: timestamp`, fixed seed and CPU-compatible defaults. The adapter, not UI/evaluator, owns internal-token conversion.

Register the pytest marker `integration` in `pyproject.toml`; ordinary unit runs exclude it explicitly.

- [ ] **Step 5: Add a tiny marked integration test**

`test_tiny_bpr_checkpoint_reloads_and_scores_known_user_items` trains the fixture for a bounded epoch count, reloads it, returns finite scores and restores source IDs. Mark it `integration` so unit runs can remain fast; CI/release command includes it.

- [ ] **Step 6: Run unit and integration checks**

Run: `.\.venv\Scripts\python.exe -m pytest -m "not integration" tests/test_recbole_adapter.py -q`

Expected: unit tests PASS.

Run: `.\.venv\Scripts\python.exe -m pytest -m integration tests/test_recbole_adapter.py -q`

Expected: tiny CPU checkpoint test PASS.

- [ ] **Step 7: Freeze the versions that actually passed and commit**

```powershell
git add pyproject.toml requirements-win-py310.lock.txt configs/bpr.yaml src/recsysedu/adapters tests/test_recbole_adapter.py results/bpr/runtime_spike.md
git commit -m "feat: integrate recbole bpr"
```

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

## Task 9: Add reproducible experiment commands and manifests

**Files:**
- Create: `src/recsysedu/experiments/__init__.py`
- Create: `src/recsysedu/experiments/runner.py`
- Create: `tests/test_experiment_runner.py`
- Create: `configs/final_experiments.yaml`
- Modify: `src/recsysedu/cli.py`

**Interfaces:**
- Consumes: dataset/split manifests and model configs from Tasks 2–8
- Produces: `run_experiment(config: dict, *, split: Literal["valid", "test"], output_root: Path) -> list[dict]` and CLI artifacts per model/run

- [ ] **Step 1: Write failing runner tests**

```python
def test_runner_refuses_test_before_config_is_marked_frozen(): ...
def test_runner_rejects_cross_dataset_or_cross_protocol_model_artifacts(): ...
def test_runner_creates_distinct_run_ids_and_never_overwrites(): ...
def test_runner_runs_four_models_on_one_shared_valid_protocol(): ...
```

- [ ] **Step 2: Verify failure**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_experiment_runner.py -q`

Expected: FAIL because the runner does not exist.

- [ ] **Step 3: Implement runner and CLI**

Commands:

```powershell
python -m recsysedu.cli train --model bpr --config configs/bpr.yaml
python -m recsysedu.cli evaluate --model popularity --split valid --config configs/final_experiments.yaml --output results/popularity/valid
python -m recsysedu.cli experiments --split valid --config configs/final_experiments.yaml
```

`split=test` requires `frozen: true`, exact dataset/split/config hashes and a distinct output root. Run manifest records Git revision, or fails release mode when no revision exists.

- [ ] **Step 4: Run focused tests and CLI help**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_experiment_runner.py tests/test_cli.py -q`

Run: `.\.venv\Scripts\python.exe -m recsysedu.cli --help`

Expected: PASS; help lists train/evaluate/experiments.

- [ ] **Step 5: Commit**

```powershell
git add configs/final_experiments.yaml src/recsysedu/experiments src/recsysedu/cli.py tests/test_experiment_runner.py tests/test_cli.py
git commit -m "feat: orchestrate reproducible experiments"
```

## Task 10: Export and display a real demo snapshot

**Files:**
- Create: `src/recsysedu/demo/export.py`
- Create: `tests/test_demo_export.py`
- Modify: `src/recsysedu/demo/artifacts.py`
- Modify: `app/streamlit_app.py`
- Modify: `tests/test_app.py`

**Interfaces:**
- Consumes: compatible run manifests/recommendations and selected demo user IDs
- Produces: `export_demo_bundle(run_dirs: Sequence[Path], user_ids: Sequence[str], output_path: Path) -> dict` compatible with `load_bundle`

- [ ] **Step 1: Write failing exporter tests**

```python
def test_exporter_builds_real_bundle_from_compatible_runs(): ...
def test_exporter_rejects_mixed_dataset_split_protocol_or_history_mode(): ...
def test_exporter_keeps_seen_items_out_and_limits_each_list_to_ten(): ...
def test_exporter_marks_missing_metrics_not_available_instead_of_zero(): ...
```

- [ ] **Step 2: Add failing Streamlit test for real mode**

Run AppTest with `RECSYSEDU_BUNDLE` pointing at a generated fixture. Assert no synthetic warning, run metadata is visible, changing user/model changes ranking, and a broken real bundle produces an error rather than fixture fallback.

- [ ] **Step 3: Verify failure**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_demo_export.py tests/test_app.py -q`

Expected: FAIL because exporter/real integration is absent.

- [ ] **Step 4: Implement exporter and minimal UI integration**

Keep schema version 1 and `paths=[]` for P0. Evidence may state content similarity/fallback/mechanism; it must not invent BPR neighbors, causal reasons or success probabilities.

- [ ] **Step 5: Run snapshot and app tests**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_demo_export.py tests/test_demo_artifacts.py tests/test_app.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add src/recsysedu/demo app/streamlit_app.py tests/test_demo_export.py tests/test_demo_artifacts.py tests/test_app.py
git commit -m "feat: export real recommendation snapshots"
```

## Task 11: Run the real pilot and freeze P0

**Files:**
- Create: `results/pilot/dataset_report.md`
- Create: `results/pilot/validation_report.md`
- Create: `artifacts/core_manifest.json` locally; commit a redacted/small copy only if it contains no local paths or learner IDs
- Modify: `configs/final_experiments.yaml`
- Modify: `tasks/todo.md`

**Interfaces:**
- Consumes: raw files already downloaded and all P0 commands
- Produces: measured dataset/runtime numbers, four compatible validation runs, chosen BPR/alpha config and a P0 freeze manifest

- [ ] **Step 1: Prepare and split the 10.000-user pilot**

Run the Task 2 and 3 CLI commands. Record elapsed time, peak memory estimate, Parquet sizes, selected user count, train/valid/test counts, cold/tie/reject counts and hashes.

Expected: manifests validate and all split invariants pass; if not, fix the owning task before continuing.

- [ ] **Step 2: Run MostPopular and Content validation**

Expected: both runs share dataset/split/protocol/cohort/universe/seen policy; metrics may be zero but must be measured.

- [ ] **Step 3: Run the bounded BPR search**

Run at most six configurations with one seed and early stopping on validation. Record all attempted configs, failures and runtime; choose by validation NDCG@10.

- [ ] **Step 4: Tune Hybrid alpha on validation**

Evaluate `[0, 0.25, 0.5, 0.75, 1]` on the same validation cohort. Assert alpha 0/1 reproduce component rankings under the documented normalization.

- [ ] **Step 5: Run the compatibility audit and freeze P0**

Run: `.\.venv\Scripts\python.exe -m recsysedu.cli experiments --split valid --config configs/final_experiments.yaml`

Expected: four model runs pass hash/protocol checks; selected config is updated to `frozen: true`. Do not run test yet.

- [ ] **Step 6: Commit only small, reviewed evidence**

```powershell
git add configs/final_experiments.yaml results/pilot/dataset_report.md results/pilot/validation_report.md tasks/todo.md
git commit -m "docs: record and freeze p0 validation"
```

## Task 12: Audit the optional P1 graph gate

**Files:**
- Create: `src/recsysedu/knowledge/__init__.py`
- Create: `src/recsysedu/knowledge/audit.py`
- Create: `tests/test_knowledge_audit.py`
- Create: `results/graph_audit.md`

**Interfaces:**
- Consumes: concept, concept–course and prerequisite source files
- Produces: `audit_knowledge_sources(concepts_path, mapping_path, prerequisites_path) -> dict` with mapping coverage, positive/zero/unknown labels, self-loops, cycles and unmapped IDs

- [ ] **Step 1: Write failing graph audit tests**

Fixtures cover `A -> B -> C`, label 0, label -1, self-loop, cycle and unmapped concept/course. Assert only label 1 is a usable edge; no cycle is silently deleted.

- [ ] **Step 2: Verify failure**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_knowledge_audit.py -q`

Expected: FAIL because the audit module does not exist.

- [ ] **Step 3: Implement audit and report generation**

The report ends with one explicit decision: `P1_READY_FOR_SEPARATE_PLAN` or `P1_STOP_INSUFFICIENT_EVIDENCE`, plus measured reasons. It does not implement reranking or paths.

- [ ] **Step 4: Run tests and the real audit if source files are available**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_knowledge_audit.py -q`

Expected: PASS. Real audit status must remain “not run” if files were not obtained; fixture success is not real-data readiness.

- [ ] **Step 5: Commit**

```powershell
git add src/recsysedu/knowledge tests/test_knowledge_audit.py results/graph_audit.md
git commit -m "feat: audit prerequisite graph readiness"
```

If and only if the report says `P1_READY_FOR_SEPARATE_PLAN`, create and approve a new design/plan for prerequisite reranking and paths. P0 execution continues independently.

## Task 13: Run final test evaluation, reproduction and handoff

**Files:**
- Create: `results/final/report.md`
- Create: `results/reproduction.md`
- Create: `reports/acceptance.md`
- Modify: `docs/09_runbook.md`
- Modify: `README.md`
- Modify: `tasks/todo.md`

**Interfaces:**
- Consumes: frozen P0 config, clean environment and selected snapshot users
- Produces: final test metrics, real snapshot, reproduction evidence and handoff checklist

- [ ] **Step 1: Run test once from the frozen config**

Run: `.\.venv\Scripts\python.exe -m recsysedu.cli experiments --split test --config configs/final_experiments.yaml`

Expected: four model runs use the frozen hashes/config; no parameter is changed from test results.

- [ ] **Step 2: Produce final analysis and real demo bundle**

Report NDCG@10, HitRate/Recall@10, Precision@10, Coverage@10, cohort size, seeds and runtime. Include low-history/high-history results and failure cases. Export at least three demo profiles and validate the bundle.

- [ ] **Step 3: Run the full automated gate**

Run: `.\.venv\Scripts\python.exe -m pytest -q`

Run: `.\.venv\Scripts\python.exe -m ruff check src app tests`

Run: `.\.venv\Scripts\python.exe -m pip check`

Expected: all pass; failures are fixed in the owning task and affected real artifacts are regenerated.

- [ ] **Step 4: Reproduce from a clean environment**

Create a clean Python 3.10 environment from the committed lock. Run fixture pipeline, load the selected BPR checkpoint, evaluate the frozen small case and validate the real snapshot. Record commands, hashes, runtime and any tolerance in `results/reproduction.md`.

- [ ] **Step 5: Browser-check the final Streamlit demo**

Run: `python -m streamlit run app/streamlit_app.py`

Check three profiles, four models, empty/short ranking, fallback, Model Lab metadata, CSV download and invalid bundle behavior. Record observations; do not treat visual inspection as model validation.

- [ ] **Step 6: Complete handoff docs and acceptance**

`reports/acceptance.md` must list P0 achieved/not achieved, P1 status, artifact locations, commands, hashes, known limits and a clean-machine reproduction result. README/runbook must distinguish commands already run from planned examples.

- [ ] **Step 7: Commit**

```powershell
git add README.md docs/09_runbook.md tasks/todo.md results/final/report.md results/reproduction.md reports/acceptance.md
git commit -m "docs: finalize recsysedu handoff evidence"
```

## Plan completion criteria

The plan is complete only when Tasks 0–11 and 13 pass. Task 12 must produce an evidence-based P1 decision; P1 implementation is not required for P0. The final report must retain failures and limitations instead of replacing them with synthetic metrics or claims based only on UI behavior.
