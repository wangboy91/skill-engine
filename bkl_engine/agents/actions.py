"""Deterministic Agent actions over SkillEngine."""

from typing import Any

from bkl_engine.core.schemas import RunResult
from bkl_engine.engine import SkillEngine


class ActionRegistry:
    def __init__(self, engine: SkillEngine) -> None:
        self.engine = engine

    async def run_skill(self, skill_id: str, input_data: dict[str, Any]) -> RunResult:
        return await self.engine.run_skill(skill_id, input_data)

    def list_skills(self) -> list[str]:
        return [skill.id for skill in self.engine.skill_registry.list_skills()]

    def list_tools(self) -> list[str]:
        return [tool.id for tool in self.engine.tool_registry.list_tools()]
