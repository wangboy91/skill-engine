"""Public SkillEngine facade shared by SDK, CLI, and API."""

from pathlib import Path

from bkl_engine.application.execution import SkillRuntime
from bkl_engine.application.ports import ToolExecutorPort
from bkl_engine.application.tool.executor import ToolExecutor
from bkl_engine.domain.execution import RunContext, RunResult
from bkl_engine.domain.skill import Skill
from bkl_engine.domain.tool import Tool
from bkl_engine.infrastructure.config.engine_config import load_engine_config
from bkl_engine.infrastructure.model_gateway.router import (
    MockModelProvider,
    ModelProvider,
    ModelRouter,
)
from bkl_engine.infrastructure.persistence import (
    InMemoryRunStore,
    JsonCatalogStore,
    LocalArtifactStore,
)
from bkl_engine.infrastructure.repositories import InMemorySkillRegistry, InMemoryToolRegistry
from bkl_engine.infrastructure.tool_runners import ApiToolRunner, PythonToolRunner
from bkl_engine.infrastructure.tracing import InMemoryTraceStore


class SkillEngine:
    def __init__(
        self,
        skill_registry: InMemorySkillRegistry,
        tool_registry: InMemoryToolRegistry,
        model_router: ModelRouter,
        tool_executor: ToolExecutorPort,
        trace_store: InMemoryTraceStore,
        artifact_store: LocalArtifactStore,
        run_store: InMemoryRunStore,
        catalog_store: JsonCatalogStore | None = None,
    ) -> None:
        self.skill_registry = skill_registry
        self.tool_registry = tool_registry
        self.model_router = model_router
        self.tool_executor = tool_executor
        self.trace_store = trace_store
        self.artifact_store = artifact_store
        self.run_store = run_store
        self.catalog_store = catalog_store
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
    def load(
        cls,
        config_path: str | Path | None = None,
        catalog_path: str | Path | None = None,
    ) -> "SkillEngine":
        config = load_engine_config(config_path or "bkl.yaml")
        catalog_store = JsonCatalogStore(catalog_path) if catalog_path is not None else None
        engine = cls(
            skill_registry=InMemorySkillRegistry(),
            tool_registry=InMemoryToolRegistry(),
            model_router=ModelRouter.from_config(config),
            tool_executor=_default_tool_executor(),
            trace_store=InMemoryTraceStore(),
            artifact_store=LocalArtifactStore("data/artifacts"),
            run_store=InMemoryRunStore(),
            catalog_store=catalog_store,
        )
        engine.load_catalog()
        return engine

    @classmethod
    def create_for_testing(
        cls,
        artifact_root: str | Path = "data/artifacts",
        model_provider: ModelProvider | None = None,
        tool_executor: ToolExecutorPort | None = None,
    ) -> "SkillEngine":
        return cls(
            skill_registry=InMemorySkillRegistry(),
            tool_registry=InMemoryToolRegistry(),
            model_router=ModelRouter(model_provider or MockModelProvider()),
            tool_executor=tool_executor or _default_tool_executor(),
            trace_store=InMemoryTraceStore(),
            artifact_store=LocalArtifactStore(artifact_root),
            run_store=InMemoryRunStore(),
        )

    async def register_tool(self, path: str | Path) -> Tool:
        tool = self.tool_registry.register_tool(path)
        if self.catalog_store is not None:
            self.catalog_store.upsert_tool(tool)
        return tool

    async def register_skill(self, path: str | Path) -> Skill:
        skill = self.skill_registry.register_skill(path)
        if self.catalog_store is not None:
            self.catalog_store.upsert_skill(skill)
        return skill

    def load_catalog(self) -> None:
        if self.catalog_store is None:
            return
        for entry in self.catalog_store.list_tools():
            if entry.enabled:
                self.tool_registry.register_tool(entry.path)
        for entry in self.catalog_store.list_skills():
            if entry.enabled:
                self.skill_registry.register_skill(entry.path)

    async def run_skill(
        self,
        skill_id: str,
        input_data: dict[str, object],
        context: RunContext | None = None,
    ) -> RunResult:
        return await self.runtime.run_skill(skill_id, input_data, context)


def _default_tool_executor() -> ToolExecutor:
    return ToolExecutor(
        python_runner=PythonToolRunner(),
        api_runner=ApiToolRunner(),
    )
