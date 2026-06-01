"""Local Skill package loader."""

import json
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from bkl_engine.core.errors import BklEngineError
from bkl_engine.core.schemas import JsonObject, Skill, SkillLimits, SkillModelConfig


class SkillLoadError(BklEngineError):
    """Raised when a Skill package cannot be loaded or validated."""

    def __init__(self, message: str) -> None:
        super().__init__("SKILL_LOAD_ERROR", message)


def load_skill(path: str | Path) -> Skill:
    skill_dir = _resolve_skill_dir(Path(path))
    standard_skill_path = skill_dir / "SKILL.md"
    if not standard_skill_path.exists():
        raise SkillLoadError(f"Skill package must contain SKILL.md: {skill_dir}")
    return _load_standard_skill(skill_dir, standard_skill_path)


def _load_standard_skill(skill_dir: Path, skill_md_path: Path) -> Skill:
    frontmatter, body = _read_markdown_with_frontmatter(skill_md_path)
    _ensure_required_fields(
        frontmatter,
        required=("name", "description", "bkl"),
        source=skill_md_path,
    )

    bkl_config = frontmatter["bkl"]
    if not isinstance(bkl_config, dict):
        raise SkillLoadError(f"bkl frontmatter field must be an object: {skill_md_path}")

    raw_skill: JsonObject = {
        "id": bkl_config.get("id", frontmatter["name"]),
        "name": frontmatter["name"],
        "version": bkl_config.get("version", "0.1.0"),
        "description": frontmatter["description"],
        "input_schema": bkl_config.get("input_schema"),
        "output_schema": bkl_config.get("output_schema"),
        "prompt": body.strip(),
        "model": bkl_config.get("model", {}),
        "limits": bkl_config.get("limits", {}),
        "tools": bkl_config.get("tools", {}),
    }
    _ensure_required_fields(
        raw_skill,
        required=("id", "name", "version", "description", "input_schema", "output_schema"),
        source=skill_md_path,
    )

    raw_skill["input_schema"] = _load_schema(skill_dir, raw_skill["input_schema"], "input_schema")
    raw_skill["output_schema"] = _load_schema(
        skill_dir,
        raw_skill["output_schema"],
        "output_schema",
    )
    return _build_skill(raw_skill, skill_dir, skill_md_path)


def _build_skill(raw_skill: JsonObject, skill_dir: Path, source: Path) -> Skill:
    allowed_tools = _load_allowed_tools(raw_skill)
    if not allowed_tools:
        raise SkillLoadError(f"Skill {raw_skill['id']} must declare at least one allowed tool")

    try:
        return Skill.model_validate(
            {
                **raw_skill,
                "allowed_tools": allowed_tools,
                "model": SkillModelConfig.model_validate(raw_skill.get("model", {})),
                "limits": SkillLimits.model_validate(raw_skill.get("limits", {})),
                "package_path": skill_dir,
            }
        )
    except ValidationError as exc:
        raise SkillLoadError(f"Invalid skill definition in {source}: {exc}") from exc


def _resolve_skill_dir(path: Path) -> Path:
    if path.is_dir():
        return path
    if path.name == "SKILL.md":
        return path.parent
    raise SkillLoadError(f"Skill path must be a directory or SKILL.md file: {path}")


def _read_markdown_with_frontmatter(path: Path) -> tuple[JsonObject, str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---\n?(.*)\Z", text, re.DOTALL)
    if match is None:
        raise SkillLoadError(f"SKILL.md must start with YAML frontmatter: {path}")

    try:
        frontmatter = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        raise SkillLoadError(f"Invalid YAML frontmatter in {path}: {exc}") from exc

    if not isinstance(frontmatter, dict):
        raise SkillLoadError(f"SKILL.md frontmatter must be a YAML object: {path}")

    body = match.group(2)
    if not body.strip():
        raise SkillLoadError(f"SKILL.md body must contain Markdown instructions: {path}")

    return dict(frontmatter), body


def _ensure_required_fields(raw_skill: JsonObject, required: tuple[str, ...], source: Path) -> None:
    missing = [field for field in required if field not in raw_skill]
    if missing:
        raise SkillLoadError(f"Missing required field(s) in {source}: {', '.join(missing)}")


def _load_schema(skill_dir: Path, schema_ref: Any, field_name: str) -> JsonObject:
    if isinstance(schema_ref, dict):
        return dict(schema_ref)
    if not isinstance(schema_ref, str):
        raise SkillLoadError(f"{field_name} must be a JSON object or schema file path")
    schema_path = skill_dir / schema_ref
    if not schema_path.exists():
        raise SkillLoadError(f"{field_name} file not found: {schema_path}")
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SkillLoadError(f"Invalid JSON schema in {schema_path}: {exc}") from exc
    if not isinstance(schema, dict):
        raise SkillLoadError(f"{field_name} must resolve to a JSON object: {schema_path}")
    return dict(schema)


def _load_allowed_tools(raw_skill: JsonObject) -> list[str]:
    tools = raw_skill.get("tools", {})
    if not isinstance(tools, dict):
        raise SkillLoadError("tools must be a YAML object")
    allowed = tools.get("allow", [])
    if not isinstance(allowed, list) or not all(isinstance(tool_id, str) for tool_id in allowed):
        raise SkillLoadError("tools.allow must be a list of tool ids")
    return allowed
