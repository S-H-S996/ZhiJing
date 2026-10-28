"""LLM-as-Judge 门控 A/B 评测：无门控 vs 有门控。

对 gold_set 前 10 条样本，分别跑「无门控」和「有门控」建议生成，
统计平均 judge avg、重试率、降级率。输出 eval/results/judge_eval_<timestamp>.csv
"""
from __future__ import annotations

import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import judge as judge_mod
from core import llm
from core.matcher import match
from core.parser import parse_resume
from core.rag import rag_suggestions


def load_jds() -> dict[str, dict]:
    path = Path(__file__).resolve().parent.parent / "data" / "jds.json"
    with open(path, encoding="utf-8") as f:
        return {j["id"]: j for j in json.load(f)}


def load_gold(path: str) -> list[dict]:
    out: list[dict] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def main() -> None:
    if not llm.is_configured():
        print("LLM 未配置，跳过 judge A/B 评测。")
        return

    base = Path(__file__).resolve().parent
    jds = load_jds()
    samples = load_gold(str(base / "gold_set.jsonl"))[:10]

    rows: list[dict] = []
    for s in samples:
        jd = jds[s["jd_id"]]
        profile = parse_resume(s["resume"])
        result = match(profile, jd)
        query = " ".join(result.gaps + result.missing_skills) + " " + jd["title"]

        # 无门控：生成 + 测量（不重试 / 不降级）
        suggs_nogate, _, _, _ = rag_suggestions(
            query, jd["title"], result.gaps, s["resume"], mode="keyword", gate=False
        )
        j_nogate = judge_mod.judge(suggs_nogate, s["resume"])
        nogate_avg = float(j_nogate["avg"]) if j_nogate else None

        # 有门控
        _, _, _, judge_info = rag_suggestions(
            query, jd["title"], result.gaps, s["resume"], mode="keyword", gate=True
        )
        gate_avg = float(judge_info["avg"]) if judge_info else None
        retried = bool(judge_info and judge_info.get("_retried"))
        fell_back = bool(judge_info and judge_info.get("_fell_back"))

        rows.append({
            "id": s["id"], "nogate_avg": nogate_avg, "gate_avg": gate_avg,
            "retried": int(retried), "fell_back": int(fell_back),
        })

    n = len(rows)
    nogate_avgs = [r["nogate_avg"] for r in rows if r["nogate_avg"] is not None]
    gate_avgs = [r["gate_avg"] for r in rows if r["gate_avg"] is not None]
    retry_rate = sum(r["retried"] for r in rows) / n
    fallback_rate = sum(r["fell_back"] for r in rows) / n

    out_dir = base / "results"
    os.makedirs(out_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    out_path = out_dir / f"judge_eval_{stamp}.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "nogate_avg", "gate_avg", "retried", "fell_back"])
        for r in rows:
            w.writerow([r["id"], r["nogate_avg"], r["gate_avg"], r["retried"], r["fell_back"]])

    print("=" * 52)
    print("LLM-as-Judge 门控 A/B 评测")
    print("=" * 52)
    print(f"样本数:     {n}")
    if nogate_avgs:
        print(f"无门控平均 judge avg: {sum(nogate_avgs)/len(nogate_avgs):.2f}")
    if gate_avgs:
        print(f"有门控平均 judge avg: {sum(gate_avgs)/len(gate_avgs):.2f}")
    print(f"重试率:     {retry_rate*100:.0f}%")
    print(f"降级率:     {fallback_rate*100:.0f}%")
    print(f"结果 CSV:   {out_path}")


if __name__ == "__main__":
    main()
