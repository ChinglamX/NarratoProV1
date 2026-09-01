# Schema and Artifact Catalog

Version: 1.0

## 1. 目标

为六阶段所有正式数据建立唯一 canonical 名称、Schema 所有者、真相源、版本和生命周期，消除同义对象与跨模块私有 JSON。

输入：Core Data Contracts 与 Stage 1–6 正式输入输出。

输出：Canonical Schema Catalog、Artifact Type Catalog、ID/State/Naming Rules。

---

## 2. Envelope 与引用

所有持久化业务产物使用：

- `ArtifactEnvelope`：artifact_id、artifact_type、version、schema_version、producer、inputs、config/model/tool refs、checksum、state、created_at。
- `ArtifactRef`：artifact_id、version、artifact_type、checksum 可选。
- `ProviderIdentity`：provider、implementation/model/version/checksum/license。
- `EvidenceLink`：source ref/range、type、excerpt。
- `ConfidenceRecord`：score/status/method/calibration/scope/risk/factors/evidence。
- `ErrorEnvelope`、`ActorRef`、`RightsMetadata`、`RationalTime/TimeRange`。

这些只能在 `packages/contracts` 定义一次。

---

## 3. Lifecycle 与引用命名

实体 Schema 名不带 Approved；批准状态通过 Decision/Pointer 表达。业务 API 可使用语义引用别名：

- `ApprovedStoryRef` → 指向 `StoryGraph` 的 approved version。
- `ApprovedCreativeBriefRef` → 指向 `CreativeBrief` approved version。
- `ApprovedTimelineIntentRef` → 指向 `MasterTimeline` 的 `approved_intent` lifecycle。
- `ConformedTimelineRef` → 指向 `MasterTimeline` 的 `conformed` lifecycle。

别名是带约束的 ArtifactRef，不创建重复 payload Schema。

---

## 4. Canonical Artifact Catalog

| Domain | Artifact Type | Owner | 主要消费者 |
|---|---|---|---|
| Foundation | ConfigArtifact / EffectiveConfigSnapshot | control/contracts | all |
| Foundation | ResourceProfile / AutomationPolicy | control | workflow/router |
| Foundation | RightsGrant / RightsManifest | control/rights | production/release |
| Media | SourceMedia / MediaProbe / ProxyMedia / AudioStem | intelligence | production |
| Media | EpisodeCatalog / SceneShotCatalog / FrameSamplePlan | intelligence | perception/timeline |
| Observation | RawProviderResponse / SpeechObservation / VisualObservation / OCRObservation / DetectionObservation / TextTrack / Tracklet / FaceObservation / VisualEmbedding / VLMObservation / VisualQualityReport / SupplementarySampleRequest | intelligence | fusion/evaluation |
| Identity | IdentityGraph / IdentityConflict | intelligence | fact/story/timeline |
| Fact | FactSet / EvidenceBundle / SourceQualityFeatureSet | intelligence | story/strategy |
| Story | EventSet / CharacterStateGraph / CausalGraph / StoryGraph | intelligence | strategy/evaluation |
| Strategy | SellingPointSet / StrategyCandidateSet / HookCandidateSet | strategy | review/evaluation |
| Strategy | CreativeBrief / VariantPlan / StrategyComparisonPackage | strategy | timeline |
| Timeline | NarrativeBeatGraph / PatchProposal / ConflictSet | timeline/production | compiler/review |
| Timeline | MasterTimeline / OTIOExport / PreviewManifest | timeline | production/review |
| Production | ClipCandidateSet / ClipSelectionPlan / ContinuityReport / VisualPlanningReport / NarrationPlanningReport / TimelineAssemblyReport / SourceSubtitleHandlingPlan / CropPath / RhythmPlan / NarrationLineSet | production | timeline/compiler |
| Voice | VoiceTakeSet / VoiceAsset / AlignmentArtifact / ConformReport | production | timeline/audio/subtitle |
| Audio | AudioAssetSelection / MixPlan / MixedAudio | production | render/QC |
| Subtitle | SubtitleCueSet / GraphicsCueSet / ASSArtifact | production | render/QC |
| Render | RenderPlan / ProxyRender / FinalCandidate / RenderExecutionReport | production | evaluation/release |
| Quality | QualityEventSet / TechnicalQCReport / QualityReview / ProductionQualificationReport | evaluation | review/router |
| Feedback | CorrectionDataset / DatasetManifest / BenchmarkPredictionSet / ProviderBenchmarkReport / EvaluationRun | evaluation | calibration/release |
| Automation | CalibrationArtifact / DriftReport / RoutingDecision | evaluation/control | router/audit |
| Release | ReleaseReviewPackage / ReleaseRecord / PerformanceWindow | evaluation/control | human/online |
| Experiment | ExperimentPlan / ExperimentResult / ApplicableScope | evaluation | strategy feedback |

大 payload 可以拆 blob/Parquet，但 Artifact Type 和 metadata 不变。

---

## 5. 非 Artifact 事务实体

Project、Run、StageExecution、ReviewRequest、ReviewDecision、CorrectionCommand、CommandRecord、AuditEvent、OutboxEvent、ProviderRegistration、ConfigPublication、ReleaseApproval 是事务/治理实体，不为了“一切 artifact”强行序列化为媒体产物。

它们可以引用 ArtifactRef，具有各自 optimistic version 和审计。

---

## 6. 状态规范

Artifact：staging、committed、approved、stale、superseded、blocked、deleted_logically。Artifact 内容不可变，状态/active pointer 是单独事务记录。

Run/Stage：pending、queued、running、awaiting_review、succeeded、failed、cancelled、rejected、superseded。

Review：open、decided、expired、cancelled；Decision：approve、revise、reject。

Candidate Release：draft、evaluation、candidate、approved_for_canary、canary、staged、production、deprecated、revoked。

禁止不同包自行新增同义状态，例如 done/complete/finished。

---

## 7. ID 与稳定键

- 所有 ID 使用 UUID；可排序需求可选择 UUIDv7，但项目内统一。
- `artifact_id` 表示逻辑产物，`version` 单调递增；blob 用 checksum 去重。
- Provider 观察使用 observation_id；融合后的 fact_id 不复用 observation_id。
- Timeline item_id 在版本间尽量稳定，split/replace 明确生成新 ID/映射。
- execution_key、cache_key、idempotency_key 语义分离。
- 外部平台 ID 只能存 external_ref，不作为内部主键。

---

## 8. Schema 演进

Schema 使用 semantic version；兼容新增字段允许 minor，破坏语义 major。每个 Artifact 声明 schema_version，reader 维护支持矩阵。

迁移优先生成新 Artifact version；不可变历史不做原地 bulk rewrite。Config/Profile、Timeline 和 Dataset 需保存 canonical serialization 用于 checksum/replay。

Schema Registry 在代码库生成 JSON Schema，并在 CI 检查重复名称、未知 Artifact Type 和 breaking changes。

实施路径：`packages/contracts/registry.py` 是生成逻辑，`packages/contracts/artifact_catalog.py` 是 Artifact Type Registry；审计生成物位于 `generated/contracts/versions/<semver>`，当前版本指针为 `generated/contracts/latest.json`。本表与代码 Registry 必须由 CI 双向核对。

---

## 9. 测试与验收

- 扫描设计和代码，所有正式输出映射到 Catalog。
- Catalog artifact_type 唯一且 owner 唯一。
- Ref lifecycle constraint 防止未批准 Story/Brief/Timeline 进入下游。
- 状态转换和非法同义状态测试。
- Schema forward/backward compatibility 与 canonical checksum。
- Provider raw response 不能作为下游公共 Contract。
