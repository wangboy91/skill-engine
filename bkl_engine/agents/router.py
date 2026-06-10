"""Skill routing for natural-language Agent requests."""

from bkl_engine.agents.schemas import RouteDecision
from bkl_engine.skills.registry import InMemorySkillRegistry


class SkillRouter:
    def __init__(
        self,
        skill_registry: InMemorySkillRegistry,
        auto_run_threshold: float = 0.85,
    ) -> None:
        self.skill_registry = skill_registry
        self.auto_run_threshold = auto_run_threshold

    def route(self, message: str, explicit_skill_id: str | None = None) -> RouteDecision:
        if explicit_skill_id is not None:
            return RouteDecision(
                intent="run_skill",
                skill_id=explicit_skill_id,
                confidence=1,
                reason="explicit skill_id",
            )

        skills = self.skill_registry.list_skills()
        if not skills:
            return RouteDecision(intent="unknown", confidence=0, reason="no registered skills")

        scored = sorted(
            (
                (self._score_skill(message, skill.id, skill.name, skill.description), skill.id)
                for skill in skills
            ),
            reverse=True,
        )
        best_score, best_skill_id = scored[0]
        if best_score < 0.6:
            return RouteDecision(
                intent="unknown",
                confidence=best_score,
                reason="no skill matched the request",
            )

        if len(scored) > 1 and best_score - scored[1][0] < 0.12:
            best_score = min(best_score, 0.74)

        return RouteDecision(
            intent="run_skill",
            skill_id=best_skill_id,
            confidence=best_score,
            reason="matched request against registered Skill metadata",
        )

    def _score_skill(
        self,
        message: str,
        skill_id: str,
        skill_name: str,
        description: str,
    ) -> float:
        text = message.casefold()
        metadata = f"{skill_id} {skill_name} {description}".casefold()
        score = 0.0

        if skill_id.casefold() in text or skill_name.casefold() in text:
            score += 0.9

        keyword_groups = {
            "wangbudong_experiment": ["王不懂", "小实验", "实验", "亲子", "科学"],
            "talking_video": ["口播", "视频", "小红书", "抖音", "b站", "微博", "秒"],
        }
        keywords = keyword_groups.get(skill_id, [])
        matched_keywords = [keyword for keyword in keywords if keyword.casefold() in text]
        if matched_keywords:
            score = max(score, 0.65)
            score += len(matched_keywords) * 0.1

        for token in ("video", "experiment", "skill", "tool"):
            if token in text and token in metadata:
                score += 0.08

        if score == 0 and len(self.skill_registry.list_skills()) == 1:
            score = 0.62

        return min(score, 0.96)
