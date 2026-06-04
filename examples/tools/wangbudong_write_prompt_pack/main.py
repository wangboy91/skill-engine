"""Write a Wangbudong experiment prompt pack to the artifact directory."""

import json
import os
from pathlib import Path
from typing import Any


def main() -> None:
    payload = json.loads(input())
    artifact_dir = Path(os.environ["BKL_ARTIFACT_DIR"])
    artifact_dir.mkdir(parents=True, exist_ok=True)

    title = str(payload["experiment_title"])
    materials = [str(item) for item in payload["materials"]]
    phenomenon = str(payload["target_phenomenon"])
    age_range = str(payload.get("age_range") or "3-8岁")
    content_lane = str(payload.get("content_lane") or "趣味引流")
    include_operations_card = bool(payload.get("include_operations_card", False))

    feasibility_summary = _feasibility_summary(title, materials, phenomenon)
    cover_prompt = _cover_prompt(title, materials, phenomenon, age_range, content_lane)
    step_prompts = _step_prompts(title, materials, phenomenon)
    xiaohongshu_copy = _xiaohongshu_copy(title, materials, phenomenon, age_range)
    safety_notes = _safety_notes(materials)

    files: dict[str, str] = {
        "00-实验拆解.md": _breakdown(
            title,
            materials,
            phenomenon,
            age_range,
            content_lane,
            feasibility_summary,
            safety_notes,
        ),
        "01-首图提示词.md": cover_prompt,
        "02-分步骤提示词.md": step_prompts,
        "03-小红书文案.md": xiaohongshu_copy,
    }
    if include_operations_card:
        files["04-发布运营卡.md"] = _operations_card(title, content_lane, age_range)

    for filename, content in files.items():
        (artifact_dir / filename).write_text(content, encoding="utf-8")

    result: dict[str, Any] = {
        "experiment_title": title,
        "output_dir": str(artifact_dir),
        "files": list(files),
        "feasibility_summary": feasibility_summary,
        "cover_prompt": cover_prompt,
        "step_prompt_count": step_prompts.count("## 第"),
        "xiaohongshu_copy": xiaohongshu_copy,
        "safety_notes": safety_notes,
    }
    print(json.dumps(result, ensure_ascii=False))


def _feasibility_summary(title: str, materials: list[str], phenomenon: str) -> str:
    material_text = "、".join(materials)
    return (
        f"{title}采用家庭低风险材料：{material_text}。目标现象是{phenomenon}。"
        "材料能支撑观察型亲子科学实验，需保持装置真实、步骤简短、现象可见。"
    )


def _breakdown(
    title: str,
    materials: list[str],
    phenomenon: str,
    age_range: str,
    content_lane: str,
    feasibility_summary: str,
    safety_notes: list[str],
) -> str:
    safety_text = (
        "\n".join(f"- {note}" for note in safety_notes)
        if safety_notes
        else "- 低风险实验，建议家长陪同观察。"
    )
    return "\n".join(
        [
            f"# {title} 实验拆解",
            "",
            "## 实验定位",
            f"- 内容栏目：{content_lane}",
            f"- 适合年龄：{age_range}",
            "- 难度：低",
            "- 成本：低",
            "",
            "## 实验合理性论证",
            f"- 目标现象：{phenomenon}",
            "- 动力来源：材料接触、液体表面变化或可观察的物理/化学过程。",
            "- 传动/约束结构：使用真实容器和材料，不添加虚构管道、机关或魔法效果。",
            f"- 原材料是否足够：{feasibility_summary}",
            "- 需要补充或修正：如材料不完整，只补充最低风险的家庭常见材料。",
            "- 最终采用装置：桌面真实实验装置，家长辅助，孩子观察。",
            "- 排除的错误版本：不画成危险加热、密封反应、夸张爆炸或不真实机关。",
            "",
            "## 材料",
            *[f"- {material}" for material in materials],
            "",
            "## 步骤",
            "1. 摆好材料，确认容器稳定。",
            "2. 按顺序加入材料，保留孩子能观察的关键动作。",
            "3. 引导孩子描述看到的变化。",
            "4. 记录成功条件和容易失败的变量。",
            "",
            "## 观察现象",
            f"- {phenomenon}",
            "",
            "## 原理解释",
            "- 用儿童能理解的语言解释可见变化，不把隐形作用画成真实零件。",
            "",
            "## 常见翻车点",
            "- 材料比例过多或过少：先少量测试。",
            "- 动作太快：关键步骤要慢慢做。",
            "- 画面不真实：提示词里明确真实装置和错误排除。",
            "",
            "## 真实装置校验",
            "- 真实摆放：材料在桌面或浅盘中，容器开口方向清楚。",
            f"- 真实现象：{phenomenon}",
            "- 不要画成：密封爆炸、火焰、虚构管道、魔法特效。",
            "- 准确原理：只解释观察到的真实变化。",
            "",
            "## 安全和制作提示",
            safety_text,
            "",
        ]
    )


