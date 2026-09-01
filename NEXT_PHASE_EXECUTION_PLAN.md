# 下一阶段执行计划：多集剧情到 3–5 分钟解说营销成片

Version: 1.0
Date: 2026-08-31
Direction: `PRODUCT_REDIRECTION.md` v2.0
Primary Role: AI System Engineer
Supporting Role: AI Drama Producer

## 1. 阶段目标

在不重复建设既有媒体能力的前提下完成一条真实纵向链路：

```text
多集原片 → 整剧证据索引 → 2–3 个营销命题 → 章节化蓝图
→ 跨集镜头/原声规划 → 解说与真实 TTS 对齐 → Master Timeline
→ 混音/字幕/Render/QC → 人工整片审核
```

成功标准不是脚本跑完，而是至少一条 3–5 分钟候选获得人工 `useful`。

## 2. 复用与新增边界

直接复用 MediaIngest、FFmpeg、FunASR、StoryGraph、Identity/Evidence、ClipIndex、TimelinePlanning/Assembly、Narration validation/Anchor、IndexTTS、Mix、ASS、RenderWorkflow 和 TechnicalQC。

只新增：

- SeriesStoryIndex 聚合读取模型与构建服务。
- Marketing Arc / ChapterBlueprint；现有 Contract 能表达时优先适配。
- 长成片章节预算与跨章连续性检查。
- 调用现有服务的单一 CLI/runner。
- 多集内容评测与热门剪辑对照报告。

禁止复制 FFmpeg/TTS/字幕/渲染实现、创建平行 Timeline、用最长对白冒充剧情理解、以热门剪辑文案作事实源，或放过事实/技术 blocker。

## 3. 工作包

### WP0 — 素材与环境基线

1. 获得 `/Users/chinglam/Downloads/又子剧场` 只读访问。
2. 生成目录、集数、文件、时长、规格和 hash 清单。
3. 建立原剧与“热门剧集”剪辑配对。
4. 推荐主实验剧与类型明显不同的泛化剧。
5. 素材登记为 `user_declared_internal_use`，不写 cleared。
6. 恢复 Python 3.11、FFmpeg、Docker/PostgreSQL/Temporal，或批准使用现有服务的本地 runner。

输出：`test_series_inventory.json`、`TEST_SERIES_SELECTION.md`、环境 readiness。

验收：两部剧可读；至少一部具备热门剪辑配对；媒体 probe 无 blocker。目录不可读或使用范围未声明时停止。

### WP1 — 整剧证据索引

1. 批量 ingest/ASR，按源 hash 缓存。
2. 每集生成带 ASR 时间窗的事件候选。
3. 对窗口抽首/中/尾帧并结合 SceneShot/VLM 生成视觉事实。
4. 复用 Story/Identity 服务合并跨集人物、事件、状态和因果。
5. 生成 Goal、Conflict、Turn、Payoff 视图，保留 unresolved。
6. 与热门剪辑的事件覆盖对比，但不吸收其未经验证的事实。

输出：SeriesStoryIndex、`series_story_review.md`、证据看片包、热门剪辑覆盖对照。

验收：人工抽查核心人物、数字、冲突和回报；严重事实错误为 0；主线没有因摘要而断裂。

### WP2 — 营销命题与章节蓝图

1. 生成 2–3 个结构差异明确的 Marketing Arc。
2. 每个候选包含 Hook、目标、冲突、升级、高潮、回报、追看动机。
3. 记录证据覆盖、视觉可用性、原声价值、预计时长和风险。
4. 推荐默认候选，保留其余候选比较。
5. 将选定命题展开为 6–9 个 Chapter 和内部 Beats。
6. 总预算 180–300 秒，显式包含原声保护区和呼吸区。

输出：Arc comparison、ChapterBlueprint、节奏曲线。

验收：至少一个候选构成完整冲突闭环，不依赖无证据动机或强行尾钩。

人工节点：项目负责人只选择营销命题，不逐镜头配置，避免在错误方向上消耗长 TTS/渲染成本。

### WP3 — 镜头、解说与 Master Timeline

