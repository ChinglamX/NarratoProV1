# Variant Planning and Strategy Review

Version: 1.0

## 1. 目标

让人基于证据、差异、风险和成本选择营销方向与 Hook，并把决策编译为 Stage 4 可稳定消费的 Approved Creative Brief 和受预算约束的 Variant Plan。

输入：StrategyComparisonPackage、CandidateEvaluation、Project Budget、Gate 2 command。

输出：StrategyDecision、ApprovedCreativeBriefRef、VariantPlan、StrategyCorrection、DecisionAudit。

---

## 2. Comparison Workspace

每个候选并排展示：

- objective、audience hypothesis、primary selling points；
- narrative spine、信息披露、时长和情绪意图；
- Hook 的画面/对白或解说/声音/衔接意图；
- Story/Event/Evidence 可点击定位；
- blockers、assumptions、unresolved、critic disagreement；
- Diversity 差异说明、feasibility 和成本区间；
- model/prompt/config/profile versions。

默认不以综合排名隐藏低分候选；人工应先看 blocker，再比较方向。

---

## 3. Gate 2 Decision

允许：Approve、Revise、Reject。Approve 必须选择：

- strategy_candidate_id/version；
- selected_hook_id/version；
- target duration/platform/audience snapshot；
- selected selling points 和 narrative spine；
- spoiler/reveal policy；
- Variant scope 和预算；
- 接受的风险、人工覆盖原因和 reviewer。

Decision 使用 expected candidate set version，防止审核期间候选更新导致 stale approval。审批结果以 Stage 1 Decision/Artifact 机制提交并 Signal Workflow。

---

## 4. Approved Creative Brief

Brief 是 Stage 3 与 Stage 4 的唯一正式边界，包含：

- ApprovedStoryRef/Evidence refs；
- EffectiveConfigSnapshot refs；
- strategy/hook/selling point refs；
- visual、rhythm、narration、audio、subtitle high-level intents；
- narrative beat budget、must-use/must-avoid、rights constraints；
- target output specs、cost ceiling、quality profile；
- unresolved accepted risks 和 provenance。

Stage 4 不读取 Strategy 草稿或 Provider 私有响应。

---

## 5. Variant Plan

Variant 不是笛卡尔积。Planner 根据实验目的和预算生成有限集合：

- 每个 Variant 只改变明确变量，例如 Hook、时长或表达方向；
- 记录 control/changed dimensions；
- 共享资产和可复用 Stage 4 计算；
- 估算增量成本与人工 Review 负担；
- 无真实发布实验时称 Candidate Variants，不称 A/B Test。

组合超过预算时按实验信息价值和人工优先级裁剪，不静默减少。

---

## 6. Correction 与增量失效

人工可以修改 Selling Point、Narrative Spine、Hook intent、Profile override 或 Variant scope。每次修改创建 StrategyCorrection 和新 Candidate/Brief version。

失效示例：

- 只改 Hook：失效对应 Hook、Brief、相关 Variant 和 Stage 4 Hook/timeline patch。
- 改 target duration：失效 Brief、全部相关 Variant 和 Stage 4 节奏/解说计划。
- 改 primary selling point：失效 Strategy 下游全部，不重算 Story。
- Story version 更新：现有 Brief 标 stale，必须重新验证并再过 Gate 2。

撤销通过新 Correction 指向先前版本，Decision/Audit 不删除。

---

## 7. 自动化边界

项目默认 L1，Gate 2 由人决定。未来 Policy 即使允许部分低风险策略流转，也不得自动替人决定品牌方向、可接受剧透和最终 Hook，除非该明确模块已有批准的自动化范围；任何冲突、unavailable 或 blocker 均 fail closed。

候选去重、硬约束校验、成本汇总和差异展示可以高度自动化。

---

## 8. 测试与验收

- stale candidate set 无法审批。
- Approve 缺少 Hook、版本、预算或 Profile snapshot 时被拒绝。
- Variant 组合不超过预算且 changed dimensions 可解释。
- Story 更新正确使 Brief stale。
- Correction/撤销保持 lineage 并触发正确依赖闭包。
- Stage 4 仅凭 ApprovedCreativeBriefRef 可获得完整输入。
