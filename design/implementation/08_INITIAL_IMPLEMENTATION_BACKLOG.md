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

---

## 7. Sprint Group F — Media Ingest Vertical Slice

### F01 Ingest Registration and Rights Snapshot

实现 source registration、streaming checksum、content identity、rights snapshot、duplicate policy 和 upload/import command。

验收：同内容幂等、同名不同内容不混淆、unknown/restricted rights fail closed、导入中断可恢复。

### F02 Technical Probe and Source Time Mapping

实现固定 FFprobe adapter、stream/timebase/VFR/rotation/color/audio metadata 和 source clock mapping。

验收：正常、VFR、旋转、多音轨、无音频、截断/损坏输入；probe raw response 可追踪且不泄漏到领域 Contract。

### F03 Proxy Audio and Frame Derivatives

实现 proxy、audio extraction、frame sample plan/execution、checksum、source↔derived exact mapping 和 cache/retry。

验收：派生物可重建、时间映射误差有界、重复 Activity 幂等、部分输出不会被发布。

### F04 Scene Shot Baseline

实现 PySceneDetect baseline、Shot/Scene catalog、source-quality features 和人工 split/merge correction。

验收：cut/fade/静态/快速运动 fixture、边界证据、Correction successor 和精准失效。

### F05 Media Catalog API Review and Demo Acceptance

实现 Media Catalog query/review API、Temporal ingest workflow、资源准入、trace/QC 和 demo/合法 fixture 验收。

验收：真实资产 ingest、source↔proxy/frame/audio mapping、Worker restart、并发项目公平、损坏媒体 fail closed；不宣称 Speech/Visual/Story 已实现。

验收：Stage 1 Acceptance Report 自动生成并由人签收。

---

## 8. Sprint Group G — Speech and Visual Observation

### G01 Provider Gateway and Observation Boundary

冻结 Provider Package、capability port、raw response artifact、normalized Observation envelope、错误分类、timeout/retry/batch、rights/data-residency、Resource/Cost Profile 和 unavailable fallback。Provider 私有字段不得泄漏到领域 Contract。

验收：主 Provider 与 unavailable/manual 路径可替换；raw/normalized lineage、版本、checksum、trace、cost 完整；许可证或数据策略缺失在执行前 fail closed；破坏性 Contract 变化有 Registry SemVer/migration。

### G02 Evaluation Corpus and Benchmark Harness

建立按剧隔离的 Development/Validation/Frozen Test manifest、ASR/OCR/Detection/Tracking/VLM 严重错误 taxonomy、标注指南、slice metrics 和可重放 BenchmarkRun。

验收：无 series leakage；每个 prediction 可定位 SourceTime/Evidence；provider/config/hardware/resource/cost 可复现；没有真实标签时只报告 baseline，不拍脑袋设生产阈值。

### G03 Speech Observation Pipeline

实现 VAD、ASR、文本规范化、强制对齐、diarization/speaker observation、hotword、cross-provider conflict、manual Correction、Temporal shard/retry 和精准失效。

验收：CER、entity CER、timestamp deviation、DER/JER 分层基线；人名/否定/金额/时间严重错误单列；无音频、重叠语音、BGM、方言、Provider 不可用、Worker restart 和预算耗尽 fail closed/recoverable。

### G04 Visual Observation Pipeline

实现 OCR/TextTrack、person/object/face detection、Shot tracking、appearance observation、embedding index、constrained VLM、supplementary sampling 和显存/Metal 资源保护。

验收：OCR、Detection、Tracking、Identity candidate、VLM 分层 benchmark；所有观察回指原帧/源时间；模型 OOM、低质量帧、遮挡、换装、快速运动和 provider fallback 可定位且不编造结果。

### G05 E06 Production Qualification

完成 Speech/Visual provider bake-off、Confidence Shadow、长视频/多项目并发、Worker 中断、resource/cost baseline、canary/rollback、dashboard/runbook 和 E06 Acceptance Report。

