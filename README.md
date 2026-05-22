# PySpark AI Agent

AI-powered data analyst built on PySpark. Ask natural-language questions about any CSV or Parquet dataset; a LangGraph ReAct agent reasons across 13 tools, runs Spark SQL, and streams answers token-by-token through a FastAPI + React interface.

---

## Features

- **Natural-language chat** — query your data in plain English; answers stream token-by-token via SSE
- **PySpark backend** — loads CSV and Parquet files from a configurable `DATA_PATH`; registers them as Spark SQL views at startup
- **ReAct reasoning loop** — LangGraph `create_react_agent` decides which tools to call and in what order (stats, anomaly detection, trend analysis, ad-hoc SQL, and more)
- **13 built-in tools** — `query_data`, `get_threshold_alerts`, `statistical_summary`, `detect_anomalies`, `get_top_n`, `analyze_trend`, `compare_periods`, `compare_segments`, `get_summary`, `update_dashboard_view`, `run_sql_query`, `retrieve_schema`, `retrieve_policy`
- **RAG knowledge base** — ChromaDB vector store (`nomic-embed-text` via Ollama) indexes Spark schema metadata and policy documents for grounded, accurate answers
- **Prompt guardrails** — every message is validated before reaching the agent: length cap, token-budget check, injection-pattern detection
- **Read-only SQL** — all queries are parsed with `sqlglot` at runtime; INSERT / UPDATE / DELETE / DDL are blocked
- **Web UI** — React + Tailwind dark-themed chat with live streaming, KPI dashboard, at-risk entity table, and user management
- **REST API** — FastAPI with JWT auth, SSE streaming, rate limiting (10 req/min per IP)
- **MCP server** — exposes data tools to Claude Code via FastMCP stdio

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | `qwen2.5:14b` via Ollama (`langchain-ollama`) |
| Agent | LangGraph ReAct (`create_react_agent`) |
| Data engine | PySpark 3.5+ (`SparkSession`, Spark SQL) |
| Data formats | CSV, Parquet (auto-loaded from `DATA_PATH`) |
| Backend | FastAPI + Uvicorn |
| Auth | JWT (python-jose) + bcrypt |
| Frontend | React 18 + Vite + Tailwind CSS |
| Vector DB | ChromaDB (persistent) |
| Embeddings | `nomic-embed-text` via Ollama |
| Rate limiter | slowapi |
| SQL safety | sqlglot (parse-time DML/DDL blocking) |

---

## Project Structure

```
├── api/                    # FastAPI backend
│   ├── main.py             # App startup, CORS, lifespan
│   ├── auth.py             # User registry (users.json), JWT, bcrypt
│   ├── deps.py             # FastAPI dependencies
│   ├── models.py           # Pydantic request/response models
│   └── routers/
│       ├── auth.py         # Login, user CRUD
│       ├── chat.py         # SSE streaming chat endpoint
│       └── data.py         # Summary, at-risk, stats, trends
│
├── src/                    # Shared Python backend
│   ├── spark_store.py      # SparkDataStore — PySpark data engine
│   ├── agent.py            # SparkAgent — LangGraph ReAct agent
│   ├── tools.py            # 13 LangGraph tools
│   ├── prompt_guard.py     # Input validation (length, token budget, injection)
│   ├── rag_store.py        # ChromaDB schema + policy vector search
│   ├── rag_ingestor.py     # Indexes PDFs/Markdown + Spark catalog schema
│   ├── security.py         # UserContext dataclass
│   └── mcp_server.py       # FastMCP stdio server for Claude Code
│
├── docs/                   # Policy documents (.pdf and .md) for RAG ingestion
├── data/                   # CSV / Parquet files loaded by SparkDataStore
│
├── web/                    # React frontend
│   └── src/
│       ├── pages/          # Login, Chat, Dashboard, Users
│       ├── components/     # Sidebar, MessageBubble, ProtectedRoute
│       └── api/client.ts   # Axios + SSE streaming helper
│
├── docker/
│   └── docker-compose.yml  # Optional: containerised stack
├── scripts/
│   └── seed_data.py        # Generate sample CSV/Parquet data for testing
├── start.sh                # Start both servers (backend :8000, frontend :5173)
├── requirements.lock       # Pinned Python dependencies
├── .env.example            # Environment variable template
└── .env.test               # Pre-filled config for local testing
```

---

## Quick Start

### 1. Install and start Ollama

