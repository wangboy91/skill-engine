import json
from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from bkl_engine.api.main import create_app
from bkl_engine.cli.main import app as cli_app
from bkl_engine.engine import SkillEngine


def test_cli_tool_test_executes_python_tool() -> None:
    result = CliRunner().invoke(
        cli_app,
        [
            "tool",
            "test",
            "examples/tools/subtitle_generate_srt",
            "examples/inputs/subtitle_input.json",
            "--output",
            "json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["output"]["srt_path"] == "subtitle.srt"


def test_cli_skill_run_executes_default_mock_chain() -> None:
    result = CliRunner().invoke(
        cli_app,
        [
            "skill",
            "run",
            "talking_video",
            "examples/inputs/talking_video_input.json",
            "--skills-dir",
            "examples/skills",
            "--tools-dir",
            "examples/tools",
            "--output",
            "json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "succeeded"
    assert payload["output"]["subtitle_path"] == "subtitle.srt"


def test_cli_skill_run_can_load_config_file(tmp_path: Path) -> None:
    config_path = tmp_path / "bkl.yaml"
    config_path.write_text(
        "\n".join(
            [
                "models:",
                "  active_profile: mock",
                "  profiles:",
                "    mock:",
                "      protocol: mock",
                "      model: mock-tool-calling",
            ]
        ),
        encoding="utf-8",
    )
    result = CliRunner().invoke(
        cli_app,
        [
            "skill",
            "run",
            "talking_video",
            "examples/inputs/talking_video_input.json",
            "--skills-dir",
            "examples/skills",
            "--tools-dir",
            "examples/tools",
            "--config",
            str(config_path),
            "--output",
            "json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "succeeded"


def test_fastapi_registers_and_runs_skill(tmp_path: Path) -> None:
    engine = SkillEngine.create_for_testing(artifact_root=tmp_path)
    client = TestClient(create_app(engine))

    tool_response = client.post(
        "/tools/register",
        json={"path": "examples/tools/subtitle_generate_srt"},
    )
    assert tool_response.status_code == 200
    assert tool_response.json()["id"] == "subtitle_generate_srt"

    skill_response = client.post(
        "/skills/register",
        json={"path": "examples/skills/talking_video"},
    )
    assert skill_response.status_code == 200
    assert skill_response.json()["id"] == "talking_video"

    run_response = client.post(
        "/skills/talking_video/runs",
        json={
            "input": {
                "topic": "适合程序员的护眼台灯",
                "platform": "xiaohongshu",
                "duration_seconds": 60,
            },
            "context": {"user_id": "user_001"},
            "mode": "sync",
        },
    )
    assert run_response.status_code == 200
    run_payload = run_response.json()
    assert run_payload["status"] == "succeeded"

    trace_response = client.get(f"/runs/{run_payload['run_id']}/trace")
    assert trace_response.status_code == 200
    assert any(event["type"] == "tool_succeeded" for event in trace_response.json())


def test_cli_chat_once_runs_skill_from_natural_language() -> None:
    result = CliRunner().invoke(
        cli_app,
        [
            "chat",
            "--once",
            "帮我生成60秒小红书口播视频，主题是程序员护眼台灯",
            "--skills-dir",
            "examples/skills",
            "--tools-dir",
            "examples/tools",
            "--output",
            "json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "completed"
    assert payload["route_decision"]["skill_id"] == "talking_video"
    assert payload["output"]["subtitle_path"] == "subtitle.srt"


def test_fastapi_chat_messages_runs_registered_skill(tmp_path: Path) -> None:
    engine = SkillEngine.create_for_testing(artifact_root=tmp_path)
    client = TestClient(create_app(engine))

    client.post("/tools/register", json={"path": "examples/tools/subtitle_generate_srt"})
    client.post("/skills/register", json={"path": "examples/skills/talking_video"})

    response = client.post(
        "/chat/messages",
        json={
            "message": "帮我生成60秒小红书口播视频，主题是程序员护眼台灯",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["route_decision"]["skill_id"] == "talking_video"
    assert payload["run_ids"]
