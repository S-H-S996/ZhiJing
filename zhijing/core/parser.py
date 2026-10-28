"""简历文本解析：从纯文本/粘贴内容中提取教育背景、技能、项目、软技能。

纯规则引擎，不依赖大模型，保证离线可跑。大模型增强在 llm.py 里可选叠加。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# 技能词表：canonical -> 别名列表（统一小写匹配）
# ---------------------------------------------------------------------------
SKILL_LEXICON: dict[str, list[str]] = {
    "Python": ["python"],
    "Java": ["java"],
    "C++": ["c++", "cpp"],
    "JavaScript": ["javascript", "js", "前端"],
    "TypeScript": ["typescript", "ts"],
    "SQL": ["sql", "mysql", "postgresql", "数据库"],
    "MySQL": ["mysql"],
    "Redis": ["redis"],
    "FastAPI": ["fastapi"],
    "Django": ["django"],
    "Flask": ["flask"],
    "RESTful API": ["restful", "rest api", "接口", "api"],
    "Prompt 工程": ["prompt", "提示词", "提示工程", "prompt engineering"],
    "大模型 API 调用": ["大模型", "llm", "gpt", "deepseek", "通义", "文心", "api 调用", "调用大模型"],
    "LangChain": ["langchain"],
    "RAG": ["rag", "检索增强", "知识库"],
    "向量数据库": ["向量数据库", "faiss", "milvus", "embedding", "向量检索"],
    "微调": ["微调", "finetune", "lora", "sft"],
    "Streamlit/Gradio": ["streamlit", "gradio"],
    "Docker": ["docker", "容器"],
    "Linux": ["linux", "ubuntu", "centos"],
    "Git": ["git", "github", "版本控制"],
    "爬虫": ["爬虫", "scrapy", "requests", "selenium"],
    "数据清洗": ["数据清洗", "pandas", "数据预处理", "numpy"],
    "数据分析": ["数据分析", "数据敏感", "数据洞察", "数据统计", "abtest", "ab test", "埋点"],
    "消息队列": ["消息队列", "kafka", "rabbitmq", "mq"],
    "单元测试": ["单元测试", "pytest", "unittest"],
    "微服务": ["微服务", "微服务架构"],
    "机器学习": ["机器学习", "machine learning", "sklearn", "scikit-learn"],
    "深度学习": ["深度学习", "pytorch", "tensorflow", "神经网络", "cnn"],
    "PyTorch": ["pytorch", "torch"],
    "TensorFlow": ["tensorflow"],
    "数据可视化": ["可视化", "matplotlib", "plotly", "echarts", "图表"],
    "Excel": ["excel", "表格"],
    "Figma": ["figma", "原型设计"],
    # --- 大模型应用 / Agent / 算法方向（来自真实 JD） ---
    "工具调用/Function Calling": ["function calling", "函数调用", "工具调用", "tool use", "tool-use"],
    "MCP/Skill": ["mcp", "model context protocol", "skill 插件"],
    "意图识别/任务拆解": ["意图识别", "任务拆解", "任务分解", "任务规划"],
    "上下文工程": ["context engineering", "上下文工程", "上下文注入"],
    "评测体系": ["评测", "llm-as-judge", "llm as judge", "autorater", "回测", "评估框架"],
    "AI Infra": ["vllm", "ollama", "推理框架", "kv cache", "模型推理"],
    "AI编程工具": ["cursor", "claude code", "copilot", "ai 编程", "ai编程", "ai coding", "ai辅助编程"],
    "异步/高并发": ["异步", "高并发", "并发", "降级", "性能优化"],
    "分布式训练": ["megatron", "deepspeed", "fsdp", "分布式训练"],
    "合成数据": ["合成数据", "synthetic data"],
    "推荐系统": ["推荐系统", "推荐算法", "召回", "精排", "粗排", "混排"],
    "特征工程": ["特征工程", "特征提取", "特征构建"],
    "大数据": ["spark", "hive", "hadoop", "maxcompute", "大数据"],
    "强化学习": ["强化学习", "reinforcement learning"],
    "广告算法": ["广告算法", "广告系统", "cvr", "gmv", "广告推荐"],
    "多模态": ["多模态", "multimodal"],
    "端侧AI": ["端侧", "端侧ai", "端侧部署", "端上推理"],
    "Go/Golang": ["golang", "go语言", "go 语言"],
    "PHP": ["php"],
    "网络协议": ["tcp", "tcp/ip", "网络协议", "网络基础", "http协议", "socket"],
    "前端框架": ["react", "vue", "vue.js", "next.js", "前端框架"],
    "客户端": ["android", "鸿蒙", "harmonyos", "flutter", "swift", "kotlin", "ios开发"],
}

# 软技能关键词
SOFT_SKILL_LEXICON: dict[str, list[str]] = {
    "沟通表达": ["沟通", "表达", "汇报", "讲解", "演讲", "路演"],
    "团队协作": ["团队", "协作", "合作", "共同完成", "组长", "负责人"],
    "快速学习": ["快速学习", "自学", "主动学习", "钻研", "上手"],
    "责任心": ["负责", "责任心", "认真", "交付", "跟进"],
    "问题定位": ["排查", "定位问题", "debug", "排错", "解决 bug"],
    "业务理解": ["业务", "需求", "理解用户", "产品思维", "产品", "商业"],
    "自驱力": ["自驱", "自驱力", "主动", "高能动", "能动性"],
    "动手能力": ["动手", "极客", "落地", "实操", "实践", "demo"],
}

# 教育背景正则
EDU_PATTERNS = [
    re.compile(r"(?P<school>[^\s,，;；]+(?:大学|学院|学校))"),
    re.compile(r"(?P<degree>本科|硕士|博士|大专|专科|学士|研究生)"),
    re.compile(r"(?P<major>[^\s,，;；]*(?:计算机|软件工程|人工智能|数据科学|信息管理|自动化|电子信息|网络工程|数学|统计|通信)[^\s,，;；]*)"),
]

# 项目相关行关键词
PROJECT_KEYWORDS = [
    "项目", "开发", "实现", "搭建", "构建", "设计", "负责", "参与", "主导",
    "完成", "优化", "重构", "独立", "基于", "使用", "采用", "demo", "app",
]

AI_RELATED_KEYWORDS = [
    "大模型", "llm", "gpt", "deepseek", "通义", "文心", "ai", "人工智能",
    "prompt", "rag", "langchain", "微调", "向量", "智能", "深度学习",
    "机器学习", "推荐", "对话", "机器人", "nlp", "自然语言",
]


@dataclass
class ResumeProfile:
    """解析后的简历结构化画像。"""
    raw: str = ""
    school: str = ""
    degree: str = ""
    major: str = ""
    skills: set[str] = field(default_factory=set)
    soft_skills: set[str] = field(default_factory=set)
    projects: list[str] = field(default_factory=list)
    ai_related: bool = False
    word_count: int = 0


def _normalize(text: str) -> str:
    return text.lower().replace("　", " ")


def extract_education(text: str) -> dict[str, str]:
    school = degree = major = ""
    for pat in EDU_PATTERNS:
        m = pat.search(text)
        if m:
            val = m.groupdict().get("school") or m.groupdict().get("degree") or m.groupdict().get("major")
            if val:
                if "school" in m.groupdict() and m.groupdict()["school"]:
                    school = m.groupdict()["school"]
                if "degree" in m.groupdict() and m.groupdict()["degree"]:
                    degree = m.groupdict()["degree"]
                if "major" in m.groupdict() and m.groupdict()["major"]:
                    major = m.groupdict()["major"]
    # 兜底：直接扫行含“专业”“学院”
    if not major:
        m = re.search(r"(?:专业|就读)[:：\s]*([^\s,，;；\n]+)", text)
        if m:
            major = m.group(1)
    return {"school": school, "degree": degree, "major": major}


def extract_skills(text: str) -> set[str]:
    low = _normalize(text)
    found: set[str] = set()
    for canonical, aliases in SKILL_LEXICON.items():
        if any(a in low for a in aliases):
            found.add(canonical)
    return found


def extract_soft_skills(text: str) -> set[str]:
    low = _normalize(text)
    found: set[str] = set()
    for canonical, aliases in SOFT_SKILL_LEXICON.items():
        if any(a in low for a in aliases):
            found.add(canonical)
    return found


def extract_projects(text: str) -> list[str]:
    """按行抽取疑似项目经历行：以项目/动词开头，或带 -/•/数字 等列表标记。"""
    lines = [ln.strip() for ln in text.splitlines()]
    projects: list[str] = []
    for ln in lines:
        if not ln or len(ln) < 4:
            continue
        clean = re.sub(r"^[-•*#\d.、()（）\s]+", "", ln)
        if not clean:
            continue
        if any(k in clean for k in PROJECT_KEYWORDS):
            projects.append(clean)
    return projects


def has_internship(text: str) -> bool:
    """判断是否真有实习经历（排除「实习经历：无 / 暂无 / 空」这类否定写法）。"""
    if "实习" not in text:
        return False
    if re.search(r"实习(?:经历|经验)?[:：\s]*[（(]?(?:无|暂无|没有|未有|空|/|—|－)", text):
        return False
    return True


def _is_ai_related(projects: list[str], skills: set[str]) -> bool:
    ai_skills = {"大模型 API 调用", "Prompt 工程", "LangChain", "RAG", "向量数据库", "微调", "机器学习", "深度学习"}
    if ai_skills & skills:
        return True
    joined = _normalize(" ".join(projects))
    return any(k in joined for k in AI_RELATED_KEYWORDS)


def parse_resume(text: str) -> ResumeProfile:
    text = (text or "").strip()
    edu = extract_education(text)
    skills = extract_skills(text)
    soft = extract_soft_skills(text)
    projects = extract_projects(text)
    return ResumeProfile(
        raw=text,
        school=edu["school"],
        degree=edu["degree"],
        major=edu["major"],
        skills=skills,
        soft_skills=soft,
        projects=projects,
        ai_related=_is_ai_related(projects, skills),
        word_count=len(text),
    )
