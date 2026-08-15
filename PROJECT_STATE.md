# Project Current State

State Version: 54
Last Updated: 2026-08-15
State Owner: Project

## 1. 当前阶段

- Lifecycle：Implementation active; E00–E05 completed; E06 production qualification debt retained（语义视觉 Provider 准入阶段 B 本地 runtime 已安装验证，State v54）; E07/E08 engineering closed with real-data qualification pending; E09 active（认证链路人天签署完成，多 Variant replay 工程验证通过，剩余 blocker 见 §5）; E10/E11 advance baseline（不启动主实现）。
- Active Release Slice：R4 Creative Production。
- Active Epics：E09 Creative Timeline；E06/G05 production qualification retained as bounded debt（准入评估 + 本地 runtime 验证进行中）。
- Active Backlog Entry：J05 Precise Multi-track Editing — 工程实现已审计修复（State v48）、渲染时间基 bug 修复并重跑认证（State v50）、项目负责人人工审核 approve（State v51）、多 Variant restart/replay 工程验证 + preview heartbeat 修复（State v52）、J05 debt 清理完成（/patches 合并、Web 接线、CI Postgres、revisions.py 经授权删除）；剩余 Epic 退出 blocker 见 §5。
- Automation：L1；Confidence 仅 Shadow。未授权任何 L2/L3 自动放行。

---

## 2. 已完成且已审计

