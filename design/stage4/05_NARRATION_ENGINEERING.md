# Narration Engineering

Version: 1.0

## 1. 目标

生成证据约束、口语自然、补充画面价值、符合 Beat 时长预算且全篇语体一致的 Narration LineSet，为 Stage 5 TTS 和对齐提供正式文本与表达意图。

输入：ApprovedCreativeBriefRef、Approved Story/Evidence、selected clips/dialogue、BeatBudget、Narration/Genre Profile、Pronunciation Dictionary。

输出：NarrationOutline、NarrationDraftSet、NarrationLineSet、EvidenceCoverage、RedundancyReport、DurationEstimate、NarrationPatchProposal。

---

## 2. Narration Line Contract

每行包含：text、intent、beat_ref、Evidence Links、target/min/max duration、emotion intent、pace/pause intent、pronunciation hints、relationship to dialogue、rhetorical status、risk 和 version。

表达性修辞必须不改变事实。人物心理、动机和因果只有在 Approved Story 明确支持时才能陈述；否则改为可观察描述、悬念或 unresolved 表达。

---

## 3. 分阶段生成

```text
Narration Function Map
→ Beat-level Outline
→ Evidence-constrained Draft
→ Spoken-language Rewrite
→ Dialogue Redundancy Check
→ Fact / Coreference / Terminology Check
→ Duration Fit
→ Global Voice and Emotional Progression
→ Narration LineSet Commit
```

禁止单 Prompt 同时承担选剧情、写文案、控时长和自我审核。各 pass 输出 typed findings，修订次数受预算限制。

---

## 4. 解说功能

每句必须至少承担一种功能：背景压缩、人物目标、因果连接、时间跳跃、潜在风险、情绪递进、信息 withheld、Hook/Payoff bridge。仅复述屏幕上清晰对白或动作的句子默认拒绝，除非重复用于强调且有明确节奏目的。

画面与原声能表达的信息优先由其承担；解说补足观众无法快速理解的背景、关系和连接。

---

## 5. 口语与全篇一致性

Narration Profile 定义语体、句长、连接方式、禁用表达、情绪范围和类型软偏好。系统检查：

- 书面化、模板化开头和 AI 套话；
- 人称、称谓、时态和指代漂移；
- 情绪一步到位、过度评价和连续感叹；
- 关键词机械重复；
- 前后信息重复或提前泄露。

Beat 草稿可并行，全篇 coreference、terminology、voice 和 progression 必须汇总检查。

---

## 6. 时长估算

目标字数只作初始约束。Duration Estimator 按语言、标点、数字、专名、emotion/pace 和目标 TTS Provider 历史数据估算区间，并带 estimator version/uncertainty。

若估算超出 BeatBudget，按顺序考虑删冗余、重写、调整画面承载或申请局部 reflow；禁止假定 TTS 可以无限加速。Stage 5 真实合成时长可能不同，必须触发正式 reflow。

---

## 7. 事实与证据检查

- 关键事实、人名、关系、时间和因果逐句映射 Evidence。
- 检查否定、程度、主体和结果是否被语言润色改变。
- 与 selected clips/dialogue 检查语义重复或矛盾。
- 修辞句标记 rhetorical，不把其当新 Fact。
- 无法验证的心理描写或细节进入 blocker/revision。

LLM fact checker 只是候选检查；结构化 Story refs、规则和人工 Correction 优先。

---

## 8. 并发、候选与人工修正

Beat outline/draft 可并行；每 Beat 候选数量受预算约束。全局 pass 串行提交。高价值 line 可生成少量表达候选，但不能让 Variant 数量无界增长。

人工 edit、lock line、change intent、split/merge line 和 pronunciation correction 生成 Patch。局部 regeneration 只能修改明确 scope；被锁定文本不得被全局润色覆盖。

---

## 9. 测试与验收

- 关键 Narration Line Evidence coverage 达标。
- 注入错人物、错因果、虚构心理和对白复述并验证阻断。
- 全文人称、称谓、术语与情绪递进一致。
- 估算时长与 Stage 5 实际 TTS 的误差可持续回测。
- 人工 lock 和局部 regeneration 不影响范围外文本。
- demo/项目人工评测覆盖口语性、画面价值、细腻度和节奏适配。

