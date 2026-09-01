# NarratoProV1 产品方向调整

Version: 2.0
Date: 2026-08-31
Status: Long-form vertical slice validated; optimization and repeatability pending
Owner: Project

## 1. 一句话目标

基于一部多集短剧的完整剧情理解，自动选择最有营销价值、具有明确冲突升级与情绪回报的跨集叙事闭环，生成一条 3–5 分钟、解说与画面匹配、节奏有层次、剧情连续且可人工修订的高质量解说营销短片。

## 2. 目标解释

这不是把高光片段拼起来，也不是把现有 30–60 秒流程简单拉长。系统必须：

1. 建立跨集人物、事件、目标、冲突、因果、反转和回报索引。
2. 从整剧选择一个适合 3–5 分钟表达的核心营销命题，而非逐集平均取材。
3. 组织连续叙事：Hook → 人物与目标 → 冲突 → 多轮升级 → 高潮 → 回报 → 追看动机。
4. 为每章选择能证明剧情、承载情绪或提供视觉回报的真实镜头。
5. 解说提供画面外的因果、背景、人物处境和期待，不复述对白、不机械描述动作。
6. 关键对白、报价、威胁、反转和情绪爆点保留原声，让解说与原声交替呼吸。
7. 全部轨道编译到同一 Master Timeline，由真实 TTS 时长驱动对齐。
8. 事实与技术 blocker 必须 fail closed；最终是否采用由人决定，公开发布不在本阶段范围。

## 3. 本阶段边界

### 要完成

- 输入 N 集视频目录，输出一条 3–5 分钟竖屏解说营销候选。
- 输出整剧证据索引、营销命题、章节蓝图、镜头清单、解说、Master Timeline、混音、字幕和 QC。
- 支持从 Story、Blueprint、Narration、Timeline、Render 检查点恢复。
- 人工修改章节、镜头或解说时，只重算受影响部分。
- 用普通剧集与对应热门剪辑做对照，学习结构规律但不复制其事实错误或表面样式。

### 当前不扩展

- 多租户、商业 SaaS、平台分发、线上反馈和 L2/L3 自动放行。
- 新 Review Web、第二套数据库或第二套媒体渲染框架。
- BGM/SFX 自动选配；首轮以原声、解说和必要留白为主。
- 所有类型一次性覆盖；首轮验证两个差异明显的剧集。

### 继续有效的底线

- 不编造人物身份、数字、关键剧情和因果。
- 类型参数从第一天配置化，即使首轮只有一个 Profile。
- 权利不得伪造为 cleared；测试素材记录为 `user_declared_internal_use`，禁止公开发布。
- 文件损坏、事实冲突、关键音画不同步、字幕不可读必须阻断通过。
- Release 始终人工决定，本阶段只生产 internal preview。

## 4. 从现有项目抽取的完整成片主链

不另起底层系统；以下能力直接复用，只允许薄适配：

| 环节 | 现有能力 | 本阶段用法 |
|---|---|---|
| 导入/探测 | `MediaIngestService`、FFmpeg provider | 批量 EpisodeCatalog、音轨和 source timebase |
| ASR | FunASR adapter 与现有缓存模式 | 逐集带时间码对白证据 |
| Story/Identity | StoryGraph、StoryReasoning、Identity contracts/services | 聚合跨集读取视图，不重写剧情真相源 |
| 视觉证据 | SceneShotCatalog、帧采样、VLM clip retrieval | ASR 窗口内取证并补纯视觉事件 |
| 选镜 | ClipIndex、TimelinePlanning、VisualPlanning | 跨集候选镜头与连续性报告 |
| 节奏/解说 | RhythmNarration、NarrationAnchor、NarrationDraft | 章节预算、校验与真实 TTS 后排程 |
| 时间线 | MasterTimeline、assembly/compiler/editing | 唯一成片时间真相源 |
| 成片 | IndexTTS、Mix、ASS、RenderWorkflow、TechnicalQC | 直接复用已验证链路 |
| 基准 | `series_main_cut_v3`、held-out/canonical 样片 | 回归与盲评基准 |