- 项目纲领、能力、五域架构、工程与质量规范。
- Stage 1–6 的生产级详细设计。
- 全局 Architecture Review 与模块化单体实施蓝图。
- Repository、Package、API、Schema Catalog、Workflow、Epic 和首批 Backlog 设计。
- Calibration Program、Calibration Pack v1 和持续运营规范。
- 上下文重建、项目索引和阶段恢复机制设计。
- 强制启动协议已接入 `AGENTS.md`、Roadmap、E00 Epic 和 A06 Backlog。
- A01 Repository Scaffold：Python 3.11 workspace、API/Worker/CLI、React Review Web、统一 Make/pnpm 入口已实现并通过安装/构建检查。
- A02 Quality Toolchain：format/lint/mypy/pytest/Bandit、依赖边界错误 fixture 和 GitHub CI 已实现。
- A04 Configuration Bootstrap：typed settings、secret-safe summary、PostgreSQL/fail-fast production 校验已实现。
- A05 Calibration Manifest Bootstrap：Pack/Dataset/Split/Slice/Guideline/Rights contracts 和空 Pack v1 registry 已实现；split leakage 与 Frozen Test 防误用测试通过。
- A06 Context Integrity Bootstrap：required files、Index links、State↔Epic/Backlog、Handoff、Cold-start Drill 已进入本地和 CI 检查。
- A03 Local Infrastructure：PostgreSQL、Temporal、Temporal UI、MinIO、OTel、Prometheus 和 Grafana 固定版本已完成真实启动、HTTP readiness、全服务 restart 与 PostgreSQL/MinIO volume persistence 验收；支持串行在线拉取和 `--skip-pull` 离线验收。
- B01 Foundation Value Objects：UUIDv4、ArtifactRef、RationalTime/TimeRange、Checksum、ActorRef、ProviderIdentity 已在 `packages/contracts` 唯一定义；immutable/forbid-extra 边界、canonical JSON 和 Hypothesis property tests 已通过。
- B02 Evidence, Confidence and Rights：EvidenceLink/FrameRange、ConfidenceRecord/Factor/Status/Risk、RightsMetadata、RightsGrantRef/RightsManifestRef 已实现；shadow/unavailable/calibrated/drifted、score/scope、UTC 期限和 unknown/restricted rights 的 fail-closed 边界已验证。
- B03 Command/Event/Error Envelopes：CommandEnvelope、EventEnvelope、ErrorEnvelope/PublicErrorEnvelope、稳定类型/版本/idempotency/trace 字段和显式 public/internal disclosure boundary 已实现；canonical JSON round-trip、redaction 与最小 breaking-change shape snapshot 已通过。
- B04 Schema Registry and Generation：唯一版本化 Registry 已生成 38 个 JSON Schema/OpenAPI/TypeScript 类型和 70 个 Artifact Type；Catalog/owner 唯一性、unknown type、生成物漂移和 SemVer breaking-change 检查已接入 `make check`。
- B11 Evaluation and Correction Contracts（历史实现时称 B05）：QualityEvent、Correction、DatasetManifest、EvaluationRun、CalibrationArtifact、ApplicableScope 和 RoutingDecision 已进入唯一 Contract Registry；S0–S3、unresolved/disagreement、shadow/unavailable、版本 lineage 和 fail-closed routing 不变量已验证。Registry 兼容升级为 v1.1.0，保留 v1.0.0 审计版本。
- E01 Contract 补全：B05 Artifact Envelope、B06 Media Catalog、B07 Fact/Evidence、B08 Story、B09 Strategy、B10 Timeline 已实现；原 Evaluation/Correction B05 在 canonical Backlog 中保留证据并重编号为 B11。Registry v1.2.0 包含 107 个 JSON Schema/OpenAPI/TypeScript components、70 个 Artifact Type，历史 v1.0.0/v1.1.0 不变。
- E02 Artifact and Persistence Core：PostgreSQL/SQLAlchemy/Alembic baseline、Project/Run/Artifact/Blob/Dependency/Command/Review/Policy/Config/Rights/Audit/Outbox schemas、LocalObjectStore、Artifact/Blob/Command/Publication repositories、CAS、cycle check、失效闭包和备份恢复已实现并用真实 PostgreSQL 验收。
- E03 Durable Workflow and Review：Temporal ProjectRunWorkflow、typed Activity envelope、retry/heartbeat/non-retryable mapping、worker wait/restart/replay、Command/Run outbox、Review/Correction API、first-wins/RBAC/CAS、Resource Admission leases、trace/redaction/metric label policy 和 Confidence Shadow correction example 已实现；真实 Temporal 与 PostgreSQL/API 验收通过。
- E04 Master Timeline Core：唯一 MasterTimeline domain validator、semantic Patch/Diff/rebase、PostgreSQL successor/CAS、OTIO 0.18.1 adapter/LossReport、deterministic RenderPlan、FFmpeg 8.1.2 fake Preview、ASS sidecar、Temporal Preview Workflow、Preview Artifact lineage/QC 和人工 Checkpoint 已实现并真实验收。
- E05 Media Ingest：UUIDv4/PostgreSQL ingest identity、FFprobe/FFmpeg provider、source/proxy/audio/frame、rational source map、PySceneDetect Shadow Catalog、Catalog API、Temporal Workflow、资源准入、L1 Review 和 rights fail-closed 已实现；Stage 1 Acceptance Report 已由项目负责人批准，E05 正式关闭。
- E06/G01 Provider Gateway：Provider Package/Data Policy/Resource Estimate/Invocation/Failure/Raw Response contracts、统一 Port、fail-closed Gateway、raw Object Store/Artifact lineage 和 unavailable/manual boundary 已实现；Registry 1.3.0 为兼容 minor evolution。
- E06/G02 Benchmark Harness：series-isolated Dataset、Prediction、Severe Error、Slice Metric、Provider Report contracts 与 deterministic summary harness 已实现；synthetic fixture 只验证工程，不声明生产质量阈值。Registry 1.4.0 为兼容 minor evolution。
- E06/G03 Speech Observation：typed VAD/Transcript/Alignment/Speaker/Conflict/unavailable contracts、FunASR HTTP/legacy SRT research adapter、raw→normalized Artifact service、Temporal Workflow、关键语义冲突与 CER/entity CER/timestamp/DER/JER metrics 已实现；Registry 1.5.0。合成普通话真实本地调用 CER=0.0 只作为工程 baseline，不是生产质量准入。
- E06/G04 Visual Observation：typed OCR/TextTrack/Detection/Tracklet/Face/Embedding/VLM/Quality/Supplementary contracts、typed HTTP 与 OpenCV research adapters、raw→normalized Artifact service、Temporal Workflow、资源保护与分能力 metrics 已实现；Registry 1.6.0。真实 demo frame OpenCV baseline 只证明 decode/quality/transport，不代表语义视觉模型准入。
- E06/G05 Production Qualification engineering review：versioned Qualification Contract/matrix、canary/rollback、dashboard、runbook、bounded concurrency probe 与 E06 Acceptance Report 已实现；Registry 1.7.0。结论为 6 passed / 4 blocked / 2 not evaluated，engineering recommendation=rejected，human decision=pending；因此 E06 未正式关闭。
- E07/H01 Identity Graph Domain：Face/tracklet/speaker/name/seed typed nodes、candidate/cannot-link/human correction edges、temporary CharacterIdentity、IdentityConflict 和 IdentityProposal 已实现；保守 assembly 仅接受人工 `corrected_same`，cannot-link 优先并产生 blocker，相似度只形成审核候选。Registry 1.8.0。
- E07/H02 Identity Persistence/Review/Invalidation：typed merge/split/name preview、immutable successor、applied proposal lineage、Project advisory lock、active-pointer CAS、Correction/outbox、exact dependency invalidation 和 Review API/RBAC 已实现；Registry 1.9.0。
- E07/H03 Fact/Evidence Fusion：Speech transcript、OCR、detection 到 observable Fact 的保守融合、supporting/opposing Evidence、ASR/OCR disagreement、incomplete partition 传播和 inferred VLM 排除已实现；Registry 1.10.0。
- E07/H04 Typed Story Reasoning：Fact retrieval→EventSet→CharacterStateGraph→CausalGraph→StoryGraph typed Artifact/Temporal Activity 链路、pointer-only history、保守 event promotion、unresolved state/causal handling 已实现。temporary unnamed Character 修复触发合规 Registry major 2.0.0。
- E07/H05 Story Review/Gate 1：exact-ref StoryReviewPackage、L1 Story Review API、blocker/incomplete fail-closed、human first-wins Decision、DB-first outbox、Approved Story project pointer/query 和 typed Review Web 六视图基线已实现；Registry 2.1.0。
- E07/H06 Engineering Qualification：versioned qualification matrix、Story severe-error taxonomy、runbook、dashboard 和 Acceptance Report 已完成；工程结论 complete，production decision=pending_human，真实 identity/story corpus、E06 provider admission 和 human Story signoff 保持 blocker。Registry 2.2.0。E07 工程正式关闭。
- E08/I01 Strategy Config/Input Boundary：versioned Genre/Platform/Audience/Duration/Brand-Safety Profile、hard/soft boundary、deterministic resolution、conflict blocker 和 ApprovedStory-only Input Service 已实现；Registry 2.3.0。
- E08/I02 Selling Point/Hook Candidates：CandidateBudget、Event/Evidence-grounded Selling Point、coverage、HookCandidateSet、结构去重和 source/mechanic/continuation deterministic blocker 已实现；Registry 2.4.0。
- E08/I03 Strategy Candidate/Comparison：bounded grounded Direction planning、independent Critic refs、blocker-over-score、Risk/Feasibility/Cost、structural Diversity 和 Comparison Package 已实现；Registry 2.5.0。
- E08/I04 Strategy Review/Gate 2：exact-ref Review Package、L1 human selection、blocker/incomplete/out-of-package fail-closed、ApprovedCreativeBrief/VariantPlan 双 publication pointer 和 typed Web 六视图已实现；Registry 2.6.0。
- E08/I05 Engineering Qualification：versioned Strategy qualification、严重错误 taxonomy、成本/并发/replay 边界、runbook、dashboard 和 pending-real-data Acceptance Report 已完成；工程结论 complete，production decision=pending_human。Registry 2.7.0。E08 工程正式关闭。
- E09/J01 Creative Timeline contract/input baseline：Approved Strategy-only input 和 Beat/Clip/Crop/Rhythm/Narration 初始 Contract 已实现；E09 不得因此关闭。
- E09/J02 Visual and Clip Planning：可替换 Clip Index Port、Story/Evidence/Character 过滤、序列级连续性选择、Continuity Report、平滑 CropPath、原片字幕降级与局部重算已实现；持久化 ClipCandidateSet 适配器（路由分数+top-k+源时长校验）、TimelinePlanningService（全部规划产物经 ArtifactRepository 落库）与确定性测试已完成。Registry 2.14.0→2.18.0。
- E09/J03 Rhythm and Narration Planning：Beat 预算/总时长对账、DurationConflict、呼吸点意图、对白复述/无依据心理阻断、证据覆盖、人工 lock 与 scoped regeneration 已实现；NarrationSourcePort/L1 人工解说边界、RhythmPlanningService（RhythmPlan/NarrationPlanningReport/后继 NarrationLineSet 落库）与 DurationConflict 分支测试已完成。Registry 2.15.0→2.18.0。
- E09/J04 Multi-track Assembly：Video/Original Audio/Narration/BGM/SFX/Subtitle/Overlay 共用唯一 MasterTimeline 的组装与 blocker 校验已实现；TimelineAssemblyService 落库、确定性原声音频/字幕 intent 投影、CreativeTimelineWorkflow（visual→rhythm→narration→assembly→media preview→人工 checkpoint，stage blocker 即停）、真实媒体 Preview（真实源文件 trim/scale/concat + ASS 安全区字幕）与 Worker 注册已完成。Registry 2.16.0→2.18.0。
- E09/J05 Timeline Checkpoint integration baseline：exact-ref Review Package、读取 API、L1 人工决定、DB-first outbox、publication pointer 和可运行 Web checkpoint cockpit 已实现；精确多轨编辑（TimelineEditingService、版本列表/diff API、局部真实预览渲染）已完成；2026-08-13 对提交 `367066b` 逐项审计并修复（见 §7 最新条目与 ADR-050）；2026-08-15 人工审核证据发现渲染时间基 bug（intent_projection cursor rate=1 + assembly 兜底 duration rate=1 + AudioIntent 缺 source_range），已修复并重跑真实认证（见 §7 v50 条目与 §5）；正式认证集成待真实数据验证。Registry 2.17.0→2.18.0→2.19.0。
- E09/J06 Qualification harness：deterministic concurrency probe、versioned demo technical/shot benchmark、qualification matrix、runbook/dashboard 已实现；四个真实退出 blocker 未解决，`engineering_complete=false`。
- E10 advance contract baseline：Voice/Alignment/Mix/Subtitle/ASS 部分 Contract 已提前建立；K01–K06 主实现未开始，不构成 E10 完成。
- E11 advance boundary baseline：Render/Release Contract、基础 preflight/executor/API 已提前建立；L01–L06 主实现未开始，不构成 E11 完成。

