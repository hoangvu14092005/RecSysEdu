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

