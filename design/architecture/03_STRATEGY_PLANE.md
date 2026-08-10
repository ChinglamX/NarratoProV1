# Strategy Plane Detailed Design

Version: 1.0

## 1. 目标

把 Approved Story 转换为可解释、可比较、可人工选择的营销策略和 Hook 候选，不直接输出不可审查的成片指令。

---

## 2. 模块

| 模块 | 建设方式 | 输入 | 输出 | 并发 |
|---|---|---|---|---|
| Genre Resolver | 规则+LLM 候选，人工可覆盖 | Story、用户目标 | Genre candidates | 类型候选并行 |
| Selling Point Miner | Event/Conflict/State 评分+LLM解释 | Approved Story | Selling Point Set | Story arc/character 并行 |
| Audience & Platform | 配置与用户输入优先 | Project Brief | Audience/Platform Profile | 无状态 |
| Strategy Generator | LangGraph typed workflow | Story、Selling Points、Genre Config | Strategy Candidates | 不同方向并行 |
| Hook Generator | 模板+证据约束+LLM | Strategy、high-value events | Hook Candidates | 候选并行 |
| Candidate Critic | 独立模型/规则/Review Director | candidates、rubric | weakness/risk/rank | 候选并行，最终合并 |
| Variant Planner | 确定性组合与预算约束 | approved strategy | Variant Plan | 版本并行计划 |

---

## 3. Genre Config

建议使用 YAML/JSON + JSON Schema，运行时解析为 immutable config snapshot。

结构：

- identity/version/schema
- applicable_scope/validated_scope
- hard_constraints
- soft_preferences
- hook/rhythm/narration/audio/subtitle profiles
- quality thresholds
- validation summary/known limitations

建设规则：

- 类型配置是先验，不是剧情事实。
- 风格和节奏默认 soft preference；事实、权利和平台要求才是 hard constraint。
- 每个参数必须说明单位、默认值和合法范围。
- 没有验证数据的模板标记 experimental，不进入自动路由依据。

---

## 4. Selling Point Discovery

输入：Approved Event/Arc/Character State、目标平台与时长。

处理：

1. 确定性特征：冲突变化、身份变化、信息揭露、情绪峰值、因果位置。
2. 语义候选：LLM/VLM 给出为什么具有营销价值。
3. 证据校验：每个卖点绑定 Event 和源时间段。
4. 多样性去重：避免十个候选实际描述同一冲突。

输出：SellingPoint `{type, description, evidence, novelty, risk, confidence}`。

局限：卖点强度是受众和平台相关判断；没有真实数据时不能叫“转化预测”。

---

## 5. Strategy Generation

每个 Strategy Candidate 必须定义：

- objective 与 target audience
- target duration/platform
- selected selling points
- narrative spine
- information reveal policy
- emotional curve intent
- source coverage and excluded facts
- risks and unresolved assumptions
- estimated production cost

生成模式：

- 同一 Story 可并行生成情感、爽点、悬疑等不同方向。
- Candidate Critic 与 Generator 使用不同 Prompt，必要时使用不同模型，减少自我认可。
- 最终选择由 Gate 2 完成；未批准策略不得触发高成本 TTS/Render。

---

## 6. Hook Engineering

Hook 不是一句文案，而是 0–3 秒内的多轨意图：

- selected source moment
- visual crop/overlay intent
- narration/dialogue text
- audio accent
- information disclosed/withheld
- transition into context

评分分成：

- Evidence correctness
- Immediate comprehensibility
- Conflict/question strength
- Target audience fit
- Continuation coherence
- Novelty/diversity
- Rights/quality risk

没有真实发布数据时称为 heuristic score。真实效果预测需要 Evaluation Plane 的 variant 数据和校准模型。

---

## 7. 并发与成本

- Selling Point 可按 Arc/Character 并行。
- Strategy Candidate 可并行，但必须设置候选数量和 token budget。
- Hook 可在每个 Strategy 下并行生成，先便宜模型扩展、后高质量模型/人工筛选。
- Critic 并行打分后使用确定性 aggregation；保留不同 reviewer 分歧。
- 生成 3–5 个真正不同的候选优于大量轻微改写。

---

## 8. Confidence 与自动化

Confidence 不是文本流畅度，而是：

- Evidence coverage
- Story assumption count
- Config validation scope
- Reviewer agreement
- Historical calibration（存在时）

自动化潜力：

- 候选扩展、证据检查、去重、格式校验高度可自动化。
- 创意方向、受众判断和最终 Hook 选择长期保留人工主导。
- L2/L3 可以自动淘汰事实错误或硬约束违规候选，但不应因高分自动决定创意方向。

---

## 9. 失败模式

- 事实正确但卖点平庸：重新检索其他 Arc，不改写 Story。
- 候选同质化：增加 diversity constraint 和不同生成路径。
- Hook 与后文脱节：Continuation coherence 必须阻断。
- 类型模板压过作品特性：降低 soft preference 权重或人工覆盖。
- 评分虚高：进入 Shadow/Calibration，不用于自动批准。

---

## 10. 生产验收

- 每个卖点和 Hook 有 Evidence Links。
- Candidate 之间满足定义的多样性阈值。
- 人工能看到差异、假设、成本和风险，不只看到总分。
- Strategy 修改精确失效受影响的 Timeline 计划。
- Genre Config 更新可回滚并能对同一 benchmark 重放比较。
- 无线上数据时系统不输出“预计播放量/完播率”等伪精确结论。