def _cover_prompt(
    title: str,
    materials: list[str],
    phenomenon: str,
    age_range: str,
    content_lane: str,
) -> str:
    material_text = "、".join(materials)
    return "\n".join(
        [
            "# 首图提示词",
            "",
            "## 画面目标",
            f"小红书首图，突出「{title}」的最终可见效果，适合{age_range}亲子科学启蒙。",
            "",
            "## 生成提示词",
            (
                "1086x1448竖版中文亲子科学启蒙信息图，温暖白底，手绘水彩贴纸风，"
                "顶部左上角小号亮宝蓝品牌贴纸「王不懂的小实验」，主标题"
                f"「{title}」，黄色丝带副标题「家里材料看见科学变化」，"
                f"主画面展示{material_text}和{phenomenon}，画面标签包含「{content_lane}」"
                "「低成本」「可复做」。"
            ),
            (
                "配色要求：品牌贴纸和标签使用高饱和亮宝蓝，暖白底，极浅清透水蓝面板，"
                "柠檬黄丝带，软粉观察框；主色取自真实材料，现象强调色使用清爽亮色，"
                "不要灰蓝、牛仔蓝、雾霾蓝。"
            ),
            (
                "科学真实性要求：只展示真实可操作的桌面实验装置，材料摆放和观察结果要一致，"
                "不要添加虚构管道、密封爆炸、火焰或魔法特效。"
            ),
            "",
            "## 负面提示词",
            "不要英文文字，不要二维码，不要外部水印，不要第三方logo，不要错别字，不要文字重叠，不要危险儿童操作，不要灰暗低饱和配色。",
            "",
        ]
    )


def _step_prompts(title: str, materials: list[str], phenomenon: str) -> str:
    material_text = "、".join(materials)
    pages = [
        ("准备材料", f"展示{material_text}，每个材料有清晰中文标签。"),
        ("开始操作", "展示成人手部进行关键动作，孩子只在旁边观察。"),
        ("观察变化", f"突出{phenomenon}，用箭头和短标签标注变化方向。"),
        ("为什么会这样", "用三格图解释原理，语言短、可读、适合亲子讲解。"),
        ("翻车排查", "展示三个常见失败原因：比例不对、动作太快、材料摆放不稳。"),
    ]
    blocks = []
    for index, (page_title, target) in enumerate(pages, start=1):
        blocks.extend(
            [
                f"## 第 {index} 张：{page_title}",
                "",
                "### 画面目标",
                target,
                "",
                "### 生成提示词",
                (
                    f"1086x1448竖版中文亲子科学启蒙信息图，「王不懂的小实验」小号亮宝蓝左上角贴纸，"
                    f"页面标题「{title}｜{page_title}」，{target}"
                ),
                (
                    "配色要求：亮宝蓝标签、暖白底、浅水蓝分区、柠檬黄提示条、软粉观察框，"
                    "材料保持真实颜色，整体清爽不拥挤。"
                ),
                (
                    f"科学真实性要求：本页仍然使用同一套{title}真实装置，现象必须是{phenomenon}，"
                    "不要切换成其他实验版本。"
                ),
                "",
                "### 负面提示词",
                "不要英文文字，不要二维码，不要外部水印，不要错别字，不要虚构机关，不要危险儿童操作。",
                "",
            ]
        )
    return "\n".join(blocks)


def _xiaohongshu_copy(
    title: str,
    materials: list[str],
    phenomenon: str,
    age_range: str,
) -> str:
    material_text = "、".join(materials)
    return "\n".join(
        [
            f"✨{title}｜{age_range}在家也能观察的小实验",
            "",
            f"今天用{material_text}，带孩子看见：{phenomenon}。",
            "",
            "🧪玩法很简单：",
            "① 先把材料摆在桌面上，让孩子猜会发生什么",
            "② 家长慢慢完成关键动作",
            "③ 让孩子描述看到的颜色、方向和速度变化",
            "",
            "👀可以问孩子：",
            "如果材料多一点，会不会变化更明显？",
            "如果动作慢一点，结果会不会不同？",
            "",
            "💬想要步骤卡，评论「步骤卡」",
            "",
            "#亲子科学 #幼儿科学启蒙 #在家做实验 #低成本实验 #王不懂的小实验",
            "",
        ]
    )


def _operations_card(title: str, content_lane: str, age_range: str) -> str:
    return "\n".join(
        [
            f"# {title} 发布运营卡",
            "",
            f"- 栏目：{content_lane}",
            f"- 年龄：{age_range}",
            "- 封面策略：结果优先，材料低成本标签辅助。",
            "- 评论关键词：步骤卡",
            "- 复盘指标：封面点击、收藏、关键词评论。",
            "",
        ]
    )


def _safety_notes(materials: list[str]) -> list[str]:
    risky_keywords = {"火", "酒精", "玻璃", "刀", "热水", "打孔"}
    if any(any(keyword in material for keyword in risky_keywords) for material in materials):
        return ["涉及潜在风险材料，必须由成人操作危险步骤。"]
    return []


if __name__ == "__main__":
    main()