1. 复用 ClipIndex/VisualPlanning 为每个 Beat 选候选镜头。
2. 检查人物、场景、动作和情绪连续性。
3. 标记原声爆点及禁止解说覆盖窗口。
4. 逐 Beat 生成解说，输入章节目的、前后文、对白与视觉证据。
5. 执行事实、复述、心理臆测和画面匹配校验。
6. 真实 TTS 后调用 NarrationAnchor 重排。
7. 组装唯一 Master Timeline。
8. 检查跨章跳跃、信息重复、无效镜头和持续高密度疲劳。

输出：选镜/连续性报告、NarrationLineSet、Voice Assets、章节节奏报告、Master Timeline 和低成本 Preview。

验收：关键解说有证据；不覆盖原声爆点；章节无因果跳跃；无持续满铺或无意义空白；TTS 时长已回写。

### WP4 — 成片与对照实验

1. 复用 Mix/ASS/RenderWorkflow 生成 internal preview。
2. 运行 TechnicalQC，blocker 必须失败。
3. 按现有八维标准做带时间码审核，增加跨集连续性和声画匹配诊断。
4. 对比 `series_main_cut_v3`、对应热门剪辑，以及可选的低解说密度版本。
5. 人工给出 `useful / useful_with_revision / reject`。
6. 只修正影响最大的三个问题，局部重算生成 v2。

输出：候选 v1/v2、QC、质量报告、热门剪辑对照、人工结论和修改成本。

验收：主实验剧 `useful`；泛化剧至少 `useful_with_revision`；严重剧情、字幕、同步和文件 blocker 为 0。

## 4. 里程碑

| 里程碑 | 可见产物 | 决策 |
|---|---|---|
| M1 输入就绪 | 两部测试剧 inventory/配对 | 输入是否有效 |
| M2 剧情理解 | 整剧索引/证据看片包 | 是否理解主冲突与回报 |
| M3 营销方向 | 2–3 个 Arc/章节蓝图 | 选择一个进入生产 |
| M4 时间线 | 3–5 分钟 Preview | 是否值得正式渲染 |
| M5 成片效果 | v1/v2 与对照报告 | useful/revise/reject |

## 5. 第一批 Backlog

1. `NP-LF-001`：获得目录访问并生成 inventory。
2. `NP-LF-002`：选择两部测试剧并建立热门剪辑配对。
3. `NP-LF-003`：定义 SeriesStoryIndex 的现有 Contract 映射。
4. `NP-LF-004`：实现 Episode → Story/Evidence 聚合 runner。
5. `NP-LF-005`：生成主实验剧整剧索引和人工抽查包。
6. `NP-LF-006`：实现 Marketing Arc 候选与 ChapterBlueprint。
7. `NP-LF-007`：复用规划服务生成跨集 ClipCandidateSet。
8. `NP-LF-008`：扩展章节级 Rhythm/Narration budget 与连续性检查。
9. `NP-LF-009`：组装 3–5 分钟 Master Timeline/Preview。
10. `NP-LF-010`：复用 E10/E11 输出 v1 并审核。
11. `NP-LF-011`：局部修订 v2，与热门剪辑/旧 v3 对照。
12. `NP-LF-012`：换第二部剧运行并形成泛化结论。

## 6. 当前唯一下一步

`NP-LF-001–012` 的纵向工程与两剧 internal-preview 验证已完成，《海渊契约》v4 已获项目负责人 `useful`，本计划的首要成功条件关闭。下一阶段不扩建平台：先补齐《海渊契约》第 9–22 集事件/视觉高光，生成后期奇观 Challenger 与当前因果完整版 A/B；随后用《神龟有灵》验证第三剧 held-out 固定入口。任何公开发布仍必须单独通过人工 Release Gate。

当前候选：

- `outputs/longform/shanshen_real/final_preview_v3_narrationfix/shanshen_longform_final_preview_v3_narrationfix.mp4`
- `outputs/longform/haiyuan/final_preview_v4_narrationfix/haiyuan_longform_final_preview_v4_narrationfix.mp4`
