import asyncio
import logging
import os
import urllib.request
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()  # must run before any src.* imports that read env vars

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers.task import router as task_router
from src.agent import PySparkCodeAgent
from src.databricks_store import DatabricksDataStore

logger = logging.getLogger(__name__)


def _validate_startup(store: DatabricksDataStore) -> None:
    model = os.environ.get("CODER_MODEL", "ollama_chat/qwen2.5-coder:14b-instruct-q4_K_M")

    ollama_ok = False
    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=3)
        ollama_ok = True
    except Exception:
        logger.warning("Ollama not reachable at http://localhost:11434 — agent responses will fail")

    databricks_ok = store.ping()
    if not databricks_ok:
        logger.error(
            "Databricks Connect session check failed — verify DATABRICKS_HOST / "
            "DATABRICKS_TOKEN in .env"
        )

    tables = store.get_table_names() if databricks_ok else []
    logger.info(
        "PySpark AI Agent startup | model=%s (%s) | databricks=%s | tables=%s",
        model, "OK" if ollama_ok else "UNREACHABLE",
        "OK" if databricks_ok else "UNREACHABLE", tables,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    store = DatabricksDataStore()
    app.state.store = store
    app.state.agent = PySparkCodeAgent(store=store)

    await asyncio.to_thread(_validate_startup, store)
    yield
    store.close()


app = FastAPI(title="PySpark AI Agent API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(task_router, tags=["task"])


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}
