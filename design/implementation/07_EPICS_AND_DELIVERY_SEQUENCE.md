# Epics and Delivery Sequence

Version: 1.0

## 1. 目标

把六阶段设计重组为可交付的工程 Epic，明确依赖、并行窗口、退出证据和最终生产能力，避免按文档数量机械实施。

输入：Implementation Blueprint、Stage 1–6 Acceptance files。

输出：Epic Catalog、Dependency Sequence、Parallel Tracks、Release Evidence。

---

## 2. 交付原则

每个 Epic 以可运行垂直能力结束，包含 Contract、domain、adapter、workflow、API、observability、tests 和 runbook。不得把“Schema 完成”“接上模型”单独称为业务能力完成。

所有 Epic 使用最终契约和生产错误语义；前期允许 fake provider，但不允许临时数据模型。

---

## 3. Epic 序列

### E00 — Engineering Bootstrap

Repository、Python/TypeScript toolchain、CI、lint/type/test、Compose、secret/config conventions、architecture tests、Context/State integrity checks。

依赖：无。

退出：空 API/worker/web、PostgreSQL/Temporal/OTel 启动，CI 可重复；新 Agent 冷启动能定位 active task。

### E01 — Canonical Contracts

IDs、ArtifactRef/Envelope、RationalTime、Evidence、Confidence、Error、Command/Event，以及 Media、Fact、Story、Strategy、Timeline、Evaluation 基础 Contract 和 Schema registry/generation/compatibility。

依赖：E00。

退出：所有跨域 payload 有唯一强类型 Contract；JSON Schema/OpenAPI 生成、breaking-change 检测、Python/TS 客户端类型通过。

### E02 — Artifact and Persistence Core

Project/Run、Artifact/Blob/Dependency、Config/Policy/Rights、migration/outbox/audit、Object Store。

依赖：E01。

退出：immutable commit、CAS、checksum、invalidation、backup/restore。

### E03 — Durable Workflow and Review

Temporal parent/child、Activity envelope、queues、resource admission、Review/Correction API、signals/reconciler、observability。

依赖：E02。

退出：crash/retry/idempotency/replay/wait-resume/failure injection。

### E04 — Master Timeline Core

Timeline/Track/Item/Patch/Validator/Diff/OTIO、locks、dependency rules、preview compiler interface。

依赖：E01–E03。

退出：round-trip、concurrency、invalidations、golden Timeline。

### E05 — Media Ingest Vertical Slice

Source upload/register、probe、proxy/audio/frame, Scene/Shot baseline、Catalog API/Review。

依赖：E02–E04。

退出：真实 demo/测试资产 ingest、source↔proxy mapping、failure recovery。

### E06 — Speech and Visual Observation

Provider gateway、ASR/VAD/alignment、OCR/detection/tracking/embedding/VLM baseline、raw response/benchmark。

依赖：E05。

退出：分层 baseline、rights/provider approval、resource/cost profile。

### E07 — Identity, Fact and Story

Identity graph/merge/split、Fact/Evidence、Story typed workflows、Story Workspace/Gate 1。

依赖：E06。

退出：多集 correction/invalidation、关键 Event evidence、ApprovedStoryRef。

### E08 — Marketing Strategy

Config/Profile、SellingPoint、Strategy/Hook/Critic/Diversity/Cost、Comparison/Gate 2/Variant。

依赖：E07。

退出：ApprovedCreativeBriefRef，无 blocker/伪效果预测。

### E09 — Creative Timeline

Beat、retrieval/continuity、crop/reframe、rhythm、narration、Compiler/reflow、Review Workspace/demo benchmark。

依赖：E04、E08；benchmark track 可提前。

退出：ApprovedTimelineIntentRef、完整 Preview、局部 Correction。

### E10 — Voice, Audio and Subtitle

TTS/voice QC、alignment/conform、asset rights、MixPlan、ASS/layout/graphics。

依赖：E09；provider bake-off 可提前。

退出：ConformedTimeline、Voice/MixedAudio/ASS 与分层 QC。

### E11 — Render and Release Candidate

RenderPlan/preflight/cache/retry、Proxy/Final parity、Technical QC、RightsManifest、Release Package/Gate 3。

依赖：E10。

退出：完整候选成片、blocker zero、人工 Release Decision。

### E12 — Evaluation and Automation

QualityEvent/Detector、Correction Dataset、MLflow benchmark、Calibration、L2/L3 routing/sampling/drift、candidate release/rollback。

依赖：E03，数据上依赖 E06–E11；基础设施可持续并行。

退出：至少一个合格 L2 canary、一个 L3 抽样演练或明确保持 L1 的数据证据。

### E13 — Online Performance

合法 connector、Release/Variant mapping、metric quality、comparison/experiment、feedback candidate。

依赖：E11；非主线 blocker。

退出：可审计线上分析，不修改 Story/Fact/Release。

---

## 4. 可并行轨道

- E01 后：前端 Design System/OpenAPI client、Rights Registry、benchmark guidelines。
- E03 后：provider fake/benchmark harness、review panels、resource profiling。
- E04 后：demo reverse engineering、crop/rhythm/narration algorithm research。
- E05 后：ASR 与视觉 Provider 独立 bake-off。
- E09 后：TTS、Audio、Subtitle 实现可并行，在 Conform 汇合。
- E06 起：Correction/QualityEvent 采集持续运行；L2/L3 必须等数据。
- E00 起：建设 `design/calibration/README.md` 定义的 manifest、guideline、fault set 和版本追踪；E05–E11 随真实能力逐批形成 Calibration Pack v1。

并行不允许绕过 Contract、Rights、Timeline 或 benchmark 前置。

---

## 5. 生产发布切片

R1 Foundation：E00–E04，空 Pipeline 可耐久运行。

R2 Story Intelligence：E05–E07，完整剧集可形成 Approved Story。

R3 Creative Plan：E08–E09，形成可精修 Approved Timeline Intent。

R4 Release Candidate：E10–E11，生成可人工发布的 demo 级候选。

R5 Safe Automation：E12，低风险模块减少人工但质量不降。

R6 Online Learning：E13，有合法数据时启用。

每个 R 都是生产质量能力增量，不是低标准 MVP。

---

## 6. 测试与验收

- Epic Dependency Graph 无循环且每项有 Artifact/API 交付。
- 每个 Epic 退出条件可由 CI/benchmark/review evidence 验证。
- R1–R4 不依赖线上数据或 L2 自动化。
- 任一 Provider research 失败不阻断替换/manual 路径。
- E12 无足够数据时保持 L1，不影响高质量生产。
- Epic 变更需更新 Catalog/ADR/Acceptance，不靠口头约定。
