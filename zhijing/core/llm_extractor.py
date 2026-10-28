"""LLM + Pydantic 简历抽取引擎：与规则引擎并存，供 A/B 对比。

用 pydantic 校验 LLM 输出的 JSON；未配置 LLM 或失败时静默返回 None，调用方回退规则引擎。
"""
from __future__ import annotations

import json

from pydantic import BaseModel, Field

from . import llm
from .parser import SKILL_LEXICON, SOFT_SKILL_LEXICON


class ExtractedResume(BaseModel):
    school: str = ""
    degree: str = ""
    major: str = ""
    skills: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    ai_related: bool = False


def extract_with_llm(text: str) -> ExtractedResume | None:
    """用 LLM 抽取简历结构化信息；未配置或失败返回 None（调用方回退规则）。"""
    if not llm.is_configured():
        return None

    skill_vocab = "、".join(SKILL_LEXICON.keys())
    soft_vocab = "、".join(SOFT_SKILL_LEXICON.keys())

    system = (
        "你是简历解析专家。从简历文本抽取结构化信息，只输出严格 JSON，不要多余文字。\n"
        f"技能(skills)只能从以下词表选：{skill_vocab}\n"
        f"软技能(soft_skills)只能从以下词表选：{soft_vocab}\n"
        "JSON 字段：school(学校,字符串)、degree(学历,字符串)、major(专业,字符串)、"
        "skills(技能数组)、soft_skills(软技能数组)、projects(项目经历数组)、ai_related(是否AI相关,布尔)。"
    )
    user = f"简历文本：\n{text[:3000]}"

    content = llm.rag_generate(system, user)
    if not content:
        return None

    # 提取 JSON：去代码块围栏，取第一个 { ... }
    content = content.strip()
    if content.startswith("```"):
        content = content.strip("`")
        if content.lower().startswith("json"):
            content = content[4:]
        content = content.strip()
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    content = content[start:end + 1]

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return None
    try:
        obj = ExtractedResume(**data)
    except Exception:
        return None

    # 只保留词表内的技能，保证与 matcher 口径一致
    obj.skills = [s for s in obj.skills if s in SKILL_LEXICON]
    obj.soft_skills = [s for s in obj.soft_skills if s in SOFT_SKILL_LEXICON]
    return obj
