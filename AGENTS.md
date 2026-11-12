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
    model: "gemini-4-hydrogen-low"
  cloud-hydrogen-workhorse:
    type: "cloud"
    subagent_model: "flash"
    model: "gemini-4-hydrogen-high"
  cloud-hydrogen-deep-reasoning:
    type: "cloud"
    subagent_model: "pro"
    model: "gemini-4-hydrogen-xhigh"
---
# AGENTS.md — SpO2 Skin Tone Execution Rules

## 1. Ground Rules & Context Conservation
- **Fail Fast:** Never assume APIs exist, tests pass, or environments build cleanly. If dependency resolution fails after 2 attempts, mark `BLOCKED` and pivot.
- **Pre-Flight `.agignore`:** Before ANY file search, verify `.agignore` blocks binaries, compiled assets, virtual environments (`.venv`), large datasets (`*.csv`, `*.parquet`, `*.h5`), and `.ipynb_checkpoints`.
- **Targeted Reads:** Inspect source files using strict line ranges (e.g., `sed -n '40,120p'`). Do not dump multi-file reads into the main thread.

## 2. Hybrid Gauntlet Routing (5-Hour & Weekly Quota Conservation)
Route tasks strictly by cognitive load and thinking level to conserve both 5-hour rolling quotas and the binding **weekly quota ceiling** across >5 hrs/day, >5 days/week schedules:
- **Local Engine (Gemma) [Primary — 0 Cloud Quota]:** Use for repository cloning, `.agignore` setup, `ripgrep`/indexing, `pytest` execution, linting, and targeted line extraction when the Legion T5 (`10.0.0.63:11434` / local LiteRT) is reachable.
- **Travel / Offline Exception (Lowest-Tier Cloud Fallback — `flash_lite` / `gemini-4-hydrogen-low`):** When travelling or when the local Gemma endpoint is unreachable, substitute the lowest-tier Cloud model (`invoke_subagent` with `Model="flash_lite"`, or `gemini-4-hydrogen-low`) for all Local Engine tasks (`recon-scout`, `env-verifier`, `test-runner`). Because Hydrogen `low` has a steeper reasoning drop-off than `medium`/`high`, keep `low` prompts strictly mechanical. All bounded-output rules (Markdown tables, targeted line ranges, max 40 lines of failing traceback) remain strictly enforced.
- **Cloud Workhorse Implementation (`gemini-4-hydrogen-medium` / `gemini-4-hydrogen-high`):** Use `medium` for single-file mechanical edits/tests and `high` (default workhorse, 2.5x faster and 12%–23% fewer tokens/task than legacy Flash 3.8) for writing multi-file PR diffs and routine refactors. **Never use `xhigh` in iterative coding/test loops.**
- **Cloud Deep Debugging & Single-Pass Audit (`gemini-4-hydrogen-xhigh`):** Use `xhigh` (~3x thinking tokens, 54 AAII score) in a **single-pass** flow for hard debugging, adversarial diff verification, and architectural triage so weekly Argon quota is spared.
- **Cloud Frontier Architect (`Gemini 4 Argon`):** Reserve strictly for high-level system blueprints (`system-architect`) and cross-module statistical sign-off when weekly Argon quota permits. *(Claude models have minimal emergency-only quota in Antigravity and must not be relied upon.)*

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