验收：固定 Mac mini Resource Profile 下质量、吞吐、成本、恢复和 rights/provider approval 获人工签收；Confidence 仍为 Shadow，E06 不创建 Fact/Story、不越过 Story Gate。

---

## 9. Sprint Group H — Identity, Fact and Story

E06 的真实数据、Provider rights 与 production qualification 可以作为显式 debt 保留，但 E07
工程实现只能依赖冻结 Contract，并以 synthetic fixtures 验证；不得把 E06 research 输出当成
已批准质量。

### H01 Identity Graph Domain

实现 Observation Node、same/cannot-link、Character cluster、Identity Conflict、merge/split/name
proposal、人工约束优先级、deterministic component 与 temporary Character。

验收：同时间互斥人脸 cannot-link、人工 different 覆盖相似度、merge/split 可逆、未知身份不强制
命名、所有 link 回指 Observation Evidence。

### H02 Identity Persistence, Review and Invalidation

实现 Identity Graph immutable successor/CAS、Project commit serialization、semantic correction、
dependency impact preview、Review Package/API 和受影响 Fact/Story 精准失效。

验收：并发 reviewer 只有一个提交成功；往返 merge/split 保留 lineage；Review 不直接写内部表。

### H03 Fact and Evidence Fusion

将 Speech/Visual/OCR Observation 转换成 dialogue/person/entity/ocr/action/signal Fact，构建
supporting/opposing Evidence Bundle、Fact Snapshot、ConflictSet 与 incomplete partitions。

验收：Fact 只含可观察命题；相关来源不重复计票；冲突不静默消解；Correction 创建后继版本并
只失效显式 dependency closure。

### H04 Typed Story Reasoning Workflow

实现 Fact Retrieval、Episode Event Candidate、Evidence Entailment、dedup/order、Character State、
Relationship、Causal Edge、Arc、contradiction/coverage scan 的独立 Artifact 与 Temporal steps。

验收：不允许单 Prompt 从视频生成 Story；关键 Event 有 Evidence；时间先后不自动变因果；
dream/recall/negation/unavailable 保持 unresolved。

### H05 Story Review Workspace and Gate 1

实现 StoryReviewPackage 查询/API、事件线/身份/状态/关系/因果/evidence/conflict 视图数据、
Correction impact preview 与 L1 Story Gate。

验收：批准固定 story/fact/identity/model/prompt/config exact refs；重复/乱序 decision first-wins；
Strategy 只能读取 ApprovedStoryRef。

### H06 E07 Engineering Qualification

完成多集 synthetic correction/invalidation、并发、Worker restart/replay、resource/cost baseline、
Story severe-error taxonomy、dashboard/runbook 与 E07 Acceptance Report。

验收：工程闭环可重放且无越权；真实人物/剧情准确率与 Story production approval 在用户提供合法
数据后执行，缺失时保持 L1/Shadow/pending，不伪造通过。

---

## 10. Sprint Group I — Marketing Strategy

### I01 Strategy Config and Approved Story Input Boundary

实现 versioned Genre/Platform/Quality profiles，并强制 Strategy 只读取项目 ApprovedStoryRef。

### I02 Selling Point and Hook Candidates

实现 evidence-grounded SellingPoint、Hook 候选、多样性和 severe-error critic。

### I03 Strategy Candidate and Comparison

实现候选策略、预测维度、成本/风险和同输入可比较性，不使用线上指标反改 Story。

### I04 Strategy Review Workspace and Gate 2

实现 exact-ref Comparison Package、人工 Gate 2、CreativeBrief 和 VariantPlan publication。

### I05 E08 Engineering Qualification

完成并发/replay、成本、严重错误、dashboard/runbook 和 pending-real-data Acceptance Report。

---

## 11. Sprint Group J — Creative Timeline

### J01 Approved Brief Input and Timeline Intent Contracts

强制只读取 Approved Creative Brief/Variant Plan，定义 visual/rhythm/narration/audio/subtitle intent。

