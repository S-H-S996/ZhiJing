"""fileio.py 单元测试：文本解码、空字节、未知扩展名回退。"""
from __future__ import annotations

from core.fileio import extract_text


def test_txt_decode():
    assert extract_text("resume.txt", "庄铭湛 本科".encode("utf-8")) == "庄铭湛 本科"


def test_md_decode():
    assert extract_text("resume.md", "# 标题".encode("utf-8")) == "# 标题"


def test_empty_bytes():
    assert extract_text("resume.txt", b"") == ""


def test_unknown_extension_fallback():
    assert extract_text("resume.xyz", "some text".encode("utf-8")) == "some text"


def test_docx_garbage_bytes():
    assert extract_text("resume.docx", b"garbage-not-a-docx") == ""


def test_pdf_garbage_bytes():
    assert extract_text("resume.pdf", b"garbage-not-a-pdf") == ""


def test_image_garbage_bytes():
    assert extract_text("resume.jpg", b"garbage-not-an-image") == ""
