# Candidate Critic, Diversity, Risk and Cost

Version: 1.0

## 1. 目标

独立验证 Strategy/Hook 候选的事实、连续性、差异、可制作性、风险和成本，为人工比较提供证据，而不是用一个总分替代判断。

输入：CandidateSet、Approved Story/Evidence、Effective Profiles、Resource/Cost Catalog、Review Rubric。

输出：CandidateEvaluation、BlockerSet、DiversityMatrix、FeasibilityReport、CostEstimate、ReviewerDisagreement。

---

## 2. 检查顺序

1. Schema 和引用完整性。
2. Story/Evidence correctness。
3. Continuity 与 Hook promise/payoff。
4. Rights、platform、brand 和 safety blockers。
5. Duration 与素材可制作性。
6. 候选结构多样性。
7. 创意质量 heuristic rubric。
8. 资源、时间和成本估算。

发现 blocker 后 Candidate 状态必须 Reject/Needs Revision；其余检查仍记录，但总分不能覆盖 blocker。

---

## 3. Critic 独立性

- Generator 与 Critic 使用不同 Prompt identity，必要时使用不同 Provider。
- Critic 只能引用固定 Candidate/Story snapshot，不能暗中重写候选。
- 规则验证器负责可确定约束；LLM critic 负责语义问题候选。
- 多 critic 分歧保留为 ReviewerDisagreement，不强行平均成一致。
- Critic 的自然语言问题必须附 candidate field、Story/Evidence ref 或明确 rubric 条目。

防止模型自我认可不等于盲目堆模型；独立性收益必须通过 benchmark 验证。

---

## 4. Diversity Matrix

候选两两比较：primary selling point、viewpoint、opening promise、reveal policy、narrative spine、emotional intent、Hook mechanic、source moment、target audience 和文本语义。

结构字段权重大于文案 embedding。系统输出相似原因和 duplicate clusters，由预算策略保留代表候选。人工可以保留相近方案，但必须说明比较目的。

多样性不是越高越好：完全偏离 Brief 或证据的候选不因“新颖”获得奖励。

---

## 5. Feasibility 与成本

Feasibility 检查：所需 Event 素材可用、时长预算、跨集跳转、必要上下文、画面质量、原片字幕风险、可能需要的解说/图卡和平台限制。

CostEstimate 分解：

- Stage 4 规划/检索/模型调用；
- TTS 字数/候选音色；
- 复杂裁切、修复、字幕/包装；
- 预览/最终渲染数量；
- 人工 Review 复杂度；
- 云端调用和估算范围。

Stage 3 成本是区间估算并声明方法，不伪造精确金额。实际成本由后续 Run Record 回写用于校准。

---

## 6. 风险体系

风险分为：story correctness、continuity、spoiler、audience comprehension、rights、brand/safety、source usability、production complexity、uncertainty。

每项具有 severity、likelihood basis、evidence、mitigation、owner 和 gate impact。没有校准数据时 likelihood 可以 unavailable，不强制填写伪概率。

---

## 7. 并发与确定性汇总

- 每候选的规则/critic/成本检查并行。
- Diversity 必须在 CandidateSet 汇合后执行。
- 汇总使用版本化 rubric 和确定性规则；保留各 critic 原始结果。
- 并发失败只使对应 evaluation unavailable，不自动把 Candidate 判 Pass。
- 预算不足时优先完成 blocker 检查，再做软质量评价。

---

## 8. 测试与验收

- 注入事实错误、连续性断裂、权利风险和时长不可行，必须形成 blocker。
- 同义改写被聚类，结构不同候选不因相似词误删。
- Critic 不可修改 Candidate Artifact。
- 成本估算可追溯到资源/价格配置版本。
- critic 分歧在 Workspace 可见。
- 模型评分异常升高不能越过 deterministic blocker。

