# System Architecture

Version: 2.0

详细模块、工具、数据、并发和建设阶段设计入口：`design/architecture/README.md`。

## 1. 架构目标

系统围绕一条可追踪、可人工干预、可逐步增强的短剧营销生产闭环建设。

架构中的“域”表示稳定职责边界；Hook、节奏、解说、音频和字幕是域内可替换模块，不作为彼此强耦合的顶层架构层。

---

## 2. 总体架构

```text
                         ┌──────────────────────────┐
                         │  1. Control Plane        │
                         │  状态 / 配置 / 审核 / 调度 │
                         └────────────┬─────────────┘
                                      │
Video Assets                          │
     │                                │
     ▼                                ▼
┌───────────────────┐        ┌───────────────────────┐
│ 2. Intelligence   │───────▶│ 3. Strategy Plane     │
│ Fact / Story      │        │ Genre / Selling Point │
│ Evidence / Episode│        │ Strategy / Hook       │
└─────────┬─────────┘        └───────────┬───────────┘
          │                              │
          └──────────────┬───────────────┘
                         ▼
              ┌──────────────────────────┐
              │ 4. Timeline Production   │
              │ Master Timeline / EDL    │
              │ Visual / Rhythm / Voice  │
              │ Audio / Subtitle / Render│
              └────────────┬─────────────┘
                           ▼
              ┌──────────────────────────┐
              │ 5. Evaluation Plane      │
              │ Quality / Approval       │
              │ Experiment / Feedback    │
              └────────────┬─────────────┘
                           │
                           └──▶ 新版本策略与时间线
```

---

## 3. Control Plane

负责：

- Project、run 和 artifact 生命周期
- Pipeline 调度与状态管理
- Strategy Config、Genre Config 和模型配置
- Human Review Gate
- 权限、成本、日志和失败恢复

核心执行者是 Codex Host Agent。它按任务加载 AI System Engineer、AI Drama Producer 或 AI Review Director，不存在第四个 Producer 角色。

输出：

- Project State
- Run Record
- Review Decision
- Configuration Version

---

## 4. Intelligence Plane

### 4.1 Media Catalog

记录 Episode、Asset、Scene、Shot、Frame 和时间坐标。每个事实必须引用 source_asset_id 与时间范围。

### 4.2 Fact Intelligence

提取：

- Dialogue、Speaker、Person、Entity、OCR、Action
- 画面、声音和表情的可观察特征
- 清晰度、亮度、响度等 Source Quality Features

Fact 只记录观察结果、来源、置信度和模型版本。“愤怒”“悲伤”等语义情绪属于推理，不直接写成无证据事实。

### 4.3 Story Intelligence

在证据引用基础上生成：

- Event、Character State、Relationship
- Conflict、Turning Point、Climax、Story Arc
- 跨集人物身份、全剧时间线和 Story Graph

多集索引与跨集身份解析属于本域内部能力，不是 Story Database 之后的独立层。

### 4.4 Source Quality Policy

质量分析只产生特征、评分和使用建议。低质量素材仍可用于理解剧情；只有 Strategy 或 Timeline Production 可以决定是否用于成片。

输出：

- Media Catalog
- Fact Database
- Story Database
- Evidence Links
- Source Quality Features

---

## 5. Strategy Plane

负责把 Story Database 转换成可审核的营销方案。

模块：

- Genre Knowledge：版本化的类型模板和参数
- Selling Point Discovery：卖点与高价值事件
- Strategy Generation：受众、方向、时长和叙事结构
- Hook Engineering：生成多个 Hook 候选及理由
- Variant Planning：不同策略、Hook、时长和平台版本

Hook 的模型评分是“先验建议”，必须记录评分依据。没有真实发布数据时，禁止称为效果预测。

A/B Test 只有在 Evaluation Plane 获得曝光、留存和互动数据后才构成闭环；仅生成两个版本称为 A/B Candidates。

输出：

- Strategy Proposal
- Hook Candidates
- Approved Strategy Config
- Variant Plan

---

## 6. Timeline Production Plane

### 6.1 Master Timeline

Master Timeline / EDL 是成片时间坐标的唯一事实来源，包含：

- Video Clip Track
- Original Audio Track
- Narration Track
- BGM / SFX Track
- Subtitle / Overlay Track
- Transition 与 Effect

所有元素使用统一 timebase，并引用来源 artifact。模块不得维护互不兼容的私有成片时间线。

### 6.2 Creative Planning Modules

- Visual Direction：镜头、构图、色彩和视觉连续性
- Rhythm Engineering：情绪曲线、信息密度、镜头时长、节拍与呼吸点
- Narration Engineering：解说文本、事实引用、情感、语速和停顿意图

