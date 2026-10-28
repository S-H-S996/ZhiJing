"""Function Calling 工具层：定义「职镜」可被模型调用的工具 + 具体实现。

模型通过 tools schema 自主决定调用哪个工具、传什么参数；程序真正执行并回填结果。
这是「工具调用 / Function Calling」能力的落点，与 RAG 的确定性检索互补。
"""
from __future__ import annotations

from .matcher import match
from .parser import parse_resume

# OpenAI 工具 schema（Function Calling 用）
TOOL_SCHEMAS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "list_jobs",
            "description": "列出内置的全部目标岗位（ID、公司、岗位名、城市），用于回答“有哪些岗位可投”。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_job_detail",
            "description": "查看某个岗位的任职要求：简介 + 必需技能 + 加分技能。",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "岗位 ID，如 alibaba-ai-app、cvte-ai-app、wps-pm-ai"},
                },
                "required": ["job_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "diagnose",
            "description": "把当前简历与某个岗位做匹配，返回综合评分、维度分与能力缺口。",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_id": {"type": "string", "description": "岗位 ID，如 alibaba-ai-app、cvte-ai-app"},
                },
                "required": ["job_id"],
            },
        },
    },
]


def run_tool(name: str, args: dict, jds: list[dict], resume_text: str) -> str:
    """执行工具，返回回填给模型的文本结果。"""
    if name == "list_jobs":
        rows = [f"{j['id']}｜{j['company']}｜{j['title']}（{j['city']}）" for j in jds]
        return "内置岗位：\n" + "\n".join(rows)

    if name == "get_job_detail":
        job_id = (args or {}).get("job_id", "")
        jd = next((j for j in jds if j["id"] == job_id), None)
        if not jd:
            return f"未找到岗位 {job_id}，可用 list_jobs 查看全部岗位 ID。"
        return (
            f"{jd['title']}（{jd['company']} / {jd['city']}）\n"
            f"简介：{jd['summary']}\n"
            f"必需技能：{'、'.join(jd['skills']['required'])}\n"
            f"加分技能：{'、'.join(jd['skills']['preferred'])}"
        )

    if name == "diagnose":
        job_id = (args or {}).get("job_id", "")
        jd = next((j for j in jds if j["id"] == job_id), None)
        if not jd:
            return f"未找到岗位 {job_id}，可用 list_jobs 查看全部岗位 ID。"
        if not (resume_text or "").strip():
            return "当前没有简历文本，请先在左侧粘贴简历，再让我诊断。"
        profile = parse_resume(resume_text)
        result = match(profile, jd)
        dims = "、".join(f"{k} {v}" for k, v in result.dims.items())
        missing = "、".join(result.missing_skills) or "无"
        return f"综合匹配 {result.score}/100（{dims}）。缺失必需技能：{missing}。"

    return f"未知工具 {name}"
