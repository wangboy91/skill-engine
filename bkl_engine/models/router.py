"""Model router primitives."""

import json
from collections import deque
from typing import Any, Protocol

from pydantic import BaseModel, Field

from bkl_engine.core.config import EngineConfig, ModelProfileConfig
from bkl_engine.core.errors import BklEngineError


class ToolCallRequest(BaseModel):
    id: str
    tool_id: str
    arguments: dict[str, object] = Field(default_factory=dict)


class ModelUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0


class ModelResponse(BaseModel):
    final_output: dict[str, object] | None = None
    tool_calls: list[ToolCallRequest] = Field(default_factory=list)
    usage: ModelUsage = Field(default_factory=ModelUsage)


class ModelProvider(Protocol):
    async def chat(
        self,
        profile: str,
        messages: list[dict[str, object]],
        tools: list[dict[str, object]],
    ) -> ModelResponse:
        ...


class MockModelProvider:
    def __init__(self, responses: list[ModelResponse] | None = None) -> None:
        self._responses = deque(responses or [])

    async def chat(
        self,
        profile: str,
        messages: list[dict[str, object]],
        tools: list[dict[str, object]],
    ) -> ModelResponse:
        del profile
        if self._responses:
            return self._responses.popleft()
        return self._default_response(messages, tools)

    def _default_response(
        self,
        messages: list[dict[str, object]],
        tools: list[dict[str, object]],
    ) -> ModelResponse:
        user_input = self._extract_user_input(messages)
        if not any(message.get("role") == "tool" for message in messages) and tools:
            return ModelResponse(
                tool_calls=[
                    ToolCallRequest(
                        id="call_mock_1",
                        tool_id=str(tools[0]["id"]),
                        arguments={
                            "text": str(
                                user_input.get("topic")
                                or user_input.get("text")
                                or "mock text"
                            ),
                            "audio_path": str(user_input.get("audio_path") or "audio.wav"),
                        },
                    )
                ]
            )

        observation = self._extract_last_tool_observation(messages)
        topic = str(user_input.get("topic") or "mock topic")
        return ModelResponse(
            final_output={
                "script": f"Mock script for {topic}",
                "titles": [f"{topic} 标题"],
                "subtitle_path": str(observation.get("srt_path", "")),
                "segments": observation.get("segments", []),
            }
        )

    def _extract_user_input(self, messages: list[dict[str, object]]) -> dict[str, Any]:
        for message in messages:
            if message.get("role") == "user":
                content = message.get("content")
                if isinstance(content, str):
                    try:
                        payload = json.loads(content)
                    except json.JSONDecodeError:
                        return {}
                    if isinstance(payload, dict) and isinstance(payload.get("input"), dict):
                        return dict(payload["input"])
        return {}

    def _extract_last_tool_observation(self, messages: list[dict[str, object]]) -> dict[str, Any]:
        for message in reversed(messages):
            if message.get("role") == "tool":
                content = message.get("content")
                if isinstance(content, str):
                    try:
                        payload = json.loads(content)
                    except json.JSONDecodeError:
                        return {}
                    if isinstance(payload, dict):
                        return payload
        return {}


class ModelRouter:
    def __init__(
        self,
        provider: ModelProvider | None = None,
        providers: dict[str, ModelProvider] | None = None,
        active_profile: str = "mock",
    ) -> None:
        self.providers = providers or {"mock": provider or MockModelProvider()}
        self.active_profile = active_profile
        self.provider = self.providers.get(active_profile) or next(iter(self.providers.values()))

    @classmethod
    def from_config(cls, config: EngineConfig) -> "ModelRouter":
        return cls(
            providers={
                profile_id: _build_provider(profile)
                for profile_id, profile in config.models.profiles.items()
                if profile.enabled
            },
            active_profile=config.models.active_profile,
        )

    async def chat(
        self,
        profile: str,
        messages: list[dict[str, object]],
        tools: list[dict[str, object]],
    ) -> ModelResponse:
        provider_id = profile if profile in self.providers else self.active_profile
        provider = self.providers.get(provider_id)
        if provider is None:
            raise BklEngineError(
                "CONFIG_INVALID",
                f"Model profile is not configured: {provider_id}",
            )
        return await provider.chat(provider_id, messages, tools)


def _build_provider(profile: ModelProfileConfig) -> ModelProvider:
    if profile.protocol == "mock":
        return MockModelProvider()
    if profile.protocol == "openai-compatible":
        from bkl_engine.models.providers.openai_compatible import OpenAICompatibleProvider

        return OpenAICompatibleProvider(profile)
    if profile.protocol == "anthropic":
        from bkl_engine.models.providers.anthropic import AnthropicProvider

        return AnthropicProvider(profile)
    raise BklEngineError("CONFIG_INVALID", f"Unsupported model protocol: {profile.protocol}")
