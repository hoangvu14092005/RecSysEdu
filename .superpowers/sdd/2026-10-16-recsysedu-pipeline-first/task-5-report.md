# Task 5 report: MostPopular baseline

## Status
Complete. Implemented and committed at `a1d00c37072855d572a33c1b5811470be36c140c` (`feat: add most-popular baseline`).

## Changes
- Added `fit_popularity(train, universe)` and immutable `PopularityModel.score(user_id, candidate_ids)`.
- Popularity scores are float enrollment counts from train rows only. The model validates a unique sorted universe and rejects train or candidate IDs outside it.
- Scores are independent of `user_id`; tie-breaking remains in the shared evaluator ranker. Evidence is empty.
- Added `configs/popularity.yaml` and tests for train-only counts, unseen candidates, shared tie ranking, and no validation/test target access.

## Verification
- TDD RED: `tests/test_popularity.py` initially failed during collection because `recsysedu.models` did not exist.
- Focused GREEN + evaluator regressions: 36 passed.
- Full suite: `<REPO_ROOT>\.venv\Scripts\python.exe -m pytest -q` — 143 passed.
- Ruff: `<REPO_ROOT>\.venv\Scripts\python.exe -m ruff check .` — passed.
- `git diff --check` and staged diff check passed. Working tree clean after commit.

## Concerns
None identified within this baseline scope. No ranking logic or validation/test data access was added to the model.
