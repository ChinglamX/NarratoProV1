# Clip Retrieval and Continuity

Version: 1.0

## 1. 目标

为每个 Narrative Beat 检索、排序和选择真实可用镜头，并在整段序列层验证人物、动作、空间、时间、视线和叙事连续性。

输入：NarrativeBeatGraph、Approved Story/Evidence、Media Catalog、Shot/Track/Quality/Embedding indexes、Visual Profile。

输出：ClipCandidateSet、ClipSelectionProposal、CoverageReport、ContinuityGraph、ContinuityRisk。

---

## 2. 检索策略

候选召回采用多路并集：

- Evidence direct range：优先引用事件原始镜头；
- Character/Identity/Action/Object/OCR filters；
- dialogue/time/episode neighborhood；
- embedding semantic similarity；
- source quality 与竖屏可用性过滤/降权；
- 人工 pin/ban list。

Embedding 相似只用于召回，不证明镜头符合 Event。正式候选必须通过 Story/Evidence、人物和时间范围验证。

---

## 3. 候选特征

每个 Candidate 包含：source range、shot/scene/episode、Story/Evidence refs、visible characters、action phase、shot scale、camera motion、gaze/screen direction、composition、source subtitles、quality、reframe feasibility、dialogue/audio availability、rights。

评分拆分为 relevance、narrative function、visual usability、continuity fit、reframe cost、quality 和 novelty。禁止使用单一 embedding score 决定镜头。

---

## 4. 选择与覆盖

先为每 Beat 形成 Top-K pool，再在序列层优化。选择目标：

- 覆盖必需 Story beats 和 Hook promise；
- 保留关键动作建立—发展—结果；
- 控制重复素材和同质构图；
- 保持人物/空间/时间可理解；
- 满足 source range、时长和 rights；
- 为解说、原声与呼吸点预留画面承载力。

素材不足时输出 CoverageGap，不以无关 B-roll 或重复镜头静默填充。

---

## 5. 连续性图

序列边检查：

- character presence/identity；
- action phase 和 match-on-action；
- screen direction、eyeline、shot scale jump；
- location/time/costume continuity；
- dialogue/original audio continuity；
- narrative order、flashback/preview marker；
- repeated frame/range overlap。

这些是风险和规则组合，不是所有跳切都禁止。人工/类型配置可以有意打破视觉连续性，但必须保留理由和叙事意图。

---

## 6. 并发与算法

- Beat 的召回和 Shot 特征评分并行。
- Embedding/DB 查询批量执行，避免 N+1。
- 每 Beat pool 形成后，在 Variant 序列层进行 beam search/动态规划/约束优化候选；算法可替换。
- 全局求解有时间和候选上限；输出 best-known 与风险。
- 不同 Variant 并行，共享 immutable candidate cache。

---

## 7. 人工修正与增量计算

支持 pin clip、ban clip、replace、trim、reorder、allow discontinuity 和原因。Pin 是 hard constraint，除非造成事实/rights/非法时间 blocker。

修改一个 Beat 只重新检索该 Beat 与相邻连续性窗口；改变人物身份或 Story version 时按 dependency closure 重算相关候选。

---

## 8. AI 局限

模型擅长语义召回和明显连续性提示，但对细微动作衔接、眼神方向、表演节拍和“镜头是否值得停留”判断不稳定。最终序列必须支持人工逐镜查看，不能只看缩略图或分数。

---

## 9. 测试与验收

- 关键 Beat 的素材/Evidence coverage 达标。
- 错人物、错误时间、重复 source range 和 rights blocker 被拒绝。
- 动作跨镜、视线、空间跳跃和有意蒙太奇样本分别测试。
- Retrieval 缺失产生 CoverageGap，不编造镜头。
- pin/ban/replace 后只重算局部窗口。
- 单镜高分但序列不连贯时不能被全局选择器误判为最优。

