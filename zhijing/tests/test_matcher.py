"""matcher.py 单元测试：分数上下界、维度分和、缺口生成。"""
from __future__ import annotations

from core.matcher import match
from core.parser import parse_resume


def test_full_match_high_score(jds, sample_resume):
    jd = next(j for j in jds if j["id"] == "alibaba-ai-app")
    r = match(parse_resume(sample_resume), jd)
    assert r.score >= 70


def test_empty_no_crash(jds):
    jd = jds[0]
    r = match(parse_resume(""), jd)
    assert r.score >= 0


def test_dim_sum_equals_total(jds, sample_resume):
    jd = next(j for j in jds if j["id"] == "alibaba-ai-app")
    r = match(parse_resume(sample_resume), jd)
    assert sum(r.dims.values()) == r.score


def test_missing_in_required(jds):
    jd = next(j for j in jds if j["id"] == "bytedance-rec-algo")
    r = match(parse_resume("某大学 英语专业 本科\n技能：无"), jd)
    required = set(jd["skills"]["required"])
    assert all(s in required for s in r.missing_skills)
