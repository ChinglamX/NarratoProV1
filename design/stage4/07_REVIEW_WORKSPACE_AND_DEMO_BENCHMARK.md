# Timeline Review Workspace and Demo Benchmark

Version: 1.0

## 1. 目标

提供专业的时间线审阅与局部修正界面，并把 `youzijuchang_demo.mp4` 转换为可重复比较的视觉、节奏、解说 benchmark，而不是仅用“像不像 demo”作主观判断。

输入：MasterTimelineDraft、PreviewArtifact、Story/Evidence、Constraint/Risk Reports、demo asset、Benchmark Profile。

输出：TimelineReviewPackage、TimelineCorrection/Patch、DemoBenchmarkArtifact、ComparisonReport、ApprovedTimelineIntentRef。

---

## 2. Workspace 能力

- 多轨 Timeline、缩略图、波形/占位音频和 markers。
- source/program 双预览与 Evidence 跳转。
- Clip trim/split/move/replace、Beat reorder。
- CropPath/keyframe、主体 anchor 和 fallback 调整。
- Narration text/intent/pause/pronunciation/lock 编辑。
- Beat budget、breathing point、transition intent 调整。
- Source subtitle handling、overlay/character-card intent。
- Constraint/continuity/evidence/rhythm problems 时间码定位。
- 版本 diff、局部 preview、接受/拒绝 AI Proposal 和撤销。

前端可使用 TypeScript/React；核心 Timeline/validation/preview compiler 仍由后端公共契约执行。

---

## 3. 编辑事务

UI 提交 semantic Patch，不直接修改内部数据库：

1. 获取 base timeline/version 和 scoped locks。
2. 本地形成 edit transaction 与 preview diff。
3. 服务端校验 expected item versions、权限和约束。
4. 冲突时返回 affected items 和 rebase options。
5. 成功后提交新 Timeline Artifact，并触发局部失效/preview。

Autosave 保存 draft branch，不自动将其设为 approved。Undo/redo 通过 Patch history，不删除历史版本。

---

## 4. Demo Benchmark 建设

Demo 是目标参考样本，不是绝对模板。Reverse-engineering 需要生成：

- Technical Profile：时长、画幅、帧率、编码、音频；
- Shot/Transition Timeline：镜头长度分布、切换/重复/速度变化；
- Composition：横转竖策略、主体位置、留边和硬字幕处理；
- Narrative Beat Map：Hook、背景、冲突、升级、payoff、ending；
- Rhythm Features：信息密度、情绪曲线、原声/留白和呼吸点；
- Narration Transcript：功能、句长、语速估计、对白重叠、语言风格；
- Packaging：人物卡、字幕层级、重点词和视觉强调；
- Reviewer Rubric：时间码证据、有效点、问题和适用范围。

所有人工标注具有 benchmark_version、annotator、agreement 和 unresolved。

---

## 5. 比较方式

机器可测：结构时长比例、shot duration distribution、cut density、重复率、画幅/主体覆盖、字幕占用、narration density、silence/original-sound windows。

人工评价：Hook 建立、上下文清晰、冲突递进、表演停留、节奏张弛、解说画面价值、情绪层次和整体可看性。

不以逐项数值复制 demo 为目标。候选因不同 Story/类型产生合理差异时，应记录设计理由；最终要求是达到或超过质量维度，而不是复制同一曲线。

---

## 6. Review Gate

Timeline Review 不是最终 Release Gate。允许 Approve Intent、Revise、Reject。Approve 固定 Timeline、Brief、Story、Profile、benchmark 与 accepted risks，作为 Stage 5 输入。

以下必须人工确认：Hook/正文衔接、关键节奏点、解说整体语体、复杂 reframe fallback、重大素材替换和任何接受的连续性风险。

---

## 7. 并发与性能

- waveform/thumbnail/problem overlays 预计算并缓存。
- 局部 preview 按 interval+handles 渲染，拖动时使用 proxy。
- 同一 Timeline 的 edit commit 串行，不同 draft branch 可并行。
- 长时间线虚拟化加载，不一次把所有 frame/crop points 送前端。
- Review session 与后台 AI Proposal 分离，后台结果不能打断或覆盖当前编辑。

---

## 8. 测试与验收

- stale edit、并发 reviewer、autosave、undo/redo 和 branch merge。
- source/program timecode 跳转准确。
- Patch diff 与实际 Preview 修改一致。
- demo benchmark 标注可重复导出、版本比较和 reviewer 分歧保留。
- 完整观看审核不能被局部问题检查替代。
- ApprovedTimelineIntent 可由 Stage 5 独立读取且不依赖 UI 状态。

