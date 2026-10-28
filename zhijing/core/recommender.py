"""岗位推荐：用向量相似度给简历推荐 top-k 岗位。

依赖 core.embeddings（sentence-transformers / bge 模型）；依赖缺失时返回空列表，主流程不受影响。
"""
from __future__ import annotations

from . import embeddings


def _jd_text(jd: dict) -> str:
    required = " ".join((jd.get("skills") or {}).get("required", []))
    return " ".join([jd.get("title", ""), jd.get("summary", ""), required])


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def recommend_jobs(resume_text: str, jds: list[dict], top_k: int = 3) -> list[tuple[dict, float]]:
    """返回 [(jd, 相似度)]，按余弦相似度降序取 top_k；依赖缺失/失败返回空列表。"""
    if not resume_text or not jds:
        return []
    texts = [resume_text] + [_jd_text(j) for j in jds]
    vecs = embeddings.embed(texts)
    if not vecs or len(vecs) != len(texts):
        return []
    resume_vec = vecs[0]
    scored = [(jd, _cosine(resume_vec, v)) for jd, v in zip(jds, vecs[1:])]
    scored.sort(key=lambda x: -x[1])
    return scored[:top_k]
