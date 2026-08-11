# Architecture Decisions

Version: 1.0

## 1. 目标

记录首批实施必须冻结的决策和变更条件，避免编码期间反复争论或无说明偏离核心架构。

输入：全局 Architecture Review 与 implementation blueprint。

输出：ADR Index、Decision、Rationale、Consequences、Revisit Trigger。

---

## ADR-001 — Modular Monolith First

决策：单仓库、共享 Contract/数据库/Object Store，多进程 Worker；不先拆微服务。

原因：个人生产环境、跨域事务和快速演进更需要一致性。部署单元已可独立扩展。

复议：明确团队/安全/扩展边界或单域独立容量证明拆分收益。

## ADR-002 — Temporal Owns Durable Execution

决策：Temporal 是唯一生产 Workflow 引擎；LangGraph 只用于 Activity 内 AI 子图。

后果：不维护第二套自研状态机；Workflow code 必须 replay-compatible。

## ADR-003 — PostgreSQL Metadata Truth

决策：Project/Artifact/Review/Policy 等事务元数据在 PostgreSQL；媒体 blob 在 Object Store；Temporal history 不复制进业务表。

复议：只在实测容量/可用性不足时演进，不因“更云原生”更换。

## ADR-004 — Immutable Artifact and Successor Correction

决策：正式 Artifact 不原地修改；Correction/rollback 创建后继版本或 active pointer event。

后果：存储增长需 retention/GC，但 lineage、审计和重放可靠。

## ADR-005 — One Master Timeline Schema

决策：ApprovedTimelineIntent、ConformedTimeline、Preview/Final 均引用同一 MasterTimeline Schema/Compiler 语义。

后果：Stage 5 actual-duration 通过 Patch 更新，不在媒体命令暗调。

## ADR-006 — Internal Timeline + OTIO Interchange

决策：内部 Schema 表达 Evidence/Dependency/Intent；OTIO 作为交换格式并输出 LossReport。

复议：若 OTIO 后续原生覆盖所有必要语义仍保留 adapter compatibility。

## ADR-007 — Provider-Agnostic AI and Media

决策：所有模型/工具通过 Provider Protocol 和项目 Contract；raw response 不进入下游业务。

后果：增加 adapter/benchmark 成本，换来模型、许可和硬件可替换。

## ADR-008 — Three Formal Human Gates

决策：Story、Strategy、Release 是正式 Gate；Timeline/Voice/Mix/Subtitle 是内部 Checkpoint。Release 永远人工。

后果：Review API 统一支持 gate/checkpoint，但权限和阻断规则不同。

## ADR-009 — Confidence Is Scoped and Calibrated

决策：模型自报概率不能自动放行；每个任务/模型/类型独立校准。无数据保持 shadow/unavailable。

## ADR-010 — Feedback Produces Candidates Only

决策：人工/线上反馈只能创建待评测 Candidate；生产配置需审批、canary、监控和回滚。

## ADR-011 — FFmpeg Execution, Typed RenderPlan Truth

决策：FFmpeg 是媒体执行器，RenderPlan/MixPlan/Timeline 是业务真相。命令以安全参数数组编译。

## ADR-012 — API Command/Query Separation

决策：长任务使用异步 Command/operation；查询读 projection，不用同步 HTTP 等待模型/渲染。

## ADR-013 — Transactional Outbox Before Event Broker

决策：PostgreSQL outbox + internal dispatcher/Temporal signal 满足首个生产部署，不先引入 Kafka。

复议：事件吞吐、跨服务解耦或独立消费者基准证明需要。

## ADR-014 — pgvector Before Specialized Vector DB

决策：初期语义检索使用 PostgreSQL/pgvector；只有 recall/latency/scale benchmark 不足才引入专用向量库。

## ADR-015 — Rights Fail Closed at Release

决策：理解流程可保留 rights unknown 素材证据，但任何 Release Candidate 的视频、声音、音乐、字体和图片必须 rights resolved。

## ADR-016 — Production Quality Without Premature Automation

决策：高标准实现不等于一开始启用 L2/L3。自动化需要真实校准；L1 可承载完整生产质量。

## ADR-017 — Bootstrap Toolchain and Local Infrastructure

决策：Python 锁定 3.11.8，使用 PEP 621/setuptools editable workspace；Web 使用 Node 22、pnpm 11.16 和 React/TypeScript/Vite lockfile。首个本地基础设施由 Compose 管理 PostgreSQL 16、Temporal、S3-compatible Object Store、OpenTelemetry Collector、Prometheus 和 Grafana。

原因：与目标 Mac 环境兼容，工具成熟且保持模块化单体部署；Python 与 Web 依赖均可由 CI 重建。镜像和直接依赖固定版本，不使用 `latest`。

