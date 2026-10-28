"""LLM-as-Judge 质量门控：对建议打 3 维度分（可执行 / 具体 / 忠实），用于质量门控。"""
from __future__ import annotations

import json

from . import llm

JUDGE_SYSTEM = (
    "你是严格的招聘建议评审员。对每条建议打 3 个维度分（1-5 整数）：\n"
    "- executability(e)：能否今天动手执行\n"
    "- specificity(s)：是否具体到动作 + 数字\n"
    "- truthfulness(t)：是否只基于原简历、不编造数据\n"
    "只输出严格 JSON：{\"scores\":[{\"i\":0,\"e\":4,\"s\":3,\"t\":5}],\"avg\":3.8,\"reason\":\"一句话理由\"}，"
    "不要输出任何多余文字。"
)


def judge(suggestions: list[str], resume: str) -> dict | None:
    """对建议列表打分，返回 {"scores": [...], "avg": float, "reason": str}；失败返回 None。"""
    if not llm.is_configured() or not suggestions:
        return None
    user = "简历：\n" + (resume or "")[:2000] + "\n\n建议：\n" + "\n".join(
        f"{i}. {s}" for i, s in enumerate(suggestions)
    )
    content = llm.chat(JUDGE_SYSTEM, user)
    if not content:
        return None
    content = content.strip()
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        data = json.loads(content[start:end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict) or "avg" not in data:
        return None
    return data
