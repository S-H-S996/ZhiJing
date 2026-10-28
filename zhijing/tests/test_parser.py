"""parser.py 单元测试：技能 / 软技能 / 教育 / 项目 / 实习解析。"""
from __future__ import annotations

from core.parser import (
    extract_education,
    extract_projects,
    extract_skills,
    extract_soft_skills,
    has_internship,
    parse_resume,
)


def test_standard_skills():
    s = extract_skills("熟悉 Python、SQL、Git")
    assert {"Python", "SQL", "Git"} <= s


def test_alias_recognition():
    s = extract_skills("会 js 和 mysql")
    assert "JavaScript" in s
    assert "SQL" in s
    assert "MySQL" in s


def test_no_internship():
    assert has_internship("实习经历：无") is False


def test_has_internship():
    assert has_internship("2024.07-2024.09 在某公司实习") is True


def test_education_full():
    edu = extract_education("华南理工大学 计算机科学与技术 本科")
    assert edu["school"] == "华南理工大学"
    assert edu["degree"] == "本科"
    assert "计算机" in edu["major"]


def test_empty_no_crash():
    p = parse_resume("")
    assert p is not None
    assert p.skills == set()
    assert p.school == ""


def test_projects_detection():
    projects = extract_projects("项目经历：\n- 基于 Python 开发爬虫\n- 负责后端接口开发")
    assert any("开发" in p for p in projects)


def test_soft_skills_detection():
    soft = extract_soft_skills("沟通表达好，自驱力强，善于定位问题")
    assert {"沟通表达", "自驱力", "问题定位"} <= soft
