# Task 1 report — shared scoring and run contracts

**Status:** Complete in the managed worktree `C:\Users\Vu\.codex\worktrees\pipeline-first\RecSysEdu`.

**Commit:** `6f920c9` — `feat: define recommendation contracts` (detached HEAD, as expected for this managed worktree).

## Delivered

- `src/recsysedu/contracts.py` defines frozen `ScoreResult`, `RankedItem`, and `RunIdentity` dataclasses plus the `Recommender.score(user_id, candidate_ids)` protocol.
- `ScoreResult` keeps source course IDs in candidate order, aligns them with a one-dimensional NumPy score array, rejects duplicate or invalid IDs, wrong lengths, non-numeric arrays, NaN, and infinity. It copies valid scores into a read-only array so later edits to the input cannot invalidate the result.
- `RankedItem` requires a source string ID, rank starting at one, and a finite real score. `RunIdentity` requires non-empty run, model, dataset hash, split hash, and protocol fields, with an integer or absent seed.
- `pyproject.toml` now declares `numpy>=1.26,<3` as a direct dependency.
- `tests/test_contracts.py` covers accepted order/defaults, invalid scores/IDs/ranks, identity fields, mutation protection, and structural protocol use.

## TDD and checks

1. **RED:** `python -m pytest tests/test_contracts.py -q` exited 1 during collection with `ModuleNotFoundError: No module named 'recsysedu.contracts'`.
2. **GREEN:** After implementation, focused contract and base demo tests passed: **33 passed** (`tests/test_contracts.py tests/test_demo_artifacts.py -q`).
3. A further RED check exposed that mutating the input NumPy array changed an already validated `ScoreResult`; the focused mutation test failed with a `nan location mismatch`. The implementation now copies scores and marks the copy read-only.
4. **Full suite:** `python -m pytest -q` passed: **46 passed in 5.36s**.
5. `python -m ruff check src/recsysedu/contracts.py tests/test_contracts.py` passed. `git diff --check` and staged diff check passed.

All test commands used `D:\VuLapTrinh2\RecSysEdu\.venv\Scripts\python.exe` from the managed worktree.

## Boundary and concern

`RunIdentity` carries the dataset and split hashes, but cannot compare them with external manifests by itself. The evaluator or artifact loader must verify those cross-file matches when it consumes the identity. No model or evaluator was implemented in this task.

## Review fix 1 — NumPy scalar scores

**Commit:** `d5a677b` — `fix: accept NumPy real scores in ranked items`.

The review found that `ScoreResult` accepted finite NumPy `float32` and `int64` arrays, but `RankedItem` rejected their scalar elements. The regression test now constructs each valid `ScoreResult` and passes `result.scores[0]` directly to `RankedItem`.

- **RED:** `python -m pytest tests/test_contracts.py::test_ranked_item_accepts_score_result_numpy_real_scalar -q` failed both cases (`float32` and `int64`) with `ValueError: score must be a finite real number` at the old `(int, float)` check.
- **Fix:** `RankedItem` accepts `numbers.Real` (including NumPy real scalars), rejects Python/NumPy booleans and non-real values, converts the accepted value to built-in `float`, and rejects NaN/infinity or overflow after conversion.
- **GREEN:** `python -m pytest tests/test_contracts.py -q` passed **25 tests**; `python -m pytest -q` passed **53 tests in 5.40s**. Ruff and `git diff --check` passed. All commands used the project environment interpreter named above.
