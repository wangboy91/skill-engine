"""Repository primitives."""

from bkl_engine.domain.errors import BklEngineError
from bkl_engine.domain.execution import RunResult


class InMemoryRunStore:
    def __init__(self) -> None:
        self._runs: dict[str, RunResult] = {}

    def save(self, run: RunResult) -> RunResult:
        self._runs[run.run_id] = run
        return run

    def get(self, run_id: str) -> RunResult:
        run = self._runs.get(run_id)
        if run is None:
            raise BklEngineError("RUN_NOT_FOUND", f"Run not found: {run_id}")
        return run

    def list_runs(self) -> list[RunResult]:
        return list(self._runs.values())
