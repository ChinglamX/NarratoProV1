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

## ADR-021 — One Versioned Contract Registry

决策：Pydantic Contract 与代码内 Artifact Catalog 是唯一生成源；JSON Schema Draft 2020-12、OpenAPI 3.1 components、Artifact Type Registry 和 Review Web TypeScript 类型由同一确定性生成器输出。审计版本保存在 `generated/contracts/versions/<semver>`，已存在版本禁止覆盖；兼容新增升级 minor/patch，删除 Schema/字段/enum、增加 required、收紧类型/约束或改变 Artifact owner/domain 必须升级 major。设计 Catalog 与代码 Registry 在 CI 双向核对。

原因：跨 Python/API/Web/Workflow 使用同一数据语言，避免手写 Schema 漂移；保留不可变版本才能比较真实 breaking change，而不是用新快照覆盖旧证据。ArtifactRef 在 Python 和生成 Schema 中都拒绝未知类型。

后果：公共 Contract 变更必须同时更新 Registry version、生成物、兼容测试和必要迁移；`make schema-check` 是 `make check` 的强制步骤。B03 临时 shape snapshot 已删除并由 Registry 版本链取代。生成器只负责 Contract 转换，不承担 B05 领域模型或 B04 之后的 Artifact payload 实现。

复议：只有跨语言 Schema 标准或生成器能力无法表达已批准 Contract 时复议；替换工具必须保持版本历史、输出等价性和回滚能力。

## ADR-022 — Evaluation Truth and Fail-closed Routing

决策：Quality、Correction、Dataset、Evaluation、Calibration、Scope 和 Routing 使用不可变公共 Contract。S0 必须是 blocker，S3 只能表示创意偏好且不能成为 blocker；`unresolved` 与 detector/reviewer `disagreement` 保留为一等状态，禁止平均或强行改写为二元标签。Correction 只描述同一 Artifact lineage 的后继版本并保存结构化 semantic operation。Dataset、Evaluation 和 Calibration 必须保存精确输入版本与父版本 lineage。

RoutingDecision 只记录已经解析的决策，不替代 Automation Policy 引擎。Release Gate、L0/L1、required check 缺失、blocker、rights risk、conflict、unresolved、disagreement、shadow/unavailable/drifted Confidence 或 Calibration 缺失一律 fail closed 到 required review；auto-flow 只允许 calibrated Confidence。`ApplicableScope` 必须显式绑定 module/task/output/provider/model/config/schema、类型、语言、平台和 risk class，不允许空维度代表“全局适用”。

原因：自动化安全依赖可重放的真实问题、人工差异和适用范围，而不是模型自评分或模糊总分。把安全不变量放入 Schema validation，可在持久化、API、Workflow 和 Web 接入之前阻断不合法状态。

后果：Registry 以兼容新增升级到 v1.1.0；B02 的字符串 `ConfidenceRecord.applicable_scope` 为保持 v1 输入兼容暂不替换，B05 结构化 `ApplicableScope` 用于 Calibration/Routing，未来统一字段需 major migration。当前仍为 L1/Shadow；这些 Contract 不授权任何 L2/L3 自动流转。

复议：只在真实 Calibration Pack、Policy engine 和数据库迁移证明需要调整时复议；不得放松 Release 人工确认、blocker precedence 或 unresolved/disagreement fail-closed。

## ADR-023 — Canonical Cross-domain Payload Contracts

决策：E01 在进入持久化前冻结 Artifact Envelope，以及 Media、Fact/Evidence、Story、Strategy 和 Timeline 的跨域 payload Contract。Envelope 只承载身份、版本、producer、lineage、checksum、rights class、trace 和 payload location；领域 payload 保持独立，禁止把整个业务对象塞入无类型 metadata。Registry v1.2.0 以兼容新增发布并保留 v1.0.0/v1.1.0。

Catalog 第 6 节的 canonical Artifact lifecycle（staging、committed、approved、stale、superseded、blocked、deleted_logically）高于 Core Data Contracts 中早期示例状态；Review/Run 状态不混入 Artifact。Artifact Contract 能拒绝 payload 缺失、重复输入和当前/未来版本自依赖；“approved 不引用 rejected input”和版本单调性需要 E02 Repository 在事务快照中校验，不能由孤立 Envelope 伪装完成。

Fact 只表达可观察值并强制 Evidence；Story 的关键 Event 和 Edge 强制 Evidence 且 Graph 引用闭合；Strategy 强制 Story/Evidence grounding、Hook continuation 和结构差异；MasterTimeline 是唯一成片时间真相源，Item 全局稳定 ID、边界和 Patch optimistic CAS 在 Contract 层 fail closed。Provider raw response 不进入这些公共 payload。

原因：E02 数据库、E04 Timeline、E05–E09 业务实现都依赖稳定跨域语言。先冻结最终 payload 可避免各模块以私有 JSON 建立第二真相源，同时仍把需要数据库快照或业务查询的约束留给正确层级。

