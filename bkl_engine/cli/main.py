"""Typer command line entrypoint."""

import asyncio
import json
from pathlib import Path

import typer
from rich.console import Console

from bkl_engine import __version__
from bkl_engine.core.schemas import ToolExecutionContext
from bkl_engine.engine import SkillEngine
from bkl_engine.tools.loader import load_tool
from bkl_engine.tools.python_tool import PythonToolRunner

app = typer.Typer(help="BKL Skill Engine command line interface.")
tool_app = typer.Typer(help="Tool commands.")
skill_app = typer.Typer(help="Skill commands.")
run_app = typer.Typer(help="Run commands.")
trace_app = typer.Typer(help="Trace commands.")
console = Console()


def version_callback(value: bool) -> None:
    if value:
        console.print(f"bkl-skill-engine {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit.",
    ),
) -> None:
    """Run BKL Skill Engine commands."""


@tool_app.command("register")
def tool_register(path: Path) -> None:
    tool = load_tool(path)
    console.print_json(data=tool.model_dump(mode="json"))


@tool_app.command("list")
def tool_list(tools_dir: Path = Path("examples/tools")) -> None:
    tools = [load_tool(path) for path in _iter_package_dirs(tools_dir, "tool.yaml")]
    console.print_json(data=[tool.model_dump(mode="json") for tool in tools])


@tool_app.command("test")
def tool_test(path: Path, input_json: Path, output: str = "table") -> None:
    tool = load_tool(path)
    payload = _read_json(input_json)
    result = asyncio.run(
        PythonToolRunner().execute(
            tool,
            payload,
            _tool_context_for_cli(),
        )
    )
    if output == "json":
        typer.echo(json.dumps(result.model_dump(mode="json"), ensure_ascii=False))
    else:
        console.print(result.model_dump(mode="json"))


@skill_app.command("register")
def skill_register(path: Path) -> None:
    engine = SkillEngine.load()
    skill = asyncio.run(engine.register_skill(path))
    console.print_json(data=skill.model_dump(mode="json"))


@skill_app.command("list")
def skill_list(skills_dir: Path = Path("examples/skills")) -> None:
    engine = SkillEngine.load()
    for path in _iter_skill_dirs(skills_dir):
        asyncio.run(engine.register_skill(path))
    console.print_json(
        data=[skill.model_dump(mode="json") for skill in engine.skill_registry.list_skills()]
    )


@skill_app.command("run")
def skill_run(
    skill_id: str,
    input_json: Path,
    skills_dir: Path = Path("examples/skills"),
    tools_dir: Path = Path("examples/tools"),
    config: Path | None = None,
    output: str = "table",
) -> None:
    engine = SkillEngine.load(config) if config is not None else SkillEngine.create_for_testing()
    _register_all(engine, tools_dir=tools_dir, skills_dir=skills_dir)
    result = asyncio.run(engine.run_skill(skill_id, _read_json(input_json)))
    if output == "json":
        typer.echo(json.dumps(result.model_dump(mode="json"), ensure_ascii=False))
    else:
        console.print(result.model_dump(mode="json"))


@run_app.command("list")
def run_list() -> None:
    engine = SkillEngine.load()
    console.print_json(data=[run.model_dump(mode="json") for run in engine.run_store.list_runs()])


@trace_app.command("show")
def trace_show(run_id: str) -> None:
    engine = SkillEngine.load()
    console.print_json(
        data=[event.model_dump(mode="json") for event in engine.trace_store.list_events(run_id)]
    )


def _register_all(engine: SkillEngine, tools_dir: Path, skills_dir: Path) -> None:
    for path in _iter_package_dirs(tools_dir, "tool.yaml"):
        asyncio.run(engine.register_tool(path))
    for path in _iter_skill_dirs(skills_dir):
        asyncio.run(engine.register_skill(path))


def _iter_package_dirs(root: Path, marker: str) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path.parent for path in root.rglob(marker))


def _iter_skill_dirs(root: Path) -> list[Path]:
    return _iter_package_dirs(root, "SKILL.md")


def _read_json(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise typer.BadParameter(f"JSON input must be an object: {path}")
    return data


def _tool_context_for_cli() -> ToolExecutionContext:
    return ToolExecutionContext(
        run_id="cli_run",
        tool_call_id="cli_tool_call",
        artifact_dir=Path("data/artifacts/cli_run/cli_tool_call"),
    )


app.add_typer(tool_app, name="tool")
app.add_typer(skill_app, name="skill")
app.add_typer(run_app, name="run")
app.add_typer(trace_app, name="trace")


if __name__ == "__main__":
    app()