设计完成不等于代码完成；不得把上述项目报告为已实现能力。

---

## 3. 尚未开始

- E09/J05 正式认证集成（TimelineEditingService、局部真实预览、undo/redo/jump API 已完成工程实现并通过审计修复，待真实数据验证）；J02–J04 生产 DoD 已补齐，但 E09 四个真实退出 blocker（语义视觉 Provider 准入、真实 Approved 项目全片 Preview、带时间码的 demo craft 对比、Worker restart/replay + 人工 checkpoint）仍待真实数据验证，`engineering_complete=false`。
- J05 剩余接线（bounded）：`/patches` 端点与 TimelineEditingService 仍为双实现（都带 approved-intent 门禁，行为一致，待合并）；`packages/timeline/revisions.py`（RevisionHistory，纯内存截断语义）未接线且与 append-only 持久化语义不一致（待删除或改写，需人工批准）；Review Web 尚未调用版本/局部预览 API；CI 无 Postgres 服务（`tests/persistence/test_timeline_repository_db.py` 在 CI 跳过）。
- Speech/Visual Review Workspace 与真实多剧 Calibration Corpus 尚未实现。
- Calibration Pack 的真实素材标注和 Baseline。
- 任何 L2/L3 自动化。

---

## 4. 下一步唯一恢复点

按 `design/implementation/08_INITIAL_IMPLEMENTATION_BACKLOG.md` 开始：

1. E09 真实数据认证已完成人工签署（State v51 / run `d8eb4cd5` / workflow succeeded）：项目负责人 2026-08-15 审核 30.27s 全片 preview（`tmp/e09-cert-d8eb4cd5-*-preview.mp4` + 带字幕播放页 `tmp/e09-cert-d8eb4cd5-preview.html`）后 approve，timeline checkpoint 关闭。**下一步**：(a) 补录带时间码的 demo craft 对比表（建议归档至 `evaluation/benchmarks/`）；(b) 处理 J05 bounded debt（`/patches` 双实现合并、`revisions.py` 处置、Review Web 接线局部预览、CI 加 Postgres service）；(c) 登记 ADR-051（渲染时间基 bug 阶段回溯）。
2. E06/G05 签署、真实 Corpus、模型 rights/checksum 与生产 load/fault/cost 验收保留为 bounded debt track，进入任何 production approval 前强制阻断。
3. E07 工程建设不得宣称人物/剧情质量通过；Confidence 仍为 Shadow，Story Gate 仍为 L1 人工。
4. E10/E11 现有代码只作为 advance baseline；在 E09 满足 Epic 退出条件（剩余 blocker 见 §5）前不得恢复为 active/completed。

包管理决定已确认：PEP 621/setuptools editable + pyenv Python 3.11.8 + .venv/pip 24.0（ADR-003）；Python resolution lock 仍为首个 Release Slice 退出前的 bounded debt（见 §6）。

---

## 5. 当前阻断与风险

- 初始设计基线 tag `architecture-baseline-v1.0.0` 指向 `de4e31c`；A01–A06 当前 checkpoint 以本 State 所在 Git revision 为准。
- Python resolution lock 尚未建立；Web 已生成 `pnpm-lock.yaml`。
- Docker daemon 直接拉取大型镜像仍可能受 system proxy EOF 影响；A03 已通过宿主代理 + 校验后的 `crane` 离线导入完成。正式自动化环境应使用稳定 registry mirror 或预置镜像，而不是依赖临时 `/tmp` 工具。
- 后续诊断确认宿主可访问 Registry，Docker daemon 使用 `http.docker.internal:3128` 代理并在 CloudFront blob 下载时 EOF；不得静默修改全局 Docker 代理。
- 2026-08-11 经用户授权临时将 Docker Desktop `vm.proxy.mode` 从 `system` 切换为 `disabled`：daemon 直连 `registry-1.docker.io` 持续 `context deadline exceeded`，证明当前环境不能依靠直连绕过代理。实验后已恢复 `system`，settings-store 与实验前备份逐字一致。
- 经用户授权临时关闭 containerd image store：Temporal 镜像下载成功，但 Compose 并行拉取随后使 daemon 无响应；已恢复原设置并重启 Docker。不得重复该路径或把部分镜像下载当作 A03 验收。
- 真实 Provider、模型权重、字体、音乐和音色的生产许可尚未完成准入。
- Calibration Pack 尚无真实项目 Gold/Baseline。
- demo 已存在于项目，但完整人工 benchmark artifact 尚未建设。
- 2026-08-12 审计发现 E09–E11 曾将 contract/boundary baseline 误标为 Epic engineering complete；原 Acceptance Report 和 ADR-044 对应关闭结论已由 ADR-047 supersede。
- E09 当前剩余 blocker：语义视觉 Provider 生产准入（blocked）、带时间码的 demo craft 对比表正式文档（AI 草稿已归档 `evaluation/benchmarks/e09_craft_compare_v1.json`，待人工签核）。真实完整 Preview、人工 checkpoint 签署（State v51）、多 Variant restart/replay 工程验证（State v52）均已关闭。
- FunASR adapter 已真实运行但只准入 research：完整模型权重 checksum、模型卡许可、商业使用批准和真实按剧隔离 Speech baseline 均缺失。
- PaddleOCR/semantic detector/tracker/embedding/VLM 尚无生产准入的 exact checkpoint 与真实短剧 benchmark；Ultralytics 许可姿态未批准，必须保持 blocked/research。
- 本地未跟踪 `.env`（gitignored）会注入 NARRATOPRO_DATABASE_URL，曾使 `test_production_rejects_bootstrap_credentials` 在本地失败（CI 无 .env 不受影响）；已改为测试内显式 bootstrap URL 断言，不再依赖环境。
- CI 无 Postgres 服务：`test_timeline_repository_db.py` 的 4 个真实 SQL 回归测试在 CI 跳过（本地 `narratopro_test` 库 4/4 通过）；后续应给 CI 加 Postgres service 以持续执行。
- Temporal 沙箱与 numpy/OpenCV 不兼容（C 扩展重复加载）：`workflows/media/__init__.py` 与 `workflows/visual/__init__.py` 已用细粒度 `imports_passed_through` 处理；禁止回退到全局 `with_passthrough_all_modules()`（ADR-050）。macOS 下 cv2/av 的 objc 重复类警告无害。
- G05 生产资格结论为 rejected/pending_human；真实 Corpus、模型权利、long-series/multi-project、exact Worker restart、完整资源成本和 telemetry operator drill 均是显式 blocker。
- 用户授权 E06 签署与真实数据验证暂存 TODO，并允许 E07 先做工程实现；该授权不等于批准 E06，也不允许 E07 绕过真实数据生产验收。
- H01 synthetic tests 只证明 Identity Contract/assembly 工程不变量，未证明跨集人物识别准确率；H02/H06 仍须保留人工纠正与真实数据验收。

---

## 6. 未决决策

