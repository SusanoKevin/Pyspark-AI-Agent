from __future__ import annotations

"""Stand-ins for smolagents/Databricks objects, used to test the agent's
event-translation and self-repair surfacing deterministically — without a
live Ollama model or a live Databricks Connect session.
"""


class FakeActionStep:
    """Stand-in for smolagents.memory.ActionStep — only the fields
    src/agent.py actually reads."""

    def __init__(self, step_number: int, code_action: str, error=None, observations: str | None = None):
        self.step_number = step_number
        self.code_action = code_action
        self.error = error
        self.observations = observations


class FakeFinalAnswerStep:
    """Stand-in for smolagents.memory.FinalAnswerStep — the last item
    yielded by `CodeAgent.run(..., stream=True)`."""

    def __init__(self, output: str):
        self.output = output


class FakeMemory:
    def __init__(self, steps: list) -> None:
        self.steps = steps


class FakeCodeAgent:
    """Stand-in for smolagents.CodeAgent — replays a fixed sequence of steps
    instead of calling a live model, so tests can assert on self-repair
    behaviour deterministically. `steps` should be ActionSteps only; a
    FinalAnswerStep is appended automatically to match the real run(stream=True)
    contract (the last streamed item is always a FinalAnswerStep)."""

    def __init__(self, steps: list[FakeActionStep], final_answer: str = "done") -> None:
        self._steps = steps
        self.memory = FakeMemory(steps)
        self._final_answer = final_answer

    def run(self, task, additional_args=None, stream=False):
        if not stream:
            return self._final_answer

        def _generator():
            yield from self._steps
            yield FakeFinalAnswerStep(self._final_answer)

        return _generator()


class FakeDatabricksStore:
    """Stand-in for DatabricksDataStore — no real Spark session required."""

    def __init__(self, catalog_context: str = "- sample_sales: order_id (int), region (string)") -> None:
        self._catalog_context = catalog_context
        self.spark = object()

    def get_catalog_context(self) -> str:
        return self._catalog_context