后果：原实施 Backlog 的 Evaluation/Correction B05 保留实现证据并规范重编号为 B11；用户指定的 B05–B10 成为 E01 补全序列。历史 commit/Handoff 不重写。后续领域演进必须通过 Registry SemVer；新增可 optional/minor，收紧或改变既有输入语义必须 major + migration。

复议：只有真实实现证明 Contract 无法表达必要语义时复议；不得以 ORM、OTIO、FFprobe JSON 或模型输出替代 canonical Contract。

## ADR-024 — PostgreSQL Transactional Artifact Core and Local Object Store

决策：E02 使用 PostgreSQL 16 + SQLAlchemy Core 2 + Alembic 作为 Project/Run、Artifact/Version/Dependency、Command、Review/Correction、Policy/Config/Rights、Audit/Outbox 的事务真相源；`psycopg[binary]` 是首个 Python PostgreSQL 驱动。初始 revision `0001_e02` 绑定不可变 `baseline_v0001` metadata，后续 revision 禁止反向修改该快照。

Artifact version commit 对 artifact identity 行加事务锁并执行 expected-latest CAS；payload/checksum/producer 不更新，active pointer 和 state transition 单独表达状态。Artifact 与 Outbox 在同一事务写入。依赖以 exact-version edge 保存，写入前做有界 cycle check；失效使用 project-scoped PostgreSQL advisory transaction lock、BFS closure 和不可变 InvalidationDecision，不物理删除下游产物。

Object Store 通过 Port 隔离。首个 adapter 是同文件系统 LocalObjectStore：`staging/<run>/<activity>.part` 流式 SHA-256、fsync、content-addressed atomic rename；路径穿越、checksum mismatch 和已提交对象删除 fail closed。数据库 Blob staging/committed row 与对象提交通过可 reconcile 协议关联。扩展到 S3-compatible backend 时必须保持 checksum、commit visibility 和 orphan reconciliation 语义。

Config/AutomationPolicy/ResourceProfile/Rights 使用不可变版本或 snapshot；publication pointer 使用 CAS，unknown rights 继续阻断 Release。Command idempotency 使用唯一 key + request checksum：同 key/同请求返回原记录，同 key/不同请求冲突。

原因：E03–E05 需要可恢复、可并发、可追踪的真实持久化内核，SQLite 或应用层“先查后写”不能证明 PostgreSQL 约束和事务语义。Blob 与元数据职责分离，避免数据库存大媒体，也避免物理路径泄漏到领域 Contract。

后果：E02 migration 必须在真实 PostgreSQL 执行 upgrade/downgrade/upgrade，并做 pg_dump/pg_restore 对账；生产数据库 downgrade/drop 仍需备份和审批。当前 LocalObjectStore 是正式单机 adapter，不代表 MinIO/S3 adapter 已完成。Python resolution lock 仍是供应链未决项。

复议：只有 PostgreSQL/Object Store 实测容量、延迟或可靠性不满足目标时复议；不得牺牲 immutable lineage、CAS、transactional outbox 或 rights fail-closed。

---

## ADR-025 — Durable Workflow, DB-first Review and Shadow Automation

决策：E03 使用 Temporal `ProjectRunWorkflow` 保存可重放的小状态与 exact Artifact pointer；所有外部 I/O 仅在 Activity 执行。Activity 使用稳定 execution key、显式 timeout/heartbeat/retry 和 non-retryable error type。Worker restart 后由 Temporal history 恢复，Workflow signal 按 `review_id` first-wins 去重；breaking Workflow 修改必须先做 history replay。

Command、Run、Review Decision、Correction 和其 outbox event 先在 PostgreSQL 同事务提交，再由 reconciler 启动 Workflow 或发送 Signal。Temporal 暂时不可用时 API 返回 accepted/delivery_pending，禁止“先 Signal 后落库”。Review target 使用 expected version；Correction 只创建不可变后继版本并用 active pointer CAS，不接受整份 payload 覆盖。Release 仅允许 human `release_approver`，service account 永远不能批准发布。

资源准入使用 queue capacity + project in-flight + CPU/GPU/memory/disk/cost 水位和有界 lease；未知 queue 或超预算 fail closed，过期 lease 可恢复。日志透传 trace context 并递归脱敏；metrics labels 使用固定低基数 allowlist，Project/Run/Artifact/Workflow/Trace ID 禁止作为 label。

Confidence 和人工 Correction 在 E03 只记录 Shadow calibration example。缺少 model/prompt/config version 时明确 `incomplete`，不得猜测补齐；任何 shadow example 均无 routing authority。Automation 保持 L1，Release 保持人工。

原因：durable orchestration、审计事务和人工 Gate 是后续 Timeline/Media/AI pipeline 可恢复、可校准的共同底座；将业务 payload 塞入 history、先发送 Signal 或用未校准 confidence 路由会产生不可重建状态与质量风险。

