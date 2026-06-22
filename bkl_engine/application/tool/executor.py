"""Tool executor primitives."""

from bkl_engine.application.ports import ToolRunnerPort
from bkl_engine.application.policy import PolicyEngine, ToolExecutionPolicy
from bkl_engine.domain.errors import BklEngineError
from bkl_engine.domain.policy import PolicyDecision
from bkl_engine.domain.tool import Tool, ToolExecutionContext, ToolExecutionResult


class ToolExecutor:
    def __init__(
        self,
        python_runner: ToolRunnerPort,
        api_runner: ToolRunnerPort,
        policy_engine: ToolExecutionPolicy | None = None,
    ) -> None:
        self.python_runner = python_runner
        self.api_runner = api_runner
        self.policy_engine = policy_engine or PolicyEngine()

    def evaluate_policy(
        self,
        tool: Tool,
        arguments: dict[str, object],
        context: ToolExecutionContext,
    ) -> PolicyDecision:
        return self.policy_engine.evaluate_tool_execution(tool, arguments, context)

    async def execute(
        self,
        tool: Tool,
        arguments: dict[str, object],
        context: ToolExecutionContext,
        policy_decision: PolicyDecision | None = None,
    ) -> ToolExecutionResult:
        decision = policy_decision or self.evaluate_policy(tool, arguments, context)
        self._ensure_policy_allows(tool, decision)
        if tool.type == "python":
            return await self.python_runner.execute(tool, arguments, context)
        if tool.type == "api":
            return await self.api_runner.execute(tool, arguments, context)
        raise BklEngineError("TOOL_TYPE_UNSUPPORTED", f"Unsupported tool type: {tool.type}")

    def _ensure_policy_allows(self, tool: Tool, decision: PolicyDecision) -> None:
        if decision.effect == "allow":
            return
        if decision.effect == "ask":
            raise BklEngineError(
                "TOOL_REQUIRES_CONFIRMATION",
                f"Tool requires confirmation: {tool.id}",
                {"reason": decision.reason, "risk": decision.risk, **decision.details},
            )
        raise BklEngineError(
            "TOOL_POLICY_DENIED",
            f"Tool execution denied: {tool.id}",
            {"reason": decision.reason, "risk": decision.risk, **decision.details},
        )
