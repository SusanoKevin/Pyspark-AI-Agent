from __future__ import annotations

import asyncio
import logging
import os
import queue
import threading

from .databricks_store import DatabricksDataStore
from .executor import build_agent, build_task_prompt

logger = logging.getLogger(__name__)

# Bounds how long we wait on any single streamed step before giving up —
# not a total-runtime cap (max_steps in src/executor.py handles that).
_STEP_TIMEOUT_S = int(os.environ.get("AGENT_STEP_TIMEOUT_S", "180"))

_SENTINEL = object()


def _final_code(agent) -> str:
    for step in reversed(agent.memory.steps):
        code = getattr(step, "code_action", None)
        if code:
            return code
    return ""


def _step_events(step) -> list[dict]:
    """Translate one smolagents memory step into SSE events.

    Replaces the old LangGraph tool_start/tool_end pair: each step here is a
    full generated-code execution attempt, not a fixed-tool call, so the
    events are renamed code_attempt / execution_result to describe that.

    Duck-typed on `code_action` (rather than `isinstance(step, ActionStep)`)
    so step objects from tests/fixtures.py can stand in for the real
    smolagents.memory.ActionStep without importing smolagents in tests.
    Other step kinds (PlanningStep, ChatMessageStreamDelta) have no
    `code_action` and are silently skipped.
    """
    code = getattr(step, "code_action", None)
    if not code:
        return []

    events = [{"type": "code_attempt", "step": step.step_number, "code": code}]

    error = getattr(step, "error", None)
    if error is not None:
        events.append({"type": "execution_result", "step": step.step_number, "error": str(error)})
    else:
        observation = getattr(step, "observations", None)
        events.append({
            "type": "execution_result",
            "step": step.step_number,
            "output": str(observation) if observation else "",
        })
    return events


class PySparkCodeAgent:
    """Thin wrapper around smolagents' CodeAgent for one-shot PySpark tasks.

    Each call builds a fresh CodeAgent bounded by max_steps and grounds it
    with live Unity Catalog context — there is no cross-request conversation
    history, since the agent's job is "write, run, and self-repair code for
    this task," not multi-turn chat.
    """

    def __init__(self, store: DatabricksDataStore) -> None:
        self._store = store

    def _prompt(self, task: str) -> str:
        return build_task_prompt(self._store.get_catalog_context(), task)

    def run(self, task: str) -> dict:
        agent = build_agent()
        result = agent.run(self._prompt(task), additional_args={"spark": self._store.spark})
        return {"code": _final_code(agent), "result": str(result)}

    async def astream_events(self, task: str):
        agent = build_agent()
        prompt = self._prompt(task)
        q: queue.Queue = queue.Queue()

        def _run() -> None:
            try:
                for item in agent.run(prompt, additional_args={"spark": self._store.spark}, stream=True):
                    q.put(item)
            except Exception as e:  # noqa: BLE001 — surfaced to the client as an SSE error event
                q.put(e)
            finally:
                q.put(_SENTINEL)

        threading.Thread(target=_run, daemon=True).start()

        loop = asyncio.get_event_loop()
        last_item = None
        try:
            while True:
                try:
                    item = await asyncio.wait_for(loop.run_in_executor(None, q.get), timeout=_STEP_TIMEOUT_S)
                except asyncio.TimeoutError:
                    yield {"type": "error", "message": "Request timed out. The model may be busy — please try again."}
                    return

                if item is _SENTINEL:
                    break
                if isinstance(item, Exception):
                    yield {"type": "error", "message": str(item)}
                    return

                for event in _step_events(item):
                    yield event
                last_item = item
        finally:
            pass

        # smolagents' streaming run yields ActionStep/PlanningStep objects as
        # they happen and a FinalAnswerStep (with an `.output` attribute, no
        # `code_action`) as the very last item — surface that as the result
        # panel payload. Duck-typed for the same reason as _step_events above.
        if last_item is not None and hasattr(last_item, "output") and not hasattr(last_item, "code_action"):
            final_text = str(last_item.output)
        else:
            final_text = str(last_item) if last_item is not None else ""
        yield {"type": "final_result", "result": final_text}
