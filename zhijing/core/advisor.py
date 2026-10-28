"""建议生成：基于匹配结果产出 3 条可执行、具体的修改建议。

原则：不说“提升能力”，要说“把 X 改成 Y，量化到 Z”。
"""
from __future__ import annotations

from .matcher import MatchResult
from .parser import ResumeProfile, has_internship


def _suggestion_for_skill(skill: str) -> str:
    """把缺的必需技能转成一条可执行的补法。"""
    mapping = {
        "Prompt 工程": "补一个可展示的 Prompt 工程实践：在项目 README 里附上你设计的评测集与 3 版 Prompt 的对比，注明“准确率从 X% 提到 Y%”",
        "大模型 API 调用": "写一个最小 demo 用大模型 API 打通一个真实场景（如简历解析），并记录 token 成本与平均耗时",
        "FastAPI": "把某个脚本项目包一层 FastAPI 接口，附一个可用 curl 调用，体现后端能力",
        "SQL": "给项目加一个 SQLite/MySQL 存储层，写明表结构设计与一条关键查询",
        "Git": "把项目推到 GitHub，保持分阶段 commit，README 写清运行方式与效果截图",
        "Linux": "把 demo 部署到一台 Linux 服务器/云主机，记录部署命令与踩坑点",
        "RESTful API": "为项目设计并实现一组 RESTful 接口，标注请求/响应格式与鉴权方式",
        "Redis": "在项目里用 Redis 做缓存/会话，记录命中率或响应时间提升",
    }
    return mapping.get(skill, f"补齐技能「{skill}」：在一个真实小项目里实际用它，并留下可被追问的实现细节")


def _suggestion_for_project() -> str:
    return (
        "把项目描述从“参与/负责”改写为“独立完成 X 模块 + 可量化结果”："
        "例如“独立实现简历解析模块，将人工 40 分钟的诊断压缩到 90 秒，27 位同学试用、建议采纳率 78%”"
    )


def _suggestion_for_experience() -> str:
    return "补一段实习/实战：优先投 AI 应用方向日常实习（2027.3 可到岗），实习中主动承接“解析—打分—建议”这类闭环需求，作为第二维度证据"


def generate_suggestions(profile: ResumeProfile, result: MatchResult, jd: dict) -> list[str]:
    suggestions: list[str] = []

    # 1) 优先补最缺的必需技能（按 JD 顺序取第一个缺失）
    if result.missing_skills:
        suggestions.append(_suggestion_for_skill(result.missing_skills[0]))

    # 2) 项目描述可量化 / 项目相关度
    if not profile.ai_related and ("AI" in jd["title"] or "大模型" in jd["title"]):
        suggestions.append(_suggestion_for_project())
    elif len(profile.projects) < jd["experience"].get("min_projects", 2):
        suggestions.append(_suggestion_for_project())

    # 3) 实习经验
    if jd["experience"].get("preferred_internship") and not has_internship(profile.raw):
        suggestions.append(_suggestion_for_experience())

    # 保证凑够 3 条：缺哪补哪
    if len(suggestions) < 2 and result.missing_skills and len(result.missing_skills) > 1:
        suggestions.append(_suggestion_for_skill(result.missing_skills[1]))
    if len(suggestions) < 3:
        suggestions.append(_suggestion_for_project())
    if len(suggestions) < 3:
        suggestions.append("写一段 2 行的「自我评价」，用 1 个数字证明你的学习/交付能力，去掉空话形容词")

    # 去重后取前 3 条
    seen, out = set(), []
    for s in suggestions:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out[:3]
