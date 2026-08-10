# Evaluation Registry and Benchmark

Version: 1.0

## 1. 目标

建立跨 Story、Strategy、Timeline、Voice、Subtitle、Render 和 Automation 的版本化评测体系，使 Prompt/Model/Config/Policy 候选能在相同数据和指标下公平比较。

输入：Dataset Manifest、Candidate/Champion versions、Evaluation Plan、Resource/Cost Profile、Human Annotation。

输出：EvaluationRun、SliceMetrics、ErrorCases、ComparisonReport、PromotionRecommendation、MLflow/Artifact Registry refs。

---

## 2. 工具职责

MLflow 用于 experiment runs、params、metrics、model/prompt candidate 和评测 artifacts。项目 Artifact Registry 仍是 Dataset、Policy、Review、Correction 和生产 lineage 的业务真相源。

Parquet/DuckDB 用于离线样本和分析；PostgreSQL 保存 registry metadata、审批和关联。不得让 MLflow run state 替代生产 Workflow/Artifact 状态。

---

## 3. Evaluation Plan

每个 Plan 指定：objective、candidate/champion、dataset/splits、applicable slices、metrics、blocker gates、statistical method、budget、reproducibility、required reviewers 和 promotion criteria。

必须先冻结 Plan 再看最终 test 结果，避免根据结果临时选择有利指标。探索性分析可做，但明确标 experimental。

---

## 4. Benchmark 分层

- Contract/engineering：Schema、replay、latency、cost、failure。
- Correctness：事实、证据、身份、因果、同步、rights、technical blocker。
- Craft：Hook、节奏、解说、画面、声音、字幕，使用 rubric/pairwise/完整观看。
- Automation：calibration、severe false negative、review precision、coverage、correction、drift。
- Online：仅合法发布数据，单独报告。

不能将 Craft 与 Online 合成一个“智能总分”，也不能用性能收益抵消 correctness 回归。

---

## 5. Candidate vs Champion

比较采用 paired samples，报告总体与 slice delta、confidence interval、regressions、wins/losses、成本和资源。Promotion 必须满足所有 hard gates；均值提升不能掩盖严重 slice 回归。

人工创意评测保存 pairwise preference、理由、agreement 和 adjudication，不强迫每个样本产生唯一绝对分。

---

## 6. LLM-as-Judge 治理

Judge 与被评模型逻辑隔离，Prompt/version 固定，并在人工 gold 上评测偏差、稳定性、位置/长度/风格偏好。Judge 用于问题召回和批量辅助，不能单独批准 Release 或自动化升级。

模型间互评可能共享盲点，不能把多个高度相关 Judge 当成独立证据。

---

## 7. 并发与成本

样本/Variant/reviewer 可并行，受模型/云端/人工预算约束。相同 prediction artifact 可在多个 rubric 中复用；评测代码/配置变化只重算 metrics，模型输入未变时不重跑 inference。

长 benchmark 分 shard 并可恢复；最终汇总验证完整性、重复和缺失样本。缺失结果不能从分母静默删除。

---

## 8. 复现与污染防护

记录 git/container/model digest、Prompt/Config/Policy、dataset/guideline、seed、hardware、dependency 和 raw prediction refs。

冻结 gold test；监控训练/Prompt few-shot 与 test 剧集重叠。发现污染时撤销相关结论并创建新 test version。

---

## 9. 测试与验收

- 相同 Plan 可重放关键指标和错误集合。
- 缺失/失败 shard 明确进入报告。
- Champion/Candidate 的 slice regression 可定位。
- LLM Judge 偏差与人工一致性被测量。
- correctness hard gate 不被成本/速度/Craft 提升覆盖。
- MLflow 删除或不可用不损坏项目 Artifact/Approval 真相。

