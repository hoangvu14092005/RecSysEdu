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

