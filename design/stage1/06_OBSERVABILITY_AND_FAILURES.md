# Stage 1 Observability and Failure Design

Version: 1.0

## 1. 目标

任何失败都能回答：哪个项目、哪个 Stage、哪个 Activity、使用什么输入/模型/配置、失败在哪里、是否重试、花费多少、影响哪些产物。

---

## 2. Trace

顶层 span：API Command。

子 span：

- Temporal Workflow/Activity
- Artifact read/commit
- provider inference
- FFmpeg subprocess
- Review wait/delivery
- invalidation/recompute

跨进程传播 trace context；Temporal event history 不是 tracing 的替代品。

---

## 3. Metrics

### Reliability

- workflow_started/completed/failed
- activity_attempts/retries/terminal_failures
- reconciliation_actions
- artifact_commit_conflicts
- stale_review_count

### Performance

- queue_wait_seconds
- activity_duration_seconds
- media_minutes_processed
- worker_memory/disk/gpu
- provider_batch_size

### Cost

- model_tokens/calls/cost
- compute_seconds
- storage_bytes
- render_seconds_per_output_minute

### Quality Process

- correction_count
- review_turnaround
- invalidation_fanout
- cache_hit_rate

高基数 ID 放 trace/log，不放 Prometheus label。

---

## 4. Structured Log

必备字段：timestamp、level、service、event、trace_id、project_id、run_id、workflow_id、activity_id、stage、artifact refs、attempt、error_code。

禁止记录：完整 Prompt 中的敏感内容、访问 token、签名 URL、未脱敏人脸/音色数据。

---

## 5. Error Envelope

```yaml
error_code: string
category: transient | resource | rate_limit | invalid_input | rights | quality | conflict | cancelled | internal
message: string
retryable: boolean
retry_after_s: integer | null
details: object
cause_chain: [object]
```

用户消息与内部诊断分离。

---

## 6. Failure Scenarios

| 场景 | 检测 | 行为 | 恢复 |
|---|---|---|---|
| Worker crash | heartbeat timeout | Temporal retry | 从 chunk cursor/缓存继续 |
| API/DB 短暂失败 | exception/health | backoff | 幂等重试 |
| 磁盘不足 | watermark | 停止 admission | 清理 staging/cache 后恢复 |
| 模型 OOM | process exit/metric | 降 batch/concurrency | 换 profile/provider 或转人工 |
| 外部 API 限流 | 429 | Retry-After | queue/backoff |
| Artifact version conflict | CAS failure | 不重试覆盖 | rebase/人工冲突处理 |
| Rights unknown | policy blocker | 停止 Release | 补充授权 |
| Review Signal 丢失 | delivery_pending | reconciler | 重发并去重 |
| Object Store commit 中断 | staging timeout | reconcile/sweep | 校验或清理 |
| Temporal 不可用 | health | API 接受 command 后 pending | 恢复后 reconciler 启动 |

---

## 7. Alert

告警：

- terminal failure rate
- queue wait P95
- repeated OOM
- staging blob backlog
- decision delivery pending
- PostgreSQL storage/connection saturation
- Temporal task queue no poller
- rights blocker approaching deadline
- cost budget exceed

每条告警关联 runbook，不创建无处处理的噪声告警。

---

## 8. Failure Injection

自动测试：

- kill -9 worker
- 在 blob commit 各步骤注入失败
- DB transaction deadlock/timeout
- duplicate/out-of-order Signal
- object store checksum mismatch
- model OOM/rate limit/invalid response
- disk high watermark
- migration 中断

验证无数据丢失、无重复正式产物、状态最终一致。

---

## 9. SLO 初始框架

不预填伪精确数字。先定义指标：

- command durability
- workflow recovery success
- artifact traceability completeness
- review delivery success
- terminal failure rate
- P95 queue wait

完成目标硬件和负载基准后设定 SLO 与 error budget。
