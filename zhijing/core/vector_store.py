"""向量库：用 chromadb.PersistentClient 持久化存储「补法知识库」的向量。

依赖按需加载：chromadb 未安装时 search() 返回空 list，调用方回退关键词检索。
首次调用若 collection 为空，自动把 KNOWLEDGE_BASE 写入。
"""
from __future__ import annotations

import os
from functools import lru_cache

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "chroma"
)


@lru_cache(maxsize=1)
def _client():
    try:
        import chromadb
    except ImportError:
        return None
    try:
        return chromadb.PersistentClient(path=DB_PATH)
    except Exception:
        return None


def _collection():
    client = _client()
    if client is None:
        return None
    try:
        return client.get_or_create_collection(
            name="zhijing_kb",
            metadata={"hnsw:space": "cosine"},
        )
    except Exception:
        return None


def upsert_docs(docs: list[dict]) -> None:
    """把知识库文档写入向量库（document = title + "：" + content）。"""
    if not docs:
        return
    from .embeddings import embed
    texts = [d["title"] + "：" + d["content"] for d in docs]
    vecs = embed(texts)
    if not vecs:
        return
    col = _collection()
    if col is None:
        return
    try:
        col.upsert(
            ids=[d["id"] for d in docs],
            embeddings=vecs,
            documents=texts,
            metadatas=[{"title": d["title"], "content": d["content"]} for d in docs],
        )
    except Exception:
        pass


def search(query: str, k: int = 20) -> list[dict]:
    """语义检索 top-k，返回 [{id, title, content, score}]；无依赖/失败返回空 list。"""
    from .embeddings import embed
    col = _collection()
    if col is None:
        return []
    try:
        if col.count() == 0:
            from .rag import KNOWLEDGE_BASE
            upsert_docs(KNOWLEDGE_BASE)
    except Exception:
        pass
    qvec = embed([query])
    if not qvec:
        return []
    try:
        n = max(1, col.count())
        res = col.query(query_embeddings=qvec, n_results=min(k, n))
    except Exception:
        return []
    ids = (res.get("ids") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    out = []
    for i, did in enumerate(ids):
        meta = metas[i] if i < len(metas) else {}
        dist = dists[i] if i < len(dists) else 1.0
        out.append({
            "id": did,
            "title": meta.get("title", ""),
            "content": meta.get("content", ""),
            "score": round(1 - float(dist), 4),
        })
    return out
