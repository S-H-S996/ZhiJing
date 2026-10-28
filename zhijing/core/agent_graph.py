"""LangGraph Plan-Act-Reflect 状态机：把单轮 Function Calling 升级为多轮 Agent。

节点流：planner（决定调哪些工具）→ executor（执行工具）→ reflector（判断信息是否足够）
        → planner（不足则再来，最多 3 轮）或 answer（足够则生成最终回答）

依赖 langgraph；未安装或未配置 LLM 时 run_agent 返回 None，调用方回退单轮。

Prompt 调优说明（答辩用）：初版实测发现「planner 说无需工具、reflector 却判信息不足」
的判断口径错位——根源是两节点对「是否已拿到足够信息」的标准不一致。为此：
1. planner 加入引导：推荐/匹配类问题若尚未调用 diagnose，优先调用它；
2. reflector 加入硬规则：若简历非空且用户意图含推荐/匹配/诊断，必须已调用 diagnose，
   否则判 need_more=True。二者对齐后，多轮才能真正把「查岗位 → 诊断简历」串起来。
"""
from __future__ import annotations

import json
import operator
import os
from functools import lru_cache
from typing import Annotated, TypedDict

from . import llm, tools


class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    resume: str
    tool_calls: list[dict]
    tool_results: list[tuple[str, str]]
    need_more: bool
    final_answer: str
    # 内部字段（run_agent 注入）
    system: str
    user_question: str
    tools_schema: list[dict]
    jds: list[dict]
    round: int
    steps: Annotated[list[dict], operator.add]


def _load_jds() -> list[dict]:
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "jds.json"
    )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _planner_node(state: AgentState) -> dict:
    called_hint = ""
    called_names = [name for name, _ in state.get("tool_results", [])]
    if called_names:
        called_hint = "\n\n【已调用过的工具及结果】\n" + "\n".join(
            f"[{name}] {result}" for name, result in state["tool_results"]
        ) + "\n\n如果这些信息已足够，请不要重复调用工具。"
    # 引导：推荐/匹配类问题，尚未调用 diagnose 时优先调用它（与 reflector 的硬规则对齐）
    if "diagnose" not in called_names:
        called_hint += (
            "\n\n如果用户询问岗位推荐或匹配度，且尚未调用过 diagnose 工具，"
            "请优先调用 diagnose 获取评分。"
        )
    user = f"用户问题：{state['user_question']}{called_hint}"
    tool_calls = llm.call_with_tools(state["system"], user, state["tools_schema"]) or []
    names = [tc["name"] for tc in tool_calls] or ["（无需工具）"]
    return {
        "tool_calls": tool_calls,
        "round": state.get("round", 0) + 1,
        "steps": [{"node": "planner", "summary": "规划调用：" + "、".join(names)}],
    }


def _executor_node(state: AgentState) -> dict:
    results = []
    for tc in state.get("tool_calls", []):
        name = tc["name"]
        args = tc["arguments"]
        r = tools.run_tool(name, args, state["jds"], state.get("resume", ""))
        results.append((name, r))
    return {
        "tool_results": list(state.get("tool_results", [])) + results,
        "steps": [{"node": "executor", "summary": f"执行 {len(results)} 个工具"}],
    }


def _reflector_node(state: AgentState) -> dict:
    results_text = "\n".join(f"[{name}] {result}" for name, result in state.get("tool_results", []))
    has_resume = bool((state.get("resume") or "").strip())
    resume_note = "当前有简历内容。" if has_resume else "当前没有简历内容。"
    # 硬规则：简历非空且用户意图含推荐/匹配/诊断时，必须已调用 diagnose，否则判 need_more=True
    prompt = (
        f"用户问题：{state['user_question']}\n\n"
        f"已获取的工具结果：\n{results_text}\n\n"
        f"简历状态：{resume_note}\n\n"
        "判断规则：\n"
        "1. 若用户意图包含岗位推荐/匹配/诊断，且当前有简历，"
        "则必须已经调用过 diagnose 工具拿到评分，否则信息不足（回答 no）。\n"
        "2. 其他情况，只要工具结果能回答用户问题即可（回答 yes）。\n"
        "请只回答 yes 或 no。"
    )
    resp = llm.chat(state["system"], prompt)
    resp_lower = (resp or "").strip().lower()
    is_enough = any(k in resp_lower for k in ("yes", "是", "足够"))
    need_more = not is_enough
    return {
        "need_more": need_more,
        "steps": [{"node": "reflector", "summary": "信息已足够" if not need_more else "信息不足，继续"}],
    }


def _answer_node(state: AgentState) -> dict:
    results_text = "\n".join(f"[{name}] {result}" for name, result in state.get("tool_results", []))
    prompt = (
        f"用户问题：{state['user_question']}\n\n工具结果：\n{results_text}\n\n"
        "请基于这些信息，用简洁的语言回答用户问题。"
    )
    answer = llm.chat(state["system"], prompt) or "抱歉，暂时无法回答。"
    return {
        "final_answer": answer,
        "steps": [{"node": "answer", "summary": "生成最终回答"}],
    }


# 最大迭代轮数：防止 planner/reflector 两节点判断口径不一致时陷入死循环
MAX_ITERATIONS = 3


def _should_continue(state: AgentState) -> str:
    if state.get("need_more") and state.get("round", 0) < MAX_ITERATIONS:
        return "planner"
    return "answer"


@lru_cache(maxsize=1)
def _build_graph():
    from langgraph.graph import END, StateGraph
    g = StateGraph(AgentState)
    g.add_node("planner", _planner_node)
    g.add_node("executor", _executor_node)
    g.add_node("reflector", _reflector_node)
    g.add_node("answer", _answer_node)
    g.set_entry_point("planner")
    g.add_edge("planner", "executor")
    g.add_edge("executor", "reflector")
    g.add_conditional_edges("reflector", _should_continue, {"planner": "planner", "answer": "answer"})
    g.add_edge("answer", END)
    return g.compile()


def run_agent(system: str, user: str, tools_schema: list[dict], resume_text: str) -> dict | None:
    """运行多轮 Agent，返回 {"answer": str, "steps": list[dict]}。

    未安装 langgraph 或未配置 LLM 或运行失败时返回 None，调用方回退单轮。
    """
    if not llm.is_configured():
        return None
    try:
        import langgraph  # noqa: F401
    except ImportError:
        return None
    try:
        app = _build_graph()
        initial: AgentState = {
            "messages": [],
            "resume": resume_text or "",
            "tool_calls": [],
            "tool_results": [],
            "need_more": False,
            "final_answer": "",
            "system": system,
            "user_question": user,
            "tools_schema": tools_schema,
            "jds": _load_jds(),
            "round": 0,
            "steps": [],
        }
        result = app.invoke(initial)
        return {
            "answer": result.get("final_answer", ""),
            "steps": result.get("steps", []),
        }
    except Exception:
        return None
