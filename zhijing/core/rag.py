"""RAG（检索增强生成）建议引擎：根据简历缺口检索「补法知识库」，再交给大模型生成落地建议。

三步：检索 → 增强（把检索到的知识片段拼进 prompt）→ 生成。
- 配置了 LLM 时：用知识片段增强 prompt，让大模型生成个性化建议。
- 未配置 LLM 时：直接返回检索到的知识片段本身作为建议（同样可用）。

检索有两种实现：
- retrieve_keyword：关键词子串匹配（baseline，无依赖、离线可跑）
- retrieve_vector：向量召回 + CrossEncoder 重排（升级版，依赖 sentence-transformers/chromadb）
- retrieve(mode="auto")：优先向量，任何异常回退关键词；无依赖时自动回退，保证完整跑通
"""
from __future__ import annotations

import json

from . import llm

# 知识库：每条 = 一个能力缺口 / 写法的可执行补法。
# tags 用于检索匹配（中英文都放，覆盖简历缺口里的各种叫法）。
KNOWLEDGE_BASE: list[dict] = [
    {
        "id": "langchain",
        "title": "如何补齐 LangChain",
        "tags": ["langchain", "llm", "大模型应用", "应用开发", "agent", "框架", "链"],
        "content": (
            "LangChain 是主流的大模型应用开发框架。补法：用它重写一个最小 Agent 链路——"
            "定义工具(Tool) + 提示词模板(PromptTemplate) + 链(Chain)，让模型按步骤调用工具完成任务。"
            "落地到「职镜」：用 LangChain 的 PromptTemplate + 链式调用替换建议生成逻辑，"
            "README 附上链结构图，说明「为什么拆成这几步」。"
        ),
    },
    {
        "id": "rag",
        "title": "如何补齐 RAG",
        "tags": ["rag", "检索增强", "向量", "知识库", "检索", "embedding"],
        "content": (
            "RAG = 检索增强生成：先检索相关知识，再让模型基于检索结果生成，减少幻觉。"
            "最小实践：建一个「简历改进知识库」（10~20 条），用关键词/向量相似度检索 top-k 条，"
            "拼进 prompt 再生成建议。「职镜」正在做的 RAG 增强就是这个证据，"
            "面试要能讲清「检索→增强→生成」三步，以及「为什么关键词够用、何时该上向量库」的选型理由。"
        ),
    },
    {
        "id": "function-calling",
        "title": "如何补齐 工具调用/Function Calling",
        "tags": ["function calling", "工具调用", "agent", "函数调用", "tool use"],
        "content": (
            "Function Calling 是让模型输出结构化参数、由程序去执行真实工具的核心能力。"
            "补法：给模型定义 2~3 个工具（如「查询岗位库」「写入诊断记录」），让它根据用户意图决定调用哪个，"
            "程序拿到参数后真正执行并回填结果。落地到「职镜」：把「选择岗位→诊断」做成模型可调用的工具。"
        ),
    },
    {
        "id": "prompt-engineering",
        "title": "如何体现 Prompt 工程",
        "tags": ["prompt", "提示词", "提示工程"],
        "content": (
            "Prompt 工程要展示「对比与量化」，不是只写一句提示词。补法：为同一任务准备 3 版 Prompt，"
            "用 20~30 条样本评出准确率/采纳率差异，把最优版固化进代码并注释设计取舍。"
            "「职镜」的建议生成就是 Prompt 应用：附上 system prompt 与温度等参数的选择理由即可。"
        ),
    },
    {
        "id": "project-writing",
        "title": "项目经历怎么写才加分",
        "tags": ["项目", "经历", "简历", "量化", "star", "写法"],
        "content": (
            "项目描述用 STAR + 数字：背景 → 你的角色 → 技术动作 → 可量化结果。"
            "把「参与开发」改成「独立实现 X 模块，将人工 40 分钟诊断压缩到 90 秒，27 人试用、建议采纳率 78%」。"
            "一个写深的项目 > 三个写浅的项目。"
        ),
    },
    {
        "id": "soft-communication",
        "title": "如何体现沟通表达",
        "tags": ["沟通", "表达", "汇报", "软技能", "协作"],
        "content": (
            "沟通表达别用形容词，用场景证明：如「向 30 位同学讲解工具用法并收集反馈」、"
            "「在课程答辩中用 5 分钟讲清架构，获评优」。把「会沟通」变成「对谁、讲什么、什么结果」。"
        ),
    },
    {
        "id": "soft-selfdrive",
        "title": "如何体现自驱力",
        "tags": ["自驱", "主动", "学习", "软技能", "自学"],
        "content": (
            "自驱力靠「主动 + 周期」证明：如「为参赛自学 Streamlit 并 3 天跑通全栈 demo」、"
            "「主动研究 7 份真实 JD 并拆解成能力图谱」。用「没人要求、但我去做了」的事实说话。"
        ),
    },
    {
        "id": "soft-problem",
        "title": "如何体现问题定位",
        "tags": ["问题定位", "排查", "debug", "排错"],
        "content": (
            "问题定位要写「定位到什么、怎么定位的」：如「发现 PDF 上传被浏览器按 MIME 类型拒绝，"
            "定位到 Streamlit type 参数只按扩展名校验，改为显式传 MIME 后修复」。这是最有含金量的细节。"
        ),
    },
    {
        "id": "soft-business",
        "title": "如何体现业务理解",
        "tags": ["业务", "需求", "产品", "商业"],
        "content": (
            "业务理解 = 从「我做了功能」升级到「我为谁解决了什么问题」。"
            "写清目标用户（求职大学生）、痛点（盲投、看不出差距）、你的方案如何命中痛点。"
            "「职镜」的痛点分析就是现成素材。"
        ),
    },
    {
        "id": "data-analysis",
        "title": "如何体现数据分析",
        "tags": ["数据分析", "数据清洗", "pandas", "统计", "埋点"],
        "content": (
            "数据分析要有「结论」而非「用了 pandas」：如「对 27 份试用数据做统计，发现应用岗平均 62 分、"
            "算法岗 40 分，据此把主攻方向定为应用岗」。用数据支撑一个决策，价值远大于罗列工具。"
        ),
    },
    {
        "id": "ai-coding-tool",
        "title": "AI 编程工具怎么用才被认可",
        "tags": ["ai编程", "cursor", "claude code", "copilot", "ai coding"],
        "content": (
            "AI 编程工具要写「用在哪、提效多少」：如「用 Claude Code 辅助重构解析模块，"
            "把开发时间从 2 天压到 1 天，人工 review 通过」。证明你能驾驭 AI 而非被 AI 取代。"
        ),
    },
    {
        "id": "go-golang",
        "title": "服务端岗缺 Go 怎么办",
        "tags": ["go", "golang", "服务端", "后端", "go语言"],
        "content": (
            "服务端岗普遍要求 Go/C++/Java 之一，你有 Java/C++ 基础，可强调「以 Java 起步、已具备服务端基础」；"
            "若要冲服务端方向，再用 Go 写一个并发小服务（如简历批量诊断接口）作为证据。"
        ),
    },
    {
        "id": "algorithm-mismatch",
        "title": "算法岗为什么不匹配",
        "tags": ["算法", "pytorch", "机器学习", "深度学习", "微调", "硕士"],
        "content": (
            "算法岗普遍要求硕士 + PyTorch/机器学习/深度学习/微调，且偏模型训练而非应用。"
            "对应用开发方向而言，与其补算法短板，不如把大模型 API 调用、RAG、Agent 的应用能力做深——"
            "应用岗才是本科生的蓝海。"
        ),
    },
]


