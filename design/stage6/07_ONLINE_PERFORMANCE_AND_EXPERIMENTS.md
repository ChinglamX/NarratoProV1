# Online Performance and Experiments

Version: 1.0

## 1. 目标

在具有合法数据来源和可靠 Variant 关联时接入线上表现，区分描述性比较、准实验和受控实验，为 Strategy/Hook/Genre Config 提供适用范围明确的校准证据。

输入：ReleaseRecord、Platform Metric Events、Variant/Experiment Assignment、Context/Campaign metadata、Consent/Retention Policy。

输出：PerformanceWindow、DataQualityReport、PerformanceComparison、ExperimentResult、ApplicableScope、OptimizationCandidate。

---

## 2. 数据契约

ReleaseRecord 绑定 project/run/variant/render checksum、platform/account、publish time、external ref、campaign/traffic context 和 creative versions。

Metric Event/Window 记录 source、event time、ingest time、timezone、metric definition version、impressions、views、retention/watch/completion/engagement/conversion、denominator、missingness 和 corrections。

平台指标定义可能变化，必须保存 definition/source version，禁止直接比较不兼容口径。

---

## 3. 接入与质量

```text
Authorized Connector/File
→ Schema/Auth/Signature Validation
→ Idempotent Raw Ingest
→ Variant/Release Resolution
→ Metric Definition Normalization
→ Completeness/Latency/Anomaly Checks
→ Immutable Raw + Corrected Windows
```

无法唯一关联 Variant、曝光分母缺失、窗口未成熟或来源不可信时标 incomplete，不进入强结论。

---

## 4. 分析等级

### Performance Summary

单 Variant 描述性指标，不包含因果结论。

### Performance Comparison

多个 Variant 的观察性比较，必须列出平台分发、发布时间、账号、投放、受众和样本量等混杂因素。

### Quasi-experiment

存在匹配/控制策略但不是随机分配，报告假设和敏感性。

### Controlled A/B Experiment

需要预先假设、assignment、共同时间窗、分母、排除规则、样本量/停止条件和干预隔离。只有满足这些条件才能称 A/B Experiment。

---

## 5. 指标与统计

报告 effect size、confidence interval、sample size、missingness、multiple-comparison policy 和 practical significance。避免只看 p-value；小样本、低曝光和平台强分发偏差应输出 inconclusive。

Retention curve、3s retention、average watch、completion、interaction 和 conversion 分开解释。完播率受视频时长强烈影响，跨时长比较必须调整或分层。

不得由线上高表现推断 Story 事实正确，也不得用互动抵消 rights/technical blocker。

---

## 6. Variant 因果归因

VariantPlan 必须声明 changed dimensions。若 Hook、时长、文案、BGM、发布时间同时改变，结果只能归因于组合，不得声称某一元素造成提升。

实验污染、跨组曝光、平台二次分发、重复用户和外部投放变化进入 confounder/quality report。

---

## 7. 并发与重算

按 platform/account/date partition 增量 ingest；raw event/window immutable，平台迟到修正产生新 version。分析按 experiment/variant/slice 并行，最终在固定 data snapshot 汇总。

Metric definition 或 attribution 修正只重算分析层，不修改 Release、Strategy、Story 或 Fact。

---

## 8. 反馈边界

线上结果只能生成 Strategy/Hook/Genre/Audience/Duration candidate 或适用范围更新。候选仍需离线 correctness/craft 评测和审批。

高表现不能直接推广到其他类型、平台、账号或受众；ApplicableScope 记录样本范围、时间、版本和已知混杂。

---

## 9. 测试与验收

- 重复/迟到/乱序事件、时区、指标口径变化和缺失分母。
- Variant 无法唯一关联时拒绝强分析。
- 观察比较不会被标为 A/B Experiment。
- 多指标、提前停止、小样本和跨时长误判测试。
- 线上数据不能修改 Fact/Story 或绕过 Rights/Release。
- 相同 snapshot/analysis version 可重现结果。