后果：outbox dispatcher 的生产常驻进程和 dashboards 会随部署切片继续增强，但持久语义不得改变。Workflow 演进需保留 replay fixture；资源容量需按真实 workload 校准；L2/L3 仍需 E12 的数据和审批。

复议：只有真实吞吐/可用性证据证明 Temporal/PostgreSQL outbox 或 lease controller 不满足目标时复议；不得取消 DB-first、Release human、immutable correction 或 replay guarantee。

## ADR-026 — Canonical Timeline, OTIO Loss Boundary and Preview Toolchain

决策：`MasterTimeline` 是内部唯一剪辑真相，精确时间继续使用整数 tick + rational rate；Validator、semantic Patch、Diff、rebase 和 RenderPlan compiler 为无状态纯逻辑。同一 Timeline 以 Artifact active pointer CAS 提交不可变后继版本；旧 base 修改不同 Item 可在 expected item version 未变时语义 rebase，触及相同 Item 必须返回 Conflict，禁止 last-write-wins。

OpenTimelineIO 固定 `0.18.1`，仅作为交换边界，不替代内部 Schema。标准 Clip/Track/Range/Transition 映射到 OTIO，NarratoPro identity/evidence/dependency/rights 字段保存在 `com.narratopro.v1` metadata；导入缺失或无效 metadata 必须输出 `LossReport`，不得覆盖 canonical/approved Timeline。

首个 Timeline Preview toolchain 固定宿主 FFmpeg/FFprobe `8.1.2`。同一 TimelineRef、ProfileRef、toolchain version 生成确定性 RenderPlan checksum。Foundation Preview 使用固定色画面、测试音、ASS sidecar，输出 H.264/AAC 720×1280；Temporal Activity 只接收 exact pointer，从 PostgreSQL 加载 Timeline，渲染后持久化独立 ProxyRender Artifact、generation dependency 和 outbox，再等待人工 Timeline Checkpoint。Artifact identity 使用 UUIDv4；重复执行按 exact Timeline dependency 查询已提交产物。

原因：剪辑语义不能由 FFmpeg 命令、OTIO 文件或 UI 本地状态反向定义；精确时间、Item identity、并发冲突和 loss accounting 是后续节奏、解说、音频、字幕与最终渲染一致性的地基。

后果：OTIO/FFmpeg 升级必须做 golden round-trip、history replay、RenderPlan checksum migration 和真实 QC。当前 Homebrew FFmpeg 未包含 libass filter，因此 Foundation Preview 保留 ASS sidecar而不伪称已 burn-in；Stage 5 字幕生产必须使用经许可且具备 libass/字体控制的锁定构建。Fake Preview 证明接口和恢复性，不代表成片质量能力。

复议：只有实际编辑器互操作或媒体兼容基准证明当前版本不足时复议；不得引入第二套 Timeline 真相或静默丢失 metadata。

## ADR-027 — Media Identity, Probe Boundary and Catalog Review

决策：E05 的 Artifact identity 继续严格使用 UUIDv4。重复/并发导入不使用 UUIDv5 或伪造 version bits，而由 PostgreSQL `media.ingest_identity` 以 `(project_id, source_checksum, profile_version, role)` 唯一键分配并复用 identity；配置版本变化产生独立派生身份。Blob 继续按流式 SHA-256 + size 去重，Artifact、Blob 和 dependency 保持分离。

FFprobe/FFmpeg 固定使用验收宿主 8.1.2；FFprobe raw response 仅保存在 MediaProbe Artifact，公共 Media Contract 只接收规范化的 stream/timebase/VFR/rotation/audio 元数据。代理、单声道 16k PCM 音轨和抽帧以临时 `.part` 完成后原子发布；SourceTimeMap 使用 rational time。PySceneDetect 固定 0.7.1 AdaptiveDetector，输出 Confidence=`shadow`，镜头边界不是剧情事实，人工 split/merge 通过 canonical Correction 后继版本处理。

MediaIngestWorkflow 只在 Activity 中执行文件、数据库和媒体 I/O，具备 heartbeat、retry 和媒体队列资源准入；完成后在 L1 等待人工 Catalog Review。unknown/restricted rights 允许隔离导入和分析，但始终阻断 Release。真实 `youzijuchang_demo.mp4` 只证明技术 ingest/categorization，不证明 Speech、Visual、Fact、Story 或成片质量。

原因：Canonical UUID、并发幂等、provider raw boundary、精确时间与权利阻断是后续 E06–E09 可重建的地基。依赖文件名、JSON 扫描或模型置信度自动批准会制造身份冲突和错误能力声明。

