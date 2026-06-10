"""Typer command line entrypoint."""

import asyncio
import json
from pathlib import Path
from typing import Annotated, Any

import typer
import uvicorn
import yaml
from rich.console import Console

from bkl_engine import __version__
from bkl_engine.agents.loop import AgentLoop
from bkl_engine.core.schemas import ToolExecutionContext
from bkl_engine.engine import SkillEngine
from bkl_engine.skills.loader import load_skill
from bkl_engine.tools.loader import load_tool
from bkl_engine.tools.python_tool import PythonToolRunner

app = typer.Typer(help="BKL Skill Engine command line interface.")
tool_app = typer.Typer(help="Tool commands.")
skill_app = typer.Typer(help="Skill commands.")
run_app = typer.Typer(help="Run commands.")
trace_app = typer.Typer(help="Trace commands.")
console = Console()
MODEL_PROTOCOLS = {"mock", "openai-compatible", "anthropic"}
DEFAULT_CONFIG_PATH = Path("bkl.yaml")
DEFAULT_CATALOG_PATH = Path(".bkl/catalog.json")


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


@app.command("init")
def init_config(
    protocol: Annotated[str, typer.Option(help="Model protocol to configure.")] = "mock",
    profile: Annotated[str, typer.Option(help="Model profile name.")] = "mock",
    base_url: Annotated[str | None, typer.Option(help="Provider base URL.")] = None,
    model: Annotated[str | None, typer.Option(help="Model name.")] = None,
    api_key: Annotated[str | None, typer.Option(help="API key written only to .env.")] = None,
    api_key_env: Annotated[
        str | None,
        typer.Option(help="Environment variable name for API key."),
    ] = None,
    config: Annotated[Path, typer.Option(help="Config file to write.")] = DEFAULT_CONFIG_PATH,
    env_file: Annotated[Path | None, typer.Option(help=".env file to write API key into.")] = None,
    force: Annotated[bool, typer.Option(help="Overwrite an existing config file.")] = False,
    output: Annotated[str, typer.Option(help="Output format: table or json.")] = "table",
) -> None:
    """Initialize model configuration for the engine."""

    if protocol not in MODEL_PROTOCOLS:
        raise typer.BadParameter(f"protocol must be one of: {', '.join(sorted(MODEL_PROTOCOLS))}")
    if config.exists() and not force:
        raise typer.BadParameter(f"Config already exists: {config}. Use --force to overwrite.")

    resolved_model = model or ("mock-tool-calling" if protocol == "mock" else None)
    if resolved_model is None:
        raise typer.BadParameter("--model is required for non-mock protocols")
    if protocol != "mock" and not base_url:
        raise typer.BadParameter("--base-url is required for non-mock protocols")

    resolved_api_key_env = api_key_env or _default_api_key_env(protocol)
    profile_config: dict[str, Any] = {
        "protocol": protocol,
        "model": resolved_model,
    }
    if base_url is not None:
        profile_config["base_url"] = base_url
    if resolved_api_key_env is not None:
        profile_config["api_key_env"] = resolved_api_key_env

    config_data = {
        "models": {
            "active_profile": profile,
            "profiles": {
                profile: profile_config,
            },
        }
    }
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(
        yaml.safe_dump(config_data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    resolved_env_file = env_file or config.parent / ".env"
    if api_key and resolved_api_key_env:
        _write_dotenv_value(resolved_env_file, resolved_api_key_env, api_key)

    summary = {
        "config": str(config),
        "env_file": str(resolved_env_file),
        "active_profile": profile,
        "protocol": protocol,
        "model": resolved_model,
        "api_key_env": resolved_api_key_env,
    }
    if output == "json":
        typer.echo(json.dumps(summary, ensure_ascii=False))
    else:
        console.print(summary)


@app.command("serve")
def serve(
    host: Annotated[str, typer.Option(help="Host to bind.")] = "127.0.0.1",
    port: Annotated[int, typer.Option(help="Port to bind.")] = 8000,
    config: Annotated[Path | None, typer.Option(help="Config file to load.")] = None,
    catalog: Annotated[Path | None, typer.Option(help="Catalog file to load.")] = (
        DEFAULT_CATALOG_PATH
    ),
    reload: Annotated[bool, typer.Option(help="Enable uvicorn reload.")] = False,
) -> None:
    """Start the FastAPI service."""

    from bkl_engine.api.main import create_app

    engine = SkillEngine.load(config, catalog_path=catalog)
    api = create_app(engine)
    uvicorn.run(api, host=host, port=port, reload=reload)


@app.command("chat")
def chat(
    once: Annotated[
        str | None,
        typer.Option(help="Run one natural-language Agent turn and exit."),
    ] = None,
    scene: Annotated[str | None, typer.Option(help="Scene id to route deterministically.")] = None,
    skill: Annotated[str | None, typer.Option(help="Explicit skill id to run.")] = None,
    input_json: Annotated[
        Path | None,
        typer.Option("--input", help="Optional JSON input draft."),
    ] = None,
    skills_dir: Annotated[Path, typer.Option(help="Directory containing Skill packages.")] = (
        Path("examples/skills")
    ),
    tools_dir: Annotated[Path, typer.Option(help="Directory containing Tool packages.")] = (
        Path("examples/tools")
    ),
    config: Annotated[Path | None, typer.Option(help="Config file to load.")] = None,
    output: Annotated[str, typer.Option(help="Output format: table or json.")] = "table",
) -> None:
    """Run the Agent orchestration layer."""

    engine = SkillEngine.load(config) if config is not None else SkillEngine.create_for_testing()
    _register_all(engine, tools_dir=tools_dir, skills_dir=skills_dir)
    loop = AgentLoop(engine)
    input_data = _read_json(input_json) if input_json is not None else None

    if once is not None:
        response = asyncio.run(
            loop.handle_message(
                once,
                scene_id=scene,
                skill_id=skill,
                input_data=input_data,
            )
        )
        if output == "json":
            typer.echo(json.dumps(response.model_dump(mode="json"), ensure_ascii=False))
        else:
            console.print(response.model_dump(mode="json"))
        return

    console.print("bkl chat interactive mode. Type 'exit' to quit.")
    while True:
        message = typer.prompt("bkl")
        if message.strip().lower() in {"exit", "quit"}:
            return
        response = asyncio.run(loop.handle_message(message, scene_id=scene, skill_id=skill))
        console.print(response.model_dump(mode="json"))


@tool_app.command("register")
def tool_register(
    path: Path,
    config: Annotated[Path | None, typer.Option(help="Config file to load.")] = None,
    catalog: Annotated[Path | None, typer.Option(help="Catalog file to write.")] = (
        DEFAULT_CATALOG_PATH
    ),
) -> None:
    engine = SkillEngine.load(config, catalog_path=catalog)
    tool = asyncio.run(engine.register_tool(path))
    console.print_json(data=tool.model_dump(mode="json"))


@tool_app.command("list")
def tool_list(
    tools_dir: Path = Path("examples/tools"),
    config: Annotated[Path | None, typer.Option(help="Config file to load.")] = None,
    catalog: Annotated[Path | None, typer.Option(help="Catalog file to read.")] = (
        DEFAULT_CATALOG_PATH
    ),
) -> None:
    if catalog is not None and catalog.exists():
        engine = SkillEngine.load(config, catalog_path=catalog)
        tools = engine.tool_registry.list_tools()
    else:
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
def skill_register(
    path: Path,
    config: Annotated[Path | None, typer.Option(help="Config file to load.")] = None,
    catalog: Annotated[Path | None, typer.Option(help="Catalog file to write.")] = (
        DEFAULT_CATALOG_PATH
    ),
) -> None:
    engine = SkillEngine.load(config, catalog_path=catalog)
    skill = asyncio.run(engine.register_skill(path))
    console.print_json(data=skill.model_dump(mode="json"))


@skill_app.command("list")
def skill_list(
    skills_dir: Path = Path("examples/skills"),
    config: Annotated[Path | None, typer.Option(help="Config file to load.")] = None,
    catalog: Annotated[Path | None, typer.Option(help="Catalog file to read.")] = (
        DEFAULT_CATALOG_PATH
    ),
) -> None:
    if catalog is not None and catalog.exists():
        engine = SkillEngine.load(config, catalog_path=catalog)
        skills = engine.skill_registry.list_skills()
    else:
        skills = [load_skill(path) for path in _iter_skill_dirs(skills_dir)]
    console.print_json(
        data=[skill.model_dump(mode="json") for skill in skills]
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


def _default_api_key_env(protocol: str) -> str | None:
    if protocol == "openai-compatible":
        return "OPENAI_AUTH_TOKEN"
    if protocol == "anthropic":
        return "ANTHROPIC_AUTH_TOKEN"
    return None


def _write_dotenv_value(path: Path, key: str, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    assignment = f"{key}={value}"
    for index, line in enumerate(lines):
        if line.split("=", 1)[0].strip() == key:
            lines[index] = assignment
            break
    else:
        lines.append(assignment)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
