# Hook Engineering

Version: 1.0

## 1. 目标

为每个 Strategy Direction 生成少量有真实剧情来源、能立即建立问题或期待、并能自然进入正文的多轨 Hook Intent。

输入：StrategyCandidate、Approved Story/Evidence、Media Catalog/Source Quality query、Hook Profile、Candidate Budget。

输出：HookCandidateSet、HookEvidenceMap、ContinuationPlan、HookValidationReport。

---

## 2. Hook Contract

Hook 不是一句标题，必须包含：

- hook type 与 opening promise；
- source moment refs 和可用素材范围；
- visual intent：主体、动作、构图、overlay/crop 意图；
- narration/dialogue/on-screen text intent；
- audio accent/silence/original sound intent；
- information disclosed、withheld 和 audience question；
- duration budget 与 transition into context；
- continuation beats 和 payoff relation；
- Evidence、assumptions、risks、heuristic scores。

Stage 3 不生成最终逐帧时间线，但字段必须足以让 Stage 4 编译和验证。

---

## 3. Hook 类型与生成路径

类型是可扩展配置，例如 conflict-in-progress、reversal-preview、identity-question、high-stakes-choice、result-first、contrast。每种类型定义适用条件、必要证据、常见风险和 continuation pattern。

生成流程：

1. 从 Strategy 的 primary promise 选择 Hook function。
2. 检索有足够画面/对白/声音支撑的 source moments。
3. 并行提出不同 Hook mechanics，而非同一句改写。
4. 检查开场可理解性和所需上下文。
5. 构建进入正文的 ContinuationPlan。
6. 检查剧透、事实、连续性、权利和素材质量。
7. 提交经过上限约束的 HookCandidateSet。

---

## 4. 多轨一致性

- 画面、对白/解说和文字不能表达互相矛盾的信息。
- 视觉只能使用真实可定位素材；尚未完成裁切时表达为 intent。
- 如果使用 result-first，必须说明回到上下文的时间/叙事机制。
- withheld information 不得造成事实误导。
- 音频强调服务理解，不能用尖锐音效掩盖信息不足。
- Hook promise 必须在 Strategy 的 narrative spine 中获得回应。

Continuation coherence 是阻断检查，不是普通加权分。

---

## 5. Heuristic Evaluation

拆分评价：Evidence correctness、immediate comprehension、conflict/question strength、audience fit、continuation coherence、novelty、source usability、rights/brand risk。

分数用于比较和诊断。没有真实按 `variant_id` 关联的发布数据与校准报告时，禁止输出预测播放量、预测完播率或“爆款概率”。

评分必须展示支持/反对因素和适用范围，blocker 优先于任何总分。

---

## 6. 并发与成本

- Strategy 间并行；同 Strategy 的 Hook mechanics 并行。
- source moment retrieval 先执行，避免为无画面支撑的创意调用昂贵模型。
- 候选扩展、critic 和最终润色使用分级预算。
- 同一 source moment 的帧/文本检索缓存复用。
- 全局 Candidate Budget 限制 Strategy×Hook 组合爆炸。

---

## 7. AI 局限与人工职责

模型善于提出开场形式和语言，但容易夸大、提前泄露、忽略后续衔接，或只依据文字而忽略素材可用性。人工负责选择开场承诺、可接受剧透和最终创意方向。

人工可以混合两个 Hook，但必须创建新 Candidate 并重新运行证据、连续性和成本检查，不能直接修改已批准 artifact。

---

## 8. 测试与验收

- 每个 Hook source ref 可打开到源视频时间码。
- 编造对白、错误人物、误导性 withheld information 被阻断。
- result-first、倒叙和悬念型 Hook 均有 ContinuationPlan。
- 相同 Strategy 下候选 mechanics 具有结构差异。
- 素材质量不足、权利风险和时长不可行显式展示。
- Hook 修改正确失效 Creative Brief/Variant/Timeline，不重算 Story。

