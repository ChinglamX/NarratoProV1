# Selling Point Discovery

Version: 1.0

## 1. 目标

从 Approved Story 中发现具有营销表达价值且有明确证据的冲突、反转、人物变化、关系张力和信息揭示，并形成去重后的 SellingPointSet。

输入：ApprovedStoryRef、Evidence query、EffectiveConfigSnapshot、Target Duration、SellingPoint Taxonomy。

输出：SellingPointCandidate、SellingPointSet、CoverageMap、Conflict/Risk Report。

---

## 2. Taxonomy

Taxonomy 是版本化分类工具，不是固定剧本公式。基础类别可包含：

- goal_pressure：目标与压制；
- reversal/reveal：反转或信息揭示；
- relationship_tension：关系冲突与变化；
- competence/payoff：能力展示与回报；
- mystery/question：未解决问题；
- sacrifice/cost：选择与代价；
- status_contrast：身份、资源或认知反差。

允许 unknown/custom。新增类别不改变 Story，只有分类版本变化。

---

## 3. 候选发现

```text
Arc/Character Partition
→ Deterministic Feature Extraction
→ Semantic Candidate Proposal
→ Evidence Entailment
→ Audience/Platform Relevance
→ Risk and Spoiler Analysis
→ Semantic/Structural Dedup
→ Bounded SellingPointSet
```

确定性特征包括冲突增量、状态变化、关系变化、因果中心性、揭示位置、素材可用性和 source quality。模型解释“为什么值得营销”，但不得补写 Story 中不存在的刺激点。

---

## 4. Selling Point Contract

每个候选至少包含：

- taxonomy type、description、story/event refs、Evidence Links；
- target audience rationale、platform fit；
- narrative role：hook/core/payoff/context；
- spoiler level、required context、continuation potential；
- source coverage 与素材质量风险；
- heuristic components、ConfidenceRecord、assumptions；
- duplicate group 和 rejection reasons。

所谓“强度”必须拆成可解释分量，不能只输出单一神秘分数。

---

## 5. 去重与覆盖

去重同时检查：

- 引用的 Event/Arc 是否相同；
- 冲突与 payoff 结构是否相同；
- 目标受众和叙事作用是否相同；
- 文本/语义相似度。

只有措辞不同但叙事作用相同的候选合并。CoverageMap 防止全部卖点集中在同一角色或同一高潮，也允许项目明确只聚焦一个主线。

---

## 6. 并发、预算与失败

- 按 Arc、Character 和 taxonomy family 并行发现。
- 每个 partition 有候选上限、token budget 和超时。
- 汇合后确定性去重、排序和覆盖约束。
- 某 partition 失败产生 incomplete 标记；其他结果可继续审核。
- Evidence entailment 失败的候选被拒绝，不要求模型反复改写到“通过”。

---

## 7. AI 潜力与局限

AI 适合跨大量 Event 发现组合、解释受众价值和产生候选视角。AI 不可靠地预测真实市场效果，也容易偏爱显眼冲突、忽略长期铺垫或细腻关系变化。

系统必须允许人工新增卖点。人工新增仍需要绑定 Story/Evidence；如果证据不足，应回到 Story Correction，而不是在 Strategy 层改事实。

---

## 8. 测试与验收

- 每个正式 Selling Point 至少一个 Approved Story ref 和可打开 Evidence。
- 无证据、错误人物、严重剧透和需要缺失上下文的候选被正确标记。
- 同义改写不会占满候选预算。
- 不同 Arc/Character 的覆盖结果可解释。
- 人工新增、合并、拒绝候选保留 Correction lineage。
- Taxonomy/Config 变化只重算 Selling Point 及下游。
