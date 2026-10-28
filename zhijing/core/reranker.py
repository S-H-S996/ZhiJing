"""重排：用 CrossEncoder + BAAI/bge-reranker-base 对召回结果精排。

依赖按需加载：sentence-transformers 未安装时原样返回 docs[:top_k]。
模型首次加载会下载（约 1.1GB），故用 lru_cache(maxsize=1) 缓存。
"""
from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def _model():
    try:
        from sentence_transformers import CrossEncoder
    except ImportError:
        return None
    try:
        return CrossEncoder("BAAI/bge-reranker-base")
    except Exception:
        return None


def rerank(query: str, docs: list[dict], top_k: int = 3) -> list[dict]:
    """按 query 与文档的相关度重排，返回 top_k 条；依赖缺失时原样返回 docs[:top_k]。"""
    if not docs:
        return []
    model = _model()
    if model is None:
        return docs[:top_k]
    try:
        pairs = [(query, d["title"] + "：" + d["content"]) for d in docs]
        scores = model.predict(pairs)
        scored = sorted(zip(docs, scores), key=lambda x: -float(x[1]))
        out = []
        for d, s in scored[:top_k]:
            dd = dict(d)
            dd["score"] = round(float(s), 4)
            out.append(dd)
        return out
    except Exception:
        return docs[:top_k]
