"""Tool executor primitives."""

from bkl_engine.core.errors import BklEngineError
from bkl_engine.core.schemas import Tool, ToolExecutionContext, ToolExecutionResult
from bkl_engine.tools.api_tool import ApiToolRunner
from bkl_engine.tools.python_tool import PythonToolRunner


class ToolExecutor:
    def __init__(
        self,
        python_runner: PythonToolRunner | None = None,
        api_runner: ApiToolRunner | None = None,
    ) -> None:
        self.python_runner = python_runner or PythonToolRunner()
        self.api_runner = api_runner or ApiToolRunner()

    async def execute(
        self,
        tool: Tool,
        arguments: dict[str, object],
        context: ToolExecutionContext,
    ) -> ToolExecutionResult:
        if tool.type == "python":
            return await self.python_runner.execute(tool, arguments, context)
        if tool.type == "api":
            return await self.api_runner.execute(tool, arguments, context)
        raise BklEngineError("TOOL_TYPE_UNSUPPORTED", f"Unsupported tool type: {tool.type}")
