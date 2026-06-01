import asyncio
from pathlib import Path

import pytest

from bkl_engine.engine import SkillEngine
from bkl_engine.models.router import MockModelProvider, ModelResponse, ToolCallRequest
from bkl_engine.skills.runtime import SkillRuntimeError


def test_skill_engine_runs_mock_skill_with_python_tool(tmp_path: Path) -> None:
    engine = SkillEngine.create_for_testing(artifact_root=tmp_path)
    asyncio.run(engine.register_tool("examples/tools/subtitle_generate_srt"))
    asyncio.run(engine.register_skill("examples/skills/talking_video"))

    result = asyncio.run(
        engine.run_skill(
            "talking_video",
            {
                "topic": "适合程序员的护眼台灯",
                "platform": "xiaohongshu",
                "duration_seconds": 60,
            },
        )
    )

    assert result.status == "succeeded"
    assert result.output is not None
    assert result.output["script"].startswith("Mock script")
    assert result.output["subtitle_path"] == "subtitle.srt"
    assert result.run_id
    assert result.trace_summary["tool_called"] == 1
    assert result.trace_summary["tool_succeeded"] == 1
    assert any(
        event.type == "tool_succeeded"
        for event in engine.trace_store.list_events(result.run_id)
    )


def test_skill_runtime_rejects_tool_not_allowed(tmp_path: Path) -> None:
    engine = SkillEngine.create_for_testing(
        artifact_root=tmp_path,
        model_provider=MockModelProvider(
            [
                ModelResponse(
                    tool_calls=[
                        ToolCallRequest(
                            id="call_bad",
                            tool_id="not_allowed",
                            arguments={},
                        )
                    ]
                )
            ]
        ),
    )
    asyncio.run(engine.register_tool("examples/tools/subtitle_generate_srt"))
    asyncio.run(engine.register_skill("examples/skills/talking_video"))

    with pytest.raises(SkillRuntimeError, match="TOOL_NOT_ALLOWED"):
        asyncio.run(
            engine.run_skill(
                "talking_video",
                {
                    "topic": "适合程序员的护眼台灯",
                    "platform": "xiaohongshu",
                    "duration_seconds": 60,
                },
            )
        )


def test_skill_runtime_stops_at_max_iterations(tmp_path: Path) -> None:
    engine = SkillEngine.create_for_testing(
        artifact_root=tmp_path,
        model_provider=MockModelProvider(
            [
                ModelResponse(tool_calls=[]),
                ModelResponse(tool_calls=[]),
                ModelResponse(tool_calls=[]),
            ]
        ),
    )
    asyncio.run(engine.register_tool("examples/tools/subtitle_generate_srt"))
    asyncio.run(engine.register_skill("examples/skills/talking_video"))

    with pytest.raises(SkillRuntimeError, match="MAX_ITERATIONS_EXCEEDED"):
        asyncio.run(
            engine.run_skill(
                "talking_video",
                {
                    "topic": "适合程序员的护眼台灯",
                    "platform": "xiaohongshu",
                    "duration_seconds": 60,
                },
            )
        )


def test_skill_runtime_appends_assistant_tool_call_message(tmp_path: Path) -> None:
    provider = RecordingToolCallProvider()
    engine = SkillEngine.create_for_testing(artifact_root=tmp_path, model_provider=provider)
    asyncio.run(engine.register_tool("examples/tools/subtitle_generate_srt"))
    asyncio.run(engine.register_skill("examples/skills/talking_video"))

    result = asyncio.run(
        engine.run_skill(
            "talking_video",
            {
                "topic": "适合程序员的护眼台灯",
                "platform": "xiaohongshu",
                "duration_seconds": 60,
            },
        )
    )

    assert result.status == "succeeded"
    second_call_messages = provider.calls[1]
    assert second_call_messages[-2]["role"] == "assistant"
    assert second_call_messages[-2]["tool_calls"][0]["function"]["name"] == "subtitle_generate_srt"
    assert second_call_messages[-1]["role"] == "tool"


class RecordingToolCallProvider:
    def __init__(self) -> None:
        self.calls: list[list[dict[str, object]]] = []

    async def chat(
        self,
        profile: str,
        messages: list[dict[str, object]],
        tools: list[dict[str, object]],
    ) -> ModelResponse:
        del profile, tools
        self.calls.append([dict(message) for message in messages])
        if len(self.calls) == 1:
            return ModelResponse(
                tool_calls=[
                    ToolCallRequest(
                        id="call_recorded",
                        tool_id="subtitle_generate_srt",
                        arguments={"text": "hello", "audio_path": "audio.wav"},
                    )
                ]
            )
        return ModelResponse(
            final_output={
                "script": "Mock script",
                "titles": ["title"],
                "subtitle_path": "subtitle.srt",
                "segments": [],
            }
        )