def _score(doc: dict, query: str) -> float:
    """按 query 与 doc.tags 的重叠打分（子串匹配，兼顾中英文）。"""
    q = (query or "").lower()
    return sum(1.0 for tag in doc["tags"] if tag and tag.lower() in q)


def retrieve_keyword(query: str, k: int = 3) -> list[dict]:
    """关键词子串匹配检索（baseline）：返回 top-k（无命中返回空列表）。"""
    scored = [(d, _score(d, query)) for d in KNOWLEDGE_BASE]
    scored = [(d, s) for d, s in scored if s > 0]
    scored.sort(key=lambda x: -x[1])
    return [d for d, _ in scored[:k]]


def retrieve_vector(query: str, k: int = 20) -> list[dict]:
    """向量召回：语义检索 top-k，返回 [{id, title, content, score}]；无依赖返回空列表。"""
    from . import vector_store
    return vector_store.search(query, k=k)


def retrieve(query: str, k: int = 3, mode: str = "auto") -> list[dict]:
    """统一检索入口。

    - mode="keyword"：强制关键词检索
    - mode="vector"：强制向量召回 20 → 重排 k
    - mode="auto"：优先向量（召回 20 → 重排 k），任何异常回退关键词
    返回的每条 doc 带 "retrieve_mode" 字段（"vector"/"keyword"）。
    """
    if mode == "keyword":
        docs = retrieve_keyword(query, k=k)
        for d in docs:
            d["retrieve_mode"] = "keyword"
        return docs

    if mode == "vector":
        docs = retrieve_vector(query, k=20)
        if docs:
            from . import reranker
            docs = reranker.rerank(query, docs, top_k=k)
        for d in docs:
            d["retrieve_mode"] = "vector"
        return docs

    # mode == "auto"
    try:
        docs = retrieve_vector(query, k=20)
        if not docs:
            raise RuntimeError("vector retrieval empty")
        from . import reranker
        docs = reranker.rerank(query, docs, top_k=k)
        for d in docs:
            d["retrieve_mode"] = "vector"
        return docs
    except Exception:
        docs = retrieve_keyword(query, k=k)
        for d in docs:
            d["retrieve_mode"] = "keyword"
        return docs