后果：migration `0002_e05_media_identity` 必须先于 E05 Worker 部署；profile/toolchain 升级需重新生成派生物并做兼容基准。当前本地路径只作为受信 Worker 输入，面向外部的 resumable upload/session adapter 尚需部署切片完成。Automation 保持 L1，Confidence 保持 Shadow。

复议：只有真实并发、容量或媒体兼容 benchmark 证明 identity registry/FFmpeg/PySceneDetect 不满足目标时复议；不得放松 UUIDv4、rights fail-closed、raw/normalized 边界或人工 Release。

## ADR-028 — Provider Gateway and Raw Observation Boundary

决策：所有 Stage 2 感知 Provider 实现统一 `package/validate/estimate/infer/health` Port。Gateway 在推理前依次验证 capability、production/research/blocked admission、代码与模型权重许可、commercial scope、execution location、data residency、cost、RAM/accelerator memory 和 health；任何缺失或越界均 fail closed。Provider `infer` 只返回进程内 `ProviderRawOutput`，不得自行分配 Artifact identity 或写领域数据库。

原始响应由 application service 立即写 Object Store 并提交 `RawProviderResponse` Artifact，记录 exact input/config/resource refs、ProviderIdentity、request/payload checksum、media type、provider schema、trace 和 rights class。下游只接收 capability-specific normalized ArtifactRef；Gateway 不提供万能 JSON Observation。ASR/OCR/Detection 等 typed payload 分别由 G03/G04 以 Registry minor evolution 引入。

错误分类固定区分 invalid input、policy/rights blocked、resource exhausted、rate limited、timeout、unavailable、malformed response 和 internal；不可重试错误在 Contract 层禁止标为 retryable。Provider 不可用时显式 unavailable/manual，禁止返回空结果冒充成功。Confidence 保持 Shadow，Provider admission 不等于输出自动批准。

原因：模型替换、许可证、数据出境、资源预算和 raw schema 漂移都必须在公共领域边界之外被治理；让 adapter 创建业务 Artifact 或让下游解析私有 JSON 会形成第二真相源并破坏可替换性。

后果：Registry 兼容升级到 1.3.0，新增 Provider contracts 和 `RawProviderResponse` Artifact。G02 benchmark、G03 Speech、G04 Visual 必须复用此 Gateway；具体 Provider 只能在许可、checksum、数据政策和 benchmark 齐全后进入 production admission。

复议：只有真实 Provider 无法通过该 Port 表达必要的 streaming/batch 行为时扩展接口；不得取消 raw/normalized 隔离、执行前 policy admission 或 explicit unavailable。

## ADR-029 — Series-isolated Provider Benchmark Evidence

决策：Provider 评测以版本化 `BenchmarkDataset`、`BenchmarkPredictionSet` 和 `ProviderBenchmarkReport` 表达。每个 case 必须绑定 series/episode、split、Source ArtifactRef、slice、annotation guideline 和 gold；同一 series 不得跨 development/validation/frozen_test，Frozen Test 禁止 tuning。Prediction 必须二选一表达 value 或 failure，并关联 ProviderIdentity、raw/normalized refs、latency、cost 和 severe errors。

指标按 capability/slice/metric version 分开，严重错误 taxonomy 使用 S0–S3 独立计数；总体平均不得掩盖否定、人名、金额、身份串线等风险。失败与缺失 case 进入 incomplete，不从 denominator 静默消失。Benchmark report 固定 code revision、dependency lock checksum、hardware、seed 和 prediction lineage。

G02 的仓库 fixture 只验证工程可重放性，明确为 synthetic/not-production；未建立合法真实标注集前 `admission_thresholds_declared=false`。生产门槛只能在 G03/G04 真实 baseline 后通过版本化 Quality Profile 和人工审批建立。

原因：公开榜单、单一 demo 和总体准确率无法证明短剧域严重错误风险；按剧隔离与逐样本 lineage 是可校准、可回归和避免数据泄漏的前提。

后果：Registry 兼容升级到 1.4.0，新增 benchmark contracts 和两个 Artifact Types。G03/G04 必须在同一 Harness 上增加 capability-specific metrics，不能为追求分数修改 Frozen Test 或隐藏 unavailable。

复议：只有评测任务需要非 series 分组时增加显式 leakage group；不得取消 Frozen Test 隔离、严重错误单列或逐 prediction lineage。

## ADR-030 — Typed Speech Boundary and Research-first FunASR Admission

决策：G03 的正式领域边界为 `SpeechObservation`，分别保存 VAD、原始/规范化
transcript、可选 word/character alignment、speaker cluster、冲突与 explicit unavailable。
全部范围使用源音轨 rational time；近似 timestamp 必须声明 granularity/error。Speaker
cluster 只表示声学聚类，永远不是角色身份。ASR 结果仍是 Observation，不能直接升级为
Fact/Story。

