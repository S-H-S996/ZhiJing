"""职镜 —— 面向大学生的 AI 简历诊断工具

运行：streamlit run app.py
闭环：粘贴/上传简历 → 自动匹配评分 + 缺口清单 + 3 条可执行建议 → 导出报告
智能选岗助手：Function Calling 让模型自主调用工具（查岗位 / 看要求 / 诊断简历），并读取当前简历内容
"""
from __future__ import annotations

import hashlib
import json
import os

import streamlit as st

from core import db, llm, rag, tools, optimizer
from core.advisor import generate_suggestions
from core.fileio import extract_text
from core.matcher import match
from core.parser import parse_resume

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JD_PATH = os.path.join(BASE_DIR, "data", "jds.json")

# 各维度满分（用于进度条归一化）
DIM_MAX = {"技能匹配": 40, "项目/经验": 35, "教育背景": 15, "软技能": 10}


def load_jds() -> list[dict]:
    with open(JD_PATH, encoding="utf-8") as f:
        return json.load(f)


def score_label(score: int) -> str:
    if score >= 80:
        return "匹配度较高"
    if score >= 60:
        return "中等匹配"
    return "匹配度偏低"


def build_report(profile, jd, result, suggestions, used_llm: bool) -> str:
    lines = [
        f"# 职镜 · 简历诊断报告",
        "",
        f"- 目标岗位：{jd['title']}（{jd['company']} / {jd['city']}）",
        f"- 综合匹配度：**{result.score} / 100**（{score_label(result.score)}）",
        f"- 引擎：{'RAG 增强（检索 + 大模型）' if used_llm else 'RAG 检索（离线，未配置 API）'}",
        "",
        "## 一、维度得分",
    ]
    for name, val in result.dims.items():
        bar = "█" * val + "░" * (DIM_MAX[name] - val)
        lines.append(f"- {name}：{val} / {DIM_MAX[name]}  `{bar}`")
    lines += ["", "## 二、已命中技能"]
    lines.append("、".join(result.matched_skills) if result.matched_skills else "（无）")
    if result.matched_preferred:
        lines += ["", "加分技能：", "、".join(result.matched_preferred)]
    lines += ["", "## 三、能力缺口"]
    for g in result.gaps:
        lines.append(f"- {g}")
    lines += ["", "## 四、修改建议"]
    for i, s in enumerate(suggestions, 1):
        lines.append(f"{i}. {s}")
    lines += ["", "---", "*本报告由「职镜」自动生成，数据仅用于诊断参考。*"]
    return "\n".join(lines)