Temporal、PostgreSQL 和 Artifact lineage 不作为新增能力目标，也不删除。Canonical 运行继续使用它们；开发迭代可增加调用现有服务的本地 runner，但不得复制实现。

## 5. 只新增三个核心能力

### 5.1 Series Story Evidence Index

在现有 StoryGraph 上增加整剧读取视图，表达 Episode、Character、Event、Goal、Conflict、Turn、Payoff、跨集因果、人物状态变化、支持/反对证据和 unresolved。

ASR 不能独立生成视觉描述。每个入选事件至少具备对白或视觉证据；核心冲突和回报优先要求两者同时存在。

### 5.2 Marketing Arc Planner

从整剧索引生成 2–3 个结构不同的候选命题。每个候选必须说明人物目标、核心冲突、升级、高潮、回报、追看动机、证据覆盖、可用画面、预计时长和风险。系统可推荐默认命题，但不得把模型自报分数称作效果预测。

### 5.3 Long-form Chapter Timeline Planner

3–5 分钟采用章节级结构，每章再拆 Beat。参考范围：

```text
Cold Open / Hook          10–20s
人物处境与目标            25–45s
第一次冲突                30–50s
升级与代价                45–75s
反转或能力兑现            35–60s
高潮与阶段回报            30–50s
收束与追看动机            10–25s
```

范围由 Genre/Profile 配置，不是固定模板。每章声明叙事功能、事实主张、证据、情绪、镜头预算、原声保护区、解说预算和连续性。

解说长度由真实 TTS 与章节预算决定，不固定为每句 20–35 字。超时优先：缩写解说 → 调整停顿/有限语速 → 替换或扩展镜头；禁止无上限延长片段。

## 6. 质量与验收

- Story Correctness：关键人物、数字、事件和因果无严重错误。
- Cross-episode Continuity：章节能够回答“为什么进入下一段”，没有逐集摘要式断裂。
- Marketing Arc：前 10–20 秒建立问题，中段至少两次升级，结尾有回报或追看动机。
- Narration Value：解说提供因果、背景、处境和期待，不与对白争夺信息。
- Narration–Visual Alignment：关键主张出现时有对应人物、场景、动作或结果证据；有意延迟揭示须在蓝图声明。
- Rhythm：高信息段、原声爆点、观察留白和高潮形成层次，不追求全程满铺解说。
- Engineering：3–5 分钟输出与 Master Timeline 一致，可局部重算、断点恢复；严重技术问题 blocked。

每条候选沿用 `quality/QUALITY_STANDARD.md` 八维评分，并增加 Cross-episode Continuity 与 Narration–Visual Alignment 两项诊断。技术 QC 通过不等于内容质量通过。

## 7. 测试素材

测试根目录：`/Users/chinglam/Downloads/又子剧场`。

选择两类样本：

1. 主实验剧：剧情冲突清楚、集数完整、存在对应热门剪辑。
2. 泛化剧：类型或人物关系明显不同。

热门剪辑仅用于比较 Hook、事件取舍、原声、解说密度和高潮位置，不作为剧情事实来源。

当前已确认目录存在，但 macOS 权限阻止枚举。正式执行前先获得只读访问并生成 `evaluation/evidence/test_series_inventory.json`，再依据集数完整性、热门剪辑配对和类型差异推荐 1–2 部剧。

## 8. 成功标准

1. 一条命令输入多集目录，输出 3–5 分钟 internal-preview 及全部中间产物。
2. 整剧索引覆盖人物目标、主要冲突、升级、反转/高潮和回报，并有跨集证据。
3. 主实验剧至少生成两个结构不同的候选，人工选择后达到 `useful`。
4. 泛化剧在不逐镜头配置下达到 `useful_with_revision` 或以上。
5. 严重剧情错误为 0，普通问题有记录和修订路径。
6. 音画同步、字幕、响度和文件完整性无 blocker。
7. 修改一个章节或一段解说时不重跑无关 ASR、TTS 和镜头。
8. 不伪造 Rights、Evidence、Approval 或生产准入状态。

下一阶段任务见 `NEXT_PHASE_EXECUTION_PLAN.md`。首个 3–5 分钟候选通过人工看片前，不扩平台、不复制媒体栈，也不宣称复杂多集自动剪辑已经完成。
