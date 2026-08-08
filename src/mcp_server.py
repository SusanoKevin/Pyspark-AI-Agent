from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from mcp.server.fastmcp import FastMCP

from src.agent import PySparkCodeAgent
from src.databricks_store import DatabricksDataStore

store = DatabricksDataStore()
agent = PySparkCodeAgent(store=store)

mcp = FastMCP(
    name="PySpark Coding Agent",
    instructions=(
        "Writes, executes, and self-repairs PySpark code against a live "
        "Databricks Connect session. Give it a natural-language data task; "
        "it returns the final PySpark code it ran and a preview of the result."
    ),
)


@mcp.tool()
def run_pyspark_task(task: str) -> str:
    """
    Write and execute PySpark code to accomplish a data task against the
    connected Databricks workspace, self-repairing on errors.

    task: natural-language description of what to compute or retrieve.
    Examples: 'How many rows are in the sample_sales table?',
              'What is the average order value by region?'

    Returns a JSON object: {"code": "<final PySpark code>", "result": "<preview>"}.
    """
    outcome = agent.run(task)
    return json.dumps(outcome)


if __name__ == "__main__":
    print("Starting PySpark Coding Agent MCP server")
    mcp.run()
