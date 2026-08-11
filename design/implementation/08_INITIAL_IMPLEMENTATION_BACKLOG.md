# Initial Implementation Backlog

Version: 1.0

## 1. 目标

定义首批可直接编码的 E00–E04 任务，建立生产基础垂直切片，而不是立即接入重模型或构建全部页面。

输入：Repository、Dependency、API、Schema、Workflow 蓝图。

输出：Ordered Work Items、Inputs/Outputs、Acceptance Tests、Definition of Done。

---

## 2. Sprint Group A — Bootstrap

### A01 Repository Scaffold

输入：`02_REPOSITORY_LAYOUT.md`。

输出：apps/packages/workflows/tests/deploy 目录、Python workspace、Web workspace、Make/task entrypoints。

验收：空包可安装；API/worker/CLI 启动；无业务代码放在 scripts。

### A02 Quality Toolchain

输出：formatter/linter/type checker/unit test/coverage/security/architecture test CI。

验收：本地与 CI 命令一致；错误 fixture 能证明规则生效。

### A03 Local Infrastructure

输出：Compose PostgreSQL、Temporal、Object Store adapter config、OTel Collector、Prometheus/Grafana。

验收：health/readiness、持久 volume、restart、secret 不入库。

### A04 Configuration Bootstrap

输出：environment loader、typed settings、secret refs、profile/config source conventions。

验收：缺少关键配置 fail fast；secret 不出现在 dump/log。

### A05 Calibration Manifest Bootstrap

输入：`design/calibration/README.md` 与 `design/calibration/02_CALIBRATION_PACK_V1.md`。

输出：Calibration Pack/Dataset/Split/Slice/Guideline manifest schemas、空的 Pack v1 registry 和 rights/usage 字段。

验收：manifest 可校验、版本化和注册；同一剧/系列跨 split 的 fixture 被拒绝；Frozen Test 标记不可用于 tuning。

### A06 Context Integrity Bootstrap

输入：`PROJECT_INDEX.md`、`PROJECT_STATE.md`、`agent/CONTEXT_RECONSTRUCTION_PROTOCOL.md` 和 `design/implementation/10_CONTEXT_AND_RECOVERY.md`。

输出：Index link checker、State active Epic/Task checker、required context file checker、Handoff lint 和 Cold-start Drill fixture。

验收：删除必需文件、填写不存在 Task、State 与 Backlog 不一致时 CI 失败；无聊天历史的测试 Agent 能找到 A01 和当前风险。

---

## 3. Sprint Group B — Contracts

### B01 Foundation Value Objects

实现 UUID、ArtifactRef、RationalTime/TimeRange、Checksum、ActorRef、ProviderIdentity。

验收：边界、canonical serialization、property tests。

### B02 Evidence, Confidence and Rights

实现 EvidenceLink、ConfidenceRecord、RightsMetadata/Manifest refs。

验收：unavailable/shadow、scope、invalid score、unknown rights 测试。

### B03 Command/Event/Error Envelopes

实现 envelope、stable error code、idempotency/trace fields。

验收：JSON round-trip、public redaction、breaking-change snapshot。

### B04 Schema Registry and Generation

输出 JSON Schema、OpenAPI components、TS types、artifact type registry。

验收：名称唯一、owner 存在、未知 type 和 breaking change 失败。

### B05 Artifact Envelope

实现 ArtifactEnvelope、ProducerRecord、ArtifactDependency、canonical lifecycle 和 exact-version refs。

验收：payload/URI、UTC、checksum、self/future dependency、canonical round-trip。

### B06 Media Catalog Contracts

实现 MediaAsset/Technical Metadata、EpisodeCatalog、SceneShotCatalog 和 FrameSamplePlan。

验收：source/derived lineage、stream/timebase、episode/segment identity、采样计划 round-trip。

### B07 Fact/Evidence Contracts

实现 Fact/FactSet、EvidenceBundle 和 SourceQualityFeatureSet。

验收：观察事实必须有 Evidence、unavailable/incomplete 显式、ID/source 一致性。

### B08 Story Contracts

实现 Character、Event、StoryEdge/Arc、UnresolvedQuestion 和 StoryGraph。

验收：关键事件/边必须有 Evidence，人物/事件/Arc 引用闭合，未知引用 fail closed。

### B09 Strategy Contracts

实现 SellingPoint/Set、NarrativeBeatIntent、HookCandidate、StrategyDirection/Set 和 CreativeBrief。

验收：Story/Evidence grounding、Hook continuation、时长与结构、候选非伪多样性。

### B10 Timeline Contracts

实现 MasterTimeline、Track/Item/Marker、TimelinePatch/Operation 和 TimelineConflict。

验收：唯一 Master Timeline 边界、全局 item identity、source pairing、Patch CAS 和 round-trip。

### B11 Evaluation and Correction Contracts

实现 QualityEvent、Correction、DatasetManifest、EvaluationRun、CalibrationArtifact、ApplicableScope 和 RoutingDecision 基础契约。

