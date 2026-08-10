# Strategy Generation

Version: 1.0

## 1. 目标

把 Approved Story、Selling Points 和 Profile Snapshot 组织成少量真正不同的营销方向，每个方向都明确叙事脊柱、信息披露、情绪意图、时长预算、风险与生产成本。

输入：ApprovedStoryRef、SellingPointSet、EffectiveConfigSnapshot、Project Brief、Candidate Budget。

输出：StrategyDirection、StrategyCandidateSet、NarrativeSpine、InformationPolicy、ProductionEstimate。

---

## 2. Strategy Direction

Direction 不是文案风格标签，至少由以下维度组成：

- objective 与 audience hypothesis；
- primary/secondary selling points；
- protagonist/viewpoint；
- opening promise 与 ending payoff；
- narrative spine 和必需上下文；
- reveal/withhold policy；
- emotional curve intent；
- target duration、information budget；
- source coverage、excluded arcs、spoiler policy；
- assumptions、risks、estimated production complexity。

如果两候选仅语气或措辞不同，它们属于同一 Direction 的表达变体，不是两个 Strategy。

---

## 3. Typed Workflow

```text
Constraint Resolution
→ Direction Skeleton Proposal
→ Selling Point Assignment
→ Narrative Spine Construction
→ Information Budget Check
→ Evidence/Continuity Validation
→ Feasibility/Cost Estimate
→ Candidate Critic
→ Bounded Revision
→ Candidate Set Commit
```

LangGraph state 使用结构化字段。每个节点输出独立 artifact 或 typed intermediate；自然语言解释不能替代约束字段。

Revision 最多执行配置化次数，失败后保留 rejected candidate 和原因，禁止无限 agent loop。

---

## 4. 信息预算与结构

Duration Profile 把总时长转换为可分配的信息/结构预算，而不是直接规定镜头秒数。Narrative Spine 至少标明：

- Hook 后观众需要理解什么；
- 背景、目标、阻碍、升级、转折、payoff 的必要性；
- 哪些信息可由画面/对白承担，哪些可能需要解说；
- 每个 beat 的 Story refs 和优先级；
- 可删减点与不可丢失连续性桥梁。

Stage 4 决定精确镜头和节奏；Stage 3 只定义意图和预算。

---

## 5. 候选生成与并发

- 先确定有限 Direction slots，再分别生成，避免随机采样制造伪多样性。
- Direction 可并行，但共享固定 input snapshot 和 global candidate budget。
- 同 Direction 可有少量 Hook/表达变体，不重复执行完整策略推理。
- 汇合时按 canonical structure 去重并检查覆盖。
- 高成本模型只处理通过规则/证据初筛的候选。

默认候选数量由 Candidate Budget 配置，不在代码写死 3–5。

---

## 6. 失败与降级

- 无足够证据支持方向：Reject，不改 Story。
- Duration 无法承载必要上下文：标 infeasible，建议更长 Profile 或换卖点。
- Platform/rights blocker：Reject，不能用分数抵消。
- 候选同质：重新分配 Direction dimensions，不仅提高 temperature。
- 模型不可用：保留确定性 skeleton，可人工完成或切换准入 Provider。
- Brief 冲突：生成 ConfigConflictReport，等待人工澄清。

---

## 7. Confidence 与决策边界

Confidence factors 包括 Evidence coverage、未解决假设、约束满足、Config validated scope 和 critic agreement。没有历史营销数据时只表示策略内部可靠性，不表示市场成功概率。

L1 下所有正式 Strategy Direction 由 Gate 2 人工决定。未来自动化可淘汰事实错误、硬约束违规或完全重复候选，但不得因高 heuristic score 自动选择创意方向。

---

## 8. 测试与验收

- 每个 Narrative Spine beat 可追溯到 Story/Evidence。
- 相同输入和 deterministic settings 可重放结构化候选。
- Duration/Platform/Profile 冲突能显式失败。
- 候选差异不仅存在于自然语言表述。
- 无法承载上下文的短时长策略不会伪装为 feasible。
- Strategy Correction 精准失效 Hook、Brief、Variant 和未来 Timeline。