def format_context(docs: list[dict]) -> str:
    """把检索结果拼成一段可注入 prompt 的上下文。"""
    return "\n\n".join(f"【{d['title']}】{d['content']}" for d in docs)


def rag_suggestions(query: str, jd_title: str, gaps: list[str], profile_text: str, mode: str = "auto"):
    """RAG 主流程：检索 → 增强 → 生成。

    返回 (suggestions, retrieved_docs, used_llm)：
    - used_llm=True 表示大模型基于知识片段生成了个性化建议
    - used_llm=False 表示离线降级，直接返回检索到的知识片段本身
    retrieved_docs 每条带 "retrieve_mode" 字段（"vector"/"keyword"）。
    """
    docs = retrieve(query, mode=mode)
    context = format_context(docs)

    if llm.is_configured() and docs:
        system = (
            "你是资深招聘专家。基于给定的「知识片段」，针对这份简历与岗位缺口给出 3 条最可执行的修改建议。"
            "必须引用知识片段里的具体做法，每条 = 动作 + 可量化结果，禁止空话。"
            "只输出 JSON 数组，元素为字符串。"
        )
        user = (
            f"目标岗位：{jd_title}\n识别缺口：{gaps}\n\n"
            f"【知识片段】\n{context}\n\n【简历】\n{profile_text[:1500]}"
        )
        content = llm.rag_generate_langchain(system, user) or llm.rag_generate(system, user)
        if content:
            try:
                arr = json.loads(content)
                if isinstance(arr, list):
                    return [str(x) for x in arr[:3]], docs, True
            except (json.JSONDecodeError, ValueError):
                pass

    # 离线降级：直接返回检索到的知识片段作为建议
    fallback = [d["content"] for d in docs] or [
        "针对当前缺口补一个可展示的小项目，留下可被追问的实现细节。"
    ]
    return fallback, docs, False
