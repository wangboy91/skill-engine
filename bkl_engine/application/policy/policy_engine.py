"""Policy engine primitives."""

from typing import Protocol

from bkl_engine.domain.policy import PolicyDecision
from bkl_engine.domain.tool import Tool, ToolExecutionContext


class ToolExecutionPolicy(Protocol):
    def evaluate_tool_execution(
        self,
        tool: Tool,
        arguments: dict[str, object],
        context: ToolExecutionContext,
    ) -> PolicyDecision:
        ...


class PolicyEngine:
    """Default policy engine.

    The v0.1 default stays permissive to preserve existing local behavior.
    Product deployments can inject stricter implementations through ToolExecutor.
    """

    def evaluate_tool_execution(
        self,
        tool: Tool,
        arguments: dict[str, object],
        context: ToolExecutionContext,
    ) -> PolicyDecision:
        del tool, arguments, context
        return PolicyDecision(effect="allow", reason="default policy")
