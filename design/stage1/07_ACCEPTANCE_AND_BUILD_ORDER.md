# Stage 1 Acceptance and Build Order

Version: 1.0

## 1. 构建顺序

### Milestone 1 — Contracts

- Pydantic/JSON Schema
- database naming/enums
- ArtifactRef、RationalTime、Error Envelope
- compatibility tests

退出：Schema 可生成、校验、版本迁移。

### Milestone 2 — Persistence

- PostgreSQL migrations
- Artifact/Blob/Dependency services
- local ObjectStore adapter
- commit/reconcile/sweep

退出：并发提交、崩溃恢复、失效图测试通过。

### Milestone 3 — Durable Execution

- Temporal dev deployment
- Command API
- Project Workflow
- dummy Activities、retry、heartbeat、cancel
- reconciler

退出：kill/restart/replay/idempotency 通过。

### Milestone 4 — Timeline Core

- RationalTime/Track/Item
- Patch/Validator/Diff
- OTIO adapter/LossReport
- invalidation integration

退出：round-trip、并发 Patch、依赖失效通过。

### Milestone 5 — Resource & Review

- Resource Profile、Task Queue、admission
- Review/Decision/Correction API
- Temporal Signal/Update/outbox
- RBAC

退出：资源水位、并发审核、Signal reconcile 通过。

### Milestone 6 — Production Operations

- OTel、metrics、logs、dashboard
- alert/runbook
- failure injection
- backup/restore/migration rehearsal
- worker versioning、canary、rollback rehearsal

退出：故障演练、全链路 trace、数据库恢复和 Workflow 兼容回滚通过。

---

## 2. 验收矩阵

| 维度 | 必须证明 |
|---|---|
| Contract | 版本、兼容、非法数据拒绝 |
| Persistence | immutable、checksum、CAS、blob 原子提交 |
| Dependency | 无环、精准失效、可重算 |
| Workflow | crash recovery、retry 分类、cancel、continue-as-new |
| Timeline | rational time、Patch、OTIO round-trip、LossReport |
| Concurrency | backpressure、公平、OOM 保护、冲突处理 |
| Review | stale 防护、RBAC、Decision delivery、Correction |
| Observability | trace/metric/log/cost/alert 完整 |
| Security | secret、签名 URL、rights、audit |
| Operations | backup/restore、migration、rollback、runbook |

回滚验收不能只证明旧镜像可以启动，还必须分别证明：

- Schema 在兼容窗口内可前滚、回切并完成数据对账。
- 历史 Workflow 可由对应 Build ID Worker replay 和继续执行。
- 配置、Prompt、模型可按版本恢复，且运行快照不漂移。
- Artifact 回退不覆盖历史版本，lineage、Decision 和 Audit Event 仍完整。
- Object Store 恢复后 checksum、引用计数与 PostgreSQL 元数据一致。

---

## 3. 端到端 Foundation Scenario

1. 提交 Project Command。
2. 启动 Workflow。
3. Dummy Media Activity 生成 Artifact/Blob。
4. Dummy AI Activity 生成带 Evidence/Confidence 的 Artifact。
5. 创建 Timeline 并应用并发 Patch。
6. 进入 Review，提交 Correction。
7. Dependency Graph 失效并重算。
8. Worker 在过程中被强制终止并恢复。
9. 完成 Run，查询完整 trace、cost、audit 和 artifact lineage。

必须做到无人工数据库修复、无重复正式 artifact、无丢失 Decision。

---

## 4. 性能测试

工作负载：

- 多 Project command burst
- 多 Episode dummy activities
- 大 Dependency Graph
- 大 Timeline Patch/serialize
- 多 reviewer concurrency
- staging blob 大量清理

输出：P50/P95、吞吐、内存、DB query plan、queue wait、失败恢复时间。

目标值必须在 Resource Profile 实测后确认。

---

## 5. 完成定义

- 所有 Milestone 退出条件通过。
- 数据库 migration 和 rollback 经演练。
- Worker canary、Build ID routing 和 Workflow replay rollback 经演练。
- Workflow replay 测试进入 CI。
- Failure injection 进入 CI/定期环境测试。
- 关键 dashboard 和 runbook 存在。
- Stage 2 可以仅通过 Worker/Artifact Contract 接入，不修改 Stage 1 核心语义。

---

## 6. 不得以此替代完成

- API 能返回 200 不代表 durable。
- Temporal UI 能看到 Workflow 不代表幂等正确。
- OTIO 能导出文件不代表 round-trip 无损。
- 有日志不代表可观测。
- 支持多个进程不代表具备资源安全并发。
- 单次 happy path 成功不代表生产就绪。
