"""Bounded Agent state machine that orchestrates SkillEngine calls."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from bkl_engine.application.agent.actions import ActionRegistry
from bkl_engine.application.agent.confirmation import ConfirmationPolicy
from bkl_engine.application.agent.input_resolver import InputResolver
from bkl_engine.application.agent.router import SkillRouter
from bkl_engine.application.ports import AgentRuntimePort
from bkl_engine.domain.agent.scene_mapping import SceneDefinition, SceneMapping
from bkl_engine.domain.agent.schemas import ActionResult, AgentResponse, RouteDecision


class AgentLoop:
    def __init__(
        self,
        engine: AgentRuntimePort,
        scene_mapping: SceneMapping | None = None,
        router: SkillRouter | None = None,
        input_resolver: InputResolver | None = None,
        action_registry: ActionRegistry | None = None,
        confirmation_policy: ConfirmationPolicy | None = None,
        auto_run_threshold: float = 0.85,
        max_agent_steps: int = 6,
    ) -> None:
        self.engine = engine
        self.scene_mapping = scene_mapping or SceneMapping()
        self.router = router or SkillRouter(engine.skill_registry, auto_run_threshold)
        self.input_resolver = input_resolver or InputResolver()
        self.actions = action_registry or ActionRegistry(engine)
        self.confirmation_policy = confirmation_policy or ConfirmationPolicy()
        self.auto_run_threshold = auto_run_threshold
        self.max_agent_steps = max_agent_steps

    async def handle_message(
        self,
        message: str,
        *,
        session_id: str | None = None,
        scene_id: str | None = None,
        skill_id: str | None = None,
        input_data: dict[str, Any] | None = None,
        confirm: bool = False,
    ) -> AgentResponse:
        del confirm
        resolved_session_id = session_id or f"sess_{uuid4().hex}"
        turn_id = f"turn_{uuid4().hex}"
        route, scene = self._route(message, scene_id=scene_id, skill_id=skill_id)

        if route.intent != "run_skill" or route.skill_id is None:
            return AgentResponse(
                session_id=resolved_session_id,
                turn_id=turn_id,
                status="needs_input",
                message="无法确定要运行哪个 Skill，请指定 skill_id 或说明业务场景。",
                route_decision=route,
            )

        if route.confidence < self.auto_run_threshold and scene_id is None and skill_id is None:
            return AgentResponse(
                session_id=resolved_session_id,
                turn_id=turn_id,
                status="requires_confirmation",
                message=f"可能要运行 {route.skill_id}，但置信度较低，请确认。",
                requires_confirmation=True,
                route_decision=route,
            )

        skill = self.engine.skill_registry.get_skill(route.skill_id)
        merged_input_draft = dict(route.input_draft)
        if input_data:
            merged_input_draft.update(input_data)
        resolution = self.input_resolver.resolve(
            skill,
            message,
            input_draft=merged_input_draft,
            defaults=scene.defaults if scene is not None else None,
        )
        route = route.model_copy(
            update={
                "input_draft": resolution.input,
                "missing_fields": resolution.missing_fields,
            }
        )
        if resolution.missing_fields:
            return AgentResponse(
                session_id=resolved_session_id,
                turn_id=turn_id,
                status="needs_input",
                message="缺少必填输入字段：" + ", ".join(resolution.missing_fields),
                route_decision=route,
                missing_fields=resolution.missing_fields,
            )

        run = await self.actions.run_skill(skill.id, resolution.input)
        return AgentResponse(
            session_id=resolved_session_id,
            turn_id=turn_id,
            status="completed",
            message=f"已运行 Skill: {skill.id}",
            route_decision=route,
            action_results=[
                ActionResult(
                    action="run_skill",
                    status="succeeded",
                    run_id=run.run_id,
                    output=run.output,
                )
            ],
            run_ids=[run.run_id],
            output=run.output,
            artifacts=[artifact.model_dump(mode="json") for artifact in run.artifacts],
        )

    def _route(
        self,
        message: str,
        *,
        scene_id: str | None,
        skill_id: str | None,
    ) -> tuple[RouteDecision, SceneDefinition | None]:
        if skill_id is not None:
            return self.router.route(message, explicit_skill_id=skill_id), None

        if scene_id is not None:
            scene = self.scene_mapping.get(scene_id)
            if scene is None:
                return (
                    RouteDecision(
                        intent="unknown",
                        confidence=0,
                        reason=f"scene not found: {scene_id}",
                        scene_id=scene_id,
                    ),
                    None,
                )
            return (
                RouteDecision(
                    intent="run_skill",
                    skill_id=scene.skill_id,
                    confidence=1,
                    reason="scene mapping",
                    scene_id=scene_id,
                ),
                scene,
            )

        return self.router.route(message), None
