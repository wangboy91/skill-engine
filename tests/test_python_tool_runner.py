import asyncio
from pathlib import Path

import pytest

from bkl_engine.core.schemas import ToolExecutionContext
from bkl_engine.tools.loader import load_tool
from bkl_engine.tools.python_tool import PythonToolRunner, ToolExecutionError


def test_python_tool_runner_executes_tool_with_json_stdio(tmp_path: Path) -> None:
    tool = load_tool("examples/tools/subtitle_generate_srt")
    result = asyncio.run(
        PythonToolRunner().execute(
            tool,
            {"text": "hello", "audio_path": "audio.wav"},
            ToolExecutionContext(
                run_id="run_test",
                tool_call_id="call_test",
                artifact_dir=tmp_path,
            ),
        )
    )

    assert result.output["srt_path"] == "subtitle.srt"
    assert result.output["segments"][0]["text"] == "hello"
    assert result.stderr == ""


def test_python_tool_runner_rejects_invalid_input_schema(tmp_path: Path) -> None:
    tool = load_tool("examples/tools/subtitle_generate_srt")

    with pytest.raises(ToolExecutionError, match="TOOL_INPUT_SCHEMA_INVALID"):
        asyncio.run(
            PythonToolRunner().execute(
                tool,
                {"text": "missing audio path"},
                ToolExecutionContext(
                    run_id="run_test",
                    tool_call_id="call_test",
                    artifact_dir=tmp_path,
                ),
            )
        )


def test_python_tool_runner_reports_timeout(tmp_path: Path) -> None:
    tool_dir = tmp_path / "slow_tool"
    tool_dir.mkdir()
    (tool_dir / "tool.yaml").write_text(
        "\n".join(
            [
                "id: slow_tool",
                "type: python",
                "name: Slow Tool",
                "description: Sleeps longer than allowed",
                "entry: main.py",
                "input_schema: input.schema.json",
                "output_schema: output.schema.json",
                "runtime:",
                "  timeout_seconds: 1",
            ]
        ),
        encoding="utf-8",
    )
    (tool_dir / "input.schema.json").write_text(
        '{"type": "object", "additionalProperties": false}',
        encoding="utf-8",
    )
    (tool_dir / "output.schema.json").write_text(
        '{"type": "object", "additionalProperties": false}',
        encoding="utf-8",
    )
    (tool_dir / "main.py").write_text(
        "import time\n"
        "time.sleep(5)\n"
        "print('{}')\n",
        encoding="utf-8",
    )

    with pytest.raises(ToolExecutionError, match="PYTHON_TOOL_TIMEOUT"):
        asyncio.run(
            PythonToolRunner().execute(
                load_tool(tool_dir),
                {},
                ToolExecutionContext(
                    run_id="run_test",
                    tool_call_id="call_test",
                    artifact_dir=tmp_path / "artifacts",
                ),
            )
        )
