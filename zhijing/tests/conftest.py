"""公共 fixture：岗位数据 + 样例简历文本。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# 确保 import core 可用（无论从哪个目录运行 pytest）
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def jds() -> list[dict]:
    path = Path(__file__).resolve().parent.parent / "data" / "jds.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def sample_resume() -> str:
    return (
        "张明轩，华南理工大学 人工智能专业 本科\n"
        "技能：Python、SQL、Git、LangChain、RAG、Prompt 工程、大模型 API 调用、工具调用 Function Calling\n"
        "项目经历：\n"
        "- 基于 LangChain + RAG 搭建知识库问答系统\n"
        "- 用 Streamlit 开发简历诊断 demo\n"
        "实习经历：2024.07-2024.09 在某公司实习\n"
        "自我评价：自学能力强，主动钻研，动手落地"
    )