- Python resolution lock 工具选择（要求不改变 PEP 621 package source）。
- MinIO/S3 adapter 及共享多机 Object Store 切换条件；单机默认已由 ADR-024 固定为 LocalObjectStore。
- FFmpeg 8.1.2 已作为首个 Timeline/Preview 验收 toolchain；E05 需验证真实 ingest/probe 的编解码覆盖，不得静默漂移版本。

未决决策必须通过证据、兼容性和 ADR 解决，不能由 Agent 默认偏好静默决定。

---

## 7. 最近验证

- 2026-08-16 E06 真实短剧视觉 benchmark v1（State v56）：`scripts/build_e06_benchmark.py` 对 13 剧/36 episodes 真实语料（`data/corpus`，软链自桌面素材，rights approved）完成分镜+抽帧（720 帧）+ PaddleOCR/RT-DETR 全帧 + Ark VLM 子集（每剧 4 帧）——**1052 OCR 文本、1268 检测框、144 VLM claims、0 错误**，train/validation/frozen_test 按剧隔离（DatasetSplitManifest 校验）；`evaluation/benchmarks/e06_visual_v1.json` + 汇总报告 `E06_VISUAL_BENCHMARK_V1.md` 归档。OCR 识别真实字幕（1.2–1.6 文本/帧），DET label 多为 unknown（COCO 类不含短剧类别，后续映射/微调），VLM 描述质量高。research 证据基线（非生产准入）。`make check` 356 tests、80.05% coverage 全绿。
- 2026-08-15 E06 VisualObservationWorkflow 接入（State v55）：`VisualWorkflowInput` 新增 `capability`（ocr/detection/vlm），`process_visual_activity` 经 `_provider_for` 选择 PaddleOCR/RT-DETR/Ark VLM adapter（替换固定 OpenCV detection），output 对齐 E06 normalize 契约（OCR→`ocr[{text,region,kind,score}]`、detection→`detections[{label,region,score}]`、VLM→`vlm_claims[{kind,statement,score}]`，region 归一化 BoundingBox）；**gateway→normalize 全链路 e2e 验证**：OCR 2.9s/1 文本、RT-DETR 2.9s/2 检测、VLM 5.5s/1 claim，均 `status=complete`（修复 RT-DETR box 字段 `coordinate` 数组解析）。**实测更正：PaddleX 同进程可共存 OCR+detection（此前"单进程单次初始化"结论是缓存 env 半初始化副作用，`_ensure_paddlex_cache` 修复后消除），无需进程隔离**。tests 补 helper/`_provider_for`/OpenCV/json_http 覆盖；`make check` 356 tests、80.05% coverage 全绿。
- 2026-08-15 E06 typed adapter 接入（State v54 追加）：新增 `packages/providers/visual/paddle_ocr.py`（PP-OCRv6）、`paddle_detection.py`（RT-DETR-L）、`volcengine_ark_vlm.py`（Ark doubao-seed VLM）三个 ProviderPort adapter——package() 复用准入注册表（research 单一真相源）、validate/estimate/health/infer 完整、paddle 依赖 lazy import（无 research extra 也能 import 模块）、PaddleX 缓存自动重定向 workspace `.paddlex-cache`、模块级模型实例缓存（避免同 adapter 重复初始化）；**gateway e2e 实测**：OCR 3.7s/1 项、RT-DETR 2.9s/2 项、VLM 7.8s/1 claim。tests/providers/test_visual_adapters.py 8 个测试（注册表一致性、validate/estimate、fail-closed）。`make check` 350 tests、80.03% coverage 全绿。**已知限制：PaddleX 单进程只允许一次初始化——OCR 与 detection 同进程顺序调用会冲突（需按 activity/进程隔离，记入 E06 集成设计）。**
- 2026-08-15 E06 VLM 火山引擎验证通过（State v54 追加）：`doubao-seed-2-0-mini-260428`（endpoint `ep-m-20260716234644-hqltj`）API key 与模型已配置（`.env` gitignored + typed settings，secret-safe）；**真实 demo 帧 VLM 调用 HTTP 200（8.1s）**，准确描述人物/野兔/山野场景/被打码文字（与 OCR "KEALN" 对应）；settings 新增 `NARRATOPRO_VOLCENGINE_ARK_API_KEY/MODEL/ENDPOINT`（public_summary 只暴露 configured 布尔）。注册表 VLM 条目 pin 模型与 endpoint。成本上限与真实短剧 VLM benchmark 仍待定。
- 2026-08-15 E06 语义视觉 Provider 本地 runtime 安装验证（State v54）：经项目负责人授权安装 paddlepaddle 3.3.1（arm64 CPU）+ paddleocr 3.7.0/paddlex 3.7.2，新增 `pyproject.toml` `[research]` extra；**PaddleOCR PP-OCRv6_medium_det+rec 与 RT-DETR-L 权重已下载、固定并记录完整 sha256 checksum**（注册表 `packages/providers/admission.py`）；demo 帧实测——OCR 推理 1.46s 识别文本、RT-DETR-L 检测 2 对象（score 0.94/0.81）；PaddleX 缓存重定向 workspace `.paddlex-cache/`（已 gitignore + ruff exclude）。`make check` 342 tests、80.38% coverage 全绿。**仍缺：真实短剧 benchmark 素材、Mac mini 容量验收、跟踪/embedding 链路验证。**
- 2026-08-15 E06 语义视觉 Provider 准入准备阶段 A + 决策（State v53）：评估报告 `evaluation/reports/E06_VISUAL_PROVIDER_ADMISSION_ASSESSMENT.md`；`packages/providers/admission.py` 候选注册表 + production 完整性校验器（fail-closed）；gateway 强制 `assert_production_ready`；tests/providers 5 新测试。**项目决策 2026-08-15：全开源路线不采用商业化**——Detection 排除 Ultralytics YOLO（AGPL）改选 PaddleDetection RT-DETR（Apache-2.0）；**VLM 走火山引擎（Volcengine Ark）豆包视觉模型 API（Doubao-SeedDance-2.0-mini，external_cloud、CN 驻留、帧外传，endpoint/API key/成本上限待定）**。
- 2026-08-15 E10 时间基防御与 qualification 测试维护（State v52 追加）：(1) `test_conform.py` 新增微秒基多行 subtitle cue 回归测试（E09 ADR-051 教训固化——cue 时间按 seconds 语义，rate 混合被拒）；(2) E10/E11 runbook 各增补时间基纪律条目（轨道微秒基 vs duration 低 rate，消费按 seconds 比较）；(3) `test_timeline_qualification.py` 更新 E09 blocker 断言 4→2（人工签署与多 Variant replay 关闭两个退出 blocker，剩余 semantic-visual-providers 与 craft 评分签核）；(4) `make check` 356 tests、80.56% coverage 全绿。
- 2026-08-15 qualification 一致性审阅（State v52 追加）：逐一对照 6 个 qualification 文件与 State 声称——e06_g05（R2，未关闭，6 passed/4 blocked/2 not_evaluated）、e07_h06（R2，工程关闭 4 passed）、e08_i05（R3，工程关闭 4 passed）、e10_k06/e11_l06（R4-release-candidate，契约基线）均与 State 一致；**修复 e09_j06 release_slice 过期值**（R3-creative-plan → R4-creative-production，与 State v49 起 Active Release Slice 一致）。其余 Epic 的 blocked/not_evaluated 均为真实 Provider/Corpus/rights 前置，无工程侧过期状态。
- 2026-08-15 E09 qualification 矩阵更新（State v52 追加）：`evaluation/qualification/e09_j06.json` 反映最新证据——`real-timeline-checkpoint` → passed（人工 approve + workflow succeeded，State v51）、`production-replay-preview` → passed（多 Variant restart/replay 工程验证，State v52）、`real-craft-benchmark` 保持 not_evaluated（AI 草稿 `e09_craft_compare_v1.json` 待人工评分签核）。9 passed / 1 blocked（semantic-visual-providers）/ 1 not_evaluated；`engineering_complete` 维持 false（语义视觉 Provider 未准入，E09 不得关闭）。
- 2026-08-15 E10/E11 advance baseline 审阅（State v52 追加）：契约模型与 runbook 约束逐一对照一致（E10 10/10 条：TTS rights/takes 边界、measured duration、reflow 范围、ducking/loudness/True Peak、subtitle collision/safe-area、libass profile；E11 RenderPlanContract/TechnicalQC 与 preflight blocker 语义）；`packages/production/render.py`、`conform.py`、`packages/timeline/compiler.py` 均有测试且 ruff/strict mypy 通过；e10_k06/e11_l06 qualification 状态正确（契约基线 engineering complete，production pending_human，真实 TTS/rights/QC 全 blocked）。
- 2026-08-15 E11 RenderPlan 编译真实数据验证（State v52 追加）：对多 Variant run 的真实 MasterTimeline（variant a，30.25s）调 `compile_render_plan` 两次，**checksum 确定性一致**（sha256:e9652a1c…）；16 operations 覆盖 video/original_audio/narration/subtitle 4 轨，8 clips 全部带 source_range；timeline duration 121/4=30.25s 正确。观察项：MasterTimeline.duration 用 rate=4（值正确），轨道 range 用微秒基（rate=1,000,000），E11 conform 消费时需按 seconds 语义处理（不构成当前缺陷）。
- 2026-08-15 E09 多 Variant restart/replay 工程验证（State v52）：`scripts/accept_e09_multi_variant.py` 用真实 SourceMedia 构造两个 variant（不同 beat/shot 组合与解说）并发跑 CreativeTimelineWorkflow，均到达 awaiting_review；**worker 硬重启后两个 workflow 均从 durable history 恢复，history replay 双双 PASS**；每 variant 9 个 Artifact 落库、preview 均渲染（variant a 30.27s / variant b 34.80s 全片）。验证期间发现并修复 preview heartbeat 潜伏 bug：`render_media_preview` 渲染期间无周期 heartbeat，长渲染（并发多 clip）触发 30s heartbeat timeout 导致 activity 超时——`real_preview.py` 新增 progress 回调（每 clip 调用），`creative_activities.py` 经 `loop.call_soon_threadsafe` 调度 heartbeat（to_thread 线程无 event loop）。`make check` 355 tests、80.60% coverage 全绿。
- 2026-08-15 J05 bounded debt 清理（ADR-051 已登记）：(1) `/patches` 端点重构为复用 `TimelineEditingService.apply_patch`，删除内联重复实现（单一实现，27+29 测试通过）；(2) Review Web timelineWorkspace 接线版本历史 `GET /timelines/{id}/versions`、`diff`、`POST /timelines/{id}/preview-partial`（typecheck + Vite build 通过）；(3) CI python-quality job 新增 PostgreSQL 16.4 service + `alembic upgrade head` + `NARRATOPRO_DATABASE_URL`，4 个真实 SQL 回归测试不再在 CI 跳过；(4) demo craft 对比表 AI 草稿归档 `evaluation/benchmarks/e09_craft_compare_v1.json`（标注 pending human signoff）。`make check` 355 tests、80.60% coverage 全绿。剩余 debt：`packages/timeline/revisions.py` 删除（需人工批准）、正式项目 Web 审核台端到端（需真实 StoryGraph/PlatformProfile 数据）。
- 2026-08-15 E09 timeline checkpoint 人工签署（State v51）：项目负责人审核 30.27s 全片 preview + 四段解说对照（带字幕播放页 `tmp/e09-cert-d8eb4cd5-preview.html`，WebVTT 字幕轨）后 approve；`scripts/sign_e09_review.py` 发送 approve signal，**CreativeTimelineWorkflow 到达 succeeded**（stages 全部 succeeded，无 blocker）；9 个 Artifact 与 run `d8eb4cd5` 落库确认。E09 "真实完整 Preview" 与 "人工 checkpoint 签署" 两个工程 blocker 关闭。
- 2026-08-15 E09 渲染时间基 bug 修复 full check（State v50）：`make check` 全绿 — 355 tests（+3 回归）、80.61% coverage、Ruff、strict mypy、Bandit、Context/Architecture、Registry 2.19.0 freshness/history 全部通过。
- 2026-08-15 E09 渲染时间基 bug 修复内容（人工审核证据驱动，对应发现见 `tmp/E09_REVIEW_DRAFT_FINDINGS.md`）：(1) 根因 — `packages/timeline/intent_projection.py` 两处游标 `RationalTime(value=0, rate_num=1)` 累加微秒基 duration，使第 2 个 intent 起 start 变成 4,083,333 **秒**（正确应为 4.083333s）；`workflows/timeline/creative_activities.py` `_assemble_sync` 兜底 duration 同样 `rate_num=1`；`AudioIntent` 契约缺 `source_range`，`multitrack.py` 把 timeline 位置当源时间复制给 ORIGINAL_AUDIO；(2) 修复 — 游标与兜底 duration 改 `rate_num=1_000_000`；`AudioIntent` 新增可选 `source_range`（ORIGINAL fail-closed 必填），projection 填充真实源范围，multitrack 使用之；Registry 兼容升级 2.19.0；(3) 验证 — 真实数据重跑 `accept_e09.py`（run `d8eb4cd5`）全链路 succeeded、Worker 硬重启恢复、history replay PASS、9 Artifact 落库；**新 preview 30.271s 全片**（修复前仅 4.08s，`-shortest` 被空音频截断），audio 4 段 4.083/9.5/12.625/4.041s 全部非空，ASS 字幕时间轴 0/4.08/13.58/26.21s 正确，DB MasterTimeline 各轨 timeline_range 正确且 ORIGINAL_AUDIO source_range=真实源时间（0/21.5/52.0417/99.625s）。
- 2026-08-13 E09 真实数据认证 evidence run（提交 `101f8a7`）：`scripts/accept_e09.py` 对真实 SourceMedia `8a0ce63f`（273MB、105.7s、17 个 PySceneDetect shots）跑通 CreativeTimelineWorkflow 全链路——visual/rhythm/narration/assembly/preview 五阶段全部 succeeded；到达人工 timeline checkpoint（awaiting_review）；**Worker 硬停止后重启，workflow 从 durable history 恢复**；**Replayer 重放 PASS**；9 个 Artifact（candidate_set/selection_plan/continuity_report/visual_report/rhythm_plan/narration_report/master_timeline/assembly_report/preview）全部确定性落库；preview 为真实 ffmpeg 渲染 720x1280 h264/aac + ASS 字幕（`tmp/e09-cert-c8dbb0bb-*-preview.mp4`，media_checksum sha256:74cc39a5…）。真实运行暴露并修复 4 个潜伏 bug：allocate_rhythm 整秒舍入（改微秒分配）、render_media_preview 三处 concat 相对路径（ffmpeg concat demuxer 按 concat 文件目录解析；改绝对路径）、MediaPreviewActivityRequest 缺 resource_profile（补字段并接线）。`make check` 352 tests、80.62% coverage 全绿。注：该 preview 事后经人工审核证据确认仅 4.08s（首段），由本 State v50 修复的时间基 bug 导致，以 run `d8eb4cd5` 的新 preview 为准。

