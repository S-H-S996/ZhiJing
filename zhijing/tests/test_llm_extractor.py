"""llm_extractor.py + optimizer.py 单元测试：模型定义 + 无 LLM 静默回退。"""
from __future__ import annotations

from core import llm
from core.llm_extractor import ExtractedResume, extract_with_llm
from core.optimizer import _jd_text, optimize_resume


def test_extracted_resume_model():
    e = ExtractedResume(school="X大学", skills=["Python"], ai_related=True)
    assert e.school == "X大学"
    assert e.skills == ["Python"]
    assert e.ai_related is True


def test_extract_without_llm(monkeypatch):
    monkeypatch.setattr(llm, "is_configured", lambda: False)
    assert extract_with_llm("简历文本") is None


def test_jd_text(jds):
    t = _jd_text(jds[0])
    assert "岗位" in t and "必需技能" in t


def test_optimize_without_llm(monkeypatch):
    monkeypatch.setattr(llm, "is_configured", lambda: False)
    jd = {"title": "x", "company": "y", "city": "z"}
    assert optimize_resume("简历", jd) is None
