import json
from pathlib import Path

from bkl_engine.engine import SkillEngine


def test_engine_persists_and_loads_catalog_entries(tmp_path: Path) -> None:
    config_path = _write_mock_config(tmp_path)
    catalog_path = tmp_path / ".bkl" / "catalog.json"

    engine = SkillEngine.load(config_path, catalog_path=catalog_path)
    tool = _run(engine.register_tool("examples/tools/subtitle_generate_srt"))
    skill = _run(engine.register_skill("examples/skills/talking_video"))

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    assert catalog["version"] == 1
    assert catalog["tools"]["subtitle_generate_srt"]["id"] == tool.id
    assert (
        catalog["tools"]["subtitle_generate_srt"]["path"]
        == "examples/tools/subtitle_generate_srt"
    )
    assert catalog["tools"]["subtitle_generate_srt"]["enabled"] is True
    assert catalog["skills"]["talking_video"]["id"] == skill.id
    assert catalog["skills"]["talking_video"]["path"] == "examples/skills/talking_video"
    assert catalog["skills"]["talking_video"]["enabled"] is True

    reloaded = SkillEngine.load(config_path, catalog_path=catalog_path)

    assert [registered_tool.id for registered_tool in reloaded.tool_registry.list_tools()] == [
        "subtitle_generate_srt"
    ]
    assert [registered_skill.id for registered_skill in reloaded.skill_registry.list_skills()] == [
        "talking_video"
    ]


def test_engine_can_disable_catalog_loading(tmp_path: Path) -> None:
    config_path = _write_mock_config(tmp_path)

    engine = SkillEngine.load(config_path, catalog_path=None)
    _run(engine.register_tool("examples/tools/subtitle_generate_srt"))

    assert not (tmp_path / ".bkl" / "catalog.json").exists()


def _write_mock_config(tmp_path: Path) -> Path:
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
    return config_path


def _run(coroutine):  # type: ignore[no-untyped-def]
    import asyncio

    return asyncio.run(coroutine)