### J02 Visual and Clip Planning

实现 evidence-grounded clip candidates、coverage、continuity、rights/safety 和 source-time mapping。

### J03 Rhythm and Narration Planning

实现节奏曲线、信息密度、呼吸点、解说与对白避重、时长预算和可解释冲突。

### J04 Audio, Subtitle and Timeline Assembly

实现 BGM/SFX/ducking、字幕安全区与唯一 MasterTimeline Patch assembly。

### J05 Timeline Review Workspace and Checkpoint

实现多轨对照、人工精修、exact-ref Timeline checkpoint 和下游 publication；不新增正式 Gate。

### J06 E09 Engineering Qualification

完成 replay/concurrency、时间/覆盖/严重错误、dashboard/runbook 和 pending-real-data 验收。

---

## 12. Sprint Group K — Voice, Audio and Subtitle

### K01 Voice Provider and Take Contracts

实现 provider-neutral VoiceTakeSet、发音/情感/rights/QC 和 bounded candidate take。

### K02 Voice Synthesis, Selection and Alignment

实现 typed synthesis boundary、真实时长、forced alignment、重试/降级和 VoiceAsset publication。

### K03 Timeline Conform and Local Reflow

以真实 Voice/Alignment 时长创建 Timeline 后继，限制 reflow scope 并精准失效下游。

### K04 Audio Asset Selection and Mix Plan

实现 rights-first BGM/SFX selection、original/narration/music routing、ducking 和 loudness intent。

### K05 Subtitle, Graphics and ASS

实现 Cue/Graphics contracts、alignment、重点词、安全区、碰撞检测与 deterministic ASS 输出。

### K06 E10 Engineering Qualification

完成同步、响度/可懂度、rights、并发/replay、runbook/dashboard 和 pending-real-data 验收。

---

## 13. Sprint Group L — Render and Release Candidate

### L01 Render Preflight and Plan

从 Conformed Timeline、Voice/Mix/Subtitle 与 Platform Profile 生成 deterministic RenderPlan。

### L02 Proxy and Final Render Execution

实现 FFmpeg graph、缓存、heartbeat、重试、资源准入和 Proxy/Final parity。

### L03 Technical QC and Rights Manifest

实现 probe、同步、黑帧/静音/字幕安全区、完整 RightsManifest 和 blocker fail-closed。

### L04 Offline Quality Review Package

按统一 Rubric 形成带时间码/Evidence 的 Story/Hook/Rhythm/Narration/Visual/Audio/Subtitle review。

### L05 Human Release Gate 3

实现 human release_approver-only、first-wins、exact candidate/checksum 和 immutable ReleaseRecord。

### L06 E11 Engineering Qualification

完成 end-to-end fault/restart/cache/parity/security/cost、runbook/dashboard 和 pending-real-data 验收。

---

## 14. Sprint Group M — Evaluation and Safe Automation

### M01 Quality Events and Blocker Detectors

实现统一 QualityEvent、required detector resolution、故障集和 unavailable fail-closed。

### M02 Correction Dataset and Governance

实现 correction normalization、label quality、rights/privacy、series split 和 frozen dataset。

### M03 Confidence Calibration

实现按 task/scope calibration、severe slice、threshold candidate 和 drift baseline。

### M04 L2/L3 Routing, Sampling and Downgrade

实现 blocker precedence、risk sampling、kill switch、自动降级和人工审批升级。

### M05 Candidate Evaluation and Rollback

实现 Prompt/Model/Config/Policy candidate、paired evaluation、canary 和 rollback。

### M06 E12 Engineering Qualification

完成安全、治理、DR、至少一个合法 canary 或明确保持 L1 的数据证据。

---

## 15. 任务完成定义

每项必须有：public contract、domain/application implementation、adapter、unit/contract/integration tests、observability、error/runbook、文档链接和 migration/rollback（适用时）。

“代码写完”“API 200”“happy path 跑通”均不算完成。

---

## 16. 首批明确不做

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
