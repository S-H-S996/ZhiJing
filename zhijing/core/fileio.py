"""从上传文件中抽取纯文本，支持 .txt / .md / .docx / .pdf。

依赖按需加载：python-docx / pypdf 未安装时对应格式返回空串，不影响其它格式。
"""
from __future__ import annotations

import io
import os


def extract_text(name: str, data: bytes) -> str:
    """按文件扩展名路由，返回抽取出的文本；失败或空返回 ""。"""
    ext = ""
    if "." in (name or ""):
        ext = (name or "").rsplit(".", 1)[-1].lower()

    if ext in ("txt", "md", "markdown", ""):
        return data.decode("utf-8", errors="ignore")
    if ext == "docx":
        return _from_docx(data)
    if ext == "pdf":
        return _from_pdf(data)
    if ext in ("jpg", "jpeg", "png", "bmp", "webp"):
        return _from_image(data)
    # 未知类型回退按文本读
    return data.decode("utf-8", errors="ignore")


def _from_image(data: bytes) -> str:
    """图片简历：用 OCR 识别文字。未装 pytesseract / Tesseract 时返回空串。"""
    try:
        import pytesseract
        from PIL import Image
    except ImportError:
        return ""
    try:
        # Windows 默认安装路径（未加入 PATH 时手动指定）
        exe = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if os.path.exists(exe):
            pytesseract.pytesseract.tesseract_cmd = exe
        # 语言包目录：优先不含中文的 Public 目录，避免 subprocess 中文路径编码问题
        tessdata = r"C:\Users\Public\tessdata"
        if not os.path.isdir(tessdata):
            tessdata = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "tessdata"
            )
        # 注意：路径不能加引号（pytesseract 会把引号当路径的一部分），且用正斜杠
        config = "--tessdata-dir " + tessdata.replace("\\", "/")
        img = Image.open(io.BytesIO(data))
        # 优先中英混合识别，失败退回英文
        for lang in ("chi_sim+eng", "eng"):
            try:
                return pytesseract.image_to_string(img, lang=lang, config=config)
            except Exception:
                continue
        return pytesseract.image_to_string(img, config=config)
    except Exception:
        return ""


def _from_docx(data: bytes) -> str:
    try:
        from docx import Document
    except ImportError:
        return ""
    try:
        doc = Document(io.BytesIO(data))
    except Exception:
        return ""
    parts = [p.text for p in doc.paragraphs if p.text.strip()]
    # 简历里的表格（如教育背景、技能表）也一并读出
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                parts.append(" ".join(cells))
    return "\n".join(parts)


def _from_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return ""
    try:
        reader = PdfReader(io.BytesIO(data))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception:
        return ""
