"""Tool registry primitives."""

from pathlib import Path

from bkl_engine.core.errors import BklEngineError
from bkl_engine.core.schemas import Tool
from bkl_engine.tools.loader import load_tool


class InMemoryToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> Tool:
        self._tools[tool.id] = tool
        return tool

    def register_tool(self, path: str | Path) -> Tool:
        return self.register(load_tool(path))

    def get_tool(self, tool_id: str) -> Tool:
        tool = self._tools.get(tool_id)
        if tool is None:
            raise BklEngineError("TOOL_NOT_FOUND", f"Tool not found: {tool_id}")
        if not tool.enabled:
            raise BklEngineError("TOOL_DISABLED", f"Tool is disabled: {tool_id}")
        return tool

    def list_tools(self) -> list[Tool]:
        return list(self._tools.values())

    def enable_tool(self, tool_id: str) -> Tool:
        tool = self.get_tool(tool_id)
        enabled = tool.model_copy(update={"enabled": True})
        self._tools[tool_id] = enabled
        return enabled

    def disable_tool(self, tool_id: str) -> Tool:
        tool = self.get_tool(tool_id)
        disabled = tool.model_copy(update={"enabled": False})
        self._tools[tool_id] = disabled
        return disabled

    def get_allowed_tools(self, allowed_tools: list[str]) -> list[Tool]:
        return [self.get_tool(tool_id) for tool_id in allowed_tools]
