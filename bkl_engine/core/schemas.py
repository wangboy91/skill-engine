"""Shared Pydantic schema primitives."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

JsonObject = dict[str, Any]
ToolType = Literal["api", "python", "llm", "skill", "system"]
RunStatus = Literal["pending", "running", "succeeded", "failed"]
ArtifactType = Literal["text", "json", "image", "audio", "video", "subtitle", "zip", "log"]


class ToolFilesystemConfig(BaseModel):
    read: list[str] = Field(default_factory=list)
    write: list[str] = Field(default_factory=list)


class ToolRuntimeConfig(BaseModel):
    timeout_seconds: int = 60
    memory_mb: int | None = None
    network: bool = False
    filesystem: ToolFilesystemConfig = Field(default_factory=ToolFilesystemConfig)


class ToolPermissions(BaseModel):
    network: bool = False
    filesystem_read: list[str] = Field(default_factory=list)
    filesystem_write: list[str] = Field(default_factory=list)
    secrets: list[str] = Field(default_factory=list)


class Tool(BaseModel):
    id: str
    name: str
    type: ToolType
    description: str
    input_schema: JsonObject
    output_schema: JsonObject
    config: JsonObject = Field(default_factory=dict)
    permissions: ToolPermissions = Field(default_factory=ToolPermissions)
    enabled: bool = True
    entry: str | None = None
    runtime: ToolRuntimeConfig = Field(default_factory=ToolRuntimeConfig)
    package_path: Path | None = None


class SkillLimits(BaseModel):
    max_iterations: int = 8
    max_tool_calls: int = 12
    max_tokens: int = 12_000
    timeout_seconds: int = 600
    max_credits: int = 100


class SkillModelConfig(BaseModel):
    profile: str = "mock"
    fallback_profile: str | None = None


class Skill(BaseModel):
    id: str
    name: str
    version: str
    description: str
    input_schema: JsonObject
    output_schema: JsonObject
    prompt: str
    allowed_tools: list[str]
    model: SkillModelConfig = Field(default_factory=SkillModelConfig)
    limits: SkillLimits = Field(default_factory=SkillLimits)
    enabled: bool = True
    package_path: Path | None = None


class ToolExecutionContext(BaseModel):
    run_id: str
    tool_call_id: str
    artifact_dir: Path
    skill_id: str | None = None


class ToolExecutionResult(BaseModel):
    output: JsonObject
    stderr: str = ""
    artifacts: list[str] = Field(default_factory=list)


class EngineError(BaseModel):
    code: str
    message: str
    details: JsonObject = Field(default_factory=dict)
    retryable: bool = False


class UsageSummary(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    model_cost: float = 0
    tool_cost: float = 0
    credits_charged: float = 0


class Artifact(BaseModel):
    id: str
    run_id: str
    tool_call_id: str | None = None
    type: ArtifactType
    mime_type: str
    uri: str
    metadata: JsonObject = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TraceEvent(BaseModel):
    id: str
    run_id: str
    type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    message: str
    data: JsonObject = Field(default_factory=dict)


class RunContext(BaseModel):
    user_id: str | None = None
    project_id: str | None = None
    metadata: JsonObject = Field(default_factory=dict)


class RunResult(BaseModel):
    run_id: str
    status: RunStatus
    skill_id: str
    output: JsonObject | None = None
    error: EngineError | None = None
    artifacts: list[Artifact] = Field(default_factory=list)
    trace_summary: JsonObject = Field(default_factory=dict)
    usage: UsageSummary = Field(default_factory=UsageSummary)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
