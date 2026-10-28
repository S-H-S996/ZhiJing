"""tools.py 单元测试：Function Calling 工具执行。"""
from __future__ import annotations

from core.tools import TOOL_SCHEMAS, run_tool


def test_schemas_exist():
    names = {t["function"]["name"] for t in TOOL_SCHEMAS}
    assert {"list_jobs", "get_job_detail", "diagnose"} <= names


def test_list_jobs(jds):
    r = run_tool("list_jobs", {}, jds, "")
    assert "alibaba-ai-app" in r


def test_get_job_detail(jds):
    r = run_tool("get_job_detail", {"job_id": "cvte-ai-app"}, jds, "")
    assert "应用软件开发" in r


def test_diagnose(jds, sample_resume):
    r = run_tool("diagnose", {"job_id": "alibaba-ai-app"}, jds, sample_resume)
    assert "综合匹配" in r


def test_diagnose_missing_resume(jds):
    r = run_tool("diagnose", {"job_id": "alibaba-ai-app"}, jds, "")
    assert "请先" in r


def test_unknown_tool(jds):
    r = run_tool("nonexistent", {}, jds, "")
    assert "未知工具" in r
