"""Public SkillEngine facade shared by SDK, CLI, and API."""

from pathlib import Path

from bkl_engine.core.config import load_engine_config
from bkl_engine.core.schemas import RunContext, RunResult, Skill, Tool
from bkl_engine.models.router import MockModelProvider, ModelProvider, ModelRouter
from bkl_engine.skills.registry import InMemorySkillRegistry
from bkl_engine.skills.runtime import SkillRuntime
from bkl_engine.storage.artifact_store import LocalArtifactStore
from bkl_engine.storage.repositories import InMemoryRunStore
from bkl_engine.tools.executor import ToolExecutor
from bkl_engine.tools.registry import InMemoryToolRegistry
from bkl_engine.trace.trace_store import InMemoryTraceStore


class SkillEngine:
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
        self.runtime = SkillRuntime(
            skill_registry=skill_registry,
            tool_registry=tool_registry,
            model_router=model_router,
            tool_executor=tool_executor,
            trace_store=trace_store,
            artifact_store=artifact_store,
            run_store=run_store,
        )

    @classmethod
    def load(cls, config_path: str | Path | None = None) -> "SkillEngine":
        config = load_engine_config(config_path or "bkl.yaml")
        return cls(
            skill_registry=InMemorySkillRegistry(),
            tool_registry=InMemoryToolRegistry(),
            model_router=ModelRouter.from_config(config),
            tool_executor=ToolExecutor(),
            trace_store=InMemoryTraceStore(),
            artifact_store=LocalArtifactStore("data/artifacts"),
            run_store=InMemoryRunStore(),
        )

    @classmethod
    def create_for_testing(
        cls,
        artifact_root: str | Path = "data/artifacts",
        model_provider: ModelProvider | None = None,
    ) -> "SkillEngine":
        return cls(
            skill_registry=InMemorySkillRegistry(),
            tool_registry=InMemoryToolRegistry(),
            model_router=ModelRouter(model_provider or MockModelProvider()),
            tool_executor=ToolExecutor(),
            trace_store=InMemoryTraceStore(),
            artifact_store=LocalArtifactStore(artifact_root),
            run_store=InMemoryRunStore(),
        )

    async def register_tool(self, path: str | Path) -> Tool:
        return self.tool_registry.register_tool(path)

    async def register_skill(self, path: str | Path) -> Skill:
        return self.skill_registry.register_skill(path)

    async def run_skill(
        self,
        skill_id: str,
        input_data: dict[str, object],
        context: RunContext | None = None,
    ) -> RunResult:
        return await self.runtime.run_skill(skill_id, input_data, context)
