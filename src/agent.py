from __future__ import annotations

import asyncio
import json
import os
import queue
import threading

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent

from .prompt_guard import check_token_budget
from .security import ADMIN_USER, UserContext
from .tools import ALL_TOOLS

SYSTEM_PROMPT = """You are an expert Data Analyst powered by PySpark AI Agent.

Guidelines:
- Be specific: name groups and entities when data is available
- If you cannot find data, say so clearly — never fabricate statistics
- Think step-by-step: retrieve data first, then analyse
- For greetings or general questions, answer directly without calling tools

Tool usage:
- query_data           — metric statistics grouped by a configured dimension
                         (leave group_by empty for default, or specify 'week', 'month', 'day_of_week', entity column)
- get_threshold_alerts — entities below a metric threshold
- statistical_summary  — distribution stats (mean, std, min, max, percentiles) across all groups
- detect_anomalies     — groups/entities whose metric_rate deviates significantly from the mean
- get_top_n            — top or bottom N groups ranked by metric_rate
- analyze_trend        — week-over-week trend direction, slope, and weekly breakdown
- update_dashboard_view — update the live dashboard to show a specific view or filter
- get_summary          — quick data overview (total records, date range, overall metric rate)
- run_sql_query        — ad-hoc Spark SQL SELECT against the registered data views
- compare_periods      — compare metric rates between two time periods
- compare_segments     — compare metric statistics for two segments side by side
- retrieve_schema      — look up table and column definitions from the schema knowledge base
- retrieve_policy      — search policy and rule documents

Analytical approach:
- "What's wrong?" or "Where are issues?": start with detect_anomalies, then get_top_n(ascending=True)
- "Show the trend" or "Is it getting better/worse?": use analyze_trend
- "Give me a summary" or "Overview": use statistical_summary for distribution, get_summary for totals
- Always interpret results — name specific groups, state what the numbers mean, flag what needs attention
- For ad-hoc SQL: call retrieve_schema first to confirm table and column names, then run_sql_query

Schema and policy retrieval:
- Call retrieve_schema BEFORE run_sql_query to confirm table and column names.
- Call retrieve_policy when the user asks about rules, thresholds, consequences,
  exemptions, or procedures — any question whose answer is in a policy document.

Dashboard rules (update_dashboard_view):
- Call this when the user asks to see a chart, visual, or dashboard view
- segments: list of segment names to focus on (omit or [] for all)
- period:   'all' | 'last_7_days' | 'last_30_days'
- view:     'overview' | 'group' | 'entity'
- Examples:
    update_dashboard_view(segments=["segment_a"], view="group")
    update_dashboard_view(period="last_30_days", view="overview")

SQL query rules (run_sql_query):
- Write valid Spark SQL: use LIMIT (not TOP), date_format(), date_sub(), date_add(), dayofweek()
- Always use SELECT — never INSERT, UPDATE, DELETE, DROP, CREATE, or ALTER
- Always call retrieve_schema first to confirm table names and column names

CRITICAL: Call tools immediately — NEVER output text like "I will use X tool" or
"Let me call X" before calling it. Narrating a tool call instead of making one is
an error.
"""

_TIMEOUT = 90

_llm = ChatOllama(
    model=os.environ.get("MODEL", "qwen2.5:14b"),
    base_url="http://localhost:11434",
    temperature=0.1,
    num_ctx=8192,
    keep_alive="10m",
)


class SparkAgent:
    def __init__(self, store=None, rag_store=None, max_history: int = 10) -> None:
        self._graph = create_react_agent(
            model=_llm,
            tools=ALL_TOOLS,
            prompt=SystemMessage(content=SYSTEM_PROMPT),
        )
        self._store        = store
        self._rag_store    = rag_store
        self._history: list = []
        self._max_history  = max_history
        self._history_lock = threading.Lock()

    def _build_config(self, user: UserContext) -> dict:
        return {
            "configurable": {
                "user_context": user,
                "store":        self._store,
                "rag_store":    self._rag_store,
            }
        }

    def _append_history(self, human: str, ai: str) -> None:
        with self._history_lock:
            self._history.append(HumanMessage(content=human))
            self._history.append(AIMessage(content=ai))
            if len(self._history) > self._max_history * 2:
                self._history = self._history[-(self._max_history * 2):]

    def _prepare(self, message: str, user: UserContext | None) -> tuple[dict, list]:
        user   = user or ADMIN_USER
        config = self._build_config(user)
        with self._history_lock:
            history       = list(self._history[-(self._max_history * 2):])
            history_chars = sum(len(m.content) for m in history)
            messages      = history[-self._max_history:] + [HumanMessage(content=message)]
        check_token_budget(message, history_chars)
        return config, messages

    def ask(self, query: str, user: UserContext | None = None) -> str:
        config, messages = self._prepare(query, user)
        result_q: queue.Queue = queue.Queue()

        def _run() -> None:
            try:
                result_q.put(("ok", self._graph.invoke({"messages": messages}, config=config)))
            except Exception as e:
                result_q.put(("err", e))

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        t.join(timeout=_TIMEOUT)

        if t.is_alive():
            return "Sorry, the request timed out. The model may be busy — please try again."

        status, value = result_q.get()
        if status == "err":
            raise value

        final  = value["messages"][-1]
        answer = final.content if isinstance(final, AIMessage) else str(final)
        self._append_history(query, answer)
        return answer

    async def astream_events(self, message: str, user: UserContext | None = None):
        config, messages = self._prepare(message, user)
        full = ""

        try:
            async with asyncio.timeout(_TIMEOUT):
                async for event in self._graph.astream_events(
                    {"messages": messages},
                    config=config,
                    version="v2",
                ):
                    kind = event.get("event", "")

                    if kind == "on_chat_model_stream":
                        chunk = event.get("data", {}).get("chunk")
                        if chunk and hasattr(chunk, "content") and chunk.content:
                            full += chunk.content
                            yield {"type": "token", "content": chunk.content}

                    elif kind == "on_tool_start":
                        yield {"type": "tool_start", "tool": event.get("name", "")}

                    elif kind == "on_tool_end":
                        name = event.get("name", "")
                        yield {"type": "tool_end", "tool": name}
                        if name == "update_dashboard_view":
                            raw = event.get("data", {}).get("output", "")
                            output = raw.content if hasattr(raw, "content") else str(raw)
                            try:
                                payload = json.loads(output)
                                yield {
                                    "type":    "dashboard_filter",
                                    "classes": payload.get("classes", []),
                                    "period":  payload.get("period", "all"),
                                    "view":    payload.get("view", "overview"),
                                }
                            except (json.JSONDecodeError, AttributeError):
                                pass

        except asyncio.TimeoutError:
            yield {"type": "error", "message": "Request timed out. The model may be busy — please try again."}
            return

        self._append_history(message, full)

    def reset_history(self) -> None:
        with self._history_lock:
            self._history.clear()
