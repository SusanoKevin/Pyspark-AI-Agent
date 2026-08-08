from __future__ import annotations

import os

from smolagents import CodeAgent, LiteLLMModel

# Tight allowlist — smolagents' CodeAgent executes LLM-authored code via its
# LocalPythonExecutor (a restricted AST interpreter). Published security
# research (NCC Group) flags real sandbox-escape risk when
# additional_authorized_imports is left permissive. Only what a PySpark
# analytics task needs, nothing broader (no os, subprocess, socket, etc).
AUTHORIZED_IMPORTS = ["pyspark", "pyspark.sql", "pandas", "numpy"]

# Databricks Free Edition's per-account fair-use quota shuts serverless
# compute down for the rest of the day if exceeded, so the write→run→fix
# loop must be bounded rather than allowed to retry indefinitely.
MAX_STEPS = int(os.environ.get("MAX_STEPS", "6"))

TASK_TEMPLATE = """You are a PySpark coding agent. You write and execute PySpark code \
against a live Databricks Spark session to answer the user's request.

A live SparkSession is available in your Python environment as the variable `spark`.

Known tables and columns (from Unity Catalog — always accurate, trust this over any
assumption you might otherwise make about table or column names):
{catalog_context}

Rules:
- Use `spark.sql(...)` or the DataFrame API against `spark` to answer the request.
- Only ever issue SELECT queries via spark.sql — never INSERT/UPDATE/DELETE/DDL.
- If your code raises an error, read the traceback, fix the code, and try again.
- When you have the answer, call `final_answer(...)` with a short summary plus a
  preview of the resulting data (e.g. `df.limit(20).toPandas().to_string()`).

Task:
{task}
"""


def build_model() -> LiteLLMModel:
    return LiteLLMModel(
        model_id=os.environ.get("CODER_MODEL", "ollama_chat/qwen2.5-coder:14b-instruct-q4_K_M"),
        api_base=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
    )


def build_agent() -> CodeAgent:
    """Wire a fresh smolagents CodeAgent with the import allowlist and step
    budget. A new agent is built per task — there is no shared conversation
    state, since the agent's job is "write, run, and self-repair code for
    this one task," not multi-turn Q&A."""
    return CodeAgent(
        model=build_model(),
        tools=[],
        additional_authorized_imports=AUTHORIZED_IMPORTS,
        max_steps=MAX_STEPS,
    )


def build_task_prompt(catalog_context: str, task: str) -> str:
    return TASK_TEMPLATE.format(catalog_context=catalog_context, task=task)
