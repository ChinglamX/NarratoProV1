# Stage 3 — Marketing Intelligence

Version: 1.0

## 1. 目标

把 Approved Story 转换为有剧情证据、方向差异明确、生产成本受控、可由人比较和批准的 Selling Points、Strategy Candidates、Hook Candidates、Creative Brief 与 Variant Plan。

本阶段不追求无限候选数量。系统价值在于发现真正不同的营销方向、解释取舍、暴露风险，并把人工决策固化为可追踪输入。

---

## 2. 组件拓扑

```text
Approved Story + Evidence + Project Brief
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
 Genre/Audience/Platform     Selling Point Mining
         │                       │
         └───────────┬───────────┘
                     ▼
            Strategy Direction Planner
                     │
             Bounded Candidate Fan-out
                     │
         Hook Multitrack Intent Generator
                     │
       Evidence / Continuity / Risk Validation
                     │
       Critic + Diversity + Cost + Feasibility
                     │
              Comparison Workspace
                     │
          Human Gate 2 Strategy Decision
                     │
                     ▼
      Approved Creative Brief + Variant Plan
```

Temporal 管理候选生成、并发预算和人工等待；LangGraph 可用于单个 typed 策略推理子图。所有候选是不可变 Artifact，批准通过 Decision 选择版本。

---

## 3. 设计文件

- `01_CONFIG_AND_PROFILES.md`
- `02_SELLING_POINT_DISCOVERY.md`
- `03_STRATEGY_GENERATION.md`
- `04_HOOK_ENGINEERING.md`
- `05_CRITIC_DIVERSITY_RISK_COST.md`
- `06_VARIANT_AND_STRATEGY_REVIEW.md`
- `07_EVALUATION_CONCURRENCY_AND_FEEDBACK.md`
- `08_ACCEPTANCE_AND_BUILD_ORDER.md`

---

## 4. 输入

- ApprovedStoryRef、Fact/Evidence 查询接口
- Project Brief：目标、受众假设、平台、时长、数量和预算
- Genre Config、Platform Profile、Audience Profile、Duration Profile
- Rights/Brand/Safety Policy
- Model/Prompt/Resource/Automation Policy

---

## 5. 输出

- Genre Resolution 与生效配置快照
- SellingPointSet
- StrategyCandidateSet
- HookCandidateSet
- CandidateEvaluation、DiversityReport、Risk/Cost/Feasibility Report
- StrategyComparisonPackage
- Gate 2 Decision
- ApprovedCreativeBriefRef
- VariantPlan

---

## 6. 非目标

- 不生成正式镜头时间线、TTS、字幕或渲染成片。
- 不修改 Fact 或 Approved Story 来适配营销套路。
- 不把类型模板变成不可覆盖的内容公式。
- 不使用无真实曝光数据的播放量、完播率或转化率预测。
- 不允许高模型分数自动替代创意方向选择。
- 不生成大量只有措辞差异的“伪多样性”候选。

---

## 7. 强制不变量

- 每个 Selling Point 与 Hook 必须引用 Approved Story/Event/Evidence。
- Hook 必须定义视觉、文字/对白、声音、信息披露和后续衔接意图。
- 硬约束优先于评分；事实、连续性、权利和平台 blocker 不能被总分抵消。
- Candidate Critic 与 Generator 的运行和 Prompt 身份可区分。
- Gate 2 默认由人选择营销方向、Hook、目标时长和 Variant 范围。
- Approved Creative Brief 固定所有输入版本，Stage 4 不读取未批准草稿。

---

## 8. 阶段验收摘要

- 候选事实与连续性 blocker 为零。
- 人工能够直接看出候选的受众、卖点、叙事、Hook、风险和成本差异。
- 多样性通过结构化距离和人工判断共同评价，不只做文本 embedding 去重。
- Genre/Platform/Audience/Duration 配置可以重放、比较和回滚。
- Strategy Correction 精准失效下游 Creative Brief/Variant/Timeline，不重跑 Story。
- 无线上校准时所有效果相关分数明确标为 heuristic/shadow。

完整构建顺序和验收矩阵见 `08_ACCEPTANCE_AND_BUILD_ORDER.md`。

