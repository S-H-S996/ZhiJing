"""简历优化：根据目标岗位 JD 重写简历，突出岗位匹配度。

四条原则：
1. 先提炼 JD 核心关键词、能力要求、筛选重点
2. 按 JD 重写经历，突出匹配度
3. 不编造经历/数据，缺失的量化数据用【待补充数据】标出
4. 语言专业、简洁、有结果感，避免空话和 AI 味
"""
from __future__ import annotations

from . import llm


def _jd_text(jd: dict) -> str:
    parts = [
        f"岗位：{jd['title']}（{jd['company']} / {jd['city']}）",
        f"职责简介：{jd['summary']}",
        f"必需技能：{'、'.join(jd['skills']['required'])}",
        f"加分技能：{'、'.join(jd['skills']['preferred'])}",
        f"软技能：{'、'.join(jd['soft_skills'])}",
        f"经验要求：{jd['experience'].get('min_projects', 1)} 个以上相关项目",
    ]
    return "\n".join(parts)


def optimize_resume(resume_text: str, jd: dict) -> str | None:
    """返回优化后的简历（Markdown）。未配置 LLM 或失败时返回 None。"""
    if not llm.is_configured():
        return None
    system = (
        "你是一位资深简历优化专家，擅长让简历与目标岗位高度匹配。"
        "严格遵守：不编造任何经历、项目或数据；原简历没有的量化结果，用【待补充数据】标出，绝不虚构数字；"
        "不要照搬 JD 里的届别、公司名、岗位头衔等身份信息，只优化用户简历中已有的真实信息；"
        "语言专业、简洁、有结果感（STAR 原则），避免空话、套话和 AI 味。"
    )
    user = (
        "请根据下面这个岗位 JD 优化我的简历。\n\n"
        f"【目标岗位 JD】\n{_jd_text(jd)}\n\n"
        f"【我的简历】\n{resume_text}\n\n"
        "按以下结构输出（Markdown）：\n"
        "## 一、JD 拆解\n"
        "- 核心关键词：…\n"
        "- 能力要求：…\n"
        "- 筛选重点：…\n\n"
        "## 二、优化后的简历\n"
        "（只基于原简历已有内容重写，突出岗位匹配度；不编造经历，缺失数据标【待补充数据】；语言专业有结果感）"
    )
    return llm.chat(system, user)
