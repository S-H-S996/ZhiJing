"""隐私脱敏：把送外部 LLM 的文本中的手机号 / 邮箱 / 身份证 / 姓名替换为占位符。

只作用于"送出去"的文本；本地存储与展示仍用原文。
"""
from __future__ import annotations

import re

_PHONE = re.compile(r"1[3-9]\d{9}")
_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_ID = re.compile(r"\d{17}[\dXx]")
# 「姓名：xxx」后的中文名（保守匹配：只匹配 2-4 个汉字）
_NAME = re.compile(r"(姓名\s*[:：]\s*)([一-龥]{2,4})")


def redact(text: str) -> tuple[str, int]:
    """脱敏，返回 (脱敏文本, 命中数量)。"""
    if not text:
        return text, 0
    out = text
    count = 0

    out, n = _PHONE.subn("[PHONE]", out)
    count += n
    out, n = _EMAIL.subn("[EMAIL]", out)
    count += n
    out, n = _ID.subn("[ID]", out)
    count += n
    out, n = _NAME.subn(lambda m: m.group(1) + "[NAME]", out)
    count += n

    return out, count
