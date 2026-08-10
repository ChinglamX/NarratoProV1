# API and Command Model

Version: 1.0

## 1. 目标

定义外部 HTTP API、内部 Command/Query/Event 的一致语义，使长任务、人工审核、局部修正和媒体访问可恢复、可追踪、可生成客户端。

输入：Stage 1–6 use cases、Review/Artifact/Workflow contracts。

输出：API Resource Model、Command/Query/Event Catalog、Idempotency/Error/Concurrency Rules。

---

## 2. API 原则

- FastAPI/OpenAPI，路径按稳定业务资源而非内部 Stage 编号。
- 写操作提交 Command，立即返回 `operation_id/run_id/resource_ref`，不持有长连接等待模型/渲染。
- 查询从 PostgreSQL read model/Artifact Registry 获取，不通过 Temporal history 拼 UI。
- 所有修改使用 expected version/ETag 和 idempotency key。
- 所有响应包含 trace/request ID；错误使用统一 Error Envelope。
- 大媒体通过受控 upload/download session 或签名 URL，不穿过 JSON API。

---

## 3. 公共资源 API

```text
POST   /v1/projects
GET    /v1/projects/{project_id}
POST   /v1/projects/{project_id}/assets:ingest
POST   /v1/projects/{project_id}/runs
GET    /v1/runs/{run_id}
POST   /v1/runs/{run_id}:cancel
GET    /v1/runs/{run_id}/stages
GET    /v1/artifacts/{artifact_id}/versions/{version}
GET    /v1/artifacts/{artifact_id}/lineage
POST   /v1/media-access:issue
```

Run command 指定 objective/stage range、input refs、effective config/resource/automation refs 和 client idempotency key。

---

## 4. Domain API

```text
GET/POST  /v1/intelligence/...       # catalog/fact/story queries and commands
GET/POST  /v1/strategies/...         # candidates, comparison, correction
GET/POST  /v1/timelines/...          # timeline, patch, proposal, preview
GET/POST  /v1/production/...         # voice, mix, subtitle, render, QC
GET/POST  /v1/evaluations/...        # benchmark, calibration, policy candidate
GET/POST  /v1/reviews/...            # requests, decisions, correction entry
GET/POST  /v1/configs/...            # draft/validate/publish/deprecate
GET/POST  /v1/providers/...          # capability/health/approval metadata
GET/POST  /v1/rights/...             # assets, grants, checks, manifests
```

详细 endpoint 随 Epic 增量生成，但 mutation 命名优先使用显式动作：`:approve`、`:reject`、`:publish`、`:rollback`、`:merge-identities`，避免语义不清的通用 PATCH。

Timeline 等专业编辑使用 `POST /timelines/{id}:apply-patch`，payload 是 typed semantic operations。

---

## 5. Command Envelope

```yaml
command_id: uuid
command_type: string
schema_version: string
project_id: uuid
run_id: uuid | null
actor: ActorRef
idempotency_key: string
expected_version: integer | null
inputs: [ArtifactRef]
effective_config_ref: ArtifactRef | null
payload: object
requested_at: datetime
```

Command 接收流程：auth/RBAC → schema → business precondition → idempotency register → DB commit/outbox → Workflow start/signal。HTTP 成功只表示命令被持久接受，不表示长任务完成。

---

## 6. Query 规则

列表采用 cursor pagination、稳定排序和 filter allowlist。查询返回 public DTO，不暴露 SQLAlchemy model、provider raw response 或 Object Store 路径。

媒体时间码查询支持 source/timeline range；Evidence response 返回受控 preview/access ref。Graph/Timeline 大对象支持 summary、section、version/diff 查询，避免每次返回全量。

一致性字段：`resource_version`、`as_of`、`projection_status`。Workflow 刚提交但 read model 尚未投影时，客户端能识别 pending，而非误判丢失。

---

## 7. Review 与 Gate API

```text
GET  /v1/review-requests?state=awaiting
GET  /v1/review-requests/{id}
POST /v1/review-requests/{id}:decide
POST /v1/review-requests/{id}:request-correction
POST /v1/corrections
GET  /v1/corrections/{id}/impact
POST /v1/corrections/{id}:apply
```

Decision payload 必须引用 exact target version、gate/checkpoint、blockers/reasons 和 expected request version。Release Decision 额外要求 Rights Manifest/QC/Quality refs。

内部 Timeline/Voice/Mix Checkpoint 使用 `checkpoint_type`，不得伪装为第四个正式 Gate。

---

## 8. Event Envelope

```yaml
event_id: uuid
event_type: string
schema_version: string
aggregate_id: string
aggregate_version: integer
project_id: uuid
run_id: uuid | null
occurred_at: datetime
producer: string
trace_id: string
payload: object
```

事件通过 transactional outbox 发布；消费者用 event_id 幂等。首个部署可由内部 dispatcher/Temporal signal 消费，不要求先引入 Kafka。

---

## 9. Error Envelope

至少包含 code、category、message、retryable、details、request/trace ID、resource/version、remediation。HTTP status 只表达 transport 类别，业务原因由稳定 error code 表达。

分类：validation、conflict/stale、permission、rights/policy、resource/budget、provider、workflow、media、quality_blocker、internal。

日志可包含内部堆栈，公共响应不得泄露 secret、路径、签名 URL 或 provider 敏感原文。

---

## 10. 测试与验收

- OpenAPI snapshot/compatibility 和生成客户端测试。
- idempotency、expected version、重复/乱序 Decision。
- 命令 DB commit 后 Workflow start 失败由 reconciler 恢复。
- 大资源分页/diff 和 projection lag 语义。
- RBAC、媒体 URL 过期、路径/协议注入和错误脱敏。
- UI 不使用任何未登记 private endpoint。

