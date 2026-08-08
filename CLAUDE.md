# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

---

## Environment Setup

```bash
ollama pull qwen2.5-coder:14b-instruct-q4_K_M
cp .env.example .env
# fill in DATABRICKS_HOST / DATABRICKS_TOKEN
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.lock          # use the lock file for reproducible installs
pip install -e ".[dev]"                   # adds pytest
cd web && npm install && cd ..
```

> `databricks-connect` and plain `pyspark` cannot coexist in the same environment — this project depends on `databricks-connect` only, which bundles its own `pyspark`-compatible client. It also pins `numpy<2` with no prebuilt wheel past cp313, so `.venv` must be built from Python 3.11–3.13, not 3.14+.

Seed sample data before first run (one time, requires live Databricks credentials):

```bash
python scripts/seed_databricks.py --rows 5000   # uploads sample_sales to Unity Catalog
cp .env.test .env                                 # pre-filled config template
```

Ollama must be running on `http://localhost:11434` before starting the stack.

Required `.env` variables:
- `DATABRICKS_HOST` — workspace URL
- `DATABRICKS_TOKEN` — personal access token

Key optional variables:
- `CODER_MODEL` — default `ollama_chat/qwen2.5-coder:14b-instruct-q4_K_M`; LiteLLM model id for the coding agent
- `OLLAMA_BASE_URL` — default `http://localhost:11434`
- `MAX_STEPS` — default `6`; bounds the write→run→fix self-repair loop (Databricks Free Edition has a per-account fair-use quota)
- `AGENT_STEP_TIMEOUT_S` — default `180`; max wait per streamed step before erroring out
- `DATABRICKS_CATALOG` / `DATABRICKS_SCHEMA` — default _(workspace default)_ / `default`; Unity Catalog catalog/schema the agent introspects and queries against
- `SEED_TABLE` — default `sample_sales`; table name used by `scripts/seed_databricks.py`
- `MAX_MESSAGE_LEN` — default `2000`; maximum characters in a single task description
- `MAX_PROMPT_TOKENS` — default `2048`; maximum estimated tokens before rejection

## Running the Stack

```bash
bash start.sh          # FastAPI :8000 + React :5173
```

Or individually:
```bash
source .venv/bin/activate
uvicorn api.main:app --reload          # backend only
cd web && npm run dev                  # frontend only
```

Interactive API docs: `http://localhost:8000/docs`

## Tests

```bash
pytest tests/ -v
```

- `TestSelfRepair` (`tests/test_qa.py`) — proves a failed attempt's error and a subsequent successful attempt both surface correctly, using a stubbed `CodeAgent` (no live Ollama needed)
- `TestAuthorizedImports` — asserts the import allowlist stays minimal and that `LocalPythonExecutor` actually blocks an unauthorized import (e.g. `os`) at runtime
- `TestPromptValidation` — length/empty/injection/token-budget checks on `src/prompt_guard.py`
- `TestSelectOnlyGuard` (`tests/test_security.py`) — the sqlglot SELECT-only guard against INSERT/UPDATE/DELETE/DDL and stacked statements
- `TestDatabricksConnectSmoke` — a real session-creation + catalog-listing check, skipped unless `DATABRICKS_HOST`/`DATABRICKS_TOKEN` are set

---

## Architecture

### Request flow

Browser → React (`web/`) → FastAPI (`api/routers/task.py`) → `validate_message` (`src/prompt_guard.py`) → `PySparkCodeAgent` (`src/agent.py`) → smolagents `CodeAgent` write→execute→self-repair loop, executing against `DatabricksDataStore.spark` (`src/databricks_store.py`)

This is not a fixed-tool agent — there's no RAG layer and no tool registry. The LLM's action *is* generated PySpark/Python source, run by smolagents' `LocalPythonExecutor` against the live Spark session, with the traceback (if any) fed back into the next step.

The `POST /task` endpoint uses SSE (`StreamingResponse`); the frontend (`web/src/api/client.ts`) consumes `code_attempt`, `execution_result`, `final_result`, `error`, and `done` events streamed from `PySparkCodeAgent.astream_events` (`src/agent.py`).

### Prompt validation (`src/prompt_guard.py`)

Two functions gate every task before it reaches the agent:
- `validate_message(message)` — strips whitespace, rejects empty strings, enforces `MAX_MESSAGE_LEN` (default 2000 chars), and scans for injection patterns (e.g. "ignore previous instructions", "jailbreak", "DAN"). Returns the stripped message or raises `ValueError`.
- `check_token_budget(message, history_chars)` — estimates token count as `(len(message) + history_chars) // 4` and raises `ValueError` if it exceeds `MAX_PROMPT_TOKENS` (default 2048).

`validate_message` is called in `api/routers/task.py` before the SSE stream starts; there is no conversation history, so `check_token_budget` runs against the task text alone.

### Agent wiring (`src/executor.py`)

`build_agent()` constructs a fresh smolagents `CodeAgent` per task — no cross-request conversation state, since each call's job is "write, run, and self-repair code for this one task." `AUTHORIZED_IMPORTS` is a tight allowlist (`pyspark`, `pyspark.sql`, `pandas`, `numpy`) enforced by `LocalPythonExecutor`; `MAX_STEPS` (default `6`) bounds the loop to respect Databricks Free Edition's fair-use quota. `build_task_prompt()` grounds the task in live catalog context from `DatabricksDataStore.get_catalog_context()`.

### Agent wrapper (`src/agent.py`)

`PySparkCodeAgent.run()` / `.astream_events()` build a fresh `CodeAgent`, run it against `store.spark`, and translate smolagents' `ActionStep` memory objects into SSE-shaped dicts (`_step_events`). Each step with a `code_action` emits a `code_attempt` event followed by an `execution_result` event (`output` on success, `error` on failure); the final `FinalAnswerStep` becomes the `final_result` event.

### Data backend (`src/databricks_store.py`)

`DatabricksDataStore` wraps a Databricks Connect session (`DatabricksSession.builder...serverless(True).getOrCreate()`), configured via `DATABRICKS_HOST`, `DATABRICKS_TOKEN`, `DATABRICKS_CATALOG`, `DATABRICKS_SCHEMA`. It holds no fixed analytics methods — the CodeAgent writes its own PySpark/SQL per task. It provides live catalog introspection (`get_catalog_context()`, backed by `spark.catalog.listTables()` / `listColumns()`) to ground the agent in real table/column names, plus a guarded `query()` escape hatch. Any `spark.sql(...)` text is parsed with `sqlglot` (`_assert_select_only`) and rejected unless it's a single `SELECT` statement — defense-in-depth alongside the import allowlist, since the primary sandbox boundary is `AUTHORIZED_IMPORTS`. `store.close()` stops the Spark session and is called automatically on FastAPI lifespan shutdown.

### MCP server (`src/mcp_server.py`)

FastMCP stdio server exposing one tool: `run_pyspark_task(task: str) -> {"code": "...", "result": "..."}`. On startup it builds its own `DatabricksDataStore` and `PySparkCodeAgent` (independent of the FastAPI process). Config for Claude Code: `python -m src.mcp_server`.