后果：Python 依赖当前以受限范围声明，CI 安装结果受上游范围更新影响；在首个 Release Slice 退出前必须补充可审计的 Python resolution lock。基础设施镜像升级需 Compose 配置验证、迁移/恢复测试和 ADR State impact。

复议：目标运行平台改变、供应链策略要求统一 resolver，或实测服务版本存在不兼容。

## ADR-018 — Canonical Foundation Value Representation

决策：项目内部 ID 统一使用 UUIDv4 并由 Contract 边界拒绝其他 UUID 版本；媒体时间持久化为 `value:int64 + rate_num/rate_den`，rate 必须为正且约分为唯一形式；checksum 使用 `sha256:<64 lowercase hex>` 字符串。公共 Pydantic Contract 为 immutable、forbid-extra，并使用 UTF-8、sorted-key、无空白、禁止 NaN 的 canonical JSON。

原因：Python 3.11 原生稳定支持 UUIDv4，无需为 UUIDv7 引入运行依赖；精确 rational time 避免浮点漂移；字符串 checksum 与既有 Artifact/API 契约兼容；唯一序列化可作为内容寻址、幂等和 replay 的稳定输入。

后果：需要可排序 ID 的存储查询必须使用显式时间/序列列，不能依赖 UUID 顺序；外部历史 ID 进入系统前必须迁移为 UUIDv4；非整 tick 的 rate 转换 fail closed，不做隐式舍入。未来支持其他 checksum 算法或 UUIDv7 属 Contract 变更，必须带兼容迁移。

复议：数据库实测证明 UUIDv4 索引局部性成为瓶颈，或跨系统标准强制 UUIDv7/其他 digest；复议不得改变已有 ArtifactRef 的解释。

## ADR-019 — Confidence and Rights Fail-Closed Semantics

决策：`ConfidenceRecord` 的 score 仅允许 0–1 有限值；unavailable 不携带 score/calibration，shadow 不得声明生产 calibration，calibrated 必须引用 calibration version，所有状态必须声明 method 和 applicable scope。`RightsMetadata` 是不可变授权快照；cleared 必须包含来源、license、typed RightsGrantRef、地域和平台范围。发布资格必须由调用者提供显式 UTC 时间、平台和地域进行确定性判断，unknown/restricted/expired/revoked 一律产生 blocker。

原因：Confidence 是可解释评估而非授权；权利检查优先于分数并必须可审计、可重放。禁止读取系统当前时间可保证 Workflow replay 和历史 Release Review 一致。

后果：B02 不实现自动路由，也不把 shadow score 当通过条件；完整 `ApplicableScope` 留给 B05，当前使用非空稳定 scope 描述。Rights scope 缺失不解释为全球授权，必须显式登记。后续 RightsGrant/RightsManifest payload Schema 在保留 typed ref 兼容性的前提下扩展。

复议：只在 B05 scope Schema 或法务权利模型提供兼容迁移时调整字段；不得放宽 unknown rights 的 Release blocker。

## ADR-020 — Envelope Identity and Public Error Boundary

决策：Command/Event payload 只接受 JSON object；schema_version 使用三段 SemVer；所有 envelope 时间使用 UTC。Command 以 command_id 和 client idempotency_key 标识意图，Event 以 event_id 作为消费者幂等键并携带 W3C 32 位非零 lowercase trace ID。内部 `ErrorEnvelope` 与 `PublicErrorEnvelope` 分离；只有显式标记 public 且不携带任意 data 的 ErrorDetail 可投影到公共响应，internal_message 和内部 data 永不投影。

原因：确定性 JSON、稳定身份和时间语义支持 outbox/replay/跨语言消费；显式 disclosure boundary 比按关键词猜测 secret 更可审计。HTTP status 不替代稳定业务 error code。

后果：provider raw response、stack、文件路径、签名 URL 和 secret 只能作为 internal detail/log artifact；公共 message/remediation 必须由调用方使用审核过的稳定文本。B03 保存最小字段形状快照用于发现破坏性变化；完整 JSON Schema/OpenAPI/TS registry 由 B04 唯一生成。

复议：Trace Context 标准或跨语言兼容策略变化时通过版本迁移复议；不得把内部诊断重新并入公共 DTO。

---

## 2. ADR 变更流程

变更必须提交：问题证据、替代方案、影响范围、Contract/Schema/Workflow migration、benchmark、安全/rights、部署和 rollback。批准后更新本文件、受影响设计与测试。

禁止通过代码依赖或临时配置事实性改变 ADR，而不留下决策记录。

---

## 3. 测试与验收

- CI/architecture tests 能验证 ADR-002/005/007/008/012 的关键边界。
- 任何新基础设施依赖关联 ADR 和 benchmark。
- Schema/Workflow breaking change 关联 migration/replay ADR。
- Review Director 可从 Audit 重建一次例外和回滚决定。
- ADR Index 与实际代码/部署不存在已知偏离。
