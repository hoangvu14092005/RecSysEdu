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

