# Stage 3 Acceptance and Build Order

Version: 1.0

## 1. 目标与契约

目标：规定 Stage 3 的依赖顺序、每个 Milestone 的退出条件、端到端验证、容量评测、回滚和最终签收标准。

输入：Stage 1/2 已批准能力、Stage 3 设计文件、Evaluation Dataset、Quality/Resource/Cost Profile、测试与故障注入环境。

输出：Milestone Evidence、Stage3 Acceptance Report、Quality/Capacity Baseline、Risk Register、Rollback Rehearsal Record、Stage 4 Handoff Approval。

本文件可以独立驱动交付验收；任何 Milestone 未满足退出条件时不得用后续阶段的人工补救声明完成。

---

## 2. 构建顺序

### Milestone 1 — Contracts and Configuration

- SellingPoint、Strategy、Hook、CreativeBrief、Variant contracts
- Genre/Platform/Audience/Duration/Brand profiles
- constraint merge、registry、snapshot 和 migration

退出：Schema、优先级、冲突、重放和配置回滚测试通过。

### Milestone 2 — Selling Point Intelligence

- taxonomy、feature extraction、semantic proposal
- evidence validation、dedup、coverage、risk
- Selling Point correction

退出：证据、严重错误、重复率和覆盖 benchmark 建立。

### Milestone 3 — Strategy Directions

- typed generation graph
- narrative spine、information/duration budget
- feasibility、bounded revision、candidate budget

退出：候选结构差异、约束、重放和失败降级通过。

### Milestone 4 — Hook Engineering

- multitrack Hook intent
- source moment retrieval、continuation plan
- heuristic rubric、spoiler/rights/source checks

退出：每个 Hook 有证据、可理解、可衔接且可由 Stage 4 编译。

### Milestone 5 — Critic and Comparison

- deterministic validators、independent critic
- diversity matrix、risk、feasibility、cost
- Comparison Workspace

退出：blocker 不可被评分覆盖，候选差异/风险/成本对人可见。

### Milestone 6 — Gate 2 and Variant Plan

- Decision/CAS/RBAC/Signal
- Approved Creative Brief compiler
- budgeted Variant Planner、Correction/invalidation

退出：审批、stale 防护、撤销、下游契约和精准失效通过。

### Milestone 7 — Production Qualification

- layered benchmark、resource/cost baseline
- concurrency/failure injection、dashboard/runbook
- Confidence shadow、feedback candidate workflow、rollback

退出：固定数据集和 Resource Profile 上的质量、成本、恢复与审核效率报告获批准。

---

## 3. 验收矩阵

| 维度 | 必须证明 |
|---|---|
| Config | hard/soft 分离、来源、冲突、snapshot、回滚 |
| Selling Point | Story/Evidence 支撑、相关性、去重和覆盖 |
| Strategy | 结构差异、叙事完整、信息预算和可制作性 |
| Hook | 多轨意图、即时理解、真实素材、后续衔接 |
| Correctness | 人物、事件、因果和连续性 blocker 为零 |
| Diversity | 结构化差异与人工判断一致，不是措辞差异 |
| Risk/Rights | blocker fail closed、接受风险有人工记录 |
| Cost | 方法、范围和版本可解释，预算执行前控制 |
| Review | stale 防护、RBAC、Decision、Correction、Audit |
| Automation | heuristic/shadow 不自动决定创意方向 |
| Incremental | Profile/Strategy/Hook/Story 修改精准失效 |
| Operations | 并发、恢复、trace、成本、runbook、rollback |

首次 benchmark 建立 baseline 后，由版本化 Stage3 Quality Profile 固定阈值。不能为了完成阶段而事后降低门槛。

---

## 4. 端到端验收场景

1. 读取一个冻结的 Approved Story 和多个 Profile。
2. 生成包含混合/unknown 类型的 Genre Resolution。
3. 按多个 Arc/Character 并行发现 Selling Points。
4. 生成有限且结构不同的 Strategy Directions 和 Hook mechanics。
5. 注入无证据卖点、错误人物 Hook、后文不兑现和权利 blocker。
6. 验证 validator/Critic 拒绝问题候选且保留证据。
7. Comparison Workspace 展示候选差异、分歧、成本和风险。
8. 审核过程中更新 CandidateSet，旧审批必须因 stale 被拒绝。
9. 人工修改 Hook/时长并批准，生成新 Brief 和 Variant Plan。
10. 验证下游失效范围、重放、trace、token/cost 和 lineage。

不得出现：直接修改 Story、综合分抵消 blocker、Variant 笛卡尔爆炸、未批准草稿进入 Stage 4、无数据的效果预测。

---

## 5. 质量评测

硬正确性和创意集合质量分别报告：

- factual/continuity/rights/platform blocker rate；
- Evidence coverage、invalid candidate rate；
- Selling Point relevance/coverage/duplicate；
- Strategy/Hook structural diversity；
- Hook comprehension/continuation 人工评分；
- reviewer agreement 与 time-to-decision；
- revision/correction rate；
- cost estimate 与后续实际差异（数据存在时）。

人工评测至少有清晰 guideline、证据定位和分歧处理。不能用 LLM-as-judge 单独作为创意质量真相。

---

## 6. 性能与容量

报告候选 fan-out、P50/P95 queue/runtime、token、模型调用、缓存命中、峰值资源、每个 approved brief 成本和审核负担。

测试覆盖多 Project burst、长 Story、多 Arc、多 Profile、Provider 限流和候选预算耗尽。候选数量增长必须受 Candidate Budget 约束，不能依赖增加机器解决组合爆炸。

---

## 7. 回滚与兼容

- Config/Profile/Prompt/Provider 回切创建新 Run，不覆盖旧候选。
- Approved Creative Brief 固定 snapshot，Registry 最新版本变化不影响历史运行。
- Strategy/Hook Correction 通过后继版本撤销。
- Story version 变化使 Brief stale，重新验证和审批后才能恢复正式状态。
- Workflow 代码保持历史 replay 兼容。
- Stage 4 Contract 破坏性变化需要版本迁移和兼容适配器。

---

## 8. 完成定义

- 所有 Milestone 和验收矩阵通过。
- 至少一个真实项目 benchmark 与一个困难/反例集完成。
- 候选事实与连续性 blocker 为零后才允许 Gate 2 Approve。
- 人工可以在不查看内部 Prompt 的情况下理解候选差异和证据。
- Stage 4 只依赖 ApprovedCreativeBriefRef 和公共查询 Contract。
- Confidence 可以继续保持 shadow；不以自动化率替代质量。

---

## 9. 不得以此替代完成

- 生成很多候选不代表具备策略能力。
- 文案不同不代表 Strategy 不同。
- Hook 有冲突词不代表能抓人或能衔接。
- LLM critic 给高分不代表没有事实错误。
- 两个版本不自动构成 A/B Test。
- 人工选出一个方案不代表系统的候选集合质量已经稳定。
