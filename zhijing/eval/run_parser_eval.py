"""解析引擎 A/B 评测：rule vs llm，比较 match().score 的 MAE 和平均耗时。

只在 LLM 已配置时跑 llm 分支；未配置则打印提示退出。
输出 eval/results/parser_eval_<timestamp>.csv
"""
from __future__ import annotations

import csv
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import llm
from core.matcher import match
from core.parser import parse_resume, parse_resume_hybrid


def load_jds() -> dict[str, dict]:
    path = Path(__file__).resolve().parent.parent / "data" / "jds.json"
    import json
    with open(path, encoding="utf-8") as f:
        return {j["id"]: j for j in json.load(f)}


def load_gold(path: str) -> list[dict]:
    import json
    samples: list[dict] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                samples.append(json.loads(line))
    return samples


def main() -> None:
    if not llm.is_configured():
        print("LLM 未配置，跳过 parser A/B 评测（llm 分支需要 API Key）。")
        return

    base = Path(__file__).resolve().parent
    jds = load_jds()
    samples = load_gold(str(base / "gold_set.jsonl"))

    rows: list[dict] = []
    for s in samples:
        jd = jds[s["jd_id"]]
        gold = int(s["gold_score"])

        t0 = time.perf_counter()
        prof_rule = parse_resume(s["resume"])
        res_rule = match(prof_rule, jd)
        t_rule = time.perf_counter() - t0

        t0 = time.perf_counter()
        prof_llm = parse_resume_hybrid(s["resume"], engine="llm")
        res_llm = match(prof_llm, jd)
        t_llm = time.perf_counter() - t0

        rows.append({
            "id": s["id"], "jd_id": s["jd_id"], "gold": gold,
            "rule_score": res_rule.score, "llm_score": res_llm.score,
            "rule_diff": res_rule.score - gold, "llm_diff": res_llm.score - gold,
            "rule_time": round(t_rule, 4), "llm_time": round(t_llm, 4),
        })

    n = len(rows)
    rule_mae = sum(abs(r["rule_diff"]) for r in rows) / n
    llm_mae = sum(abs(r["llm_diff"]) for r in rows) / n
    rule_avg_t = sum(r["rule_time"] for r in rows) / n
    llm_avg_t = sum(r["llm_time"] for r in rows) / n

    out_dir = base / "results"
    os.makedirs(out_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    out_path = out_dir / f"parser_eval_{stamp}.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "jd_id", "gold", "rule_score", "llm_score",
                    "rule_diff", "llm_diff", "rule_time", "llm_time"])
        for r in rows:
            w.writerow([r["id"], r["jd_id"], r["gold"], r["rule_score"], r["llm_score"],
                        r["rule_diff"], r["llm_diff"], r["rule_time"], r["llm_time"]])

    print("=" * 52)
    print("解析引擎 A/B 评测（rule vs llm）")
    print("=" * 52)
    print(f"样本数:   {n}")
    print(f"rule MAE: {rule_mae:.2f}  | 平均耗时 {rule_avg_t*1000:.1f}ms")
    print(f"llm  MAE: {llm_mae:.2f}  | 平均耗时 {llm_avg_t*1000:.1f}ms")
    winner = "rule" if rule_mae <= llm_mae else "llm"
    print(f"更接近 gold: {winner}")
    print(f"结果 CSV: {out_path}")


if __name__ == "__main__":
    main()
