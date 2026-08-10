# Governance, Observability and Security

Version: 1.0

## 1. 目标

保障自动化、评测、反馈和线上数据的权限、审计、隐私、安全、成本和运行可见性，使任何自动决定与版本变化都能解释和追责。

输入：Policy/Version/Approval events、Routing/Review/Correction、Dataset/Performance access、Trace/Metric/Log、Security/Rights Policy。

输出：AuditTrail、AutomationDashboard、AccessDecision、Incident/Drift Alert、CostReport、GovernanceReviewPackage。

---

## 2. 角色与权限

权限至少区分：dataset reader/builder、evaluator、candidate author、approver、rollout operator、reviewer、release approver、security/admin。

关键分离：作者不能单独批准候选；评测服务不能写 Production pointer；Automation Router 不能批准 Release；线上 connector 不能修改创作 Artifact。

高风险操作使用强认证、最小权限、短期凭证和完整 Audit Event。

---

## 3. 审计

必须记录：谁在何时基于什么数据/评测批准什么版本，作用域、旧/新 pointer、canary cohort、Policy/Calibration、原因、风险、回滚目标和结果。

RoutingDecision、SamplingDecision、AutomaticDowngrade、KillSwitch、Release Gate、Dataset export 和线上数据访问均不可变审计。

日志不能替代审计表；审计保留策略与 legal hold 独立配置。

---

## 4. 可观测性

Trace：Quality Event → Detector → Calibration/Router → Review/Correction → Dataset → Eval → Approval → Canary → Promotion/Rollback。

Dashboard 按 module/scope 显示：

- blocker/severe false negative、detector unavailable；
- calibration error、coverage-risk、review precision；
- automation coverage、sampling coverage、correction rate；
- drift、downgrade、kill switch、rollback；
- benchmark/canary regressions、cost/latency；
- dataset freshness、label disagreement、online data completeness。

高基数 ID 进入 trace/log，不作为 Prometheus label。

---

## 5. 告警与响应

P0：Release 自动批准尝试、rights/security violation、大规模 blocker miss。

P1：高置信严重错误、required detector outage、错误 Policy rollout、Calibration drift。

P2：Review load/latency、cost、数据延迟或低风险指标异常。

Alert 必须关联 runbook、scope、owner 和自动/人工动作。P0/P1 优先 fail closed/kill switch，再调查，不等待聚合报告。

---

## 6. 数据安全与隐私

- Dataset/Performance 原始数据分级、加密、访问控制和保留期。
- 脱敏日志和最小上下文导出，避免暴露完整视频/声音/个人信息。
- 外部模型/评测前检查 data residency、合同和用途授权。
- 删除请求通过 lineage 传播到 Dataset/derived artifacts；模型已训练场景按治理政策处理和记录。
- Secret 使用 Secret Manager/环境注入，不写入 Config Artifact 或日志。

---

## 7. 成本治理

Benchmark、judge、canary 和抽样审核分别有预算。执行前估算，运行中限额，超限停止新增任务但保留已完成结果和完整性状态。

成本下降不能抵消 correctness 回归。报告单位成本、边际自动化收益、人工审核节省和严重错误风险，不只看 token。

---

## 8. 灾难恢复

备份 PostgreSQL registry/approval/audit、Object Store dataset/eval artifacts、Policy/Calibration snapshots。恢复演练验证 pointer、checksum、lineage 和 active rollback target。

MLflow 可重建/恢复，但不能成为唯一审批和业务真相源。外部线上源不可用时保留 raw snapshots 和 ingestion checkpoints。

---

## 9. 测试与验收

- RBAC 越权、作者自批、评测服务改 production、Router 自动 Release 均被拒绝。
- Audit 可重建一次 Policy 从候选到回滚的完整过程。
- P0/P1 注入触发 scoped fail closed/kill switch。
- 数据导出、删除、保留和 legal hold 测试。
- 预算耗尽不会产生不完整却标成功的评测。
- 灾难恢复后 active Policy、Calibration、Dataset 和 Audit 对账一致。

