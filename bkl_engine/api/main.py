"""FastAPI application entrypoint."""

from typing import Any, Literal, cast

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from bkl_engine.agents.loop import AgentLoop
from bkl_engine.core.errors import BklEngineError
from bkl_engine.engine import SkillEngine


class RegisterPathRequest(BaseModel):
    path: str


class RunSkillRequest(BaseModel):
    input: dict[str, object]
    context: dict[str, object] = Field(default_factory=dict)
    mode: Literal["sync"] = "sync"


class ChatMessageRequest(BaseModel):
    session_id: str | None = None
    message: str
    scene_id: str | None = None
    skill_id: str | None = None
    input: dict[str, object] = Field(default_factory=dict)
    confirm: bool = False


def create_app(engine: SkillEngine | None = None) -> FastAPI:
    api = FastAPI(title="BKL Skill Engine", version="0.1.0")
    api.state.engine = engine or SkillEngine.load()

    @api.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @api.post("/tools/register")
    async def register_tool(request: RegisterPathRequest) -> dict[str, Any]:
        try:
            tool = await _engine(api).register_tool(request.path)
            return tool.model_dump(mode="json")
        except BklEngineError as exc:
            raise HTTPException(status_code=400, detail=exc.message) from exc

    @api.get("/tools")
    def list_tools() -> list[dict[str, Any]]:
        return [
            tool.model_dump(mode="json")
            for tool in _engine(api).tool_registry.list_tools()
        ]

    @api.get("/tools/{tool_id}")
    def get_tool(tool_id: str) -> dict[str, Any]:
        try:
            return _engine(api).tool_registry.get_tool(tool_id).model_dump(mode="json")
        except BklEngineError as exc:
            raise HTTPException(status_code=404, detail=exc.message) from exc

    @api.post("/skills/register")
    async def register_skill(request: RegisterPathRequest) -> dict[str, Any]:
        try:
            skill = await _engine(api).register_skill(request.path)
            return skill.model_dump(mode="json")
        except BklEngineError as exc:
            raise HTTPException(status_code=400, detail=exc.message) from exc

    @api.get("/skills")
    def list_skills() -> list[dict[str, Any]]:
        return [
            skill.model_dump(mode="json")
            for skill in _engine(api).skill_registry.list_skills()
        ]

    @api.get("/skills/{skill_id}")
    def get_skill(skill_id: str) -> dict[str, Any]:
        try:
            return _engine(api).skill_registry.get_skill(skill_id).model_dump(mode="json")
        except BklEngineError as exc:
            raise HTTPException(status_code=404, detail=exc.message) from exc

    @api.post("/skills/{skill_id}/runs")
    async def run_skill(skill_id: str, request: RunSkillRequest) -> dict[str, Any]:
        try:
            run = await _engine(api).run_skill(skill_id, request.input)
            return run.model_dump(mode="json")
        except BklEngineError as exc:
            raise HTTPException(status_code=400, detail=exc.message) from exc

    @api.post("/chat/messages")
    async def chat_message(request: ChatMessageRequest) -> dict[str, Any]:
        try:
            loop = AgentLoop(_engine(api))
            response = await loop.handle_message(
                request.message,
                session_id=request.session_id,
                scene_id=request.scene_id,
                skill_id=request.skill_id,
                input_data=request.input,
                confirm=request.confirm,
            )
            return response.model_dump(mode="json")
        except BklEngineError as exc:
            raise HTTPException(status_code=400, detail=exc.message) from exc

    @api.get("/runs")
    def list_runs() -> list[dict[str, Any]]:
        return [run.model_dump(mode="json") for run in _engine(api).run_store.list_runs()]

    @api.get("/runs/{run_id}")
    def get_run(run_id: str) -> dict[str, Any]:
        try:
            return _engine(api).run_store.get(run_id).model_dump(mode="json")
        except BklEngineError as exc:
            raise HTTPException(status_code=404, detail=exc.message) from exc

    @api.get("/runs/{run_id}/trace")
    def get_trace(run_id: str) -> list[dict[str, Any]]:
        return [
            event.model_dump(mode="json")
            for event in _engine(api).trace_store.list_events(run_id)
        ]

    @api.get("/runs/{run_id}/artifacts")
    def get_artifacts(run_id: str) -> list[dict[str, Any]]:
        return [
            artifact.model_dump(mode="json")
            for artifact in _engine(api).artifact_store.list_by_run(run_id)
        ]

    @api.get("/artifacts/{artifact_id}")
    def get_artifact(artifact_id: str) -> dict[str, Any]:
        try:
            return _engine(api).artifact_store.get(artifact_id).model_dump(mode="json")
        except BklEngineError as exc:
            raise HTTPException(status_code=404, detail=exc.message) from exc

    return api


def _engine(api: FastAPI) -> SkillEngine:
    return cast(SkillEngine, api.state.engine)


app = create_app()
