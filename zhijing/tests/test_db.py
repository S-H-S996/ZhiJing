"""db.py 单元测试：save_record 后 stats() 数量 +1（用临时库隔离）。"""
from __future__ import annotations

from core import db


def test_save_record_increments(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    before = db.stats()["total_runs"]
    db.save_record("测试简历文本", "alibaba-ai-app", 80, 5, 1, 3, False)
    after = db.stats()["total_runs"]
    assert after == before + 1
