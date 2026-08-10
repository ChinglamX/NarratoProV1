# Automation Routing, Sampling and Drift

Version: 1.0

## 1. 目标

依据已批准 Automation Policy、校准 Confidence、风险和 blocker 状态执行可审计路由，并通过风险分层抽样与漂移检测保证 L2/L3 不降低质量。

输入：Artifact/Quality Events、ConfidenceRecord、AutomationPolicy Snapshot、CalibrationRef、Risk/Blocker State。

输出：RoutingDecision、ReviewRequest、SamplingDecision、DriftEvent、AutomaticDowngrade、RoutingAudit。

---

## 2. Policy 解析

作用域优先级：module/task override → run → project → system default。最终 Effective Policy Snapshot 记录 level、thresholds、required checks、blockers、sampling、fallback、calibration refs 和生效范围。

缺失、解析冲突、Calibration drifted/unavailable 或 required detector unavailable 时 fail closed 到 L1/人工。

---

## 3. 路由顺序

```text
Contract / Required Checks Complete?
→ Rights / Blocker / Conflict?
→ Scope and Calibration Valid?
→ Risk Class Allowed?
→ Threshold Decision
→ Sampling Policy
→ Route: auto-flow / suggest-review / required-review
→ Immutable Routing Audit
```

Blocker 和 rights 优先，Confidence 高低不能改变。所有自动流转都记录被检查项、未检查项、分数、阈值、scope、Policy 和原因。

---

## 4. L2 Confidence Routing

只对批准范围的低风险模块自动流转。阈值可设 auto-flow/review 两段，但必须来自 Calibration Report。阈值附近、opposing evidence、OOD、冲突或 unavailable 转人工。

Story/Strategy/Timeline 中高风险语义判断保持人工，除非该具体任务另有批准 Policy。Gate 3 无条件人工。

---

## 5. L3 风险分层抽样

Sampling 不是固定随机 10%。样本组合：

- uniform random baseline；
- threshold-near cases；
- rare genre/language/platform/provider；
- high-impact/high-cost artifacts；
- OOD/drift/high disagreement；
- recently changed model/prompt/config；
- historically severe-error neighborhoods。

每个 stratum 有目标样本、权重和审查频率。分析自动化真实错误率时必须使用抽样概率/权重，不能把风险过采样的原始比例当总体错误率。

---

## 6. Drift Detection

监控输入特征、score/uncertainty、quality/error、review correction、provider failure 和 slice mix。方法可包括 PSI/KS/分布距离、control chart、change-point 与规则阈值，按数据特性选择。

无标签的 feature drift 是预警，不等同质量下降；高置信严重错误、blocker miss 或 correction spike 是直接安全信号。

DriftEvent 声明 scope、baseline、window、metric、severity、evidence 和 recommended action。

---

## 7. 自动降级与恢复

严重错误、校准失效、required detector unavailable 或 drift 越界触发 scoped downgrade：L3→L2/L1、L2→L1。降级优先改变未来路由，不重写历史 Decision；必要时生成受影响已流转 artifact 的回顾审核任务。

恢复需要新数据、离线重评、审批和 canary，不允许指标恢复后自动无审批升级。

Kill switch 支持 system/project/module/provider scope，操作需 RBAC、reason、审计和过期/恢复流程。

---

## 8. 并发与一致性

路由是低延迟确定性服务，读取 immutable Policy Snapshot；同 Artifact/Policy idempotency key 只产生一个正式 Decision。Policy 更新不影响已开始 Run 的 snapshot，除非安全 kill switch 明确覆盖。

Sampling/Drift 离线或流式聚合，不阻塞生产；降级事件通过 Control Plane 原子发布新 Policy version。

---

## 9. 测试与验收

- 阈值边界、unavailable、scope mismatch、blocker precedence。
- L3 各 sampling stratum 和加权估计正确。
- 注入高置信严重错误、feature drift、correction spike 和 detector outage。
- downgrade/kill switch 在并发 Run 下行为一致。
- 自动恢复被禁止，重新升级必须审批。
- Release Gate 无论 Policy/Confidence 都不能 auto-flow。

