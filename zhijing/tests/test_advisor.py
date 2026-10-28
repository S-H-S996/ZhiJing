"""advisor.py 单元测试：建议生成（规则兜底）。"""
from __future__ import annotations

from core.advisor import generate_suggestions
from core.matcher import match
from core.parser import parse_resume


def test_generate_suggestions_nonempty(jds, sample_resume):
    jd = jds[0]
    profile = parse_resume(sample_resume)
    result = match(profile, jd)
    suggestions = generate_suggestions(profile, result, jd)
    assert isinstance(suggestions, list)
    assert 1 <= len(suggestions) <= 3


def test_generate_suggestions_with_missing_skills(jds):
    jd = next(j for j in jds if j["id"] == "bytedance-rec-algo")
    profile = parse_resume("某大学 英语专业 本科")
    result = match(profile, jd)
    suggestions = generate_suggestions(profile, result, jd)
    assert isinstance(suggestions, list)
    assert len(suggestions) > 0
