# TTS Provider and Voice Production

Version: 1.0

## 1. 目标

通过可替换 Provider 把 NarrationLineSet 转换为发音正确、自然、情绪和语体一致、权利明确的 Voice Takes，并保留候选选择和质量依据。

输入：NarrationLineSet、Voice Profile、Pronunciation Dictionary、Provider/Resource/Cost Policy、Voice Rights。

输出：NormalizedText、VoiceTakeSet、VoiceTakeSelection、VoiceAsset、VoiceQC、ProviderRawResponse。

---

## 2. Provider Gateway

统一接口：`capabilities()`、`validate_input()`、`estimate_resources()`、`estimate_cost()`、`synthesize()`、`health()`、`model_identity()`、`rights_metadata()`。

候选包括 IndexTTS2、CosyVoice 和商业 TTS；必须通过中文发音、情感、时长、稳定性、资源、成本与许可证 bake-off 后进入 Production Policy。不在业务代码固定单一模型或特有参数。

Provider Adapter 把通用 emotion/pace/style intent 映射到模型能力，并生成 CapabilityLossReport。Provider 不支持的能力必须显式降级，不能静默忽略。

---

## 3. 文本规范化与发音

规范化处理数字、日期、金额、英文缩写、标点、儿化/方言和停顿标记，同时保留原 Narration text。规则和词典版本化。

Pronunciation Dictionary 包含人名、地名、多音字、设定词、读法、适用范围和人工锁定。自动 G2P 候选不能覆盖人工批准读法。

规范化结果必须可逆展示：审核者能看到原文、合成文本和差异。

---

## 4. Voice Take 生成

按语义段或句生成，保留上下文 prompt/style anchor 以维持一致性。每个 Take 记录：line refs、seed/controls、provider/model、voice identity、audio checksum、duration、sample rate、cost 和 raw response。

高风险关键句可生成少量候选；普通句默认单候选加失败重试。候选数由 Voice Budget 配置，不能全句无界多生成。

失败重试区分 transient、invalid input、model OOM、content policy 和 quality rejection。Quality rejection 使用新 take_id，不覆盖原音频。

---

## 5. Voice QC

机器检查：空音频、时长异常、静音头尾、削波、采样率、NaN、重复片段、ASR back-check、漏字/多字、关键词/数字/否定和发音词典匹配。

学习/人工检查：自然度、音色一致、情绪、语速、停顿、重音、句间衔接和“像念稿”问题。

ASR back-check 只能发现候选错误，不证明 TTS 自然。技术检查通过与声音表演通过必须分开记录。

---

## 6. 音色与权利

Voice Identity 记录来源、许可、授权主体、地域/平台/期限、是否允许克隆/衍生、撤销状态。未经明确授权禁止克隆演员或真实个人声音。

音色权利失效时，相关 Release Candidate 变为 rights_blocked；生成过的 Voice Artifact 保留用于审计但不得发布。

---

## 7. 并发与资源

- 独立语义段并行；相同 voice/model 使用受控 micro-batch。
- 相邻句共享 style context，但正式输出独立可替换。
- GPU/Metal/统一内存使用 semaphore；云端受 rate/cost/data policy 控制。
- 模型冷启动和 voice reference cache 纳入 Resource Profile。
- OOM 降 batch 后有限重试；不得通过无限并发提高吞吐。

---

## 8. AI 局限与修正

情绪、音色和精确时长往往互相制约。“刚好 3 秒”不代表自然。优先保证发音和表达，再通过文本、停顿和 Timeline Reflow 解决时长。

人工可选择 Take、重生成、修改发音、调整 intent 或退回 Narration Correction。锁定的 Take 不被批量重生成覆盖。

---

## 9. 测试与验收

- 人名、多音字、数字、否定、英文、方言和情绪句测试集。
- 漏字、重复、长静音、削波、音色漂移和句间不连续。
- Provider unavailable、OOM、限流、预算耗尽和回退。
- 相同输入/seed 的可复现能力按 Provider 如实记录，不强制伪确定性。
- 权利 unknown/revoked 无法进入 Release Candidate。
- Voice Correction 正确失效 Alignment、Subtitle、Mix 和 Render。