def main():
    st.set_page_config(page_title="职镜 · AI 简历诊断", page_icon="🎯", layout="wide")
    st.title("🎯 职镜 —— 面向大学生的 AI 简历诊断工具")
    st.caption("粘贴 / 上传简历 → 自动出匹配评分、能力缺口与可执行修改建议")

    jds = load_jds()
    stats = db.stats()

    # ---------- 侧边栏 ----------
    with st.sidebar:
        st.header("⚙️ 配置")
        if llm.is_configured():
            st.success("已检测到 LLM API，建议将用大模型增强")
        else:
            st.info("未配置 LLM API，当前使用**规则引擎 + RAG 检索**（可离线运行）。\n\n"
                    "要开启大模型增强：在项目根目录建 `.env`，填入\n\n"
                    "`LLM_BASE_URL=https://api.deepseek.com/v1`\n"
                    "`LLM_API_KEY=你的key`\n"
                    "`LLM_MODEL=deepseek-chat`")
        st.divider()
        st.header("🔍 检索模式")
        search_mode = st.selectbox(
            "RAG 检索方式",
            options=["auto", "keyword", "vector"],
            index=0,
            help="auto=优先向量、异常回退关键词；keyword=纯关键词；vector=纯向量召回+重排",
        )
        st.divider()
        st.header("📊 试用统计")
        st.metric("累计诊断次数", stats["total_runs"])
        st.metric("独立简历数", stats["unique_resumes"])
        st.metric("平均匹配分", stats["avg_score"])
        st.divider()
        st.caption("数据存于 data/records.db，可导出为「试用人数」等真实证据")

    # ---------- 输入区 ----------
    col1, col2 = st.columns([3, 2])
    with col1:
        st.subheader("① 粘贴或上传简历")
        resume_text = st.text_area(
            "简历文本（纯文本 / Markdown 均可）",
            height=260,
            placeholder="姓名 / 学校 / 专业\n技能：Python、SQL、Git、FastAPI\n项目经历：\n- 独立完成 XXX，实现……\n实习经历：……",
        )
        uploaded = st.file_uploader(
            "或上传简历文件（.txt / .md / .docx / .pdf / .jpg / .png）",
            type=[
                "txt", "md", "docx", "pdf", "jpg", "jpeg", "png",
                "application/pdf",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "text/plain", "image/jpeg", "image/png",
            ],
        )
        if uploaded is not None and not resume_text:
            resume_text = extract_text(uploaded.name, uploaded.getvalue())
            if not resume_text.strip():
                st.warning("未能从该文件提取到文本（图片简历需要安装 OCR 引擎，扫描版 PDF 也可能无法提取），请直接粘贴文本。")
    with col2:
        st.subheader("② 选择目标岗位")
        jd_options = {f"{j['title']} · {j['company']}": j["id"] for j in jds}
        jd_label = st.radio("内置岗位库", list(jd_options.keys()))
        jd = next(j for j in jds if j["id"] == jd_options[jd_label])
        with st.expander("查看岗位要求"):
            st.markdown(f"**{jd['title']}**（{jd['city']}）\n\n{jd['summary']}")
            st.markdown("**必需技能**：" + "、".join(jd["skills"]["required"]))
            st.markdown("**加分技能**：" + "、".join(jd["skills"]["preferred"]))

    # ---------- 诊断（自动触发：粘贴 / 上传 / 换岗位即重新匹配）----------
    if resume_text.strip():
        profile = parse_resume(resume_text)
        result = match(profile, jd)

        # RAG：检索「补法知识库」→ 增强 → 生成建议（无 API 时降级为检索结果本身）
        query = " ".join(result.gaps + result.missing_skills) + " " + jd["title"]
        suggestions, rag_docs, used_llm = rag.rag_suggestions(query, jd["title"], result.gaps, resume_text, mode=search_mode)
        if not suggestions:
            suggestions = generate_suggestions(profile, result, jd)

        # 仅当简历或岗位变化时记录一次，避免每次重跑重复写入
        key = hashlib.md5((resume_text + "\x00" + jd["id"]).encode()).hexdigest()
        if st.session_state.get("_last_diag_key") != key:
            db.save_record(
                resume_text, jd["id"], result.score,
                len(result.matched_skills), len(result.missing_skills),
                len(suggestions), used_llm,
            )
            st.session_state["_last_diag_key"] = key

        st.divider()
        st.subheader("诊断结果")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("综合匹配度", f"{result.score} / 100", score_label(result.score))
        c2.metric("已命中必需技能", f"{len(result.matched_skills)} / {len(jd['skills']['required'])}")
        c3.metric("能力缺口", f"{len(result.gaps)} 条")
        c4.metric("引擎", "RAG+大模型" if used_llm else "RAG检索(离线)")

        st.markdown("#### 维度得分")
        for name, val in result.dims.items():
            pct = val / DIM_MAX[name]
            st.progress(min(1.0, pct), text=f"{name}  {val} / {DIM_MAX[name]}")

        left, right = st.columns(2)
        with left:
            st.markdown("#### ✅ 已匹配技能")
            if result.matched_skills:
                for s in result.matched_skills:
                    st.markdown(f"- `{s}`")
                if result.matched_preferred:
                    st.markdown("**加分项**：" + "、".join(f"`{s}`" for s in result.matched_preferred))
            else:
                st.caption("未命中任何必需技能，请重点补齐岗位要求技能。")
        with right:
            st.markdown("#### ⚠️ 能力缺口")
            for g in result.gaps:
                st.markdown(f"- {g}")

        st.markdown("#### 💡 三条修改建议")
        for i, s in enumerate(suggestions, 1):
            st.markdown(f"**{i}.** {s}")

        if rag_docs:
            with st.expander("🔍 RAG 检索到的知识片段（建议的增强依据）"):
                for d in rag_docs:
                    tag = d.get("retrieve_mode", "keyword")
                    st.markdown(f"**[{tag}] {d['title']}**：{d['content']}")

        report = build_report(profile, jd, result, suggestions, used_llm)
        st.download_button(
            "📄 导出诊断报告（Markdown）",
            data=report.encode("utf-8"),
            file_name=f"职镜诊断报告_{jd['id']}.md",
            mime="text/markdown",
        )

        with st.expander("查看解析出的结构化信息"):
            st.json({
                "学校": profile.school, "专业": profile.major, "学历": profile.degree,
                "技能": sorted(profile.skills), "软技能": sorted(profile.soft_skills),
                "项目行数": len(profile.projects), "AI相关": profile.ai_related,
                "项目预览": profile.projects[:6],
            })
    else:
        st.info("粘贴或上传简历后，将自动诊断（无需点击按钮）。", icon="👆")

    # ---------- 简历优化（按 JD 重写）----------
    st.divider()
    st.subheader("✨ 简历优化（按 JD 重写）")
    st.caption("提炼 JD 关键词与筛选重点，重写经历突出匹配度；不编造、缺失数据标【待补充数据】。需配置 LLM API。")

    if st.button("🚀 生成优化简历"):
        if not llm.is_configured():
            st.warning("简历优化需要配置大模型 API（在 .env 里填 LLM_API_KEY）。")
        elif not resume_text.strip():
            st.warning("请先粘贴或上传简历。")
        else:
            with st.spinner("正在优化…"):
                result = optimizer.optimize_resume(resume_text, jd)
            if result:
                st.session_state["_opt_result"] = result
            else:
                st.error("优化失败，请检查 API 配置后重试。")

    if st.session_state.get("_opt_result"):
        st.markdown(st.session_state["_opt_result"])
        st.download_button(
            "📄 下载优化后的简历",
            data=st.session_state["_opt_result"].encode("utf-8"),
            file_name=f"优化简历_{jd['id']}.md",
            mime="text/markdown",
        )

    # ---------- 智能选岗助手（Function Calling）----------
    st.divider()
    st.subheader("🤖 智能选岗助手（Function Calling）")
    st.caption("用自然语言提问，助手会读取你当前的简历内容，并结合工具（查岗位 / 看要求 / 诊断）作答。需配置 LLM API。")

    agent_q = st.text_input(
        "问点什么",
        placeholder="我适合投哪个岗位？ / CVTE 的岗位要求是什么？ / 帮我诊断一下阿里应用岗",
    )
    ask = st.button("💬 询问")

    if ask:
        if not llm.is_configured():
            st.warning("Function Calling 需要配置大模型 API（在 .env 里填 LLM_API_KEY）。")
        elif not agent_q.strip():
            st.warning("先输入你的问题。")
        else:
            # 把当前简历内容带进上下文，让模型基于简历思考
            resume_ctx = ""
            if resume_text.strip():
                resume_ctx = (
                    f"\n\n【当前简历内容】\n{resume_text[:1500]}\n"
                    "（回答可结合这份简历；需要精确分数或岗位要求时再调用工具）"
                )
            system = (
                "你是「职镜」的智能选岗助手。" + resume_ctx +
                "\n\n先判断用户问题需要调用哪个工具来获取信息，拿到工具结果后再用简洁的语言回答。"
            )
            tool_calls = llm.call_with_tools(system, agent_q, tools.TOOL_SCHEMAS)
            if not tool_calls:
                answer = llm.chat(system, agent_q)
                if answer:
                    st.markdown("**💬 助手回答**")
                    st.markdown(answer)
            else:
                executed = []
                for tc in tool_calls:
                    name, args = tc["name"], tc["arguments"]
                    r = tools.run_tool(name, args, jds, resume_text)
                    executed.append((name, r))
                    with st.expander(f"🔧 调用工具 `{name}`（参数 {args}）"):
                        st.text(r)
                final_user = (
                    f"用户问题：{agent_q}\n\n工具结果：\n"
                    + "\n".join(f"[{name}] {r}" for name, r in executed)
                )
                answer = llm.chat(system, final_user)
                if answer:
                    st.markdown("**💬 助手回答**")
                    st.markdown(answer)


if __name__ == "__main__":
    main()
