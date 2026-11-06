---
default_routing:
  subagents: "local-litert-gemma"
  tools: 
    - "bash"
    - "read"
    - "ripgrep"
endpoints:
  local-litert-gemma:
    type: "litert"
    path: "~/.litert-lm/models/gemma4-26b/model.litertlm"
---
# AGENTS.md — SpO2 Skin Tone Execution Rules

## 1. Ground Rules & Context Conservation
- **Fail Fast:** Never assume APIs exist, tests pass, or environments build cleanly. If dependency resolution fails after 2 attempts, mark `BLOCKED` and pivot.
- **Pre-Flight `.agignore`:** Before ANY file search, verify `.agignore` blocks binaries, compiled assets, virtual environments (`.venv`), large datasets (`*.csv`, `*.parquet`, `*.h5`), and `.ipynb_checkpoints`.
- **Targeted Reads:** Inspect source files using strict line ranges (e.g., `sed -n '40,120p'`). Do not dump multi-file reads into the main thread.

## 2. Hybrid Gauntlet Routing
Route tasks strictly by cognitive load to conserve cloud quota:
- **Local Engine (Gemma):** Use for repository cloning, `.agignore` setup, `ripgrep`/indexing, `pytest` execution, linting, and targeted line extraction.
- **Cloud Engine (Gemini Argon / Claude):** Use strictly for reviewing architectural summaries, designing system blueprints, and writing multi-file PR diffs.

## 3. Subagent Protocols
Use built-in `@research` or invoke these scoped subagents. Do not dump raw multi-file reads into the parent thread.

### A. `recon-scout` (Local Engine)
- **Role:** Codebase & Issue reconnaissance.
- **Action:** Run localized `ripgrep` searches to map file dependencies or query `gh issue list`. 
- **Output:** Markdown table with exact file paths, line numbers, and required changes.

### B. `env-verifier` (Local Engine)
- **Role:** Clean sandbox validator.
- **Action:** Check for existing `.venv`. If none, create it, execute `pip install -e ".[dev]"`, and run the primary test suite.
- **Kill Criterion:** If native dependencies fail compiling within 2 tries, halt and log stderr.

### C. `system-architect` (Cloud Engine)
- **Role:** Software Blueprint Designer.
- **Action:** Design the structural architecture for new modules or refactors based on scouted context.
- **Output Contract:** Generate a strict, testable Python Class/Method blueprint (empty methods with type hints and docstrings). NO implementation logic.

### D. `test-runner` (Local Engine)
- **Role:** Verification & Linting.
- **Action:** Run `pytest` and `ruff`/`black` on modified files.
- **Output:** Pass confirmation OR max 40 lines of failing traceback.