# Task 0 — Repository baseline report

## Status

Completed on `main`. The repository baseline is committed and the tracked working tree is clean.

## Commit

- `8670d1802a940d167e7ae7fe7430907b684c7287` — `chore: establish RecSysEdu base`
- Parent: `db215ef2b6f460e41f7155e4a09a522c47fc9af5` — `docs: add pipeline-first implementation plan`

The commit adds 46 files (3,769 insertions): source, app, configuration, docs, task files, tests and small fixtures, plus existing non-sensitive reports and the small UI screenshot. It does not change product behavior.

## Ignore and staging audit

- Added `.archify/`, `.mypy_cache/`, `.hypothesis/`, `.tox/` and `.nox/` to `.gitignore`; existing ignore rules for `.venv/`, Python caches, `/data/`, `/artifacts/`, model checkpoint extensions and `/results/local/` remain.
- Confirmed `data/raw/course.json`, `data/raw/user.json`, `results/local/data_audit.json`, `.venv/pyvenv.cfg` and the generated `.archify/` HTML are ignored.
- Kept `.streamlit/config.toml`, tests and Markdown reports as directed. The explicit staged list contained 46 files and no raw/processed data, local result, generated `.archify/` content or checkpoint path.
- `git diff --cached --check` completed without whitespace errors after removing extra blank lines at EOF in `.streamlit/config.toml` and `configs/data.yaml`.
- Self-review after commit: `git show --stat` confirmed the expected 46 paths; `git status --short --branch` showed `## main` with no pending changes.

## Verification

- `\.venv\Scripts\python.exe -m pytest -q` — **28 passed**.
- `\.venv\Scripts\python.exe -m ruff check src app tests` — **All checks passed**.

## Concerns and limits

Git emitted Windows line-ending conversion notices while staging text files (LF will be converted to CRLF in the working copy on a later Git write). The staged diff check was clean, tests and Ruff passed, and the commit completed. No other baseline issue was found. This records the existing base only; it does not claim that recommendation training/evaluation or the planned pipeline is complete.

## Fix round 1

Addressed review findings:

- Added `*.ckpt` to `.gitignore` for planned RecBole/PyTorch checkpoint files; existing `.pth` and `.pt` rules remain.
- Updated the README and runbook to say the local baseline commit exists and no GitHub remote is configured.

Changed files: `.gitignore`, `README.md`, `docs/09_runbook.md`.

Focused checks and exact outputs:

```text
git check-ignore -v results/bpr/model.ckpt
.gitignore:21:*.ckpt    results/bpr/model.ckpt

rg -n -i "chưa có commit|chưa có commit/remote|chưa có commit hoặc remote|no commit" README.md docs/09_runbook.md
No stale commit wording found.

git diff --check
(no output; exit code 0)
```

`git diff` confirmed only the three changed files listed above. Commit: `0a36d4332bbea09463391b8d518e7bd4e24d8b0a` — `chore: update baseline ignore and status`.
