"""Anthropic-compatible model provider primitives."""

import json
import os
import re
from typing import Any

import httpx

from bkl_engine.core.config import ModelProfileConfig
from bkl_engine.core.errors import BklEngineError
from bkl_engine.models.router import ModelResponse, ModelUsage, ToolCallRequest


class AnthropicProvider:
    def __init__(
        self,
        config: ModelProfileConfig,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.config = config
        self.client = client or httpx.AsyncClient(timeout=config.timeout_seconds)

    async def chat(
        self,
        profile: str,
        messages: list[dict[str, object]],
        tools: list[dict[str, object]],
    ) -> ModelResponse:
        del profile
        if self.config.base_url is None:
            raise BklEngineError("CONFIG_INVALID", "Anthropic base_url is required")

        response = await self.client.post(
            f"{self.config.base_url.rstrip('/')}/v1/messages",
            headers=self._headers(),
            json={
                "model": self.config.model,
                "max_tokens": self.config.max_tokens,
                "messages": self._format_messages(messages),
                "tools": self._format_tools(tools),
            },
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise BklEngineError("MODEL_PROVIDER_ERROR", "Anthropic response is invalid")
        return self._parse_response(payload)

    def _headers(self) -> dict[str, str]:
        api_key = self._api_key()
        auth_header = self.config.auth_header or "x-api-key"
        auth_scheme = self.config.auth_scheme
        auth_value = f"{auth_scheme} {api_key}" if auth_scheme else api_key
        return {
            auth_header: auth_value,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

    def _api_key(self) -> str:
        if self.config.api_key_env is None:
            raise BklEngineError("CONFIG_INVALID", "api_key_env is required")
        api_key = os.environ.get(self.config.api_key_env)
        if api_key is None:
            raise BklEngineError(
                "SECRET_NOT_AVAILABLE",
                f"Missing model credential: {self.config.api_key_env}",
            )
        return api_key

    def _format_messages(self, messages: list[dict[str, object]]) -> list[dict[str, object]]:
        formatted: list[dict[str, object]] = []
        for message in messages:
            role = message.get("role")
            if role == "system":
                continue
            if role == "tool":
                formatted.append(
                    {
                        "role": "user",
                        "content": str(message.get("content", "")),
                    }
                )
                continue
            formatted.append(
                {
                    "role": "assistant" if role == "assistant" else "user",
                    "content": str(message.get("content", "")),
                }
            )
        return formatted

    def _format_tools(self, tools: list[dict[str, object]]) -> list[dict[str, object]]:
        return [
            {
                "name": tool["id"],
                "description": tool.get("description", ""),
                "input_schema": tool.get("input_schema", {"type": "object"}),
            }
            for tool in tools
        ]

    def _parse_response(self, payload: dict[str, Any]) -> ModelResponse:
        usage_payload = payload.get("usage", {})
        usage = ModelUsage()
        if isinstance(usage_payload, dict):
            usage = ModelUsage(
                input_tokens=int(usage_payload.get("input_tokens", 0)),
                output_tokens=int(usage_payload.get("output_tokens", 0)),
            )

        content = payload.get("content", [])
        tool_calls = self._parse_tool_calls(content)
        if tool_calls:
            return ModelResponse(tool_calls=tool_calls, usage=usage)

        return ModelResponse(final_output=self._parse_text_content(content), usage=usage)

    def _parse_tool_calls(self, content: object) -> list[ToolCallRequest]:
        if not isinstance(content, list):
            return []

        parsed: list[ToolCallRequest] = []
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            name = block.get("name")
            if not isinstance(name, str):
                continue
            raw_input = block.get("input", {})
            parsed.append(
                ToolCallRequest(
                    id=str(block.get("id", name)),
                    tool_id=name,
                    arguments=dict(raw_input) if isinstance(raw_input, dict) else {},
                )
            )
        return parsed

    def _parse_text_content(self, content: object) -> dict[str, object]:
        if not isinstance(content, list):
            return {}
        text = "".join(
            str(block.get("text", ""))
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
        text = self._strip_code_fence(text)
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {"text": text}
        if isinstance(parsed, dict):
            return dict(parsed)
        return {"text": text}

    def _strip_code_fence(self, content: str) -> str:
        match = re.match(r"\A```(?:json)?\s*(.*?)\s*```\Z", content.strip(), re.DOTALL)
        if match is None:
            return content
        return match.group(1).strip()
