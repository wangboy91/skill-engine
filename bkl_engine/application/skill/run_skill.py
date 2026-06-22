"""Application use case for direct Skill execution."""

from __future__ import annotations

from bkl_engine.application.ports import SkillRunnerPort
from bkl_engine.application.skill.commands import RunSkillCommand
from bkl_engine.domain.execution import RunResult


class RunSkillUseCase:
    def __init__(self, engine: SkillRunnerPort) -> None:
        self.engine = engine

    async def execute(self, command: RunSkillCommand) -> RunResult:
        return await self.engine.run_skill(command.skill_id, command.input, command.context)
