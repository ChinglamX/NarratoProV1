# Project Current State

State Version: 39
Last Updated: 2026-08-12
State Owner: Project

## 1. 当前阶段

- Lifecycle：Implementation active; E00–E05 completed; E06 production qualification debt retained; E07/E08 engineering closed with real-data qualification pending; E09 active.
- Active Release Slice：R3 Creative Plan。
- Active Epics：E10 Voice, Audio and Subtitle；bounded debt tracks E06/G05、E07/H06、E08/I05、E09/J06 production qualification。
- Active Backlog Entry：K01 Voice Provider and Take Contracts。
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
- E09/J01–J06 Creative Timeline：Approved Strategy-only input、typed Beat/Clip/Crop/Rhythm/Narration intents、grounded selection、CoverageGap、唯一 MasterTimeline assembly、Checkpoint 语义和 engineering qualification 已实现；Registry 2.9.0。工程结论 complete，production decision=pending_human。

设计完成不等于代码完成；不得把上述项目报告为已实现能力。

---

## 3. 尚未开始

- E10 Voice/Audio/Subtitle 与 E11 Render/Release Candidate 尚未实现；Story/Strategy/Timeline 真实素材人工签署尚未完成。
- Speech/Visual Review Workspace 与真实多剧 Calibration Corpus 尚未实现。
- Calibration Pack 的真实素材标注和 Baseline。
- 任何 L2/L3 自动化。

---

## 4. 下一步唯一恢复点

按 `design/implementation/08_INITIAL_IMPLEMENTATION_BACKLOG.md` 开始：

1. 按 E10/K01 建立 Voice Provider/Take、rights 和真实时长回写边界。
2. E06/G05 签署、真实 Corpus、模型 rights/checksum 与生产 load/fault/cost 验收保留为 bounded debt track，进入任何 production approval 前强制阻断。
3. E07 工程建设不得宣称人物/剧情质量通过；Confidence 仍为 Shadow，Story Gate 仍为 L1 人工。

开始编码前必须验证工作区状态、选择包管理/版本并将决定写入 ADR/State。

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
- FunASR adapter 已真实运行但只准入 research：完整模型权重 checksum、模型卡许可、商业使用批准和真实按剧隔离 Speech baseline 均缺失。
- PaddleOCR/semantic detector/tracker/embedding/VLM 尚无生产准入的 exact checkpoint 与真实短剧 benchmark；Ultralytics 许可姿态未批准，必须保持 blocked/research。
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
