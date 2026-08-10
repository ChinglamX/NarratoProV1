# Evaluation, Concurrency and Feedback

Version: 1.0

## 1. 目标

为 Stage 3 建立候选质量评测、资源预算、并发控制、可观测性和结构化反馈，使营销智能可持续优化但不能自行修改生产配置。

输入：Stage 3 Workflow、Evaluation Dataset、Resource/Cost Profile、Human Decisions/Corrections、可选合法线上数据。

输出：Stage3Benchmark、Candidate/Review Metrics、CapacityReport、FeedbackDataset、Config/Prompt/Model Candidate Proposal。

---

## 2. 并发拓扑

| Queue | 工作 | 限制 |
|---|---|---|
| strategy_rules | profile、constraint、evidence、dedup | CPU/DB query |
| strategy_model | selling point、direction、hook generation | model residency/token |
| critic_model | semantic critic | 独立 provider、token |
| cloud_model | 高价值生成/critic | rate、budget、data policy |
| strategy_eval | diversity、benchmark、cost aggregation | candidate-set barrier |

Selling Point 按 Arc/Character 并行，Strategy 按 Direction 并行，Hook 按 mechanic 并行，Critic 按 Candidate 并行。Diversity、global budget 和 Comparison Package 必须等待 CandidateSet 汇合。

Temporal fan-out 使用 Candidate Budget 和分批启动；LangGraph 内部 revision loop 有硬上限。

---

## 3. Candidate Budget

预算同时约束：

- Strategy Direction 数量；
- 每方向 Hook 数量；
- 生成/critic token；
- 本地/云端调用；
- 最大 revision 次数；
- 总预计 Stage 4/5 生产成本；
- 人工比较负担。

预算解析由确定性 Planner 完成。超限候选标 `not_scheduled/budget_exceeded`，不能静默丢弃或执行后再报超支。

---

## 4. 离线评测数据集

评测单元不是孤立文案，而是 `ApprovedStory + Brief + Profiles + CandidateSet + Human Decision`。数据按类型、平台、时长、主角视角、Hook mechanic 和剧情复杂度分层。

标注内容：

- factual/continuity blockers；
- Selling Point relevance 与遗漏；
- Strategy structural difference；
- Hook comprehension/continuation；
- feasibility、risk 和 cost estimate error；
- reviewer preference、理由和 agreement。

创意偏好不存在唯一绝对答案。指标区分硬正确性、候选集合质量和人工偏好一致性。

---

## 5. 指标

硬质量：fact blocker rate、continuity blocker rate、Evidence coverage、rights/platform violation、unavailable rate。

候选集合：valid candidate yield、duplicate rate、structural diversity、selling-point/arc coverage、candidate budget efficiency。

审核效率：time-to-decision、revision rounds、candidate rejection reasons、correction rate、reviewer agreement。

估算：predicted vs actual Stage 4/5 cost/time，只有后续数据存在时计算。

效果：只有具备合法曝光与 variant 关联时记录 retention/completion/interaction；必须控制平台、时间窗、样本量和实验分组，不能把相关性当因果。

---

## 6. Confidence 与 Automation

Stage 3 Confidence 主要表达事实/约束可靠性和候选内部一致性，不表达创意一定成功。初期保持 shadow。

可逐步自动化：Schema、Evidence、hard constraint、duplicate、budget 和明显 infeasible 检查。

长期人工主导：目标受众假设、品牌方向、剧透容忍、营销承诺和最终 Hook。Automation Level 必须按模块配置，不以 Stage 3 整体平均准确率升级。

---

## 7. 反馈闭环

结构化记录人工选择、拒绝、混合、修改字段和理由，关联 Candidate、Story、Prompt、Model、Config、Profile 和 reviewer。

分析可以提出：

- Selling Point taxonomy/config candidate；
- Genre/Audience/Profile 参数 candidate；
- Prompt/Provider/rubric candidate；
- Candidate Budget 或 threshold candidate。

候选优化必须经过离线 benchmark、人工审批、canary、监控和回滚。禁止根据一次人工选择或线上高播放直接改生产配置，更不得修改 Story/Fact。

---

## 8. 故障、恢复与可观测性

- 单 Candidate 失败不取消全部集合；必须标 incomplete 并决定是否仍可审核。
- Generator/Critic timeout、rate limit 和预算耗尽按 typed error 处理。
- 输入 Story/Profile 更新使运行 snapshot stale，禁止提交旧 Comparison Package。
- 相同 idempotency key 不重复计费或提交候选。
- Trace 贯穿 StoryRef → SellingPoint → Strategy → Hook → Critic → Decision → Brief。

Metrics：queue/runtime/token/cost、candidate yield、duplicate/blocker、review latency、Correction、cache hit 和 downstream estimate。Candidate ID 不作为 Prometheus label。

---

## 9. 测试与验收

- 候选 fan-out 不越过配置预算。
- 单候选失败、Provider 限流和预算耗尽均可恢复或明确降级。
- 多 reviewer 数据不会被错误解释成唯一标签。
- 线上数据缺少曝光/实验信息时不能进入效果校准。
- 反馈只生成 candidate config/prompt，不自动发布。
- 回切旧 Config/Prompt/Provider 可重放历史 benchmark。