Download Ollama from [ollama.com](https://ollama.com) and pull the required models:

```bash
ollama pull qwen2.5:14b
ollama pull nomic-embed-text
```

Ollama must be running on `http://localhost:11434` before starting the app.

### 2. Clone and configure

```bash
cp .env.example .env
```

Set at minimum:

```env
PRIMARY_TABLE=your_table_name    # filename stem of your CSV/Parquet (no extension)
GROUP_COLUMNS=department,region  # comma-separated grouping dimensions
```

### 3. Add your data

Place CSV or Parquet files in the `data/` directory. Each file is registered as a Spark SQL view named after its stem (e.g. `data/sales.csv` → view `sales`).

### 4. Install Python dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.lock
```

### 5. Install frontend dependencies

```bash
cd web && npm install && cd ..
```

### 6. Start both servers

```bash
bash start.sh
```

- **FastAPI** → `http://localhost:8000`
- **React** → `http://localhost:5173`

Open **http://localhost:5173**. Default credentials: `admin` / the value of `ADMIN_PASSWORD` in `.env` (defaults to `admin123`).

---

## Local PySpark Setup

### Java prerequisite

PySpark requires Java 8, 11, or 17. Verify you have it:

```bash
java -version
```

If Java is missing, install OpenJDK and set `JAVA_HOME`:

```bash
# macOS (Homebrew)
brew install openjdk@17
export JAVA_HOME=$(brew --prefix openjdk@17)
```

```bash
# Ubuntu / Debian
sudo apt install openjdk-17-jdk
export JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
```

Add the `export JAVA_HOME=...` line to your `~/.zshrc` or `~/.bashrc` so it persists across sessions.

### Generate test data

The seed script creates a ready-to-use Parquet dataset so you can start the agent without bringing your own data:

```bash
python scripts/seed_data.py               # 50,000 rows (default)
python scripts/seed_data.py --rows 10000  # smaller set, faster Spark startup
```

Output: `data/records.parquet`

| Column | Type | Example values |
|---|---|---|
| `entity_id` | string | `E00001` … `E01000` |
| `entity_name` | string | `Entity 1` … `Entity 1000` |
| `status` | string | `active` (78%) / `inactive` (22%) |
| `date` | date string | `2024-03-15` |
| `segment` | string | `Engineering`, `Sales`, `Marketing`, `Operations`, `Finance` |
| `category` | string | `Full-Time`, `Part-Time`, `Contractor` |

### Use the pre-filled test config

`.env.test` has all Spark vars pre-configured for the seed data:

```bash
cp .env.test .env
```

Key values it sets:

```env
SPARK_MASTER=local[*]
DATA_PATH=./data
PRIMARY_TABLE=records
GROUP_COLUMNS=segment,category
METRIC_COLUMN=status
POSITIVE_VALUE=active
```

### Spark UI

While the app is running, the Spark job dashboard is available at **http://localhost:4040**. Useful for inspecting query plans and monitoring job progress.

### Memory tuning

The defaults work for most laptops. If you run into issues:

```env
# Reduce shuffle partitions on machines with < 8 GB RAM
# Add to .env:
SPARK_DRIVER_MEMORY=2g   # increase for datasets > 500 MB
```

To lower shuffle partitions, edit `spark_store.py:83`:
```python
.config("spark.sql.shuffle.partitions", "4")  # default is 8
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `MODEL` | No | `qwen2.5:14b` | Ollama model for the ReAct agent |
| `SPARK_MASTER` | No | `local[*]` | Spark master URL (`local[*]` or `spark://host:7077`) |
| `SPARK_APP_NAME` | No | `pyspark-ai-agent` | Spark application name |
| `DATA_PATH` | No | `./data` | Directory scanned for CSV and Parquet files |
| `PRIMARY_TABLE` | Yes | — | Spark view name the agent queries by default |
| `METRIC_COLUMN` | No | `status` | Column holding the measured metric |
| `POSITIVE_VALUE` | No | `active` | Value counted as a positive outcome |
| `DATE_COLUMN` | No | `date` | Date column for time-based queries |
| `ENTITY_COLUMN` | No | `entity_id` | Primary entity key column |
| `ENTITY_NAME_COLUMN` | No | `entity_name` | Human-readable entity name column |
| `GROUP_COLUMNS` | No | _(empty)_ | Comma-separated grouping dimensions |
| `AT_RISK_THRESHOLD` | No | `75.0` | Default metric % threshold for alerts |
| `JWT_SECRET` | Yes (prod) | `change-me-in-production` | Secret key for JWT signing |
| `ADMIN_PASSWORD` | No | `admin123` | Password for the default admin account |
| `CHROMA_PATH` | No | `.chroma` | Persistent ChromaDB directory |
| `EMBED_MODEL` | No | `nomic-embed-text` | Ollama embedding model for RAG |
| `DOCS_PATH` | No | `docs` | Directory scanned for policy documents |
| `MCP_USER_ID` | No | `mcp_user` | Fixed user identity for the MCP server |
| `MAX_MESSAGE_LEN` | No | `2000` | Maximum characters in a single chat message |
| `MAX_PROMPT_TOKENS` | No | `2048` | Maximum estimated tokens before rejection |

---

## Example Questions

```
Which groups have the lowest metric rate this month?
List all entities below 70% in segment_a
What's the week-over-week trend for the last 6 weeks?
Are there any statistical anomalies in the data?
Compare last 7 days vs last 30 days
Run a SQL query to count records by region
```

---

## REST API

Interactive docs at `http://localhost:8000/docs`.

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/auth/login` | None | Username + password → JWT |
| GET | `/auth/me` | Any | Current user info |
| GET | `/auth/users` | Admin | List all users |
| POST | `/auth/users` | Admin | Create user |
| DELETE | `/auth/users/{username}` | Admin | Delete user |
| POST | `/chat/stream` | Any | SSE streaming chat |
| GET | `/data/summary` | Any | Data overview |
| GET | `/data/at-risk` | Any | Entities below threshold |
| GET | `/data/stats` | Any | Stats by group/period |
| GET | `/data/trends` | Any | Period comparison (last 30 vs prior 30) |
| GET | `/data/sparklines` | Any | Sparkline trend data |
| GET | `/health` | None | Liveness check |

---

## MCP Server

The FastMCP stdio server lets Claude Code query your data directly:

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

Tools exposed: `ask_analyst`, `data_summary`, `threshold_alerts`, `group_statistics`, `schema_lookup`, `knowledge_lookup`.

---

## Spark SQL

The `run_sql_query` tool executes ad-hoc **Spark SQL** against the registered data views. Only `SELECT` statements are allowed — DML and DDL are blocked at parse time by `sqlglot`.

### Key syntax differences from T-SQL / standard SQL

| Operation | T-SQL | Spark SQL |
|---|---|---|
| Limit rows | `SELECT TOP 10 …` | `SELECT … LIMIT 10` |
| Format a date | `FORMAT(date, 'yyyy-MM')` | `date_format(date, 'yyyy-MM')` |
| Subtract days | `DATEADD(day, -7, date)` | `date_sub(date, 7)` |
| Add days | `DATEADD(day, 7, date)` | `date_add(date, 7)` |
| Day of week | `DATEPART(weekday, date)` | `dayofweek(date)` (1=Sun … 7=Sat) |
| String concat | `col1 + col2` | `CONCAT(col1, col2)` |
| Null-safe divide | `col / NULLIF(n, 0)` | `col / NULLIF(n, 0)` _(same)_ |
| Cast | `CAST(x AS INT)` | `CAST(x AS INT)` _(same)_ |

### Common date format patterns

| Pattern | Output example |
|---|---|
| `'yyyy-MM-dd'` | `2024-03-15` |
| `'yyyy-MM'` | `2024-03` |
| `'yyyy'` | `2024` |
| `'EEEE'` | `Friday` |
| `'E'` | `Fri` |

### Example queries

```sql
-- Records per group in the last 30 days
SELECT department, COUNT(*) AS total
FROM employees
WHERE CAST(date AS DATE) >= date_sub(CURRENT_DATE(), 30)
GROUP BY department
ORDER BY total DESC
LIMIT 20

-- Weekly metric rate over the last 8 weeks
SELECT
  date_format(date_sub(CAST(date AS DATE), (dayofweek(CAST(date AS DATE)) + 5) % 7), 'yyyy-MM-dd') AS week_start,
  ROUND(100.0 * SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) / COUNT(*), 1) AS metric_rate
FROM my_table
GROUP BY week_start
ORDER BY week_start DESC
LIMIT 8

-- Entities with the most records, filtered by segment
SELECT entity_id, entity_name, COUNT(*) AS total
FROM my_table
WHERE region = 'APAC'
GROUP BY entity_id, entity_name
ORDER BY total DESC
LIMIT 10
```

### Tips

- Call `retrieve_schema` first to confirm view names and column names before writing a query.
- Use `LIMIT` — queries without one are automatically capped at 200 rows.
- All views live in the same Spark catalog; there is no database prefix needed.
- Use `CAST(date_col AS DATE)` before date functions if the column is stored as a string.

---

## Tests

```bash
pytest tests/ -v                     # unit tests (no Ollama needed)
pytest tests/ -v -m integration      # integration tests (requires Ollama)
pytest tests/ -v --run-all           # everything
```