首个 adapter 固定 FunASR HTTP interface version `1.3.26`，同时兼容官方
OpenAI-style transcription transport 与已部署的 legacy Narrato SRT transport。代码许可与
模型权重许可分开审计；缺少完整 model checksum、weight license 或 commercial approval
时 adapter 必须报告 `research`，G01 Gateway 在 production policy 下执行前阻断。原始响应
先形成 RawProviderResponse，normalized service 只读取该不可变 blob 并提交独立
SpeechObservation Artifact。

关键否定、数字、金额和时间的跨 Provider 差异形成 `SpeechConflict`，不由 LLM 猜测消解。
人工 transcript 修正继续使用 E03 canonical Correction successor/CAS 与 dependency
invalidation，不覆盖原观察。CER、entity CER、timestamp deviation、DER 与 JER 分开评测；
synthetic baseline 只证明工程链路，不能建立生产阈值。Confidence 保持 Shadow，Automation
保持 L1。

原因：短剧对白的否定、人名、金额和归属错误可直接污染后续剧情；将 provider 私有 JSON、
speaker label 或单一总体 CER 暴露给下游会制造不可追踪的伪事实。Research-first admission
可在本地能力可用的同时保持 rights 和质量诚实。

后果：Registry 兼容升级到 1.5.0。真实多剧标注、方言/BGM/重叠语音 slice、forced
alignment 与 diarization bake-off 留给 G05 qualification；未满足前不得把 FunASR adapter
或任何 Speech confidence 标为 production/calibrated。

复议：只有真实 benchmark 证明其他 transport/model 更优且完成同等 license/checksum 审计时
切换 champion；不得取消 raw/normalized 分层、source time、cluster/identity 隔离或 L1 Gate。

## ADR-031 — Typed Visual Boundary, Shot-local Association and License-first Providers

决策：G04 用独立 typed contracts 表达 OCR/TextTrack、Detection、Shot-local Tracklet、
Face/Appearance、VisualEmbedding、VLM Claim、Source Quality 与 Supplementary Sample Request。
每条观察必须引用 exact frame Artifact 与源时间；OCR 不得被 ASR 静默改写，Tracklet 不跨 Shot
合并，Face/Embedding 只产生项目内 identity candidate，VLM 必须区分 visible/inferred/unknown，
不得形成角色身份、Fact 或 Story。

视觉模型接入复用 G01 Gateway 与 raw→normalized 边界。`VisualJsonHttpProvider` 是 OCR、
detection、tracking、face/visual embedding 和 VLM 的统一 transport adapter，但每个实例只能声明
一个 capability 与 exact Provider Package。首个可真实执行 baseline 固定 OpenCV 5.0.0.93
contour/quality，只有 research admission；它不把 foreground contour 宣称为 person。

工具候选按许可先行：PaddleOCR 3.x、Grounding DINO、ByteTrack、OpenCLIP/SigLIP 与 Qwen-VL
只有在 exact revision/checkpoint checksum、代码/权重许可、商业范围和 benchmark 齐全后准入。
Ultralytics YOLO 的 AGPL/Enterprise 许可必须显式解决，否则 production policy 阻断。任何 checkpoint
许可不得由代码仓库许可推断。显存/Metal 通过 Resource Estimate、reserve 和缩小 micro-batch
fail closed；重复 OOM 不得无限重试。

原因：视觉工具的代码许可、checkpoint 权重、检测标签与跨帧身份含义互不等价。将“检测到了人”、
“相似”或流畅 VLM 文本直接当成剧情事实会制造高风险串人和幻觉；Shot-local 和 typed claim
边界使后续 E07 Fusion 可以显式解决冲突。

后果：Registry 兼容升级到 1.6.0。G04 的真实 baseline 只证明 OpenCV decode/quality/transport；
OCR、semantic detection、tracking、embedding、VLM 的真实质量与生产 Provider admission 必须在
G05 报告中逐项判定。缺失能力显式 unavailable，Automation 保持 L1，Confidence 保持 Shadow。

复议：只有真实短剧 benchmark 与许可审计支持替换/晋级时更新 Provider config；不得取消
source-frame evidence、Shot-local tracking、embedding-space versioning、bounded sampling 或
visible/inferred/unknown 区分。

## ADR-032 — Qualification Can Reject, Human Approval Cannot Be Synthesized

决策：G05 以 versioned `ProductionQualification` 和逐项 `QualificationCheck` 表达生产资格。
passed、failed、blocked、not_evaluated 必须显式区分；工程任务完成可以产生“资格审计已完成但
拒绝生产准入”的结果，不得把缺证据解释为通过。`approved` 只有全部检查 passed 且 human
Actor 明确签署时 Contract 才接受；Agent、service account、Git commit 或 Automation Policy
不能代替人工签署。

E06 当前结论固定为 engineering recommendation=`rejected`、decision=`pending_human`：Speech
权重许可与真实域 benchmark、Visual semantic providers、长视频/多项目容量、Speech/Visual exact
Worker restart、完整资源/成本均为 blocker。Confidence 保持 Shadow，Automation 保持 L1，E06
不创建 Fact/Story。Canary 只能先运行 shadow，无 routing authority；rollback 使用 CAS 指回最后
批准的 Provider Package，并保留所有旧 Artifact。

