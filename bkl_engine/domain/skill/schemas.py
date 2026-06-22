"""Skill domain schemas."""

from pathlib import Path

from pydantic import BaseModel, Field

from bkl_engine.domain.common import JsonObject


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
