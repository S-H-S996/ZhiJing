"""向量化：用 sentence-transformers + BAAI/bge-small-zh-v1.5 把文本转成 512 维向量。

依赖按需加载：sentence-transformers 未安装时 embed() 返回空 list，调用方回退关键词检索。
模型首次加载会下载（约 100MB），故用 lru_cache(maxsize=1) 缓存。
"""
from __future__ import annotations

from functools import lru_cache

EMBED_DIM = 512


@lru_cache(maxsize=1)
def _model():
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        return None
    try:
        return SentenceTransformer("BAAI/bge-small-zh-v1.5")
    except Exception:
        return None


def embed(texts: list[str]) -> list[list[float]]:
    """把文本列表转成向量列表；依赖缺失或失败返回空 list。"""
    if not texts:
        return []
    model = _model()
    if model is None:
        return []
    try:
        return model.encode(list(texts), normalize_embeddings=True).tolist()
    except Exception:
        return []