- 2026-08-13 J05 审计修复 full check：`make check` 全绿 — 352 tests、80.61% coverage、Ruff、strict mypy、Bandit、Context/Architecture、Registry 2.18.0 freshness/history 全部通过。
- 2026-08-13 J05 审计修复内容（对提交 `367066b` 逐项审查后）：(1) 迁移根因修复 — `media_schema.py` 不再污染不可变 `baseline_v0001.metadata`（媒体表独立 metadata），已在真实 Postgres 全新库验证 `alembic upgrade head` 与 downgrade/upgrade 往返（此前全新库会在 0001 失败）；豆包就地改写的 0001/0002 已按用户授权丢弃并保持不可变（test_media_identity_migration 回归通过）；(2) Worker 沙箱 — 撤销全局 `with_passthrough_all_modules()`，改为 `workflows/media/__init__.py`、`workflows/visual/__init__.py` 细粒度 `imports_passed_through`（scenedetect/cv2/numpy C 扩展重复加载根因）；真实启动 worker 验证 7 个 workflow 全部通过沙箱验证并持续运行；(3) 编辑通道 L1 门禁 — 新增 `TimelineRepository.approved_intent_version`，`apply_patch`（服务与 `/patches` 端点两条路径）在 active version 等于已批准 timeline intent 时返回 409（fail-closed，防止改写已批准版本）；(4) append-only 版本分配 — `commit` 改为 max(version)+1，undo→新编辑不再与既有版本 PK 冲突（v3 保留为孤儿审计版本）；真实 Postgres 回归测试 4/4 通过（`tests/persistence/test_timeline_repository_db.py`，CI 无 DB 时跳过）；(5) 局部预览接线 — 新增 `POST /v1/timelines/{id}/preview-partial`（服务器端从 Object Store 解析真实源媒体、计算 changed ranges、渲染首段）；修复 `render_partial_preview` 的 `.mp4.part` 扩展名导致 ffmpeg 无法推断容器格式的 bug（改为 `.tmp.mp4`）；新增 compute_changed_ranges 单元测试与 ffmpeg 集成测试；(6) `JumpRequest.version` 加 ge=1；导航端点存储冲突统一映射 409（此前 missing version 会 500）；(7) settings 测试确定性修复（显式 bootstrap URL，不受本地 .env 影响）；Bandit assert 修复；(8) 死代码 `revisions.py`（RevisionHistory）保留但记为 bounded debt（删除需人工批准）。ADR-050 记录本轮决策。

