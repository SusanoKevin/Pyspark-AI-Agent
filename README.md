# Excelsis 360 — Data Analyst Agent

AI-powered data analyst for the Excelsis360 platform, built on a LangGraph ReAct agent (Ollama local LLMs), SQL Server data backend, and a FastAPI + React full-stack web interface.

---

## Features

- **Natural-language chat** — ask questions about Excelsis360 data in plain English; the analysis model reasons across multiple tools and streams the answer token-by-token
- **ReAct reasoning loop** — the analysis model decides which tools to call (attendance stats, at-risk query, ad-hoc SQL) and in what order
- **RAG knowledge base** — ChromaDB vector store (`nomic-embed-text` embeddings via Ollama) indexes SQL schema metadata and policy documents; the agent uses `retrieve_schema` and `retrieve_policy` for accurate, grounded answers
- **Two-model setup** — `qwen2.5:14b` handles reasoning and tool calling; `nomic-embed-text` handles vector encoding for the RAG layer; both run fully locally via Ollama
- **Prompt guardrails** — every chat message is validated before reaching the agent: length cap (2000 chars), token-budget check, and injection-pattern detection
- **SQL Server backend** — connects to one or more SQL Server databases; the agent can run ad-hoc T-SQL SELECT queries alongside structured tools
- **Interactive dashboards** — Plotly interactive charts and a multi-panel matplotlib/seaborn static dashboard (PNG)
- **Web UI** — React + Tailwind dark-themed interface with live streaming chat, KPI dashboard, at-risk student table, and user management
- **REST API** — FastAPI backend with JWT auth, SSE streaming, file upload, and dashboard generation
- **Rate limiting** — 10 requests/minute per IP on all chat and data endpoints (slowapi)
- **Jupyter notebook** — full interactive analysis environment that shares the same `src/` backend
- **MCP server** — exposes Excelsis360 data tools to Claude Code

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | `qwen2.5:14b` via Ollama (`langchain-ollama`) |
| Agent | LangGraph ReAct (`create_react_agent`) |
| Database | SQL Server via SQLAlchemy + `pyodbc` (ODBC Driver 18, `QueuePool`) |
| Backend | FastAPI + Uvicorn |
| Auth | JWT (python-jose) + bcrypt |
| Frontend | React 18 + Vite + Tailwind CSS |
| Data | pandas, supports CSV / Excel / Parquet |
| Dashboards | Plotly (interactive HTML) + matplotlib/seaborn (PNG) |
| Vector DB | ChromaDB (persistent) |
| Embeddings | `nomic-embed-text` via Ollama |
| Rate limiter | slowapi |

---

## Project Structure

```
├── api/                  # FastAPI backend
│   ├── main.py           # App startup, CORS, static file mounts
│   ├── auth.py           # User registry (users.json), JWT, bcrypt
│   ├── deps.py           # FastAPI dependencies (get_current_user, etc.)
│   ├── models.py         # Pydantic request/response models
│   ├── users.json        # Persisted user accounts (auto-created)
│   └── routers/
│       ├── auth.py       # Login, user CRUD
│       ├── chat.py       # SSE streaming chat endpoint
│       └── data.py       # Data stats, at-risk, trends, sparklines
│
├── src/                  # Shared Python backend (used by API + notebook)
│   ├── security.py       # UserContext dataclass (user_id)
│   ├── sql_store.py      # SQLDataStore — primary data backend (SQL Server via SQLAlchemy + pyodbc, pooled)
│   ├── tools.py          # LangGraph tools (13 tools, all security-aware)
│   ├── prompt_guard.py   # Input validation: length cap, token budget, injection patterns
│   ├── rag_store.py      # ChromaDB collections for schema and policy vector search
│   ├── rag_ingestor.py   # Ingests PDFs/Markdown from docs/ + auto-indexes SQL schema
│   ├── agent.py          # ExcelsisAgent — LangGraph ReAct agent (qwen2.5:14b)
│   └── mcp_server.py     # FastMCP server for Claude Code
│
├── docs/                 # Policy documents scanned by rag_ingestor.py (.pdf and .md)
│
├── web/                  # React frontend
│   └── src/
│       ├── pages/        # Login, Chat, Dashboard, Users
│       ├── components/   # Sidebar, MessageBubble, ProtectedRoute
│       └── api/client.ts # Axios instance + SSE streaming helper
│
├── docker/               # Local test infrastructure
│   └── docker-compose.yml  # SQL Server 2022 container (education_db + finance_db)
├── scripts/
│   └── seed_test_db.py   # Seed script — populates education_db (16 tables) and finance_db (18 tables)
├── Excelsis.ipynb        # Interactive Jupyter notebook
├── start.sh              # Start both servers (backend :8000, frontend :5173)
├── requirements.lock     # Pinned Python dependencies (use this for installs)
├── .env.example          # Environment variable template
└── .env.test             # Pre-filled config for the Docker test database
```

