"""Model router primitives."""

import json
from collections import deque
from typing import Any, Protocol

from bkl_engine.domain.model import ModelResponse, ModelUsage, ToolCallRequest
from bkl_engine.domain.errors import BklEngineError
from bkl_engine.infrastructure.config.engine_config import EngineConfig, ModelProfileConfig

__all__ = [
    "MockModelProvider",
    "ModelProvider",
    "ModelResponse",
    "ModelRouter",
    "ModelUsage",
    "ToolCallRequest",
]


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
            tool_id = str(tools[0]["id"])
            if tool_id == "wangbudong_write_prompt_pack":
                return ModelResponse(
                    tool_calls=[
                        ToolCallRequest(
                            id="call_mock_1",
                            tool_id=tool_id,
                            arguments=self._wangbudong_tool_arguments(user_input),
                        )
                    ]
                )
            return ModelResponse(
                tool_calls=[
                    ToolCallRequest(
                        id="call_mock_1",
                        tool_id=tool_id,
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
        if "output_dir" in observation and "files" in observation:
            return ModelResponse(
                final_output=self._wangbudong_final_output(user_input, observation)
            )
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

    def _wangbudong_tool_arguments(self, user_input: dict[str, Any]) -> dict[str, object]:
        raw_materials = user_input.get("materials")
        if isinstance(raw_materials, list):
            materials = [str(item) for item in raw_materials]
        else:
            materials = [str(raw_materials or "家庭常见材料")]
        return {
            "experiment_title": str(user_input.get("experiment_title") or "小实验"),
            "materials": materials,
            "target_phenomenon": str(user_input.get("target_phenomenon") or "观察明显变化"),
            "age_range": str(user_input.get("age_range") or "3-8岁"),
            "content_lane": str(user_input.get("content_lane") or "趣味引流"),
            "include_operations_card": bool(user_input.get("include_operations_card", False)),
        }

    def _wangbudong_final_output(
        self,
        user_input: dict[str, Any],
        observation: dict[str, Any],
    ) -> dict[str, object]:
        raw_files = observation.get("files", [])
        files = [str(item) for item in raw_files] if isinstance(raw_files, list) else []
        raw_safety_notes = observation.get("safety_notes", [])
        safety_notes = (
            [str(item) for item in raw_safety_notes]
            if isinstance(raw_safety_notes, list)
            else []
        )
        return {
            "experiment_title": str(
                observation.get("experiment_title")
                or user_input.get("experiment_title")
                or "小实验"
            ),
            "output_dir": str(observation.get("output_dir") or ""),
            "files": files,
            "feasibility_summary": str(observation.get("feasibility_summary") or ""),
            "cover_prompt": str(observation.get("cover_prompt") or ""),
            "step_prompt_count": int(observation.get("step_prompt_count") or 0),
            "xiaohongshu_copy": str(observation.get("xiaohongshu_copy") or ""),
            "safety_notes": safety_notes,
        }


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
        from bkl_engine.infrastructure.model_gateway.providers.openai_compatible import (
            OpenAICompatibleProvider,
        )

        return OpenAICompatibleProvider(profile)
    if profile.protocol == "anthropic":
        from bkl_engine.infrastructure.model_gateway.providers.anthropic import AnthropicProvider

        return AnthropicProvider(profile)
    raise BklEngineError("CONFIG_INVALID", f"Unsupported model protocol: {profile.protocol}")