- J02–J04 remediation full check：298 tests、80.35% coverage、Ruff、strict mypy、Bandit、Context/Architecture 和 Registry 2.18.0 freshness/history 全部通过。
- J02–J04 remediation 内容：新增 Artifact 类型 ClipSelectionPlan/ContinuityReport/VisualPlanningReport/NarrationPlanningReport/TimelineAssemblyReport/SourceSubtitleHandlingPlan（设计 Catalog 同步）；`packages/persistence/artifact_writer.py` 确定性 checksum 提交；`apps/services/clip_index.py` 持久化检索适配器；TimelinePlanningService/RhythmPlanningService/TimelineAssemblyService 全部落库；NarrationSourcePort L1 人工解说边界；`CreativeTimelineWorkflow` + 5 个 Activity 注册进 Worker；`packages/production/real_preview.py` 真实媒体 Preview（真实源文件 trim/scale/concat 集成测试通过，产出 720x1280 h264/aac + ASS 安全区字幕）；runbook 增补 8 条（#13–#20）；ADR-049 记录本链决策；J05 精确多轨编辑为下一项。

- J05 checkpoint cockpit：新增 exact-ref Timeline Review 读取 API、不可变 repository snapshot、可运行多轨审核台、L1 approve/revise/reject 提交和 fail-closed UI；`make check` 272 tests、80.57% coverage、Ruff、strict mypy、Bandit、Context/Architecture 和 Registry freshness 通过；Review Web TypeScript/Vite build 通过。精确编辑器和真实 Preview 仍未完成。

- J04/J05 targeted checks：Multi-track Contract/domain 和 Timeline Review API/Web typecheck 通过；Registry 2.17.0 freshness/history 通过；提交 `486cf94` / `1297e50`。
- J06 demo benchmark：`youzijuchang_demo.mp4`=260.7s、544x720、30fps、HEVC/AAC；PySceneDetect ContentDetector 记录 189 shots，median=1.2s；人工创意标注 pending。

- J02/J03 full check：263 tests、80.77% coverage、Ruff、strict mypy、Bandit、Context/Architecture 和 Registry 2.15.0 freshness/history 通过；提交 `95986d3` / `7bb5d22`。E09 仍 active，J04–J06 未完成。

