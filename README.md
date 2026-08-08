# PySpark AI Agent

**A coding agent that writes, runs, and self-repairs PySpark code against a real Databricks workspace.**

Give it a task in plain English — the agent writes PySpark, executes it against a live Databricks Connect session, reads the traceback if it fails, fixes the code, and tries again. Every attempt streams to the UI as it happens: the code, the execution result or error, and finally the answer.

This is not a fixed-tool Q&A agent. There is no menu of pre-built analytics functions to call — the agent's entire job is producing and running its own code, grounded in the real Unity Catalog schema, with a tight sandbox around what that code is allowed to import.

---

## Features

- **Code-writing agent, not tool-calling** — [smolagents](https://github.com/huggingface/smolagents) `CodeAgent`: the LLM's action *is* Python/PySpark source code, executed and observed each step
- **Self-repair loop** — a failed attempt's traceback feeds straight back into the next step; no custom retry logic needed
- **Real compute** — [Databricks Connect](https://docs.databricks.com/en/dev-tools/databricks-connect/index.html) against free-tier serverless compute, not a local Spark process
- **Live schema grounding** — table/column context comes from `spark.catalog.listTables()` / `listColumns()` on every run, not a stale vector index
- **Tight sandbox** — `additional_authorized_imports` limited to `pyspark`, `pandas`, `numpy`; bounded `max_steps` to respect Databricks Free Edition's fair-use quota
- **Read-only defense-in-depth** — any `spark.sql(...)` the generated code issues is still parsed with `sqlglot`; non-SELECT statements are blocked
- **Minimal trace-viewer UI** — task input, streamed attempt-by-attempt code/result cards, final result panel
- **MCP server** — exposes a single `run_pyspark_task` tool to Claude Code

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | `qwen2.5-coder:14b-instruct-q4_K_M` via Ollama (LiteLLM) |
| Agent | smolagents `CodeAgent` (write → execute → self-repair) |
| Sandbox | smolagents `LocalPythonExecutor`, restricted import allowlist |
| Compute | Databricks Connect (serverless, free-tier compatible) |
| Backend | FastAPI + Uvicorn, single SSE endpoint |
| Frontend | React 18 + Vite + Tailwind CSS |
| SQL safety | sqlglot (parse-time DML/DDL blocking) |

---

## Project Structure

```
├── api/                       # FastAPI backend
│   ├── main.py                # App startup, CORS, lifespan
│   ├── deps.py                # FastAPI dependencies (store, agent)
│   ├── models.py               # Pydantic request model
│   └── routers/
│       └── task.py            # POST /task — SSE streaming trace
│
├── src/                        # Shared Python backend
│   ├── databricks_store.py    # Databricks Connect session + catalog introspection
│   ├── executor.py             # smolagents CodeAgent wiring (model, sandbox, prompt)
│   ├── agent.py                 # Thin wrapper: run task, stream step events
│   ├── prompt_guard.py         # Input validation (length, token budget, injection)
│   └── mcp_server.py           # FastMCP stdio server — one tool: run_pyspark_task
│
├── web/                        # React frontend (minimal trace viewer)
│   └── src/
│       ├── App.tsx              # Task input + streamed attempts + final result
│       ├── components/AttemptCard.tsx
│       ├── lib/useTaskRun.ts
│       └── api/client.ts        # SSE streaming helper
│
├── scripts/
│   └── seed_databricks.py      # One-time: uploads sample data to a Unity Catalog table
├── start.sh                    # Start both servers (backend :8000, frontend :5173)
├── requirements.lock           # Pinned Python dependencies
├── .env.example                # Environment variable template
└── .env.test                   # Pre-filled config template for local testing
```

---

## Quick Start

### 1. Install and start Ollama

```bash
ollama pull qwen2.5-coder:14b-instruct-q4_K_M
```

Ollama must be running on `http://localhost:11434` before starting the app.

### 2. Set up a Databricks workspace

Any Databricks workspace with serverless compute works, including the free tier. You'll need:

- The workspace URL (`DATABRICKS_HOST`)
- A personal access token (`DATABRICKS_TOKEN`)
- A catalog/schema to work in (`DATABRICKS_CATALOG` / `DATABRICKS_SCHEMA`) — Free Edition ships a default Unity Catalog catalog you can use as-is

### 3. Configure

```bash
cp .env.example .env
# fill in DATABRICKS_HOST / DATABRICKS_TOKEN
```

### 4. Install Python dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock
pip install -e ".[dev]"     # adds pytest
```

> `databricks-connect` and plain `pyspark` cannot coexist in the same environment — this project depends on `databricks-connect` only, which bundles its own `pyspark`-compatible client.

### 5. Seed sample data (one time)

```bash
python scripts/seed_databricks.py --rows 5000
```

Uploads a synthetic `sample_sales` table (order_id, order_date, region, product, quantity, unit_price) to your configured catalog/schema so there's something to query immediately.

### 6. Install frontend dependencies and start both servers

```bash
cd web && npm install && cd ..
bash start.sh
```

- **FastAPI** → `http://localhost:8000`
- **React** → `http://localhost:5173`

Open **http://localhost:5173**, describe a task (e.g. *"What is the average order value by region?"*), and watch the agent write, run, and — if needed — fix its own PySpark code.

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `CODER_MODEL` | No | `ollama_chat/qwen2.5-coder:14b-instruct-q4_K_M` | LiteLLM model id for the coding agent |
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` | Ollama server URL |
| `MAX_STEPS` | No | `6` | Bound on the write→run→fix self-repair loop |
| `AGENT_STEP_TIMEOUT_S` | No | `180` | Max wait per streamed step before erroring out |
| `DATABRICKS_HOST` | Yes | — | Workspace URL |
| `DATABRICKS_TOKEN` | Yes | — | Personal access token |
| `DATABRICKS_CATALOG` | No | _(workspace default)_ | Unity Catalog catalog name |
| `DATABRICKS_SCHEMA` | No | `default` | Schema within the catalog |
| `SEED_TABLE` | No | `sample_sales` | Table name used by `scripts/seed_databricks.py` |
| `MAX_MESSAGE_LEN` | No | `2000` | Maximum characters in a single task description |
| `MAX_PROMPT_TOKENS` | No | `2048` | Maximum estimated tokens before rejection |

---

## REST API

Interactive docs at `http://localhost:8000/docs`.

| Method | Endpoint | Description |
|---|---|---|
| POST | `/task` | SSE stream of the agent's step-by-step trace (`code_attempt`, `execution_result`, `final_result`, `error`, `done`) |
| GET | `/health` | Liveness check |

There is no auth layer or rate limiting — this is a personal, single-user tool, not a multi-tenant service.

---

## MCP Server

The FastMCP stdio server exposes one tool to Claude Code:

```json
{
  "mcpServers": {
    "pyspark-agent": {
      "command": "python",
      "args": ["-m", "src.mcp_server"],
      "cwd": "/path/to/PySpark-AI-Agent"
    }
  }
}
```

`run_pyspark_task(task: str) -> {"code": "...", "result": "..."}` — writes and executes PySpark code to accomplish the task, self-repairing on errors, and returns the final code plus a preview of the result.

---

## Security

- **Import allowlist**: the CodeAgent's sandbox (`smolagents.LocalPythonExecutor`) only authorizes `pyspark`, `pyspark.sql`, `pandas`, `numpy` — no `os`, `subprocess`, `socket`, or filesystem/network access from generated code.
- **Bounded steps**: `max_steps` caps the self-repair loop, both to respect Databricks Free Edition's fair-use quota and to avoid runaway loops.
- **SELECT-only guard**: `sqlglot` parses any `spark.sql(...)` text the generated code constructs and rejects anything that isn't a single `SELECT` statement — defense-in-depth alongside the import allowlist.

---

## Tests

```bash
pytest tests/ -v
```

- `TestSelfRepair` — proves a failed attempt's error and a subsequent successful attempt both surface correctly, using a stubbed CodeAgent (no live Ollama needed)
- `TestAuthorizedImports` — asserts the import allowlist stays minimal and that `LocalPythonExecutor` actually blocks an unauthorized import (e.g. `os`) at runtime
- `TestSelectOnlyGuard` (`tests/test_security.py`) — the sqlglot SELECT-only guard against INSERT/UPDATE/DELETE/DDL and stacked statements
- `TestDatabricksConnectSmoke` — a real session-creation + catalog-listing check, skipped unless `DATABRICKS_HOST`/`DATABRICKS_TOKEN` are set
