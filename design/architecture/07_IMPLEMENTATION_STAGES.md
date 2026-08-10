# Production Implementation Stages

Version: 1.0

## 1. 阶段方法

阶段按依赖建设，但每个模块按最终生产标准实现。阶段完成意味着其数据契约、并发、恢复、监控和质量验收成立，不表示整个产品已经完成。

---

## Stage 1 — Production Foundation

详细设计入口：`design/stage1/README.md`。

### 目标

建立后续所有智能与媒体能力共同依赖的 durable execution、artifact、timeline、policy 和 observability 基座。

### Work Packages

1. Schema & Migration：Project/Run/Artifact/Dependency/Policy/Review/Correction。
2. Storage：PostgreSQL、ObjectStore interface、checksum、retention。
3. Durable Workflow：Temporal namespace、task queues、retry/timeout/heartbeat。
4. Worker Contract：Activity envelope、resource requirement、idempotency。
5. Master Timeline Core：timebase、tracks、items、patch、dependency invalidation、OTIO adapter。
6. Review API：awaiting review、signal/update、optimistic lock。
7. Observability：OTel trace、metrics、structured logs、dashboard。
8. Security/Rights：asset policy、secret、access、audit。

### 工具

Python、FastAPI、Pydantic、SQLAlchemy/Alembic、PostgreSQL、Temporal、OpenTimelineIO、OpenTelemetry、Prometheus/Grafana、Docker Compose。

### 输入

项目命令、媒体 URI、配置、Resource Profile、Rights Metadata。

### 输出

可耐久运行的空 Pipeline、版本化 Artifact、可编辑 Timeline、Review/Correction、完整 trace。

### 并发

先验证多 Run、多 Task Queue 和资源 admission；不接入重模型也要做 worker kill、重复提交和 backpressure 测试。

### 达到效果

系统可以可靠接收和恢复长任务，媒体/AI 模块以后只需实现 Activity Contract，不各自发明状态管理。

### Exit Criteria

- crash/restart/retry/idempotency 全部通过
- Schema migration 和 rollback 演练通过
- Timeline patch 与 invalidation 测试通过
- trace 可贯穿 API→Workflow→Activity→Artifact
- Review wait/resume 跨进程生命周期通过

---

## Stage 2 — Full Drama Intelligence

详细设计入口：`design/stage2/README.md`。

### 目标

完成完整短剧的可证据化理解，而不是一次性大模型摘要。

### Work Packages

1. Ingest/Proxy/Media Catalog。
2. Scene/Shot 与 Audio Segmentation。
3. ASR/VAD/Punctuation/Alignment/Speaker。
4. OCR/Person/Object/Tracking/VLM/Embedding providers。
5. Source Quality Features。
6. Identity Fusion 与人工 merge/split。
7. Fact Store 与观察/推理分离。
8. Event/State/Relationship/Causal/Arc typed workflows。
9. Story Conflict、Correction 与 Approval Workspace。
10. Intelligence benchmark 与 confidence shadow。

### 输入

合法完整视频资产、Episode manifest（可为空）、语言/热词、模型配置。

### 输出

Media Catalog、Fact Database、Character Graph、Story Graph、Evidence、Confidence、Approved Story。

### 并发

Episode、Shot、Audio Segment、Frame batch 并行；Identity Fusion 与全局 Story assembly 在汇合点执行。

### 达到效果

系统能回答“谁在何时做了什么、证据在哪、人物如何变化、冲突如何发展”，并允许人工纠错后增量重算。

### Exit Criteria

- 分层评测 ASR/OCR/identity/story，不使用单一总准确率
- 严重 Story 错误阈值达标
- 关键 Event Evidence coverage 达标
- 多集人物 merge/split 可逆
- 模型切换和失败回退通过
- 固定资源档案下吞吐/成本基线建立

---

## Stage 3 — Marketing Intelligence

详细设计入口：`design/stage3/README.md`。

### 目标

从 Approved Story 生成专业、可解释、足够多样但数量受控的营销候选。

### Work Packages

1. Genre Config Schema、registry、validation。
2. Selling Point taxonomy 与 evidence scoring。
3. Audience/Platform/Duration profiles。
4. Strategy Generator typed graph。
5. Hook multimodal intent schema。
6. Candidate Critic、diversity、risk、cost。
7. Comparison Workspace 与 Gate 2。
8. Strategy correction feedback。

### 输入

Approved Story、用户 Brief、Platform Profile、Genre Config、预算。

### 输出

Selling Points、Strategy Candidates、Hook Candidates、Approved Creative Brief、Variant Plan。

### 并发

Selling Point 按 Arc/Character，Strategy 按方向，Hook 按候选并行；统一由 budget limiter 控制。

### 达到效果

人看到的是带证据、差异、风险和成本的真正不同方向，而不是大量同义改写。

### Exit Criteria

- 事实/连续性 blocker 为零
- 候选多样性和 reviewer agreement 达标
- Genre Config 可重放、比较、回滚
- 不输出无数据支撑的效果预测
- Strategy 修改正确失效 Timeline

