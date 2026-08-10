# Calibration Program Design

Version: 1.0

## 1. 目标

定义代码实现后的分层校准体系，使系统从“功能可运行”演进为“质量边界已知、自动化安全、持续可改进”的生产系统。

输入：Calibration Pack、系统预测、人工 gold/Correction、版本化 Provider/Prompt/Config、Quality/Automation Policy。

输出：Module Baseline、CalibrationModel、ThresholdCandidate、ApplicableScope、Promotion/Rollback Evidence。

---

## 2. 五类校准对象

| 类别 | 模块 | 主要问题 |
|---|---|---|
| 感知正确性 | Scene、ASR、OCR、Tracking、Identity、Alignment | 看见/听见的内容是否准确 |
| 剧情正确性 | Event、Character、Relationship、Causal、Arc | 剧情结论是否被证据支持 |
| 创意质量 | Selling Point、Strategy、Hook、Rhythm、Narration | 是否有效、连贯、有差异、有观看价值 |
| 媒体质量 | TTS、Mix、Subtitle、Reframe、Render/QC | 是否自然、同步、可懂、可读、稳定 |
| 自动化安全 | Confidence、Detector、Routing、Sampling、Drift | 自动流转是否遗漏严重错误 |

禁止把五类合成一个“系统总准确率”。

---

## 3. 数据集设计

首批建议 5–10 部代表性短剧，覆盖年代/农村、逆袭、情感、家庭、悬疑/身份反转、多人物、方言、强 BGM、复杂原字幕和低画质。

分区：

- Development：开发和错误发现。
- Validation：模型、Prompt、参数和阈值选择。
- Frozen Test：最终独立验收。

按剧/系列分组拆分；同剧相邻集、同人物和相似 Variant 不跨分区。每个 manifest 记录类型、语言、人物规模、画质、困难 slice、rights 和可用范围。

---

## 4. Gold 与标注

### Media/Perception

Shot boundary、Transcript、word/time、Speaker、OCR/text region、Track、Identity、source subtitle、关键主体。

### Fact/Story

关键人物、Event、顺序、关系/状态变化、因果、身份揭示、冲突/结果和 Evidence；允许 correct/incorrect/insufficient/disputed。

### Creative

Selling Point、Strategy 结构差异、Hook 理解/衔接/剧透、Rhythm 问题时间码、Narration 功能/复述/事实、Clip/Crop 修改。优先 pairwise preference + reason，不强制唯一绝对答案。

### Media Production

TTS 发音/完整性/自然度/音色、Alignment、BGM/ducking、Subtitle timing/layout、Reframe、Render/rights blocker。

所有标注带 guideline、reviewer、agreement、adjudication 和 unresolved。

---

## 5. 错误等级

- S0 Blocker：错人物、编造关键剧情、严重因果/同步/权利/文件错误。
- S1 Major：关键卖点或对白错误、明显节奏/复述/构图/盖声问题。
- S2 Minor：局部语言、镜头、强调或布局问题。
- S3 Preference：多个合理创意选择之间的偏好。

S3 不作为客观模型错误。S0/S1 必须按模块和困难 slice 单独统计。

---

## 6. 分模块指标

| 模块 | 指标 | 严重 Slice |
|---|---|---|
| Shot | boundary precision/recall/tolerance F1 | 漏剧情切换、过切 |
| ASR | CER、entity/negative/number error、timestamp | 人名、否定、金额时间 |
| Diarization | DER/JER | 关键对白归错人 |
| OCR | text/track precision/recall | 手机、文件、关键字幕 |
| Identity | pair/cluster precision/recall | 错 merge 高风险 |
| Story | event/evidence/causal accuracy | 身份、因果、结局 |
| Strategy | valid yield、coverage、duplicate、human choice | 无证据、伪多样性 |
| Hook | comprehension、continuation、pairwise preference | 误导、断裂、剧透 |
| Timeline | edit density、continuity、full-watch issues | Hook bridge、节奏、构图 |
| Narration | fact/redundancy/rewrite、duration | 编造、复述、错主体 |
| TTS | keyword error、take reject、naturalness | 人名、漏字、音色漂移 |
| Subtitle | timing/readability/collision/missing glyph | 挡脸、不同步、缺字 |
| Render/QC | spec/parity/failure/blocker detection | 文件、同步、rights |

指标阈值在首轮 baseline 后由版本化 Quality Profile 固定，不能事后为通过降低。

---

## 7. Confidence 校准

1. L1 Shadow 收集 raw score、features、scope、版本和人工结果。
2. 按 module/task/provider/model/prompt/type/language/platform 分桶。
3. 选择 Platt/logistic、isotonic、temperature、分桶规则或任务特定方法。
4. 在独立数据上报告 reliability、Brier、ECE、coverage-risk、severe false negative 和置信区间。
5. 先满足 severe false negative/blocker miss，再选择自动流转阈值。
6. 生成 CalibrationArtifact、ApplicableScope 和 DriftBaseline。

LLM 自报概率只能作为弱特征。数据不足或任务无法可靠估计时使用 unavailable/shadow。

---

## 8. 创意校准

同一 Brief 生成有限 Candidate，执行 pairwise review：Hook 建立、继续观看意愿、正文衔接、节奏、解说画面价值、类型适配和风险。

记录人工最终版相对 AI 初稿的：clip replace、trim、beat move、crop keyframe、narration rewrite、take reject、BGM replace、subtitle correction。

修改密度只是诊断指标；完整观看、时间码问题和 reviewer reason 才能判断创作质量。

demo benchmark 拆为 Hook/Context/Conflict/Escalation/Payoff/Ending、shot/rhythm、original sound/silence、narration function、subtitle/packaging 和人工 rubric。目标是达到质量维度，不机械复制数值。

---

## 9. 自动化晋级

### L1 Shadow

所有正式 Gate 人工；收集数据和 baseline。

### L2 Canary

只开放已校准低风险 scope。优先 technical/checksum/bounds/loudness/missing glyph，随后才是部分 ASR/OCR/TTS。Identity/Causal/Hook/Rhythm/Release 保守。

### L3 Risk Sampling

uniform baseline + threshold-near + rare slice + changed version + drift/OOD + historical severe-error neighborhood，并按抽样概率估计总体风险。

### L4 Candidate Optimization

反馈只能产生 Prompt/Model/Config/Threshold/Policy Candidate，经过 frozen plan、offline eval、approval、canary、monitoring 和 rollback。

---

## 10. 单项目校准记录

每条真实成片保存 AI→人工差异：Story、Strategy、Timeline、Narration、Voice/Mix/Subtitle、自动 Review→Release Review。

生成 Project Calibration Report：module、before、after、severity、reason、versions、dependency impact 和 proposed action。重复错误聚合后才提出候选优化，不能见一条改一次生产配置。

---

## 11. 测试与验收

- 数据集按剧/系列隔离且 Frozen Test 未污染。
- S0/S1/S2/S3 标签和 reviewer disagreement 可重放。
- 每个 CalibrationReport 绑定精确版本和 scope。
- 阈值选择优先满足严重漏检要求。
- 创意评测不只依赖 LLM Judge 或总分。
- 无足够数据的模块不能进入 L2。

