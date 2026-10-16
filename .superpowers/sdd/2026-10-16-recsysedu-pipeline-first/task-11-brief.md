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