---

## Quick Start

### 1. Install and start Ollama

Download Ollama from [ollama.com](https://ollama.com) and pull the required model:

```bash
ollama pull qwen2.5:14b
ollama pull nomic-embed-text
```

Ollama must be running on `http://localhost:11434` before starting the app.

### 2. Clone and configure

```bash
cp .env.example .env
```

Edit `.env` and fill in as needed:

```env
JWT_SECRET=change-me-in-production
ADMIN_PASSWORD=your-admin-password
```

### 3. Install Python dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock
```

> Ollama model weights are downloaded on first `ollama pull`. Subsequent starts are instant. `nomic-embed-text` is required for the RAG knowledge base; `qwen2.5:14b` drives the ReAct agent.

### 4. Install frontend dependencies

```bash
cd web && npm install && cd ..
```

### 5. Start both servers

```bash
bash start.sh
```

This starts:
- **Ollama** must already be running (see step 1)
- **FastAPI** on `http://localhost:8000`
- **React** on `http://localhost:5173`

Open **http://localhost:5173** in your browser. You'll be redirected to the login page.

Default credentials: `admin` / the value of `ADMIN_PASSWORD` in your `.env` (defaults to `admin123` if not set).

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `MODEL` | No | `qwen2.5:14b` | Ollama model for the ReAct agent |
| `SQL_SERVER` | Yes | — | SQL Server hostname or IP |
| `SQL_DATABASES` | Yes | — | Comma-separated list of databases to expose |
| `SQL_PRIMARY_DB` | No | first in list | Default database for queries |
| `SQL_DRIVER` | No | `{ODBC Driver 18 for SQL Server}` | ODBC driver string |
| `SQL_AUTH_METHOD` | No | `sql` | `sql`, `windows`, or `azure_ad` |
| `SQL_USERNAME` | If `sql` auth | — | SQL Server login username |
| `SQL_PASSWORD` | If `sql` auth | — | SQL Server login password |
| `SQL_POOL_SIZE` | No | `5` | SQLAlchemy `QueuePool` base connection count per database |
| `SQL_QUERY_TIMEOUT` | No | `30` | Per-query connection timeout in seconds |
| `AT_RISK_THRESHOLD` | No | `75.0` | Default attendance % threshold for at-risk flagging |
| `JWT_SECRET` | Yes (prod) | `change-me-in-production` | Secret key for JWT signing |
| `ADMIN_PASSWORD` | No | `admin123` | Password for the default admin account |
| `PRIMARY_TABLE` | No | `attendance` | Primary SQL table the agent queries |
| `METRIC_COLUMN` | No | `status` | Column holding the measured metric |
| `POSITIVE_VALUE` | No | `present` | Value counted as a positive outcome |
| `DATE_COLUMN` | No | `date` | Date column for time-based queries |
| `ENTITY_COLUMN` | No | `student_id` | Primary entity key column |
| `ENTITY_NAME_COLUMN` | No | `student_name` | Human-readable entity name column |
| `GROUP_COLUMNS` | No | `class,grade` | Comma-separated grouping columns |
| `CHROMA_PATH` | No | `.chroma` | Persistent ChromaDB directory path |
| `EMBED_MODEL` | No | `nomic-embed-text` | Ollama embedding model for RAG |
| `DOCS_PATH` | No | `docs` | Directory scanned for policy documents |
| `MAX_MESSAGE_LEN` | No | `2000` | Maximum characters allowed in a single chat message |
| `MAX_PROMPT_TOKENS` | No | `2048` | Maximum estimated tokens (message + history) before rejection |

---

## Docker Test Database

For local development and integration testing without a production SQL Server, a Docker-based SQL Server 2022 instance is provided with two pre-seeded databases.

```bash
# Start the container (first run downloads ~1.5 GB image)
docker compose -f docker/docker-compose.yml up -d

# Install the seeding dependency (one-time)
pip install faker

# Seed both databases — choose a scale tier
python scripts/seed_test_db.py --scale small   # ~100K rows, fast
python scripts/seed_test_db.py --scale medium  # ~1M rows
python scripts/seed_test_db.py --scale large   # ~5M rows across 34 tables, ~5–10 min

# Use the pre-filled config
cp .env.test .env
```

| Database | Tables | Purpose |
|---|---|---|
| `education_db` | 16 | Attendance, students, teachers, grades, subjects |
| `finance_db` | 18 | Transactions, invoices, purchase orders, budgets, expenses |

---

## Models

All models run locally via [Ollama](https://ollama.com). No API keys or internet access required at inference time.

### LLM — `qwen2.5:14b`

Drives the LangGraph ReAct loop via `ChatOllama`. Handles both tool calling (data queries, at-risk identification, dashboard requests, knowledge-base lookups) and direct conversational replies in a single unified pipeline.

---

## Web Interface

| Page | Path | Access |
|---|---|---|
| Login | `/login` | Public |
| Chat | `/chat` | All authenticated users |
| Dashboard | `/dashboard` | All authenticated users |
| Users | `/users` | Admin only |

### Chat
Type any question in natural language. The analysis model streams its response token-by-token, with tool-use indicators showing which data sources it consulted (e.g. *Attendance data*, *SQL query*).

Example questions:
- *Which classes have the lowest attendance this month?*
- *List all students below 70% in class 10A*
- *What are the best intervention strategies for chronic absenteeism?*
- *How does Monday attendance compare to Friday?*

---

## REST API

The FastAPI backend is available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/auth/login` | None | Username + password → JWT |
| GET | `/auth/me` | Any | Current user info |
| GET | `/auth/users` | Admin | List all users |
| POST | `/auth/users` | Admin | Create user |
| DELETE | `/auth/users/{username}` | Admin | Delete user |
| POST | `/chat/stream` | Any | SSE streaming chat |
| GET | `/data/summary` | Any | Data overview |
| GET | `/data/at-risk` | Counselor+ | At-risk student list |
| GET | `/data/stats` | Any | Stats by group/period |
| GET | `/data/trends` | Any | Period comparison: last 30 days vs prior 30 days |
| GET | `/data/sparklines` | Any | Sparkline trend data |
| GET | `/health` | None | Liveness check |

---

## Jupyter Notebook

For interactive analysis, run the notebook directly:

```bash
source .venv/bin/activate
jupyter notebook Excelsis.ipynb
```

Run cells in order (1 → 9). The notebook uses the same `src/` modules as the web backend. Cell 2 verifies that Ollama is reachable before continuing.

To change who the analyst is (and what data they can access), edit `CURRENT_USER` in Cell 5:

```python
CURRENT_USER = UserContext(user_id="ms_johnson")
```

---

## Data

Data is read directly from SQL Server. Configure the connection in `.env` (see [Environment Variables](#environment-variables)).

The agent can query any database listed in `SQL_DATABASES`. The agent will adapt its T-SQL to whatever schema it finds via `run_sql_query`.

---
