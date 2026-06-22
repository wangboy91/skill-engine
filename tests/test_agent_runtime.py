import asyncio
from pathlib import Path

from bkl_engine.application.agent.state_machine import AgentLoop
from bkl_engine.domain.agent import SceneDefinition, SceneMapping
from bkl_engine.engine import SkillEngine


def test_agent_loop_runs_skill_from_scene_mapping_with_defaults(tmp_path: Path) -> None:
    engine = SkillEngine.create_for_testing(artifact_root=tmp_path)
    asyncio.run(engine.register_tool("examples/tools/subtitle_generate_srt"))
    asyncio.run(engine.register_skill("examples/skills/talking_video"))
    loop = AgentLoop(
        engine,
        scene_mapping=SceneMapping(
            {
                "talking_video_writer": SceneDefinition(
                    scene_id="talking_video_writer",
                    skill_id="talking_video",
                    title="口播视频生成",
                    defaults={"platform": "xiaohongshu", "duration_seconds": 60},
                )
            }
        ),
    )

    response = asyncio.run(
        loop.handle_message("主题是程序员护眼台灯", scene_id="talking_video_writer")
    )

    assert response.status == "completed"
    assert response.route_decision is not None
    assert response.route_decision.skill_id == "talking_video"
    assert response.run_ids
    assert response.output is not None
    assert response.output["subtitle_path"] == "subtitle.srt"


def test_agent_loop_routes_natural_language_to_registered_skill(tmp_path: Path) -> None:
    engine = SkillEngine.create_for_testing(artifact_root=tmp_path)
    asyncio.run(engine.register_tool("examples/tools/wangbudong_write_prompt_pack"))
    asyncio.run(engine.register_skill("examples/skills/wangbudong_experiment"))
    loop = AgentLoop(engine)

    response = asyncio.run(
        loop.handle_message(
            "帮我做一个王不懂小实验，实验标题是彩虹牛奶，"
            "材料有牛奶、色素、洗洁精，现象是色素扩散成彩虹纹路"
        )
    )

    assert response.status == "completed"
    assert response.route_decision is not None
    assert response.route_decision.skill_id == "wangbudong_experiment"
    assert response.run_ids
    assert response.output is not None
    assert response.output["experiment_title"] == "彩虹牛奶"


def test_agent_loop_asks_for_missing_required_skill_input(tmp_path: Path) -> None:
    engine = SkillEngine.create_for_testing(artifact_root=tmp_path)
    asyncio.run(engine.register_tool("examples/tools/wangbudong_write_prompt_pack"))
    asyncio.run(engine.register_skill("examples/skills/wangbudong_experiment"))
    loop = AgentLoop(engine)

    response = asyncio.run(
        loop.handle_message("帮我做一个王不懂小实验，实验标题是彩虹牛奶")
    )

    assert response.status == "needs_input"
    assert response.run_ids == []
    assert response.missing_fields == ["materials", "target_phenomenon"]
    assert "materials" in response.message
