"""SQLite 记录存储：每次诊断保存一条，用于积累「试用人数 / 建议采纳」等真实数据。"""
from __future__ import annotations

import hashlib
import os
import sqlite3
import time

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "records.db")


def _conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts INTEGER,
            resume_hash TEXT,
            jd_id TEXT,
            score INTEGER,
            matched_count INTEGER,
            missing_count INTEGER,
            suggestions_count INTEGER,
            used_llm INTEGER
        )
        """
    )
    return conn


def save_record(resume_text: str, jd_id: str, score: int, matched: int, missing: int, suggestions: int, used_llm: bool) -> None:
    conn = _conn()
    conn.execute(
        "INSERT INTO records (ts, resume_hash, jd_id, score, matched_count, missing_count, suggestions_count, used_llm) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            int(time.time()),
            hashlib.md5(resume_text.encode("utf-8")).hexdigest(),
            jd_id,
            score,
            matched,
            missing,
            suggestions,
            int(used_llm),
        ),
    )
    conn.commit()
    conn.close()


def stats() -> dict:
    conn = _conn()
    row = conn.execute(
        "SELECT COUNT(*), COUNT(DISTINCT resume_hash), COALESCE(AVG(score), 0) "
        "FROM records"
    ).fetchone()
    conn.close()
    return {"total_runs": row[0], "unique_resumes": row[1], "avg_score": round(row[2], 1)}
