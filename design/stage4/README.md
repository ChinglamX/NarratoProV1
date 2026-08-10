# Stage 4 — Creative Timeline Engineering

Version: 1.0

## 1. 目标

把 Approved Creative Brief 编译为可精修、可验证、可供 Stage 5 稳定执行的 Master Timeline Draft，使画面选择、竖屏构图、节奏、解说与包装意图共享统一 timebase、依赖和版本语义。

本阶段直接决定候选成片的叙事表达与观看节奏，但不完成正式 TTS、混音、字幕渲染或最终编码。

---

## 2. 协同拓扑

```text
Approved Creative Brief + Story/Evidence + Media Catalog
                         │
                  Narrative Beat Graph
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
 Visual Planner     Rhythm Planner   Narration Planner
        │                │                │
        └────── typed Patch Proposals ────┘
                         │
                 Timeline Compiler
            Constraint / Conflict / Reflow
                         │
                  Master Timeline Draft
                         │
             Preview + Review Workspace
                         │
             Human Correction / Local Regen
                         │
                         ▼
               Approved Timeline Intent
```

Planner 不能直接修改 Timeline；只能提交基于同一 base version 的 Patch Proposal。Compiler 统一求解硬约束、报告冲突并提交新 Timeline version。

---

## 3. 设计文件

- `01_TIMELINE_COMPILER_AND_PATCHES.md`
- `02_CLIP_RETRIEVAL_AND_CONTINUITY.md`
- `03_SMART_REFRAME_AND_SOURCE_SUBTITLES.md`
- `04_RHYTHM_ENGINEERING.md`
- `05_NARRATION_ENGINEERING.md`
- `06_COORDINATION_REFLOW_AND_PREVIEW.md`
- `07_REVIEW_WORKSPACE_AND_DEMO_BENCHMARK.md`
- `08_EVALUATION_CONCURRENCY_AND_FAILURES.md`
- `09_ACCEPTANCE_AND_BUILD_ORDER.md`

---

## 4. 输入

- ApprovedCreativeBriefRef 与 Variant scope
- ApprovedStoryRef、Fact/Evidence 查询接口
- Media Catalog、Shot/Track/OCR/Quality Features
- Platform/Genre/Duration/Visual/Narration Profiles
- Timeline Core、Artifact、Workflow、Review 与 Resource Profile
- demo benchmark asset：`youzijuchang_demo.mp4`

---

## 5. 输出

- NarrativeBeatGraph 与 BeatBudget
- ClipCandidateSet、SelectionDecision、ContinuityReport
- CropPath、ReframeFallback、SourceSubtitleHandlingPlan
- RhythmCurve、ShotDurationProposal、Transition/Breathing Intent
- NarrationOutline、NarrationLineSet、PronunciationHints
- typed PatchProposalSet、ConflictReport、ReflowReport
- MasterTimelineDraft、PreviewPlan、TimelineReviewPackage
- ApprovedTimelineIntentRef

---

## 6. 非目标

- 不合成正式 TTS 音频或承诺其精确时长。
- 不执行最终混音、字幕 burn-in 或发布规格渲染。
- 不让 Visual、Rhythm 或 Narration Planner 持有私有成片时间线。
- 不为了凑目标时长删掉必要因果或编造解说。
- 不把 demo 的表面样式复制成所有类型的固定模板。
- 不宣称 AI 能稳定完成 0.5 秒级艺术节奏判断。

---

## 7. 强制不变量

- Master Timeline 是唯一编辑时间真相源，时间使用 RationalTime。
- 所有 Clip 和关键 Narration Line 能追溯到 Story/Evidence 与源素材。
- Hard Constraint 不可由总分、最后写入或模型意见覆盖。
- Planner 并发结果通过 Patch Proposal 和 Compiler 合并。
- 任意影响时长的修改必须产生新 timeline version 和 dependency invalidation。
- Preview 与 Stage 5 Final 使用同一 Timeline/Transform compiler 语义。
- 人工修改优先保留；局部重新生成不得覆盖未授权区域。

---

## 8. 阶段验收摘要

- Timeline 无非法区间、隐藏重叠、负时长和静默漂移。
- Hook、正文、payoff 和 ending 在结构上连贯。
- 横转竖失败有明确降级，关键主体和原片字幕不被误裁。
- 节奏评测同时包含结构指标和人工完整观看，不只依赖平均镜头时长。
- 解说不复述对白、不编造心理，并满足证据和目标时长预算。
- demo 的视觉、节奏、解说特征形成版本化 benchmark，不作为单一万能模板。
- Timeline Correction、局部 reflow、preview 和回滚可独立测试。

完整构建与验收见 `09_ACCEPTANCE_AND_BUILD_ORDER.md`。

