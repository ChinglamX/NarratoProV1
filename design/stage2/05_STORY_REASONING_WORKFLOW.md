# Story Reasoning Workflow

Version: 1.0

## 1. 目标

在 Approved/Observed Fact 和 Identity Graph 之上形成有证据的 Event、Character State、Relationship、Causal Edge、Turning Point 和 Story Arc，并通过 Story Gate 固定可供 Strategy 使用的版本。

输入：Fact Snapshot、Identity Graph、Episode order、Story Prompt/Config、Model Policy。

输出：EventSet、StateTransitions、RelationshipGraph、CausalGraph、ArcSet、ConflictReport、StoryReviewPackage、ApprovedStoryRef。

---

## 2. 编排边界

Temporal 管理持久化步骤、重试、并发和人工等待。LangGraph 只在单个 Story Reasoning Activity 内管理 typed AI state、工具检索和有限修订循环。

禁止一个 Prompt 从全剧视频直接输出最终 Story Graph。每个节点都提交独立 artifact：

```text
Fact Retrieval
→ Episode Event Candidates
→ Evidence Entailment Check
→ Event Dedup / Ordering
→ Character State Transitions
→ Relationship Changes
→ Causal Edge Candidates
→ Cross-episode Arc Assembly
→ Contradiction / Coverage Scan
→ Story Review Package
```

---

## 3. Event Contract

Event 至少包含：description、participants、source ranges、evidence、order key、confidence、status。Event 描述必须是最小有意义变化，不把一整集摘要塞入一个 Event。

事件类型可以由配置扩展，但类型只用于组织，不得迫使事实匹配类型套路。关键 Event 定义由 Story Quality Profile 给出，例如身份揭示、目标变化、重大冲突、不可逆结果。

---

## 4. Evidence Validation

对每个候选命题分别检查：

- evidence 是否真的蕴含描述；
- participants 与 Identity Graph 是否一致；
- 时间顺序和 Episode order 是否成立；
- 是否存在否定、转述、梦境、回忆或假设语气；
- opposing evidence 和 unresolved conflict；
- 该结论是 observed、inferred 还是 unknown。

LLM critic 只能提供候选判断。确定性约束、检索证据和人工 Correction 优先。

---

## 5. State、Relationship 与因果

Character State 使用 diff 表达：目标、已知信息、处境和可观察情绪解释。每个 diff 关联触发 Event 和证据，不为每个镜头生成冗余状态。

Relationship 记录从前一状态到后一状态的变化及触发事件，不把“夫妻/敌人”等标签当作永久事实。

Causal Edge 类型限定为 causes、enables、reveals、contradicts、changes_state、changes_relationship。时间先后不是因果；模型必须给出机制说明和 evidence，弱因果可标 candidate/unresolved。

---

## 6. 全剧汇总与并发

- Episode Event extraction 并行，输入固定 Fact Snapshot。
- Character State chain 按 Character component 并行。
- 全局 Event ordering、Causal cycle scan 和 Arc assembly 在汇合点执行。
- 并发输出用 stable IDs、deterministic sort 和 semantic dedup 合并。
- Project Story version 通过 CAS 提交；输入 snapshot 漂移则拒绝提交并重算受影响部分。

长剧按 Episode/Arc 分层摘要，但关键 Event 和 Evidence 不因压缩丢失。上下文构建使用检索和结构化索引，不把全部转录无界塞入模型窗口。

---

## 7. Story Review Package

Review UI 必须同时展示：

- Episode/全剧事件时间线；
- Character identity 与状态链；
- 因果/关系图；
- 每个结论的 supporting/opposing evidence；
- 视频定位与文本上下文；
- conflict、unavailable、低覆盖和高风险列表；
- Correction 操作及 dependency impact preview。

Story Gate 在 L1 必须由人批准。批准固定 `story_version + fact_snapshot + identity_version + prompt/model/config versions`。

---

## 8. AI 能力与局限

适合自动化：显式对白事件、明显动作、候选摘要、重复事件合并建议、结构化冲突扫描。

必须保守：隐含动机、潜台词、复杂倒叙、虚假陈述、身份反转、梦境、缺失镜头和跨集长因果。无法验证时用 unresolved，不得以语言流畅性填补。

线上营销表现不能反向改变 Story；只允许人工证据修正或新感知结果生成 Story 新版本。

---

## 9. 测试与验收

- 每个关键 Event Evidence coverage 达到版本化目标。
- 人物、否定词、Episode 顺序和因果严重错误分别统计。
- 注入互相矛盾 Fact，系统必须产生 Conflict 而非静默选边。
- 删除/修正一条 Fact 只重算依赖闭包。
- 模型更换产生可比较的新 Story artifact，不覆盖旧版。
- Story Approval 后 Strategy 只能引用批准版本。

