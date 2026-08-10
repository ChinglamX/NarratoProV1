# Confidence Calibration

Version: 1.0

## 1. 目标

把模型/规则的原始分数转化为在明确任务、模型、类型和数据范围内可解释的正确率风险估计，为 L2/L3 路由提供依据。

输入：Shadow Predictions、adjudicated labels、risk/blocker taxonomy、slice metadata、Calibration Config。

输出：CalibrationModel/Rule、CalibrationReport、ConfidenceRecord、ThresholdCandidate、ApplicableScope、DriftBaseline。

---

## 2. 校准单元

每个校准器绑定：module/task、output type、provider/model/prompt/config family、genre/platform/language scope、risk class、dataset/guideline version 和时间窗口。

禁止跨任务复用含义，例如 ASR 0.9、身份 0.9 和 Story 因果 0.9 不能直接比较。配置或模型变化是否可沿用校准必须有兼容性证据。

---

## 3. 输入分数与特征

可使用 raw model score、ensemble agreement、evidence coverage、source quality、constraint conflicts、reviewer disagreement 和 OOD/drift features。LLM 自报概率只能作为弱特征，不能单独校准自动放行。

如果任务无法产生可靠分数，Confidence status 为 unavailable；不强迫所有 AI 输出伪精确概率。

---

## 4. 方法与评测

候选方法包括 Platt/logistic、isotonic、temperature scaling、分桶规则或任务特定校准器；通过独立验证集选择，不预设复杂模型更好。

报告：reliability diagram、Brier、ECE/maximum calibration error、coverage-risk curve、selective accuracy、severe false negative、review precision、automation coverage 和 confidence intervals。

平均 ECE 不能掩盖高风险 slice；身份/因果/rights 等严重类别单独设置上限。

---

## 5. 阈值选择

阈值来自显式成本/风险约束：先满足 severe false negative 和 blocker miss 上限，再在允许范围内优化人工审核量。候选 `0.85/0.60` 没有项目数据时不能直接成为生产阈值。

每个 ThresholdCandidate 包含适用范围、最小样本、置信区间、预期 coverage、review load、失败模式和 rollback policy。

---

## 6. 数据充分性

最低要求同时考虑样本量、正负/严重错误数量、类型/平台/语言覆盖、时间跨度和 reviewer quality。无严重错误样本不代表严重漏检率为零。

数据不足时保持 shadow；可使用保守规则转人工，但不能用合成样本完全替代真实人工标签。

---

## 7. 发布与生命周期

状态：shadow、candidate、approved、drifted、deprecated、revoked。批准后 CalibrationRef 写入 Automation Policy Snapshot。

Provider/Prompt/Config/schema 变化、输入分布漂移或高置信度严重错误可以使 scope drifted；路由立即回退到更保守 Policy，随后重新评测。

回滚恢复上一 Approved Calibration/Threshold，但创建新 Policy version；历史 RoutingDecision 不重写。

---

## 8. 并发与复现

预测/分桶/Bootstrap 可按样本和 slice 并行；模型选择和最终报告在固定 dataset snapshot 汇合。记录代码、依赖、随机种子、dataset、feature schema 和硬件。

完整校准离线运行，不阻塞生产；实时服务只读取已发布的轻量校准 artifact。

---

## 9. 测试与验收

- 完美校准、过度自信、欠自信、数据稀疏和无严重错误样本。
- 阈值边界、score unavailable、NaN 和 scope mismatch。
- 高风险 slice 退化能阻止批准或触发 drift。
- 模型/Prompt/Config 变化时兼容规则正确。
- 相同 dataset/config 可重现 Calibration Report。
- 未批准或 drifted Calibration 不能参与自动放行。