Dashboard 与 runbook 必须与能力同时版本化，但“存在 JSON 面板”不证明 telemetry 部署完成；
部署端 metric export、alert 与 operator drill 仍需单独验收。当前 4-thread/16-frame OpenCV probe
只证明 research adapter 的有界线程执行，不替代 long-series/full-workflow capacity。

原因：生产资格的价值在于阻断不可靠能力。若把 G05 完成等同于“必须通过”，系统会诱导 Agent
编造阈值、忽略许可或用工程 fixture 代替真实短剧质量，直接违背项目质量纲领。

后果：Registry 兼容升级到 1.7.0，新增 `ProductionQualificationReport` Artifact Type。E06 不能
正式关闭或进入 E07 作为稳定依赖，直到 blocker 关闭、报告重跑并获得项目负责人明确签署。

复议：只有新 evidence 使所有 blocker 变为 passed 时生成后继 qualification；不得覆盖本次拒绝
记录，也不得降低检查项来获得 approval。

## ADR-033 — Identity Is a Reviewed Graph, Not a Similarity Threshold

决策：E07 人物身份由 `IdentityNode`、typed `IdentityEdge`、`CharacterIdentity` 和
`IdentityConflict` 组成。Face、tracklet、speaker cluster、name mention 和 known seed 只是带
Evidence 的节点；模型相似度只能产生 `same_candidate`，不得自动合并人物。只有人工创建的
`corrected_same` 可以合并 component；`cannot_be_same`/`corrected_different` 优先于合并并形成
blocker。未知人物保留 temporary identity，禁止为填满字段猜名字。

Identity assembly 必须按稳定 key 排序，并允许调用者注入 UUIDv4 factory，以便 Workflow replay
复用预分配 ID；默认 factory 只适用于首次执行。Identity Proposal 与正式 Graph 分离，Proposal
不能充当批准结果。Confidence 在真实按剧隔离数据校准前保持 Shadow，Story Gate 保持 L1 人工。

原因：脸、声音、名字和同框只是不同强度的观察，直接按 embedding threshold 合并会造成跨集串人，
并污染所有下游 Fact/Story。显式 cannot-link、冲突和临时身份使错误可审核、可修正、可失效。

后果：Contract Registry 兼容升级到 1.8.0。H01 只完成领域契约和保守 assembly，不包含持久化、
Review API、跨版本失效或真实人物识别质量；这些分别由 H02 和 H06 验收。

复议：只有真实短剧 benchmark 和人工修正数据证明某个适用范围已校准，才能讨论受 policy 约束的
候选自动化；不得取消 Evidence、cannot-link、Conflict、人工纠正来源或 Story Gate。

## ADR-034 — Identity Corrections Are Immutable, Serialized and Precisely Invalidating

决策：Identity merge/split/name 统一使用 typed `IdentityProposal`，先 preview 后由
`story_reviewer`/`editor` 提交。Project advisory transaction lock 串行化全局 graph commit，active
pointer CAS 拒绝 stale reviewer；Correction 创建同一 Artifact ID 的不可变后继版本，并保存 applied
proposal ID、before/after、actor 和 outbox。旧 IdentityGraph 的 exact dependency closure 生成
InvalidationDecision，只影响显式依赖的 Fact/Story，不扫描或删除其他产物。Review API 只能调用
application/repository，不直接写内部表。

后果：Registry 兼容升级到 1.9.0。H02 工程闭环支持 reversible successor lineage；真实 reviewer
体验、跨集规模和 PostgreSQL 并发压力在 H06/真实数据验收，不得由单元 fixture 推断。

## ADR-035 — Facts Contain Observable Claims and Preserve Evidence Disagreement

决策：H03 只把 timed transcript、OCR、detection 等直接观察转换为 Fact；speaker cluster 仍是候选
subject，不升级为 Character。VLM `inferred`/`unknown`、动机、关系、因果和营销标签禁止进入 Fact。
ASR 与烧录字幕作为可能相关的来源分别保留，不因一致而重复计票，不一致时生成包含 supporting 与
opposing Evidence 的 `FusionConflict`。Provider unavailable/incomplete 必须传播到 FactSet partition，
不得用空结果伪装 complete。EvidenceBundle 指向将要持久化的 exact FactSet ref。

后果：Registry 兼容升级到 1.10.0。H03 synthetic fixture 只验证类型和边界；真实 OCR/ASR/视觉
准确率仍受 E06 qualification 阻断，Confidence 保持 Shadow。

## ADR-036 — Story Reasoning Is a Typed Artifact Pipeline