- 六阶段、实施和校准设计入口全部存在。
- Markdown `git diff --check` 通过。
- 未发现旧 `Product V0.1`、`Python DAG` 或已废弃角色术语。
- 详细设计与实施/校准文档约 8,000+ 行；数量不是完成依据，权威入口以 `PROJECT_INDEX.md` 为准。
- Cold-start 检查：Index/State/Protocol/Handoff/Backlog 引用存在，active E00/A03 和当前风险可恢复。
- Git 根提交 `7f7591c` 已保存全部设计/治理文件；本地 demo 视频与抽帧由 `.gitignore` 排除。
- `make check`：17 tests、92.31% coverage、Ruff、strict mypy、Bandit、Context/Architecture checks 通过。
- Review Web：TypeScript typecheck 与 Vite production build 通过，依赖由 `pnpm-lock.yaml` 锁定。
- Compose：固定镜像配置通过 `docker compose ... config --quiet`；未启动服务。
- A03 runtime 尝试：Docker daemon 29.5.3 可用；镜像授权/manifest 请求 EOF，`compose ps -a` 和项目 volume 检查为空。
- A03 acceptance 已固化为 `make infra-accept`：覆盖启动等待、PostgreSQL/MinIO persistence probe、全服务 restart、再次 health 和最终状态；单元测试验证步骤完整。
- 2026-08-11 A03 runtime：containerd image store 关闭实验只解决 Temporal 单镜像下载，未完成全栈启动；实验已回滚，Docker 29.5.3/原设置恢复，项目 container/volume 为空。
- 2026-08-11 A03 recovery：验收脚本改为从 Compose 动态读取镜像、去重后串行拉取、每镜像最多 5 次指数退避，并以 `--pull never` 启动；PostgreSQL probe 改用容器有效配置。定向测试 4 项通过。
- 串行恢复已缓存 `postgres:16.4`、`temporalio/auto-setup:1.25.2`、`temporalio/ui:2.31.2`、`minio/minio:RELEASE.2024-11-07T00-52-20Z`、`otel/opentelemetry-collector-contrib:0.113.0`；`prom/prometheus:v2.55.1` 连续两轮有界重试仍在 Docker Hub/CloudFront blob 请求 EOF，故未进入服务启动。Docker 29.5.3 正常，项目 container/volume 为空。
- 代理隔离实验：Docker Desktop API 确认原模式为 `system`，macOS 系统代理为 `127.0.0.1:7890`；临时 `disabled` 后 registry manifest HEAD 超时，未改善拉取。已中止重试、恢复原设置并重启 Docker；最终 API=`system`、settings-store backup cmp=0、daemon 正常、项目 container/volume 为空。A03 仍未通过。
- A03 final acceptance：使用 checksum 验证的 `crane v0.20.3` 经宿主代理导入 Prometheus/Grafana arm64 固定镜像；Prometheus 来自官方 Quay 渠道并保留 digest。`scripts/accept_local_infra.py --skip-pull` 两次通过，第二次自动验证启动/重启后的 Temporal UI、OTel、Prometheus、Grafana HTTP readiness 及 PostgreSQL/MinIO persistence。
- 最终运行态：七个 Compose 服务运行；PostgreSQL、MinIO、Prometheus、Grafana 四个 named volume 存在；Prometheus host port 因 ClashX 9090 冲突改为配置驱动的默认 `19090`。本地 `.env` 未被 Git 跟踪。
- B01 full check：Ruff format/lint、strict mypy、Bandit、Context/Architecture checks 全部通过；32 tests、93.26% coverage；Hypothesis 对 checksum 任意 bytes、rational rate 约分和 exact rescale 执行 property tests。
- B01 runtime regression：Compose 七项服务仍运行，PostgreSQL/Temporal/MinIO health 正常；本次未修改 runtime 数据或配置。
- ADR-018 固定 UUIDv4、rational time、`sha256:<digest>` 和 canonical JSON 表示；B01 完成，恢复点切换 B02。
- B02 full check：Ruff format/lint、strict mypy、Bandit、Context/Architecture checks 全部通过；51 tests、92.43% coverage；定向 contracts tests 32 项通过。
- ADR-019 固定 Confidence 与 Rights fail-closed 语义：unavailable 无 score、shadow 无生产 calibration、calibrated/drifted 关联版本；Rights 以显式 UTC 时间/平台/地域判断，unknown/restricted/expired/revoked 和未解释限制均阻断发布。
- B02 完成，恢复点切换 B03；本轮未实现自动路由、RightsManifest payload 或 B05 ApplicableScope。
- B03 full check：Ruff format/lint、strict mypy、Bandit、Context/Architecture checks 全部通过；62 tests、93.86% coverage；`packages/contracts/envelopes.py` 100% coverage。
- ADR-020 固定 Envelope identity、UTC/SemVer/JSON payload、W3C trace ID 和公共错误显式披露边界；内部诊断不会进入 PublicErrorEnvelope。
- B03 完成，恢复点切换 B04；B03 仅保存最小 contract-shape snapshot，完整 Schema Registry/生成物尚未实现。
- B04 full check：73 tests、89.63% coverage；Ruff、strict mypy、Bandit、Context/Architecture、生成物 freshness 全部通过；Registry 定向测试 12 项、Review Web 离线 TypeScript typecheck 通过。
- Registry v1.0.0 生成 38 个 JSON Schema/OpenAPI components、38 个 TypeScript types、70 个 Artifact Type；设计 Catalog 与真实 package owner 一致。
- ADR-021 固定单一版本化 Registry、不可覆盖历史、SemVer breaking rules 和跨语言 unknown Artifact Type fail-closed；B03 临时 shape snapshot 已吸收并删除。
- B04 完成，恢复点切换 B05；ArtifactEnvelope payload、数据库 persistence 和业务 API 尚未实现。
- B05 full check：83 tests、87.68% coverage；Ruff、strict mypy、Bandit、Context/Architecture、Registry freshness 全部通过；Review Web 离线 TypeScript typecheck 通过。
- Registry v1.1.0 生成 52 个 JSON Schema/OpenAPI components 和 TypeScript types、70 个 Artifact Type；v1.0.0 保持不可变且 SemVer history 检查通过。
- ADR-022 固定 S0/S3、unresolved/disagreement、Correction successor lineage、结构化 ApplicableScope 和 Routing fail-closed 语义；B02 字符串 scope 为兼容性保留，未来替换需要 major migration。
- B05 完成，E01 关闭，恢复点切换 E02/C01 Database Baseline；当前仍为 L1/Confidence Shadow，未启用自动放行。
- E01 B05–B10 补全 full check：97 tests、88.94% coverage；Ruff、strict mypy、Bandit、Context/Architecture、Registry freshness 和 Review Web TypeScript typecheck 全部通过。
- ADR-023 固定 Envelope/领域 payload 分离、canonical Artifact lifecycle、Fact→Story→Strategy grounding、唯一 MasterTimeline/Patch CAS 和跨域 Registry 演进边界。
- E01 重新审计后完成，恢复点仍为 E02/C01；Envelope 无法独立检查的输入状态和版本单调性明确留给 E02 事务 Repository。
- E02 full check：105 tests、83.96% coverage；Ruff、strict mypy、Bandit、Context/Architecture、Registry freshness 和 Review Web TypeScript typecheck 通过。
- E02 PostgreSQL acceptance：隔离库完成 Alembic upgrade→downgrade→upgrade；Artifact CAS 并发 1 winner、cycle rejected、2-node invalidation closure、4 ArtifactVersion/4 Outbox、Blob committed、idempotency/publication conflict rejected、EffectiveConfig 创建、unknown rights blocked。
- E02 backup/restore：`pg_dump -Fc` 恢复到隔离库，对账 4 ArtifactVersion、4 Outbox、1 ConfigSnapshot、1 AssetRights。
- ADR-024 固定 PostgreSQL transactional artifact core、不可变 migration snapshot、LocalObjectStore atomic commit、CAS/outbox/dependency/invalidation 和 Policy/Rights publication 语义。
- E02 完成，恢复点切换 E03/D01；测试数据库仅为隔离验收数据，未触碰生产数据。
- E03 full check：126 tests，coverage gate 通过；Ruff、strict mypy、Bandit、Context/Architecture、Registry freshness 全部通过。
- E03 Temporal acceptance：真实 Temporal 完成 transient retry、人工 wait、Worker stop/restart、重复 Signal 去重、成功完成、history replay 和 InvalidInput non-retryable 验收。
- E03 PostgreSQL/API acceptance：Command idempotency、Run start outbox、Correction preview/apply CAS、Review first-wins、Release human RBAC 全部通过；使用隔离 `narratopro_e02_acceptance` 数据库，未触碰主数据库。
- ADR-025 固定 replay-safe Workflow、DB-first outbox reconciliation、human Release、lease admission、low-cardinality telemetry 和 Shadow-only confidence/correction semantics。
- E03 完成，恢复点切换 E04/E01 Master Timeline Domain。
- E04 full check：143 tests，80.06% coverage；Ruff、strict mypy、Bandit、Context/Architecture、Registry freshness 和 Review Web TypeScript 全通过。
- E04 real acceptance：PostgreSQL semantic Patch version 1→2、disjoint old-base Patch 自动 rebase 至 version 3、same-item old-base Patch 409；OTIO round-trip lossless。
- E04 Preview acceptance：Temporal Activity 从 exact Timeline Artifact v3 加载，FFmpeg 8.1.2 输出 720×1280 H.264/AAC 与 ASS sidecar，Preview Artifact/Dependency/Outbox 持久化，人工 Timeline Checkpoint 后 Workflow succeeded。
- ADR-026 固定唯一内部 MasterTimeline、semantic optimistic concurrency、OTIO loss boundary、deterministic RenderPlan、FFmpeg 8.1.2 和 Preview Artifact lineage。
- E04 完成，R1 Foundation 退出；恢复点切换 E05/F01。E05 只代表 Media Ingest，不得报告 Story Intelligence 已完成。
- E05 full check：157 tests、80.05% coverage；Ruff、strict mypy、Bandit、Context/Architecture、Registry freshness 全通过。
- E05 real demo acceptance：12,747,283 bytes；6 core Artifacts、9 frame samples、220 PySceneDetect Shadow shots；audio present、duplicate idempotent、unknown rights blocked。
- ADR-027 固定 UUIDv4 + PostgreSQL ingest identity、FFprobe raw boundary、FFmpeg derivatives、PySceneDetect Shadow、Temporal/L1 Catalog Review；Stage 1 人工签收已于 2026-08-12 完成。
- 2026-08-12 项目负责人明确批准 `quality/STAGE1_ACCEPTANCE_REPORT.md`；E05 正式关闭，恢复点进入 E06/G01。E06 只建设 Speech/Visual Observation，不得报告 Identity/Fact/Story 已完成。
- G01 full check：Provider/Contract/Gateway/Raw persistence 定向测试通过；Registry 1.3.0 生成 118 schemas、71 Artifact Types，历史版本保持不变。ADR-028 固定 Provider Port、执行前 policy admission、raw/normalized 隔离和 explicit unavailable；恢复点切换 G02。
- G02 acceptance：3-case synthetic fixture 覆盖 development/validation/frozen_test、4 个 slice metrics、显式 unavailable、series isolation，未声明阈值；ADR-029 固定按剧隔离、Frozen Test 防调参、严重错误单列和 prediction lineage。恢复点切换 G03。
- G03 full check：183 tests、80.55% coverage；Ruff、strict mypy、Bandit、Context/Architecture、Registry freshness 和 Review Web TypeScript 通过。
- G03 local research acceptance：生成普通话 WAV 经本地 FunASR legacy adapter 得到 1 个 timed segment、1 个 speaker cluster、1,313 ms、synthetic CER=0.0；adapter 明确 `research`，不声明真实域 CER/DER/质量阈值。ADR-030 固定 typed Speech/raw boundary、cluster≠identity、关键冲突与 L1/Shadow。恢复点切换 G04。
- G04 targeted check：9 tests；Ruff、strict mypy、Registry generation 和 Review Web TypeScript 通过。真实 demo frame 经 OpenCV research adapter 24 ms，8 个 generic foreground candidates，质量特征可追踪且 identity usability=false；未声明 OCR/detection/tracking/embedding/VLM 生产质量。ADR-031 固定 source-frame/Shot-local/typed VLM/license-first 边界。恢复点切换 G05。
- G05 deterministic qualification：12 checks=6 passed/4 blocked/2 not evaluated；engineering recommendation=rejected、human decision=pending、production_qualified=false。最近 bounded probe 为 4 threads/16 requests、16 successes、P50 8 ms/P95 17 ms（非准入指标），仅证明 research adapter 线程执行。ADR-032 禁止 Agent 合成生产批准；E06 保持 active，等待人工审核与 blocker closure。
- H01 targeted checks：Identity Contract/assembly 5 tests 通过；Registry 1.8.0 生成并通过 freshness；Ruff 和 strict mypy 通过。ADR-033 固定 similarity≠identity、human-only merge、cannot-link precedence、temporary unknown 和 replay ID injection；恢复点切换 H02。
- H02 targeted checks：Identity correction/persistence/API 9 tests 通过；Ruff、strict mypy、Registry 1.9.0 generation 通过。ADR-034 固定 preview→human commit、Project serialization、CAS、successor lineage 和 exact dependency invalidation；恢复点切换 H03。
- H03 targeted checks：Fact/Story contract 与 fusion 5 tests 通过；Ruff、strict mypy、Registry 1.10.0 generation 通过。ADR-035 固定 observable-only、correlated evidence 不重复计票、disagreement/incomplete 显式传播；恢复点切换 H04。
- H04 targeted checks：Story contracts/domain/workflow 6 tests 通过；Ruff、strict mypy、Registry history/generation 通过。ADR-036 固定 typed Artifact pipeline 与 temporal≠causal；nullable temporary Character 属 breaking change，Registry 正确升级 2.0.0；恢复点切换 H05。
- H05 targeted checks：Story Review Contract/API/control 5 tests 与 Review Web TypeScript 通过；Registry 2.1.0 generation 通过。ADR-037 固定 exact approval snapshot、L1 human Gate、blocked/incomplete fail-closed 和 Strategy approved-pointer-only；恢复点切换 H06。
- H06 full check：215 tests、80.04% coverage、Ruff、strict mypy、Bandit、Context/Architecture、Registry 2.2.0 freshness/history 和 Review Web TypeScript 通过。ADR-038 固定 engineering complete≠production approved；E07 engineering 关闭，恢复点切换 E08/I01。
- I01 targeted checks：Strategy profile/config/input 4 tests、Ruff、strict mypy、Registry 2.3.0 generation 通过。ADR-039 固定 ApprovedStory-only、hard-over-soft、equal-priority conflict blocker 和 experimental scope；恢复点切换 I02。
- I02 targeted checks：Candidate Contract/domain 8 tests、Ruff、strict mypy、Registry 2.4.0 generation 通过。ADR-040 固定 evidence-grounded、bounded fan-out、structural dedup 和 blocker-over-score；恢复点切换 I03。
- I03 targeted checks：Strategy planning/evaluation 7 tests、Ruff、strict mypy、Registry 2.5.0 generation 通过。ADR-041 固定 grounded direction、critic independence、structural diversity、blocker-over-score 和 cost range；恢复点切换 I04。
- I04 targeted checks：Strategy Gate Contract/API/Web tests、Ruff、strict mypy、Registry 2.6.0 generation/history 和 Review Web TypeScript 通过。ADR-042 固定 exact selection、双批准 pointer、L1 human Gate 和 candidate-only Variant 语义；恢复点切换 I05。
- I05 qualification：4 个工程/治理/成本检查 passed，5 个真实质量/运行检查 blocked 或 not_evaluated；production decision=pending_human。Registry 2.7.0、ADR-043、runbook/dashboard/Acceptance Report 已建立；E08 工程关闭，恢复点切换 E09/J01。

---

## 8. 恢复确认

新 Agent 应能在不读取历史会话的情况下回答：

- 项目目标是什么？
- 当前做到哪里？
- 哪些只是设计、哪些已实现？
- 下一项任务是什么？
- 哪些核心决策不可重做？
- 哪些风险/未决选择需要处理？

无法回答时，Context Reconstruction 未完成，不得开始修改。
