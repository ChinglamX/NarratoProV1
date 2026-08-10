# Stage 1 Workflow and Execution Design

Version: 1.0

## 1. Workflow 边界

一个 Project Run 对应一个 Temporal Workflow Execution。Workflow 只保存小型控制状态和 ArtifactRef，不传递媒体 blob 或大型模型 JSON。

Workflow 代码必须 deterministic：

- 不直接调用网络、数据库、文件系统、随机数和系统时间。
- 所有副作用进入 Activity。
- Workflow 变更使用 versioning/patch 策略，保证历史 replay。

---

## 2. ProjectProductionWorkflow

```text
ValidateCommand
→ ResolvePolicyAndResourceProfile
→ RegisterInputAssets
→ ExecuteStageGraph
→ AwaitReview（按 Policy）
→ RecomputeAffectedStages（有修订时）
→ CompleteRun
```

Stage 2–6 以后作为 Child Workflow 或 Activity Group 插入，Stage 1 先用 dummy/conformance activities 验证执行框架。

---

## 3. Workflow State

```yaml
run_id: uuid
project_id: uuid
effective_policy_ref: ArtifactRef
resource_profile_ref: ArtifactRef
stage_states: map[string, StageState]
active_review: ReviewRef | null
current_artifacts: map[string, ArtifactRef]
graph_version: integer
cancel_requested: boolean
```

媒体和完整 artifact payload 通过 Registry Activity 查询。

---

## 4. Signals 与 Updates

### Signals

- `submit_review_decision`
- `request_cancel`
- `notify_external_completion`

Signal 适合异步事件；handler 只验证最小 envelope 并写入 Workflow 内部队列。

### Updates

- `apply_correction`
- `change_priority`
- `request_recompute`

Update 需要同步返回接受/拒绝结果。Correction 的数据库提交由 Activity 完成，Update 等待 Activity 结果后更新 state。

### Queries

- `get_run_status`
- `get_pending_review`
- `get_stage_summary`

Query 不产生副作用，不查询外部数据库。

---

## 5. Activity Contract

```yaml
activity_request:
  activity_id: uuid
  run_id: uuid
  stage: string
  execution_key: string
  inputs: [ArtifactRef]
  config_snapshot: ArtifactRef
  resource_requirement: object
  output_contract: string

activity_result:
  execution_key: string
  outputs: [ArtifactRef]
  metrics: object
  warnings: [object]
```

Activity 必须：

- 先检查 execution_key 缓存/已完成记录。
- heartbeat 保存 chunk 游标。
- 在取消点响应 cancellation。
- 输出先校验 Schema，再 commit Artifact。
- 不把 partial artifact 标记 approved。

---

## 6. Timeout 与 Retry

每类 Activity 配置：

- Schedule-to-start：队列拥塞告警。
- Start-to-close：单次尝试硬上限。
- Heartbeat：长媒体任务存活检测。
- Schedule-to-close：包含所有重试的总上限。

错误分类：

- RetryableTransient：网络、临时服务、worker crash。
- RetryableResource：OOM/磁盘水位，先降并发或换队列。
- RateLimited：按服务 Retry-After/backoff。
- InvalidInput：不重试。
- RightsBlocked：不重试，转人工。
- ModelQualityFailure：可换 provider 或转人工，不能无限重试同模型。
- Cancelled：清理临时资源后结束。

禁止对所有异常使用同一指数重试。

---

## 7. Human Review

流程：

1. Activity 创建 review_request artifact/row。
2. Workflow 进入 AwaitingReview。
3. API 提交 Decision，数据库唯一约束防止重复。
4. API 发送 Temporal Signal。
5. Workflow 核对 request_id、target version 和 decision。
6. revise 触发 Correction Activity 和 dependency invalidation。
7. approve/reject 更新 Run 控制流。

Temporal 保存等待状态，PostgreSQL 保存审核业务记录；两者通过 reconciler 解决极端情况下的提交/Signal 间隙。

---

## 8. Reconciliation

定时 Reconciler 检查：

- command 已注册但 Workflow 未启动
- decision 已提交但 Signal 未送达
- artifact committed 但 stage_execution 未完成
- staging blob 超时
- Workflow 完成但 Run 状态未投影

Reconciler 只能执行幂等补偿，不直接猜测业务决定。

---

## 9. Continue-as-new

长项目 Workflow history 达到配置阈值时使用 Continue-as-new：

- 仅携带当前 ArtifactRefs、stage summary、policy 和 graph_version。
- 审核请求和数据库记录不复制。
- 新 execution 与同一 workflow_id/run_id 关联。

---

## 10. Child Workflow 粒度

建议：

- Project Run：Parent Workflow。
- Episode Intelligence：每 Episode Child Workflow。
- Variant Production：每 Variant Child Workflow。
- 单次 OCR/TTS/Render：Activity，不建 Child Workflow。

选择依据是独立生命周期、可见性和取消边界，不是单纯为了并发。

---

## 11. 测试

- Workflow replay 在代码升级后通过。
- Worker kill 后 Activity 从 heartbeat 恢复。
- Signal 重复/乱序不产生重复 Decision。
- DB commit 成功但 Signal 失败可 reconcile。
- Continue-as-new 不丢 ArtifactRefs。
- Parent cancellation 正确传播到 Child/Activity。
- 非 retryable 错误不会反复执行。

---

## 12. Worker 部署、Replay 与回滚

Workflow 代码升级必须保持历史可重放，不能把普通服务的“重新部署旧镜像”等同于工作流回滚。

- CI 使用脱敏后的生产 history corpus 执行 replay test。
- 非确定性逻辑、外部 I/O、当前时间和随机数只能位于 Activity，或使用 Temporal 提供的确定性 API。
- Workflow 行为变更使用显式 patch/version marker；兼容窗口内保留旧分支。
- Worker deployment 采用 Build ID / Worker Versioning，将新 Workflow 与存量 Workflow 路由到兼容 Worker。
- 先 canary task queue，再逐步放量；错误率、replay failure 或 queue latency 越界立即停止晋级。
- 回滚服务版本时，先验证旧 Worker 能消费目标 Build ID；禁止让不兼容 Worker 接管历史 execution。
- Activity 输出已提交后不做物理撤销；由补偿 Activity 创建新 artifact/version，并保留原始 lineage。

部署记录必须关联 git revision、container digest、Workflow Build ID、Schema version、config/prompt/model version。这样一次失败运行可以准确恢复执行环境，而不是猜测当时使用了什么代码。
