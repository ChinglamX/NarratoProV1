# Candidate Release and Rollback

Version: 1.0

## 1. 目标

对 Prompt、Model、Provider、Config、Rubric、Calibration 和 Automation Policy 候选执行审批、灰度、晋级、监控和回滚，防止反馈优化绕过生产治理。

输入：Candidate Version、EvaluationComparison、Risk/Compatibility Report、Rollout Policy、Approval Command。

输出：ReleasePlan、ApprovalDecision、CanaryAssignment、ProductionVersionRef、RollbackTarget、ReleaseAudit。

---

## 2. 候选生命周期

`draft → evaluation → candidate → approved_for_canary → canary → staged → production → deprecated/revoked`。

状态转换需要角色权限和证据。评测系统可以提出 PromotionRecommendation，但不能自行批准。

每个 Candidate 指定 owner、scope、dependencies、Contract compatibility、migration、resource/cost delta、known risks、monitoring、rollback target 和 expiry。

---

## 3. 审批分离

- Candidate 作者不能单独完成最终生产审批。
- 高风险 Policy/Calibration/rights 变更需要 AI System Engineer 与质量负责人共同签收。
- 创意 Prompt/Rubric 需要 Producer/Review Director 评测证据。
- 权限由 RBAC 管理，Decision 写 Audit，不依赖聊天消息作为批准依据。

---

## 4. Canary 与 cohort

灰度按 project/type/language/platform/provider/resource cohort 隔离，并配置流量、时间、最小样本、hard stop、comparison baseline 和人工抽样。

Canary Run 固定 Candidate Snapshot；不能在运行中漂移到最新版。与 Champion 尽量使用配对输入，避免把素材差异误判为候选效果。

高风险 automation policy 先 shadow，再只影响 Review suggestion，最后才允许有限 auto-flow。

---

## 5. 晋级标准

必须满足：correctness/blocker non-regression、severe false negative、calibration、关键 slices、资源/成本、稳定窗口、review feedback 和 rollback rehearsal。

自动化覆盖提升只是收益指标，不是 hard gate。任何新严重错误可阻止晋级，即使总体均值提升。

---

## 6. 回滚

Rollback Trigger：严重错误、detector miss、calibration/drift、provider outage、资源/成本失控、rights/security、schema/replay failure。

操作：

1. 激活已验证 RollbackTarget 或保守 L1 Policy。
2. 停止新 Candidate assignment。
3. 保留运行中 snapshot，按风险决定取消或完成。
4. 生成受影响 cohort/artifact 回顾审核任务。
5. 保存触发证据、时间、operator、影响与恢复计划。

回滚不删除 Candidate/Run/Decision。Rights/security 紧急 kill switch 可以覆盖运行 snapshot，但必须审计。

---

## 7. 兼容与依赖

Prompt/Model/Config/Policy 是组合版本，回滚必须验证完整依赖，不只替换一个 ID。Schema 使用 expand/migrate/contract；Workflow code 通过 replay/Worker versioning。

Embedding/Calibration/Index 等不兼容派生资产必须选择匹配版本或重建，禁止混用。

---

## 8. 并发与一致性

Control Plane 原子发布 active version pointer；worker 在 Run 开始解析并固定 snapshot。并发审批使用 expected candidate version；重复命令幂等。

多 cohort 可并行 canary，但共享全局风险/预算上限。Promotion/Rollback 单 scope 串行，避免竞态切换。

---

## 9. 测试与验收

- 未评测、未批准和过期 Candidate 无法进入 canary。
- canary cohort、snapshot、paired baseline 和 hard stop 正确。
- 注入严重错误、成本失控、provider outage 和 schema incompatibility。
- 自动回退到 L1/Champion 后新路由立即生效。
- 回顾审核覆盖受影响 artifacts。
- rollback rehearsal 可在规定时间内完成且 lineage 不丢失。

