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

