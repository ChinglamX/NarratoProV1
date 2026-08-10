# Rhythm Engineering

Version: 1.0

## 1. 目标

把 Strategy 的叙事承诺、Story beats、候选镜头、对白和解说预算组织成有张弛、可解释、可局部调整的 Rhythm Plan，而不是机械追求更快切换。

输入：NarrativeBeatGraph、ClipCandidate/Selection、Hook/Duration/Genre Profiles、Dialogue ranges、Narration duration estimates。

输出：BeatBudget、RhythmCurve、ShotDurationProposal、BreathingPoint、TransitionIntent、RhythmRisk、RhythmPatchProposal。

---

## 2. 节奏模型

每个 Beat 记录：

- narrative function 与 required information；
- emotional intensity/valence intent；
- novelty、conflict、uncertainty、payoff；
- visual change 和 shot complexity；
- dialogue/narration/original-sound demand；
- target/min/max duration；
- entry/exit energy、breathing requirement；
- must-preserve moments 和 allowed compression。

RhythmCurve 是多维意图，不压成单一“节奏分”。

---

## 3. Beat Budget

1. 从 Approved Brief 获取目标总时长和 Narrative Spine。
2. 计算不可压缩信息、原声与 Hook/ending 最低预算。
3. 为 Beat 分配目标和允许区间。
4. 镜头选择与解说估时回传实际需求。
5. 在总时长约束下调整、压缩或暴露 infeasible。

若最低预算总和已超过目标时长，必须返回 DurationConflict，建议删减非核心 Beat、换表达方式或调整目标时长，禁止通过极端语速或不可理解快切强行塞入。

---

## 4. Shot Duration 与转场

镜头时长考虑动作完成、对白边界、表情反应、画面信息量、相邻构图和情绪作用。规则检测：

- 无意义长停留；
- 动作/对白中途切断；
- 连续过短导致不可理解；
- 等间隔机械切换；
- 高潮连续堆叠无建立或余韵；
- 转场重复、抢注意力或掩盖连续性问题。

转场默认 cut；特殊 transition 必须有时间/空间/情绪功能，不能为了“丰富”随机添加。

---

## 5. Hook、呼吸与 Payoff

- Hook 先建立承诺，不等于前 3 秒塞满最多信息。
- Hook 后必须提供足够 context bridge，避免观众不知道人物和冲突。
- Breathing Point 可以是静止镜头、原声、留白、反应或音乐空间，必须有叙事作用。
- Payoff 后保留理解/情绪落点；是否快速结束由 Strategy 决定。
- Ending intent 与下一集/行动引导不能破坏当前叙事闭合。

---

## 6. 优化与并发

Beat 初始预算可并行估算；全局总时长与曲线在 Variant 汇合点优化。局部 Shot duration proposal 可并行，序列级检查串行提交。

求解可采用约束优化/动态规划/启发式搜索，但必须输出：约束满足、权重版本、best-known、未解决风险和替代方案。模型只提出意图和问题，不能拥有最终时间坐标。

---

## 7. 局部 Reflow

人工修改 Beat/Shot/停顿时，Reflow Scope 默认限制为当前 Beat、相邻 transition 和受影响 narration placeholder。扩大范围前显示 impact preview。

锁定项包括人工选定 cut、原声时刻、Hook/Payoff anchor 和 pause。局部优化不得移动锁定项；无解则报告 Conflict，不偷偷修改远端 Beat。

---

## 8. AI 潜力与局限

AI 可以提出多种曲线、检查明显过密/拖沓、估计信息负担并生成备选。它不能稳定判断细微停顿、表演余韵和 0.5 秒级观看感受。最终节奏需要完整播放、人工标注时间码和 demo/项目 benchmark。

平均镜头时长只能描述结果，不能单独评价好坏。

---

## 9. 测试与验收

- DurationConflict、极短/极长 Beat、原声锁定和 Hook bridge。
- 曲线、预算和实际 Timeline duration 对账。
- 不同类型 Profile 产生差异但不违反 Story/Brief。
- 人工 lock 在 reflow 后保持稳定。
- 局部修改不造成远端静默漂移。
- 人工完整观看评测记录问题时间码、原因和修正效果。

