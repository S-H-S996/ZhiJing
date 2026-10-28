# 评测体系（eval）

「职镜」匹配能力的评测地基。任何改动 matcher / parser 之前，先在这里跑一遍，用数字判断改好还是改坏。

## 运行

```bash
cd zhijing
python eval/run_matcher_eval.py
```

输出：

- **MAE**：预测分与标注分的平均绝对误差，越小越好（当前目标 < 15）
- **RMSE**：对大误差更敏感，反映「个别样本偏差很大」的情况
- **Spearman ρ**：排序一致性（-1~1），越接近 1 说明「高分样本真高分、低分样本真低分」
- **缺口召回率**：标注的「缺的技能」里，matcher 真正识别出来的比例

## 怎么标样本

`gold_set.jsonl` 每行一条，字段：

```json
{
  "id": "r01",
  "source": "synthetic",
  "resume": "<简历纯文本>",
  "jd_id": "<data/jds.json 里的 id>",
  "gold_score": 85,
  "gold_missing": ["LangChain", "RAG"],
  "note": "公式估算 / 人工微调"
}
```

标注口径：

1. `gold_score` 按 matcher 的公式逻辑估算（技能 40 + 项目 35 + 教育 15 + 软技能 10 = 100）
2. 允许基于常识微调，但要在 `note` 里写清楚「公式估算」还是「人工微调」
3. `gold_missing` 填「这个简历相对该 JD 缺的**必需技能**」，用于算缺口召回率
4. `source` 一律 `synthetic`，后续用真人简历替换时改成 `human`

## 如何解读结果

- **MAE < 15 且 ρ > 0.8**：matcher 与人工判断基本一致，可以作为稳定 baseline
- **MAE 偏高**：要么标注口径松了，要么 matcher 在某类样本上系统性偏差——查 CSV 里的 `diff` 列定位
- **缺口召回率低**：matcher 漏报缺口（可能词表没覆盖该技能的叫法）

## 如何扩充到真人样本

1. 收集真实简历 + 对应岗位的人工评分
2. 新样本 `source` 填 `human`，`id` 从 `r31` 往后
3. 追加到 `gold_set.jsonl`（不删旧样本，保证可比）
4. 重跑评测，对比新旧 baseline
