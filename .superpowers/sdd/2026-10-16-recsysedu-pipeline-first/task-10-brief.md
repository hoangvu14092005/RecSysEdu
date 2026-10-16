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

