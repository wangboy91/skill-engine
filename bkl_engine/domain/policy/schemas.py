"""Policy domain schemas."""

from typing import Any, Literal

from pydantic import BaseModel, Field

PolicyEffect = Literal["allow", "ask", "deny"]


class PolicyDecision(BaseModel):
    effect: PolicyEffect = "allow"
    reason: str = ""
    risk: str = "none"
    details: dict[str, Any] = Field(default_factory=dict)
