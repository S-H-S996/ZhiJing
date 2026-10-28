"""可选的大模型增强层：用 DeepSeek / 通义 / 任意 OpenAI 兼容接口提升解析与建议质量。

- 未配置 API Key 时自动降级为纯规则引擎，App 仍可完整运行。
- 通过环境变量或 .env 配置：LLM_BASE_URL / LLM_API_KEY / LLM_MODEL。
"""
from __future__ import annotations

import json
import os

try:
    from openai import OpenAI
except ImportError:  # openai 未安装时优雅降级
    OpenAI = None


def _load_env():
    """加载 .env 文件 + Streamlit Cloud Secrets 到环境变量。

    本地用 .env；线上部署（无 .env）用 st.secrets。二者都不覆盖已存在的环境变量。
    """
    # 1) .env 文件
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())
    # 2) Streamlit Cloud Secrets（线上无 .env 时用）
    try:
        import streamlit as st
        for key in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
            if key in st.secrets:
                os.environ.setdefault(key, str(st.secrets[key]))
    except Exception:
        pass


def is_configured() -> bool:
    _load_env()
    return bool(os.environ.get("LLM_API_KEY"))


def _client():
    _load_env()
    if OpenAI is None or not is_configured():
        return None
    return OpenAI(
        api_key=os.environ["LLM_API_KEY"],
        base_url=os.environ.get("LLM_BASE_URL") or "https://api.deepseek.com/v1",
    )


def _chat(system: str, user: str) -> str | None:
    client = _client()
    if client is None:
        return None
    try:
        resp = client.chat.completions.create(
            model=os.environ.get("LLM_MODEL") or "deepseek-chat",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
        )
        return resp.choices[0].message.content
    except Exception:
        return None


def chat(system: str, user: str) -> str | None:
    """通用单轮对话（不含工具），供智能选岗助手最终回答使用。"""
    return _chat(system, user)


def call_with_tools(system: str, user: str, tool_schemas: list[dict]) -> list[dict] | None:
    """Function Calling：让模型自主决定调用哪些工具、传什么参数。

    返回 [{name, arguments}, ...]；模型未调用工具或出错返回 None。
    """
    client = _client()
    if client is None:
        return None
    try:
        resp = client.chat.completions.create(
            model=os.environ.get("LLM_MODEL") or "deepseek-chat",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            tools=tool_schemas,
            tool_choice="auto",
            temperature=0.0,
        )
        msg = resp.choices[0].message
        if not msg.tool_calls:
            return None
        out = []
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            out.append({"name": tc.function.name, "arguments": args})
        return out
    except Exception:
        return None


def rag_generate(system: str, user: str) -> str | None:
    """供 RAG 使用：带知识库上下文的生成，复用底层 _chat。"""
    return _chat(system, user)


def rag_generate_langchain(system: str, user: str) -> str | None:
    """用 LangChain 组织 RAG 生成链（ChatPromptTemplate + ChatOpenAI，LCEL）。

    未安装 langchain 或未配置 API 时返回 None，调用方降级到原生客户端/规则。
    """
    try:
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_openai import ChatOpenAI
    except ImportError:
        return None
    _load_env()
    if not is_configured():
        return None
    try:
        llm_obj = ChatOpenAI(
            model=os.environ.get("LLM_MODEL") or "deepseek-chat",
            api_key=os.environ["LLM_API_KEY"],
            base_url=os.environ.get("LLM_BASE_URL") or "https://api.deepseek.com/v1",
            temperature=0.2,
        )
        prompt = ChatPromptTemplate.from_messages(
            [("system", system), ("human", user)]
        )
        chain = prompt | llm_obj
        result = chain.invoke({})
        return getattr(result, "content", None) or str(result)
    except Exception:
        return None


def enhance_suggestions(profile_text: str, jd_title: str, gaps: list[str]) -> list[str] | None:
    """用 LLM 生成更贴合简历的 3 条建议。失败返回 None，调用方降级。"""
    system = (
        "你是资深招聘专家。针对这份简历与目标岗位，给出 3 条最可执行的修改建议。"
        "每条必须具体到动作 + 可量化结果，禁止空话。只输出 JSON 数组，元素为字符串。"
    )
    user = f"目标岗位：{jd_title}\n当前识别缺口：{gaps}\n\n简历：\n{profile_text[:2000]}"
    content = _chat(system, user)
    if not content:
        return None
    try:
        arr = json.loads(content)
        if isinstance(arr, list):
            return [str(x) for x in arr[:3]]
    except json.JSONDecodeError:
        pass
    return None
