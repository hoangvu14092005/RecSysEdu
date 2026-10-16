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

