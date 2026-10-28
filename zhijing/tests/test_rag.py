"""rag.py 单元测试：关键词精确命中、auto 模式不报错。"""
from __future__ import annotations

from core.rag import retrieve, retrieve_keyword


def test_keyword_exact_match():
    docs = retrieve_keyword("langchain")
    assert any(d["id"] == "langchain" for d in docs)


def test_keyword_prompt_nonempty():
    docs = retrieve("prompt", mode="keyword")
    assert len(docs) > 0


def test_auto_no_exception():
    result = retrieve("xx 无意义查询 xx", mode="auto")
    assert isinstance(result, list)
