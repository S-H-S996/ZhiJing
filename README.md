# 🎯 职镜 (ZhiJing) —— 面向大学生的 AI 简历诊断与岗位匹配工具

![CI](https://github.com/S-H-S996/Zhijing/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.11-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-FF4B4B)
![LangChain](https://img.shields.io/badge/LangChain-0.3-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

**职镜** 是一款面向大学生求职场景的 AI 应用：只需粘贴/上传简历并选择目标岗位，即可一键获得 **匹配评分 + 能力缺口 + 可执行修改建议 + 导出诊断报告**。项目不仅实现了完整的业务闭环，更在底层引入了 RAG 增强、多轮 Agent 以及完善的自动化评测与工程化体系。

## ✨ 核心特性 (Features)

- **🎯 多维人岗匹配**：基于规则与语义，从技能（40%）、项目（35%）、教育（15%）、软技能（10%）四个维度进行综合评分，并输出能力缺口清单。
- **🔍 高级 RAG 建议引擎**：从传统的「关键词匹配」升级为 **BGE 向量召回 + Reranker 重排**，结合本地知识库为大模型提供精准上下文，生成可落地的修改建议。
- **🤖 Plan-Act-Reflect 智能选岗 Agent**：基于 **LangGraph** 构建的多轮反思智能体。能自主规划调用工具（岗位查询、简历诊断），并在发现信息不足时自动发起多轮推理。
- **⚖️ LLM-as-Judge 质量门控**：对生成的建议进行多维度打分（可执行性、具体度、忠实度），低于阈值自动打回重试，杜绝“假大空”的 AI 幻觉。
- **🔄 混合解析策略 (Hybrid Routing)**：正则规则引擎（毫秒级、零成本）优先兜底，仅在识别置信度低时触发大模型进行 Pydantic 结构化抽取，兼顾速度与准确率。

## 🛠️ 技术栈 (Tech Stack)

- **前端/交互**：Streamlit
- **大模型层**：OpenAI SDK (兼容 DeepSeek / 通义千问)
- **RAG & Agent**：LangChain, LangGraph, ChromaDB, Sentence-Transformers (BGE)
- **数据处理**：Pydantic, SQLite, Pandas
- **工程化**：Pytest (覆盖率>60%), Ruff, GitHub Actions (CI), Docker

## 📊 评测与实证数据 (Evaluation)

为了验证引擎的有效性，项目自建了包含 30 份真实/合成简历的 Gold Set（基准评测集）：

- **匹配器精确度**：与人工标注对比，MAE = 10.97，Spearman 秩相关系数 ρ = 0.959（高度正相关），缺口召回率 100%。
- **检索模式**：支持关键词 / 向量 / auto 三种检索；向量召回（BGE）+ CrossEncoder 重排的语义相关性优于纯关键词子串匹配（无依赖时自动回退关键词，保证离线可用）。
- **混合策略收益**：采用”规则优先 + LLM 兜底”策略，在保证 100% 解析率的同时，规避了大多数简历调用大模型带来的延迟与 Token 成本。

## 🚀 快速开始 (Quick Start)

### 本地运行

```bash
# 1. 克隆项目
git clone https://github.com/S-H-S996/Zhijing.git
cd Zhijing/zhijing

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量 (可选，不配也能离线运行规则引擎)
cp .env.example .env
# (Windows 用户使用 copy .env.example .env)
# 编辑 .env，填入 LLM_API_KEY (如 DeepSeek)

# 4. 启动应用
streamlit run app.py

Docker部署
cd zhijing
docker build -t zhijing:v2 .
docker run -p 8501:8501 zhijing:v2

目标目录
zhijing/
├── app.py              # Streamlit 主界面
├── core/
│   ├── parser.py       # 简历规则解析
│   ├── llm_extractor.py# LLM 结构化抽取兜底
│   ├── matcher.py      # 匹配评分规则
│   ├── rag.py          # RAG 检索与生成链路
│   ├── agent_graph.py  # LangGraph 智能体
│   └── judge.py        # LLM-as-Judge 质量门控
├── eval/               # 评测脚本与基准数据集
├── tests/              # Pytest 单元测试
└── .github/workflows/  # GitHub Actions CI 流水线

本项目为大学生创新创业训练计划（大创）项目，旨在用 AI 技术解决大学生求职痛点，探索 AI 应用开发的最佳实践。

*注：所有评测数据均支持运行 `eval/run_matcher_eval.py` 现场复现。*