决策：Story 不允许由视频或一个大 Prompt 直接生成。H04 固定 Fact retrieval → EventSet →
CharacterStateGraph → CausalGraph → StoryGraph 的独立 Activity/Artifact 链路，Temporal history 只传
ArtifactPointer。每步输入引用 exact version 并可单独重试/失效。当前确定性 baseline 只把
dialogue/action/signal 提升为 evidence-grounded Event；OCR/entity 保持上下文 Fact。时间相邻事件
只进入 unresolved causal pair，不能自动生成因果边；无法支持的 Character State 保持 unresolved。

H01 temporary identity 要求 Story Character 允许无名，但仅 `temporary=true` 时合法。这改变既有
`Character.display_name` 类型，因此 Registry 必须按 SemVer 从 1.10.0 major 升级为 2.0.0，禁止
伪装成 minor。迁移消费者必须处理 nullable display name。

后果：各阶段可并发处理 Episode，但 Project Story assembly 读取固定 snapshot。Synthetic baseline
只证明 typed/replay boundary，不代表模型理解质量；矛盾、梦境、回忆、否定仍需后续模型候选和人工 Gate。

## ADR-037 — Gate 1 Publishes an Exact Approved Story Snapshot

决策：Story Review Package 必须固定 FactSet、IdentityGraph、EventSet、CharacterStateGraph、
CausalGraph、StoryGraph、Config 和 Model 的 exact refs。Gate 1 永远按 L1 创建 ReviewRequest；只有
human reviewer 可提交 first-wins Decision。incomplete 或存在 blocker 的 Package 不允许 approve。
批准事务同时 CAS 发布 project-scoped `approved_story` pointer，并先落 DB/outbox 后发送 Workflow
Signal。Strategy 只能通过 Approved Story query 获取该 exact StoryGraph ref，不能读取“最新草稿”。

Review Web 以 events/identities/states/causality/evidence/risks 六视图呈现 Package；UI 只提供交互
投影，不直接写数据库。unresolved 必须显示并要求人工判断，但没有 blocker 时仍由 reviewer 决策，
不由 Agent 自动批准。

后果：Registry 兼容升级到 2.1.0。当前 UI 是 typed view-model 基线，不是完整视频交互体验；H06
只验工程闭环，真实 Story Gate 签署等待用户数据。

## ADR-038 — E07 Can Close Engineering While Production Qualification Remains Pending

决策：H06 使用 versioned `StoryEngineeringQualification` 区分 engineering completion 与 production
approval。E07 H01–H05 代码、Contract、Workflow、Gate、runbook/dashboard 和 synthetic invariants
全部通过时可以关闭工程 Epic；真实 identity/story corpus、E06 provider admission 和 human Story
signoff 任一缺失时，production decision 必须为 `pending_human`，Automation=L1、Confidence=Shadow。

严重错误分类至少包含 wrong identity、fabricated/missing event、reversed causality、negation/dream/
recall error 和 evidence mismatch。未来验收创建后继 Qualification/Report，不覆盖本次 pending 证据。

后果：Registry 兼容升级到 2.2.0。E08 可继续建设工程能力，但 Strategy 生产运行只能消费真实人工
批准的 ApprovedStoryRef；synthetic Story 不得成为营销策略质量依据。

## ADR-039 — Strategy Starts from Approved Story and Deterministic Profile Resolution

决策：E08 Strategy Input Service 只能通过 project-scoped `approved_story` publication 读取 exact
StoryGraph；不存在批准 pointer 时 fail closed，禁止读取 latest/draft Story。Genre/Platform/Audience/
Duration/Brand-Safety Profile 使用 versioned typed Contract。Rights/Safety 和 Platform hard constraint
优先于 soft preference；Genre/Audience/Duration 只能表达偏好，不能制造剧情或硬约束。同优先级 hard
constraint 冲突形成 blocker，不以模型选择一方。Approved Profile 必须声明 validated scope；
experimental Profile 不得成为自动路由依据。

后果：Registry 兼容升级到 2.3.0。I01 只建立配置和输入真相边界，不声称完成 Genre 自动识别或
营销效果验证；配置变化只失效 Strategy 及下游，不重算 Story。

## ADR-040 — Selling Points and Hooks Are Bounded Evidence-grounded Candidates

决策：Selling Point 只能从 Approved Story Event/Evidence 和 versioned taxonomy 形成，未知类型保留
unknown，不补写刺激点。CandidateBudget 同时约束卖点、方向、每方向 Hook、总候选、revision、token
和成本，Strategy×Hook 乘积不得突破全局上限；超限显式 incomplete/not-scheduled。Hook 是多轨 intent，
必须包含 source moment、visual/audio/text intent、disclosed/withheld information、audience question、
duration 和 continuation beats。未知 source、无后续兑现或未启用 mechanic 是 deterministic blocker，
任何 heuristic score 均不能抵消。无真实发布数据时 Confidence/score 只表示内部一致性且保持 Shadow。

