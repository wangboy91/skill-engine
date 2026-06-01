"""Skill runtime primitives."""

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate

from bkl_engine.core.errors import BklEngineError
from bkl_engine.core.schemas import (
    EngineError,
    RunContext,
    RunResult,
    Skill,
    Tool,
    ToolExecutionContext,
    UsageSummary,
)
from bkl_engine.models.router import ModelRouter
from bkl_engine.skills.registry import InMemorySkillRegistry
from bkl_engine.storage.artifact_store import LocalArtifactStore
from bkl_engine.storage.repositories import InMemoryRunStore
from bkl_engine.tools.executor import ToolExecutor
from bkl_engine.tools.registry import InMemoryToolRegistry
from bkl_engine.trace.trace_store import InMemoryTraceStore


class SkillRuntimeError(BklEngineError):
    """Raised when a Skill run fails."""


class SkillRuntime:
    def __init__(
        self,
        skill_registry: InMemorySkillRegistry,
        tool_registry: InMemoryToolRegistry,
        model_router: ModelRouter,
        tool_executor: ToolExecutor,
        trace_store: InMemoryTraceStore,
        artifact_store: LocalArtifactStore,
        run_store: InMemoryRunStore,
    ) -> None:
        self.skill_registry = skill_registry
        self.tool_registry = tool_registry
        self.model_router = model_router
        self.tool_executor = tool_executor
        self.trace_store = trace_store
        self.artifact_store = artifact_store
        self.run_store = run_store

    async def run_skill(
        self,
        skill_id: str,
        input_data: dict[str, object],
        context: RunContext | None = None,
    ) -> RunResult:
        del context
        skill = self.skill_registry.get_skill(skill_id)
        run_id = f"run_{uuid4().hex}"
        run = RunResult(run_id=run_id, status="running", skill_id=skill.id)
        self.run_store.save(run)
        self.trace_store.record(run_id, "skill_started", "Skill started", {"skill_id": skill.id})

        try:
            self._validate_schema(skill.input_schema, input_data, "INPUT_SCHEMA_INVALID")
            allowed_tools = self.tool_registry.get_allowed_tools(skill.allowed_tools)
            result = await self._run_loop(run_id, skill, input_data, allowed_tools)
            self.run_store.save(result)
            return result
        except BklEngineError as exc:
            failed = run.model_copy(
                update={
                    "status": "failed",
                    "error": EngineError(
                        code=exc.code,
                        message=exc.message,
                        details=exc.details,
                        retryable=exc.retryable,
                    ),
                    "trace_summary": self._trace_summary(run_id),
                    "completed_at": datetime.now(UTC),
                }
            )
            self.trace_store.record(
                run_id,
                "skill_failed",
                "Skill failed",
                {"code": exc.code, "message": exc.message},
            )
            self.run_store.save(failed)
            if isinstance(exc, SkillRuntimeError):
                raise
            raise SkillRuntimeError(exc.code, exc.message, exc.details, exc.retryable) from exc

    async def _run_loop(
        self,
        run_id: str,
        skill: Skill,
        input_data: dict[str, object],
        allowed_tools: list[Tool],
    ) -> RunResult:
        messages = self._build_messages(skill, input_data)
        tool_call_count = 0
        usage = UsageSummary()

        for _ in range(skill.limits.max_iterations):
            model_response = await self.model_router.chat(
                skill.model.profile,
                messages,
                self._tools_to_llm_schema(allowed_tools),
            )
            usage.input_tokens += model_response.usage.input_tokens
            usage.output_tokens += model_response.usage.output_tokens
            usage.model_cost += model_response.usage.cost
            self.trace_store.record(
                run_id,
                "llm_called",
                "Model called",
                {
                    "tool_call_count": len(model_response.tool_calls),
                    "has_final_output": model_response.final_output is not None,
                },
            )

            if model_response.final_output is not None:
                self._validate_schema(
                    skill.output_schema,
                    model_response.final_output,
                    "OUTPUT_SCHEMA_INVALID",
                )
                result = RunResult(
                    run_id=run_id,
                    status="succeeded",
                    skill_id=skill.id,
                    output=model_response.final_output,
                    artifacts=self.artifact_store.list_by_run(run_id),
                    trace_summary=self._trace_summary(run_id),
                    usage=usage,
                    completed_at=datetime.now(UTC),
                )
                self.trace_store.record(
                    run_id,
                    "skill_succeeded",
                    "Skill succeeded",
                    {"skill_id": skill.id},
                )
                return result

            for tool_call in model_response.tool_calls:
                tool_call_count += 1
                if tool_call_count > skill.limits.max_tool_calls:
                    raise SkillRuntimeError(
                        "MAX_TOOL_CALLS_EXCEEDED",
                        "Maximum tool calls exceeded",
                    )

                tool = self._find_allowed_tool(allowed_tools, tool_call.tool_id)
                messages.append(self._assistant_tool_call_message(tool_call))
                tool_artifact_dir = Path(self.artifact_store.root) / run_id / tool_call.id
                self.trace_store.record(
                    run_id,
                    "tool_called",
                    "Tool called",
                    {"tool_id": tool.id, "tool_call_id": tool_call.id},
                )
                tool_result = await self.tool_executor.execute(
                    tool,
                    tool_call.arguments,
                    ToolExecutionContext(
                        run_id=run_id,
                        skill_id=skill.id,
                        tool_call_id=tool_call.id,
                        artifact_dir=tool_artifact_dir,
                    ),
                )
                self.trace_store.record(
                    run_id,
                    "tool_succeeded",
                    "Tool succeeded",
                    {"tool_id": tool.id, "tool_call_id": tool_call.id},
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(tool_result.output, ensure_ascii=False),
                    }
                )

        raise SkillRuntimeError("MAX_ITERATIONS_EXCEEDED", "Maximum iterations exceeded")

    def _assistant_tool_call_message(self, tool_call: object) -> dict[str, object]:
        from bkl_engine.models.router import ToolCallRequest

        if not isinstance(tool_call, ToolCallRequest):
            return {"role": "assistant", "content": ""}
        return {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.tool_id,
                        "arguments": json.dumps(tool_call.arguments, ensure_ascii=False),
                    },
                }
            ],
        }

    def _validate_schema(
        self,
        schema: dict[str, object],
        value: dict[str, object],
        code: str,
    ) -> None:
        try:
            validate(instance=value, schema=schema)
        except JsonSchemaValidationError as exc:
            raise SkillRuntimeError(code, exc.message) from exc

    def _build_messages(
        self,
        skill: Skill,
        input_data: dict[str, object],
    ) -> list[dict[str, object]]:
        return [
            {"role": "system", "content": skill.prompt},
            {"role": "user", "content": json.dumps({"input": input_data}, ensure_ascii=False)},
        ]

    def _tools_to_llm_schema(self, tools: list[Tool]) -> list[dict[str, object]]:
        return [
            {
                "id": tool.id,
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in tools
        ]

    def _find_allowed_tool(self, tools: list[Tool], tool_id: str) -> Tool:
        for tool in tools:
            if tool.id == tool_id:
                return tool
        raise SkillRuntimeError("TOOL_NOT_ALLOWED", f"Tool is not allowed: {tool_id}")

    def _trace_summary(self, run_id: str) -> dict[str, object]:
        summary: dict[str, int] = {
            "llm_called": 0,
            "tool_called": 0,
            "tool_succeeded": 0,
            "tool_failed": 0,
        }
        for event in self.trace_store.list_events(run_id):
            if event.type in summary:
                summary[event.type] += 1
        return dict(summary)