验收：S0–S3、unresolved/disagreement、shadow/unavailable 和版本 lineage round-trip。

---

## 4. Sprint Group C — Persistence and Artifact

### C01 Database Baseline

实现 Alembic、schemas/enums、Project/Run/Command/Audit/Outbox 基表。

验收：clean migrate、upgrade/rollback、旧 reader compatibility。

### C02 Blob Store Port and Local Adapter

实现 staging/commit/read/head/delete-candidate、checksum 和路径隔离。

验收：崩溃、重复 blob、checksum mismatch、路径穿越。

### C03 Artifact Registry

实现 immutable Artifact/Version、active pointer、CAS、lineage。

验收：并发 commit 只有一个成功；旧版本可查；回退不覆盖。

### C04 Dependency and Invalidation

实现 typed edge、cycle check、closure、RecomputePlan。

验收：精准闭包、并发 project lock、graph version、无物理删除。

### C05 Config/Policy/Rights Registry

实现 draft/validate/publish/deprecate、EffectiveConfigSnapshot、Rights check。

验收：snapshot 不漂移、unknown rights blocker、rollback pointer。

---

## 5. Sprint Group D — Workflow and Review

### D01 Temporal Bootstrap

实现 namespace/task queues、Worker Build ID、ProjectRunWorkflow skeleton。

验收：start/query/cancel、worker restart、replay fixture。

### D02 Activity Envelope and Fake Activities

实现 ArtifactRef-only payload、execution key、timeout/retry/heartbeat/error mapping。

验收：kill/retry/idempotency、non-retryable 不循环。

### D03 Command API and Reconciler

实现 Project/Run endpoints、command register、outbox、workflow start reconciliation。

验收：HTTP retry、DB success/Temporal fail、projection lag。

### D04 Review/Correction API

实现 ReviewRequest、Decision、Correction impact/apply、Signal reconciliation。

验收：stale/duplicate/乱序/RBAC、跨进程 wait-resume。

### D05 Resource Admission

实现 ResourceRequest/reservation、queue limits、disk/memory/cost backpressure。

验收：burst、公平、超水位不启动、lease recovery。

### D06 Observability Baseline

实现 trace propagation、structured log、metrics、cost/audit dashboard。

验收：API→Workflow→Activity→Artifact→Review trace；高基数不进 label。

### D07 Shadow and Correction Instrumentation

实现 AI/fake Activity 的 prediction/version/confidence shadow 记录、Review before/after 和人工耗时采集接口，不启用自动路由。

验收：一次 Review/Correction 可生成完整、可脱敏的 Calibration example；缺失版本时标 incomplete，不猜测填充。

---

## 6. Sprint Group E — Timeline Vertical Slice

### E01 Master Timeline Domain

实现 Sequence/Track/Item/Marker、RationalTime invariants 和 canonical serialization。

验收：非法区间、不同 rate、duration/property tests。

### E02 Timeline Patch/Validator/Diff

实现 semantic operations、expected version、scope lock、Conflict。

验收：并发 edit、stale base、undo-by-successor、deterministic diff。

### E03 OTIO Adapter

实现 Clip/Track/Transition/Marker 和 private metadata/LossReport。

验收：golden round-trip、unsupported field 显式 loss。

### E04 Fake Media-to-Preview Workflow

用固定颜色/测试音/ASS 生成 Timeline→RenderPlan→FFmpeg Preview，证明完整接口。

验收：API command、Workflow、Artifact、Timeline、Review、Preview、QC trace 全链路；不依赖真实 AI。

### E05 Foundation Acceptance Harness

自动执行 crash、retry、duplicate、stale、migration/restore、disk watermark 和 replay。

验收：Stage 1 Acceptance Report 自动生成并由人签收。

---

## 7. 任务完成定义

每项必须有：public contract、domain/application implementation、adapter、unit/contract/integration tests、observability、error/runbook、文档链接和 migration/rollback（适用时）。

“代码写完”“API 200”“happy path 跑通”均不算完成。

---

## 8. 首批明确不做

- 不接真实 ASR/VLM/TTS。
- 不实现 Story/Strategy Agent。
- 不实现最终专业 Timeline UI。
- 不启用 L2/L3。
- 不引入 Kubernetes、Ray、Kafka 或独立向量数据库。

这些不影响基础采用最终生产契约；E04 的 fake vertical slice 用来证明系统内核，而不是重复验证低质量视频生成。

---

## 9. 测试与验收

- A→E 可按依赖执行，每个 Group 都有可运行输出。
- 首个 vertical slice 覆盖 API/DB/Temporal/Artifact/Timeline/FFmpeg/Review/OTel。
- 替换 fake activity 不改变 workflow/domain contract。
- 所有 failure test 可重复，无人工改数据库。
- 完成本文件的任务 `E05 Foundation Acceptance Harness` 后，才开始总 Epic 编号中的 `E05 — Media Ingest Vertical Slice`。
