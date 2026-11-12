---
default_routing:
  subagents: "local-litert-gemma"
  fallback_subagents: "flash_lite"
  tools: 
    - "bash"
    - "read"
    - "ripgrep"
endpoints:
  local-litert-gemma:
    type: "litert"
    path: "~/.litert-lm/models/gemma4-26b/model.litertlm"
    remote_ollama: "http://10.0.0.63:11434/api/generate"
  cloud-flash-lite-fallback:
    type: "cloud"
    subagent_model: "flash_lite"
    model: "gemini-3.8-flash-low"
---
# AGENTS.md — SpO2 Skin Tone Execution Rules

## 1. Ground Rules & Context Conservation
- **Fail Fast:** Never assume APIs exist, tests pass, or environments build cleanly. If dependency resolution fails after 2 attempts, mark `BLOCKED` and pivot.
- **Pre-Flight `.agignore`:** Before ANY file search, verify `.agignore` blocks binaries, compiled assets, virtual environments (`.venv`), large datasets (`*.csv`, `*.parquet`, `*.h5`), and `.ipynb_checkpoints`.
- **Targeted Reads:** Inspect source files using strict line ranges (e.g., `sed -n '40,120p'`). Do not dump multi-file reads into the main thread.

## 2. Hybrid Gauntlet Routing
Route tasks strictly by cognitive load to conserve cloud quota:
- **Local Engine (Gemma) [Primary]:** Use for repository cloning, `.agignore` setup, `ripgrep`/indexing, `pytest` execution, linting, and targeted line extraction when the Legion T5 (`10.0.0.63:11434` / local LiteRT) is reachable.
- **Travel / Offline Exception (Lowest-Tier Cloud Fallback — `flash_lite` / `gemini-3.8-flash-low`):** When travelling or when the local Gemma endpoint is unreachable, substitute the lowest-tier Cloud model (`invoke_subagent` with `Model="flash_lite"`, or `gemini-3.8-flash-low`) for all Local Engine tasks (`recon-scout`, `env-verifier`, `test-runner`). All bounded-output rules (Markdown tables, targeted line ranges, max 40 lines of failing traceback) remain strictly enforced to protect main-thread context.
- **Cloud Engine (Gemini Argon / Claude):** Use strictly for reviewing architectural summaries, designing system blueprints, and writing multi-file PR diffs.

## 3. Subagent Protocols
Use built-in `@research` or invoke these scoped subagents (using `Model="flash_lite"` when the Local Engine is unreachable during travel). Do not dump raw multi-file reads into the parent thread.

### A. `recon-scout` (Local Engine | Travel Fallback: `flash_lite`)
- **Role:** Codebase & Issue reconnaissance.
- **Action:** Run localized `ripgrep` searches to map file dependencies or query `gh issue list`. 
- **Output:** Markdown table with exact file paths, line numbers, and required changes.

### B. `env-verifier` (Local Engine | Travel Fallback: `flash_lite`)
- **Role:** Clean sandbox validator.
- **Action:** Check for existing `.venv`. If none, create it, execute `pip install -e ".[dev]"`, and run the primary test suite.
- **Kill Criterion:** If native dependencies fail compiling within 2 tries, halt and log stderr.

### C. `system-architect` (Cloud Engine)
- **Role:** Software Blueprint Designer.
- **Action:** Design the structural architecture for new modules or refactors based on scouted context.
- **Output Contract:** Generate a strict, testable Python Class/Method blueprint (empty methods with type hints and docstrings). NO implementation logic.

### D. `test-runner` (Local Engine | Travel Fallback: `flash_lite`)
- **Role:** Verification & Linting.
- **Action:** Run `pytest` and `ruff`/`black` on modified files.
- **Output:** Pass confirmation OR max 40 lines of failing traceback.