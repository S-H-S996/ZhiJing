"""匹配评测：读 gold_set.jsonl，跑 parse_resume → match，计算评测指标。

指标：
1. MAE = mean(|pred - gold|)
2. RMSE = sqrt(mean((pred - gold)^2))
3. Spearman ρ（用 scipy.stats.spearmanr，报告 ρ 和 p 值）
4. 缺口召回率 = gold_missing 中被 missing_skills 命中的比例

输出：eval/results/matcher_eval_<YYYYMMDD_HHMM>.csv（每行一条样本）
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# 让脚本无论从哪个目录运行都能 import core
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.parser import parse_resume
from core.matcher import match


def load_jds() -> dict[str, dict]:
    path = Path(__file__).resolve().parent.parent / "data" / "jds.json"
    with open(path, encoding="utf-8") as f:
        return {j["id"]: j for j in json.load(f)}


def load_gold(path: str) -> list[dict]:
    samples: list[dict] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                samples.append(json.loads(line))
    return samples


def main() -> None:
    parser = argparse.ArgumentParser(description="职镜匹配评测")
    parser.add_argument("--gold", default=None, help="gold 样本路径，默认 eval/gold_set.jsonl")
    parser.add_argument("--out", default=None, help="结果目录，默认 eval/results")
    args = parser.parse_args()

    base = Path(__file__).resolve().parent
    gold_path = args.gold or str(base / "gold_set.jsonl")
    out_dir = args.out or str(base / "results")

    jds = load_jds()
    samples = load_gold(gold_path)

    rows: list[dict] = []
    for s in samples:
        jd = jds[s["jd_id"]]
        profile = parse_resume(s["resume"])
        result = match(profile, jd)

        pred = result.score
        gold = int(s["gold_score"])
        missing_set = set(result.missing_skills)
        gold_missing = s.get("gold_missing", []) or []

        if gold_missing:
            hit = sum(1 for g in gold_missing if g in missing_set)
            recall = hit / len(gold_missing)
        else:
            # 无标注缺口：理想情况 matcher 也不报缺口
            recall = 1.0 if not missing_set else 0.0

        rows.append({
            "id": s["id"],
            "jd_id": s["jd_id"],
            "pred": pred,
            "gold": gold,
            "diff": pred - gold,
            "recall": recall,
        })

    n = len(rows)
    if n == 0:
        print("错误：gold 样本为空")
        return

    diffs = [r["diff"] for r in rows]
    mae = sum(abs(d) for d in diffs) / n
    rmse = (sum(d * d for d in diffs) / n) ** 0.5
    preds = [r["pred"] for r in rows]
    golds = [r["gold"] for r in rows]

    from scipy.stats import spearmanr
    rho, pval = spearmanr(preds, golds)

    avg_recall = sum(r["recall"] for r in rows) / n

    os.makedirs(out_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    out_path = Path(out_dir) / f"matcher_eval_{stamp}.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "jd_id", "pred", "gold", "diff"])
        for r in rows:
            w.writerow([r["id"], r["jd_id"], r["pred"], r["gold"], r["diff"]])

    print("=" * 48)
    print("职镜匹配评测结果")
    print("=" * 48)
    print(f"样本数:       {n}")
    print(f"MAE:          {mae:.2f}")
    print(f"RMSE:         {rmse:.2f}")
    print(f"Spearman ρ:   {rho:.3f}  (p={pval:.4f})")
    print(f"缺口召回率:   {avg_recall:.3f}")
    print(f"结果 CSV:     {out_path}")


if __name__ == "__main__":
    main()