后果：Registry 兼容升级到 2.4.0。I02 接受模型或人工 proposal，但 deterministic assembly/validation
拥有最终工程约束；真实卖点相关性和 Hook 吸引力留给 I05 真实数据验收。

## ADR-041 — Strategy Comparison Separates Blockers, Diversity, Feasibility and Cost

决策：Strategy Direction 必须引用已知 Selling Point 和 Story-grounded Narrative Beat，并先经过
CandidateBudget admission。Critic 使用独立 prompt/provider/run refs，只能产生 finding，不能修改
Candidate。Evaluation 分开保存 deterministic blocker、critic disagreement、risk、feasibility、cost
range 和 heuristic；blocker 或 infeasible 永远不能被综合分抵消。Diversity 以 primary selling point、
viewpoint、reveal policy 和 narrative spine 等结构字段比较，文本改写不构成新 Direction。成本以
versioned method/resource profile 和区间表达，不伪造精确金额。Comparison Package 保留所有候选、
失败和差异，不用排名隐藏低分方案。

后果：Registry 兼容升级到 2.5.0。I03 只建立可审核的候选比较基础；真实创意优劣和成本误差需
Stage 4/5 实际数据与人工偏好校准。

## ADR-042 — Gate 2 Freezes an Exact Creative Boundary

决策：Strategy Review Package 必须固定 Approved Story、Effective Config、Candidate/Hook Set 和
Comparison exact refs，并显式列出允许选择、blocker 和候选 Brief/Variant refs。Gate 2 保持 L1；
只有 human reviewer 可选择一个非阻断 Strategy 与 Hook。批准事务以 DB-first/outbox 和 project lock
同时发布 `approved_creative_brief` 与 `approved_variant_plan` pointer；缺失 selection、越界 ref、stale
target、incomplete 或 blocker 一律 fail closed。Stage 4 只能读取这两个批准 pointer。

Creative Brief 冻结平台、受众、时长、质量 Profile、叙事脊柱、五类创意 intent、硬约束、必用 Story
refs、风险与成本上限。Variant Plan 必须恰有一个 control、总增量成本不超预算；没有真实 exposure
assignment 与结果时只能称 candidate variants，不得宣称 A/B experiment。

后果：Registry 兼容升级到 2.6.0。Review Web 提供候选/Hook/Evidence/Diversity/Risk/Cost 六视图的
typed fail-closed view model；实际视频对照体验和营销 lift 由后续真实数据验收，不由工程 fixture 推断。

## ADR-043 — E08 Engineering Closure Does Not Certify Marketing Performance

决策：I05 用 versioned `StrategyEngineeringQualification` 独立表达 engineering completion 与
production approval。Contract/config/candidate/comparison/Gate/cost/fan-out 工程检查通过可关闭 E08
工程；真实多类型策略 corpus、Hook exposure/retention、E06 Provider admission、真实 Story/Gate 2
签署和 production-like concurrency/restart 任一缺失时，production decision 必须保持
`pending_human`，Automation=L1、Confidence=Shadow。

严重错误至少覆盖虚构卖点、选择 blocker、Hook 无兑现、Strategy 改写 Story、安全/权利违反、
成本/时长不可行和虚假 experiment 声明。并发 first-wins、deterministic exact-input repeat 与
DB-first signal 是工程不变量；真实多项目容量、运营成本和营销效果只能由后继验收确认。

后果：Registry 兼容升级到 2.7.0。E09 可以开始工程建设，但只能消费 project-scoped Approved
Creative Brief/Variant Plan；本报告不得被解释为 demo 成片质量或投放效果已经达标。

## ADR-044 — Creative Planning Compiles into One Timeline and Uses a Checkpoint

决策：E09 只能读取 project-scoped Approved Creative Brief/Variant Plan，并固定 Approved Story、
Media Catalog 和 Platform Profile exact refs。Beat、Clip/Coverage、Crop、Rhythm、Narration 是独立
typed intent；它们必须汇合为唯一 Master Timeline，不得各自维护成片时间真相。Embedding 只负责
召回；正式 Clip 必须有 Story/Evidence、合法 source range 和 rights。CoverageGap、DurationConflict、
不可行 crop 或无证据 narration 必须显式失败，禁止静默填充、极端加速或编造。

Timeline Review 是可反复 Patch/CAS 的人工 Checkpoint，不是第四个正式 Gate。Story、Strategy、
Release 三个 Gate 保持不变。E10 只消费 exact Approved Timeline Intent；任何时长改变创建 Timeline
后继并精准失效 voice/alignment/subtitle/mix/render。

后果：Registry 兼容升级到 2.9.0。E09 工程可在真实 craft benchmark 未完成时关闭，但 production
decision 保持 pending_human、L1/Shadow；专业节奏、解说、表演余韵与构图只能由完整播放和真实数据验收。

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