三者共同形成 Timeline Draft，不是严格单向串行关系。

### 6.3 Media Production Modules

- TTS 与强制对齐：以实际音频时长回写时间线
- Audio Design：原声、解说、BGM、SFX、混音和响度
- Subtitle Visual：字幕文本、对齐、样式、安全区和动画
- Rendering：按 Master Timeline 合成候选成片

任何影响时长的修改都必须生成新的 timeline_version，并触发受影响轨道重新校准。

输出：

- Timeline Draft / ApprovedTimelineIntentRef
- Narration Script 与 Voice Asset
- Audio Mix Plan
- Subtitle Config
- Rendered Candidate

---

## 7. Evaluation Plane

### 7.1 Offline Quality Review

依据 quality/QUALITY_STANDARD.md 审核：

- 剧情事实与连续性
- Hook、营销结构和节奏
- 解说、音频、字幕和画面
- 技术规格、素材权利和发布风险

### 7.2 Human Approval

Story、Strategy 和 Release 三个 Gate 的权限边界以 workflow/PRODUCER_WORKFLOW.md 为准。

### 7.3 Experiment & Performance Feedback

在具备合法数据来源时记录：

- variant_id 与发布版本
- 曝光、3 秒留存、平均观看时长、完播率
- 跳出时间点、互动与转化指标
- 实验分组和样本量

线上指标只能用于校准策略和模板，不能覆盖剧情事实。

### 7.4 Human Correction Feedback

所有人工修改必须保存为结构化 Correction Record，至少包含原值、新值、修正类型、原因、artifact 与模型/提示词/配置版本。

反馈可以提出 Prompt、Genre Config、阈值或模型的新候选版本，但候选必须经过离线评测、人工批准和受控发布，不允许系统直接修改生产配置。

---

## 8. 横向基础能力

### Artifact Registry

所有数据、配置、提示词、模型结果和成片都必须有 artifact_id、version、producer、inputs、created_at 和 checksum。

### Asset Rights Metadata

视频、BGM、音效、字体和音色必须记录来源、许可证、使用范围和到期信息。权利不明的资产不得进入 Release Approval。

### Resource Profile

每次运行必须选择资源配置，声明硬件、并发、模型驻留、超时、本地/云端路由和成本上限。

### Confidence System

所有用于自动路由的 AI 推理输出必须包含 Confidence Record：

- score：0.0–1.0，或 unavailable
- method：模型概率、规则聚合、检索一致性或校准器版本
- factors：支持和削弱该判断的可解释因素
- evidence：事实与时间码引用
- calibration_version：校准数据与算法版本
- applicable_scope：该分数适用的任务、类型和模型范围

不同任务的 score 不能直接互相比较。模型自报置信度只能作为 factor，不能单独用于自动放行。

置信度阈值由版本化 Automation Policy 管理。`0.85 / 0.60` 仅可作为待验证的初始候选，未经校准不得成为生产阈值。

### Automation Levels

自动化等级作用于项目、运行或模块，模块级配置优先：

| Level | 名称 | 行为 |
|---|---|---|
| L0 | Manual | AI 仅辅助，主要结果由人创建或确认 |
| L1 | Review Required | 所有正式 Gate 必须人工决定；当前默认 |
| L2 | Confidence Routed | 经过校准的低风险结果可自动流转，低置信度或高风险结果转人工 |
| L3 | Risk-based Sampling | 已稳定模块采用风险分层抽样，阻断项和异常始终人工处理 |
| L4 | Feedback Optimized | 使用受控反馈持续优化候选版本，配置发布仍需审批，Release Gate 仍由人决定 |

人工介入率是观测指标，不是等级定义或质量保证。等级升级必须按模块评估校准误差、严重漏检率、样本覆盖和连续稳定窗口；发生严重错误时自动降级到更保守等级。

### Genre Config System

Genre Config 必须版本化并区分：

- hard_constraints：事实、权利、平台和禁止项，不得违反
- soft_preferences：Hook、节奏、语体、BGM 和字幕偏好，可由人工覆盖
- validated_scope：适用类型、平台、时长和样本范围
- evidence_summary：验证数据与已知限制

类型配置用于提供质量下限和一致性，不得替代剧情证据，也不得强迫所有作品使用同一表达。

---

## 9. 依赖与迭代规则

- 下游不得覆盖上游 artifact，只能引用或产生新版本。
- Evaluation 可以触发新的 Strategy 或 Timeline 版本，但不得反向篡改 Fact。
- 所有 AI 推理必须保留 Evidence Links、模型、提示词与配置版本。
- 模块以数据契约协作，禁止读取其他模块的内部状态。
- 自动化路由必须同时检查 confidence、risk_class、automation_level 和 blocker；高置信度不能覆盖阻断项。