---

## Stage 4 — Creative Timeline Engineering

详细设计入口：`design/stage4/README.md`。

### 目标

形成达到 demo 目标的视觉、节奏、解说一体化可精修 Timeline。

### Work Packages

1. Timeline Compiler 与 Patch Proposal merge。
2. Clip retrieval/selection/continuity。
3. Smart Reframe 和 crop keyframes。
4. Burned-in subtitle detection/handling。
5. Rhythm curve、beat budget、reflow。
6. Evidence-constrained Narration 与全文 consistency。
7. Character card/emphasis/ending intent。
8. Timeline Review Workspace 和局部 regeneration。
9. demo reverse-engineered benchmark。

### 输入

Approved Creative Brief、Story/Evidence、Media Catalog、Platform/Genre Profile。

### 输出

Master Timeline Draft、Visual Plan、Rhythm Curve、Narration Script、Packaging Intent。

### 并发

Visual/Rhythm/Narration 产生并行 Patch Proposal；Compiler 解决冲突后提交。Shot 候选并行，序列连续性统一检查。

### 达到效果

产生可以人工精确编辑的专业时间线，画面、节奏和解说不再是三个互不一致的 JSON。

### Exit Criteria

- demo 拆解完成并形成 gold timeline/rubric
- Timeline 无非法区间和静默漂移
- smart reframe 失败有明确降级
- Narration 关键句有 Evidence
- 人工调整可局部重算
- demo 视觉/节奏/解说维度达标

---

## Stage 5 — Production Audio, Subtitle & Rendering

详细设计入口：`design/stage5/README.md`。

### 目标

完成可发布候选的声音、字幕、包装和确定性渲染。

### Work Packages

1. TTS Provider Gateway、capability/rights/cost。
2. Pronunciation、text normalization、multi-candidate TTS。
3. ASR back-check、forced alignment、Timeline reflow。
4. BGM/SFX registry、retrieval 和 Rights。
5. Mix Plan、ducking、loudness、true peak。
6. ASS subtitle、layout collision、libass render。
7. Render Plan/compiler、proxy/final、cache、retry。
8. Technical QC 与 Release Package。

### 输入

ApprovedTimelineIntentRef、Voice/Audio/Subtitle profiles、合法媒体资产。

### 输出

Voice、Alignment、Mix Plan、ASS/Overlay、Proxy、Final Candidate、Technical QC、Rights Manifest。

### 并发

TTS 分段、BGM 检索、字幕初稿并行；在 Timeline conform 汇合；Variant Render 按资源池并行。

### 达到效果

候选成片在同步、响度、字幕、安全区、编码和权利上达到生产标准，并在创作维度接近或超过 demo benchmark。

### Exit Criteria

- TTS 发音/完整性/音色一致性评测通过
- 音画字幕同步与响度达标
- proxy/final 一致
- render crash/retry/cache 测试通过
- 所有资产 rights resolved
- Release Review 通过

---

## Stage 6 — Quality Automation & Feedback Intelligence

详细设计入口：`design/stage6/README.md`。

### 目标

把人工机械审核逐步变成校准后的自动检查，保留创意和发布决策。

### Work Packages

1. Blocker detectors 与可定位 Review。
2. Correction taxonomy/data pipeline。
3. Confidence calibration 和 dashboard。
4. L2 routing、L3 risk sampling、drift/fallback。
5. MLflow prompt/model/config evaluation。
6. Candidate rollout、approval、rollback。
7. Online variant/performance ingestion。
8. Experiment analysis 与适用范围管理。

### 输入

历史 Run、Correction、Review、Benchmark、合法线上指标。

### 输出

Calibration Report、Automation Policy、Candidate Prompt/Model/Config、Experiment Result、Rollback Target。

### 并发

离线 benchmark 按样本并行；不阻塞生产；灰度按 project/type cohort 隔离。

### 达到效果

低风险机械任务减少人工，高风险和创意任务继续由人处理；系统每次升级都能证明没有降低质量。

### Exit Criteria

- 严重漏检、校准误差、覆盖率满足模块阈值
- 漂移和严重错误自动降级成功
- candidate→eval→approval→rollout→rollback 链路通过
- Release 不能被自动批准
- 线上结论包含样本、窗口、混杂因素和适用范围

---

## 2. 跨阶段并行建设

允许并行：

- Stage 1 稳定契约后，Stage 2 感知 provider 与 Stage 4 demo benchmark 可并行。
- Stage 2 的部分事实稳定后，Stage 3 Genre/Strategy Schema 可并行。
- Stage 4 Timeline Core 稳定后，Stage 5 TTS/Audio/Subtitle provider 可并行。
- Benchmark、Rights Registry、Observability 从 Stage 1 起持续建设。

禁止并行造成的假进度：

- Timeline Schema 未定就分别实现字幕/音频私有时间线。
- Evidence Schema 未定就大量生成 Story JSON。
- Rights Policy 未定就建设不可商用模型资产库。
- Benchmark 未定就宣称达到 demo 或 SOTA。
