"""匹配评分：简历画像 vs 岗位 JD，输出总分 + 各维度分 + 缺口清单。

评分规则（总分 100）：
- 技能匹配 40 分：必需技能命中率 + 加分技能命中加成
- 项目/经验 35 分：项目数量、AI 相关度、实习经验
- 教育匹配 15 分：专业相关、学历匹配
- 软技能 10 分：软技能覆盖
"""
from __future__ import annotations

from dataclasses import dataclass

from .parser import ResumeProfile, has_internship


@dataclass
class MatchResult:
    score: int
    dims: dict[str, int]          # 各维度得分
    matched_skills: list[str]     # 已命中必需技能
    missing_skills: list[str]     # 缺口（必需技能未命中）
    matched_preferred: list[str]  # 命中的加分技能
    gaps: list[str]               # 人类可读的缺口描述
    matched_soft: list[str]
    missing_soft: list[str]


def _score_skills(profile: ResumeProfile, jd: dict) -> tuple[int, list[str], list[str], list[str]]:
    required = jd["skills"]["required"]
    preferred = jd["skills"]["preferred"]

    matched = [s for s in required if s in profile.skills]
    missing = [s for s in required if s not in profile.skills]
    matched_pref = [s for s in preferred if s in profile.skills]

    hit_rate = len(matched) / len(required) if required else 0.0
    # 必需技能 30 分 + 加分技能加成最高 10 分
    base = round(30 * hit_rate)
    pref_bonus = min(10, len(matched_pref) * 4)
    return min(40, base + pref_bonus), matched, missing, matched_pref


def _score_projects(profile: ResumeProfile, jd: dict) -> tuple[int, list[str]]:
    n_projects = len(profile.projects)
    min_projects = jd["experience"].get("min_projects", 2)
    gaps: list[str] = []

    # 项目数量 20 分：达标给满，不足按比例
    proj_score = round(20 * min(1.0, n_projects / max(1, min_projects)))
    if n_projects < min_projects:
        gaps.append(f"项目经历偏少（当前识别 {n_projects} 个，JD 要求 {min_projects} 个以上）")

    # AI 相关度 10 分
    _is_ai_jd = any(k in jd["title"] for k in ("AI", "大模型", "算法", "LLM", "Agent"))
    ai_score = 10 if profile.ai_related else 0
    if not profile.ai_related and _is_ai_jd:
        gaps.append("缺少与该岗位核心方向（AI/大模型/算法）直接相关的项目经历，这是最看重的匹配点")

    # 实习 5 分
    intern_score = 5 if jd["experience"].get("preferred_internship") and has_internship(profile.raw) else 0
    if jd["experience"].get("preferred_internship") and intern_score == 0:
        gaps.append("JD 偏好有实习经验，建议补充一段后端/AI 相关实习")

    return proj_score + ai_score + intern_score, gaps


def _score_education(profile: ResumeProfile, jd: dict) -> tuple[int, list[str]]:
    majors = jd["education"]["majors"]
    degree = jd["education"].get("degree", "")
    score = 0
    gaps: list[str] = []

    major_hit = any(m and m in (profile.major or "") for m in majors)
    if major_hit:
        score += 10
    elif profile.major:
        gaps.append(f"专业「{profile.major}」不在 JD 优先范围内，需在技能/项目上补足相关性")
    else:
        gaps.append("简历未识别到专业信息，建议在「教育背景」写明专业全称")

    if degree and degree in (profile.degree or ""):
        score += 5
    elif degree:
        if profile.degree:
            gaps.append(f"该岗要求「{degree}」学历（当前识别为「{profile.degree}」），需用论文/项目/竞赛成果支撑")
        else:
            gaps.append(f"学历未识别，建议补全（该岗要求「{degree}」）")

    return score, gaps


def _score_soft(profile: ResumeProfile, jd: dict) -> tuple[int, list[str], list[str]]:
    required = jd["soft_skills"]
    matched = [s for s in required if s in profile.soft_skills]
    missing = [s for s in required if s not in profile.soft_skills]
    score = round(10 * len(matched) / len(required)) if required else 10
    return score, matched, missing


def match(profile: ResumeProfile, jd: dict) -> MatchResult:
    skill_score, matched, missing, matched_pref = _score_skills(profile, jd)
    proj_score, proj_gaps = _score_projects(profile, jd)
    edu_score, edu_gaps = _score_education(profile, jd)
    soft_score, matched_soft, missing_soft = _score_soft(profile, jd)

    dims = {
        "技能匹配": skill_score,
        "项目/经验": proj_score,
        "教育背景": edu_score,
        "软技能": soft_score,
    }
    score = sum(dims.values())

    gaps = []
    for s in missing:
        gaps.append(f"缺必需技能「{s}」")
    gaps.extend(proj_gaps)
    gaps.extend(edu_gaps)
    for s in missing_soft:
        gaps.append(f"缺软技能体现「{s}」")

    return MatchResult(
        score=score,
        dims=dims,
        matched_skills=matched,
        missing_skills=missing,
        matched_preferred=matched_pref,
        gaps=gaps,
        matched_soft=matched_soft,
        missing_soft=missing_soft,
    )
