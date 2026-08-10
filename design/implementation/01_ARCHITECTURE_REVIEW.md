# Global Architecture Review

Version: 1.0

## 1. 目标

检查六阶段设计的内在一致性、职责重复、契约缺口、可完成性和实施风险，并给出冻结后的收敛决策。

输入：纲领文件、architecture 设计、Stage 1–6 全部规格。

输出：Review Findings、Resolution Decisions、Remaining Risks、Implementation Preconditions。

---

## 2. 总体结论

总体架构内在一致：Control、Intelligence、Strategy、Timeline Production 和 Evaluation 五个稳定域，按六个生产能力阶段交付。核心数据链始终保持：

```text
Source → Observation → Fact → Story → Strategy → Timeline → Media → Quality/Feedback
```

不存在需要推翻的顶层矛盾。主要缺口集中在实施层：详细阶段新增了若干 Artifact 名称、Review checkpoint 和运行对象，但尚未统一到单一 Catalog、代码包和 API。

---

## 3. 已解决的边界问题

### 正式 Gate 与内部 Review

正式 Gate 只有 Story、Strategy、Release 三个。Stage 4 的 Timeline Review、Stage 5 的 Voice/Mix/Subtitle Review 是内部生产 Checkpoint，可以 Revise/Approve Intent，但不增加对外治理 Gate，也不能替代 Release Gate。

### Approved Timeline 命名

Canonical 名称使用 `ApprovedTimelineIntent`。它是 Stage 4 通过内部 Checkpoint 后的创意时间线，含 placeholder/intent；Stage 5 实际时长回写后产生 `ConformedTimeline`。二者都是 `MasterTimeline` 的不同 lifecycle state，不建立两种 Timeline Schema。

### Profile 与 Config

Genre/Platform/Audience/Duration/Voice/Audio/Subtitle/Render 等全部实现统一 `ConfigArtifact` envelope，内容使用各自 typed payload。运行时合并结果统一称 `EffectiveConfigSnapshot`，不再同时使用 EffectiveProfileSnapshot/Config Snapshot 等多个概念。

### Review 与 Correction

ReviewDecision 永不修改目标。所有人工修改统一使用 `Correction` + domain Patch；“批准”只创建 Decision 和 approved pointer，不复制一份内容实体。

### Confidence 与 Quality Score

Confidence 表示特定任务正确性/不确定性；Quality Score 表示 rubric 评价；Online Metric 表示平台表现。三者存储、校准和展示分离，禁止合成万能分数。

### Preview 与 Final

Preview、Final 共享 Timeline/Transform/Subtitle/Mix compiler 语义。Preview 只是 RenderProfile 降级，不拥有独立创意规则。

---

## 4. 重复职责收敛

| 重复表象 | 唯一所有者 | 其他模块职责 |
|---|---|---|
| Stage 2/6 都做评测 | Evaluation domain | Stage 2 提供任务数据和指标插件 |
| Stage 4/5 都做 Preview | Media Rendering application | Stage 4 请求 creative proxy，Stage 5 实现统一 renderer |
| Stage 1/各阶段都做失效 | Artifact Dependency service | 域模块只注册 typed invalidation rule |
| 多阶段都提 Review Workspace | 单一 Web application + Review API | 各域贡献 typed panels/actions |
| 多阶段都提 Rights | Rights Registry/Policy | 域模块提供 asset usage refs |
| 多阶段都提 Resource Admission | Control Plane Scheduler | Provider 声明 ResourceRequest |
| Stage 3/6 都做 feedback | Evaluation/Feedback service | Stage 3 只生成 Correction events |
| Stage 4/5 都做 Timeline conform | Timeline domain | Stage 4 创意 reflow；Stage 5 提交 actual-duration patch |

---

## 5. 契约缺口与解决

详细设计中新增而核心文件未完整展开的对象：EffectiveConfigSnapshot、Observation、IdentityGraph、NarrativeBeatGraph、PatchProposal、ApprovedTimelineIntent、ConformedTimeline、VoiceTake、QualityEvent、Calibration、RoutingDecision、DatasetManifest、ReleaseReviewPackage。

解决：全部登记到 `05_SCHEMA_AND_ARTIFACT_CATALOG.md`，后续落地为 `packages/contracts` 的版本化模型。`design/architecture/09_CORE_DATA_CONTRACTS.md` 保持高层契约，不再复制所有细节。

---

## 6. 可完成性判断

架构可完成，但必须遵守依赖顺序：先建立 Foundation Vertical Slice，再逐能力接入 Provider 和质量基准。最大工程风险不是单个算法，而是：

- 契约过多但没有生成/兼容测试；
- AI/媒体 Worker 各自处理状态和缓存；
- UI 直接修改数据库；
- 过早实现六阶段全部页面；
- 没有标注集却提前启用 L2/L3；
- Mac 单机同时运行模型和渲染导致资源争用。

解决方案是先实现可运行的 Contract/Artifact/Workflow/Timeline/Review 骨架，再按 Stage 2–6 逐个加入能力，所有模型先走 shadow/bake-off。

---

## 7. 尚需真实数据决定的内容

- ASR/OCR/Identity/Story Provider 与质量阈值。
- Mac mini 具体并发、模型驻留和 Render 容量。
- TTS、字体、模型权重与媒体资产商用许可。
- demo benchmark 的人工标注和分维度门槛。
- Confidence 校准阈值和允许 L2/L3 的具体模块。
- 平台技术规格及合法线上数据来源。

这些不是架构缺失，必须通过 benchmark/rights review 获得，禁止在实现前拍脑袋固定。

---

## 8. 测试与验收

- Schema Catalog 覆盖全部 Stage 正式输入输出。
- Truth Source/Owner 表无一对象多所有者。
- 三个正式 Gate 和内部 Checkpoint 行为测试。
- Package/Workflow Dependency Graph 无环。
- 任何跨阶段更新通过 ArtifactRef/Command/Event，不读取私有表。
- 架构新增概念必须同步 Catalog/ADR，否则 CI 文档检查失败。

