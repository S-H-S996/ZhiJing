# CLAUDE.md

## 项目定位

面向大学生的 AI 简历诊断工具：Streamlit + RAG + Function Calling。
粘贴 / 上传简历 → 自动匹配评分 + 能力缺口 + 修改建议 + 按 JD 优化简历 + 导出报告。

## 运行

```bash
cd zhijing
streamlit run app.py
```

- Python 3.12（当前开发环境）
- 无外部服务依赖；无 API Key 也能完整跑通（规则引擎 + RAG 离线检索）

## 目录结构与文件职责

| 文件 | 职责 |
|---|---|
| `app.py` | Streamlit 主界面：粘贴/上传 → 自动诊断 → 建议 → 导出 → 智能选岗助手 → 简历优化 |
| `core/parser.py` | 简历解析（规则引擎：技能/教育/项目/软技能词表 + 正则，返回 `ResumeProfile`） |
| `core/matcher.py` | 人岗匹配评分 + 缺口清单（四维度，返回 `MatchResult`） |
| `core/advisor.py` | 建议生成（规则兜底，无 LLM 时用） |
| `core/rag.py` | RAG 建议引擎（`KNOWLEDGE_BASE` 关键词检索 → 大模型增强，离线可降级） |
| `core/llm.py` | 大模型层（`.env`/Streamlit Secrets 加载；`chat` / `call_with_tools` / `rag_generate_langchain`） |
| `core/tools.py` | Function Calling 工具层（`list_jobs` / `get_job_detail` / `diagnose` 三个工具 schema + 执行） |
| `core/optimizer.py` | 简历优化（JD 拆解 + 按岗重写，缺失数据标【待补充数据】） |
| `core/fileio.py` | 文件文本抽取（txt/md/docx/pdf/jpg/png，图片走 OCR，依赖按需加载） |
| `core/db.py` | SQLite 记录（`data/records.db`，累计诊断/独立简历/平均分统计） |
| `data/jds.json` | 内置 7 份真实岗位 JD（应用/算法/后端/产品四类） |
| `requirements.txt` | 依赖清单 |
| `README.md` | 项目说明 |

## 硬约束（后续任何修改必须遵守）

1. **无 API Key 时仍能完整跑通**：`core/llm.py` 的 `is_configured()` 兜底逻辑不能破坏；`rag.py` / `optimizer.py` / `app.py` 都依赖它做离线降级。
2. **app.py 的 UI 流程不能删任何一步**：粘贴/上传 → 自动诊断（评分 / 缺口 / 建议）→ 导出报告 → 智能选岗助手 → 简历优化。
3. **core/matcher.py 的评分公式未经同意不得改**：技能匹配 40 + 项目/经验 35 + 教育背景 15 + 软技能 10 = 100。
4. **core/rag.py 的 `KNOWLEDGE_BASE` 不得删减**（当前 13 条，可以追加）。

## 每次改完必须跑

```bash
python -m compileall app.py core
pytest -q   # 批次 4 之后
```

## 代码风格

- 每个模块顶部 `from __future__ import annotations`
- dataclass 优先（如 `parser.ResumeProfile`、`matcher.MatchResult`）
- 类型注解完整（函数签名 + 返回类型）
- 单个模块不超过 400 行
- 敏感 / 长逻辑抽到 `core/` 下新文件

## 禁止事项

- 不引入 Redis / Postgres / Kafka 等需要外部服务的依赖
- 不用 langchain 全家桶替代现有的极简实现（langchain 仅用于 `llm.rag_generate_langchain` 这一处可选增强）
- 不改动 `data/jds.json` 的结构（字段：`id` / `title` / `company` / `city` / `summary` / `skills` / `soft_skills` / `experience` / `education`）

## Future Work / 后续优化

> 记录已识别但暂不实现的优化项，供答辩「不足与展望」环节引用。

### 1. 多轮 Agent 的批量诊断（Token 成本优化）

- **现状**：智能选岗助手（`core/agent_graph.py`）问「我适合投哪个岗位？」时，planner 会
  对 7 个岗位各调一次 `diagnose`（7 次单点工具调用），每轮产生 7 次 LLM 工具往返。
- **优化方向**：在 `core/tools.py` 新增一个「批量诊断」工具（一次返回 7 个岗位的评分与缺口），
  把 7 次调用压成 1 次，降低 Token 成本与端到端延迟。
- **答辩用途**：作为「不足与展望」环节的工程思维证明——主动识别「7 次单点 vs 1 次批量」
  的调用模式差异，说明有成本 / 延迟意识，而不只是"功能跑通"。
- **状态**：暂不实现（冲刺期优先主线：评测集、工程质量、答辩材料）。
