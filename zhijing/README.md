# 🎯 职镜 —— 面向大学生的 AI 简历诊断工具

[![CI](https://github.com/S-H-S996/ZhiJing/actions/workflows/ci.yml/badge.svg)](https://github.com/S-H-S996/ZhiJing/actions)
[![coverage](https://img.shields.io/badge/coverage-63%25-brightgreen)](https://github.com/S-H-S996/ZhiJing)
[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://www.python.org/)

面向大学生求职场景的 AI 简历诊断与岗位匹配工具：粘贴简历 → 选择岗位 → 一键得到
**匹配评分 + 能力缺口 + 3 条可执行修改建议 + 可导出报告**。

> 院赛就业赛道参赛作品 · AI 应用开发方向

## 最小闭环（本次已实现）

1. 粘贴 / 上传简历（.txt / .md / .docx / .pdf）
2. 结构化解析出教育背景、技能、项目、软技能
3. 选择内置岗位 JD → 输出匹配度评分（四维度）+ 缺口清单
4. 生成 3 条具体到「动作 + 量化结果」的修改建议
5. 一键导出 Markdown 诊断报告

## 快速开始

```bash
cd zhijing
pip install -r requirements.txt
streamlit run app.py
```

浏览器会自动打开 `http://localhost:8501`。

## 开启大模型增强（可选）

不配置也能完整运行（走内置规则引擎）。要提升解析/建议质量：

```bash
cp .env.example .env   # Windows: copy .env.example .env
# 编辑 .env，填入 LLM_API_KEY 等
```

## 向量检索说明（可选）

RAG 的检索默认是「关键词匹配」，可升级为「向量召回 + 重排」（语义更准）：

- 依赖：`sentence-transformers` + `chromadb`（`requirements.txt` 已含）
- 首次运行会下载模型：`bge-small-zh-v1.5`（约 100MB）+ `bge-reranker-base`（约 1.1GB）
- 国内可设镜像加速：`export HF_ENDPOINT=https://hf-mirror.com`
- 无依赖时会自动回退关键词检索，不影响运行

## 目录结构

```
zhijing/
├── app.py              # Streamlit 主界面
├── core/
│   ├── parser.py       # 简历解析（规则引擎，离线可跑）
│   ├── fileio.py       # 上传文件文本抽取（txt/md/docx/pdf）
│   ├── matcher.py      # 人岗匹配评分 + 缺口
│   ├── advisor.py      # 建议生成（规则兜底）
│   ├── rag.py          # RAG 建议引擎（LangChain + 检索知识库 → 大模型增强）
│   ├── tools.py        # Function Calling 工具层（智能选岗助手）
│   ├── llm.py          # 可选大模型增强（DeepSeek/通义，OpenAI 兼容）
│   └── db.py           # SQLite 记录（累积试用数据）
├── data/
│   ├── jds.json        # 内置 7 份岗位 JD（应用/算法/后端/产品四类）
│   └── records.db      # 诊断记录（运行后生成）
└── requirements.txt
```

## 评分规则

总分 100：技能匹配 40 · 项目/经验 35 · 教育背景 15 · 软技能 10。

## 关键数据来源

- `data/records.db`：累计诊断次数、独立简历数、平均分 → 可直接统计「试用人数」等真实证据
- 诊断报告：每次可导出，用于留存样例

## 开发与测试

```bash
pytest -q tests/                      # 跑全部单元测试
pytest --cov=core --cov-report=term-missing tests/   # 带覆盖率
```

目标覆盖率 ≥ 60%。改 core/ 逻辑前先跑测试，避免回归。
