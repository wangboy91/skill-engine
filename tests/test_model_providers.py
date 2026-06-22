import asyncio
import json

import httpx

from bkl_engine.infrastructure.config.engine_config import ModelProfileConfig
from bkl_engine.infrastructure.model_gateway.providers.anthropic import AnthropicProvider
from bkl_engine.infrastructure.model_gateway.providers.openai_compatible import (
    OpenAICompatibleProvider,
)


def test_openai_compatible_provider_posts_chat_completions(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("MODEL_KEY", "secret")

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://example.com/v2/chat/completions"
        assert request.headers["authorization"] == "Bearer secret"
        body = json.loads(request.content)
        assert body["model"] == "astron-code-latest"
        assert body["messages"][0]["role"] == "user"
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": '{"ok": true}'}}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 2},
            },
        )

    provider = OpenAICompatibleProvider(
        ModelProfileConfig(
            protocol="openai-compatible",
            base_url="https://example.com/v2",
            api_key_env="MODEL_KEY",
            model="astron-code-latest",
        ),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    response = asyncio.run(provider.chat("active", [{"role": "user", "content": "ping"}], []))

    assert response.final_output == {"ok": True}
    assert response.usage.input_tokens == 3
    assert response.usage.output_tokens == 2


def test_openai_compatible_provider_parses_fenced_json(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("MODEL_KEY", "secret")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": '```json\n{"ok": true}\n```'}}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 2},
            },
        )

    provider = OpenAICompatibleProvider(
        ModelProfileConfig(
            protocol="openai-compatible",
            base_url="https://example.com/v2",
            api_key_env="MODEL_KEY",
            model="astron-code-latest",
        ),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    response = asyncio.run(provider.chat("active", [{"role": "user", "content": "ping"}], []))

    assert response.final_output == {"ok": True}


def test_anthropic_provider_posts_messages(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("MODEL_KEY", "secret")

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://example.com/anthropic/v1/messages"
        assert request.headers["x-api-key"] == "secret"
        assert request.headers["anthropic-version"] == "2023-06-01"
        body = json.loads(request.content)
        assert body["model"] == "astron-code-latest"
        assert body["messages"][0]["role"] == "user"
        return httpx.Response(
            200,
            json={
                "content": [{"type": "text", "text": '{"ok": true}'}],
                "usage": {"input_tokens": 4, "output_tokens": 2},
            },
        )

    provider = AnthropicProvider(
        ModelProfileConfig(
            protocol="anthropic",
            base_url="https://example.com/anthropic",
            api_key_env="MODEL_KEY",
            model="astron-code-latest",
        ),
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    response = asyncio.run(provider.chat("active", [{"role": "user", "content": "ping"}], []))

    assert response.final_output == {"ok": True}
    assert response.usage.input_tokens == 4
    assert response.usage.output_tokens == 2
