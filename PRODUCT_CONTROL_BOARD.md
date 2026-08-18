# Product Control Board

Board Version: 1.0
Updated: 2026-08-19（Director-assisted 能力审计）
Product Goal: Repeatable Series-to-Cut

## 1. 当前产品结论

项目不是“整体完成百分之多少”的问题，而是前半段工程较强、后半段个人成片链未闭合。

当前已经有一条产品负责人判定 `useful` 的七段解说样片，并已将同一内容迁入 canonical E10→E11 链路。真实 VoiceAsset、Alignment、Conform、MixedAudio、ASS、RenderExecutionReport 和 TechnicalQCReport 均已持久化；Temporal + Docker libass 渲染成功，产出 30.25 秒正式验证文件。它关闭 First Usable Cut 的产品与技术闭环，但不等于发布授权或各 Epic 全面完成。

当前唯一产品主目标：

> 对整部短剧一次性建立剧情索引，从全剧统一选择高价值营销闭环，再生成少量候选片；不再逐集生产、逐集确认。

《山神印》Candidate v3 已验证 Codex 导演辅助下的跨集候选生产，但镜头选择、解说文本和绝对 cue 时间主要由 Codex 写入配置。它是 `director_assisted_reference`，证明执行链可用，不证明新剧自动声画规划已具备。当前产品主线因此进入“导演决策沉淀为工具能力”：角色/决策来源落盘、声画语义锚定、TTS 后重排、内容寻址缓存和 held-out 盲测。

截至 2026-08-19，角色/决策溯源、声画锚定、TTS 后重排和内容寻址缓存已实现并通过确定性测试；第 7–8 集 held-out 候选在不填写任何解说绝对时间的条件下成功生成。当前下一必要产品节点仅为完整观看该 40 秒候选并评价效果；自动视觉事件、自动解说文本和自动选镜仍不在本次通过声明内。

本剧整剧理解与策略评审已完成，主路线为“觉醒山神印→驱狼→五十年野山参变现→守护妹妹”，目标产出 45–60 秒主片。第 3 集单集 checkpoint 已被整剧评审替代。

## 2. 产品能力看板

符号：`M0` 规格、`M1` 代码、`M2` 真实工具、`M3` 人工有用、`M4` 切片接通、`M5` 个人可重复使用。

| 模块 | 分类 | Delivery | Effect | 可查看证据 | First Cut blocker | 下一验证 |
|---|---|---:|---|---|---|---|
| Media Ingest | Core | M4 | useful | E05 demo ingest / Stage 1 sign-off | no | 纳入统一个人入口 |
| Visual Observation | Enhancer | M2 | unreviewed | E06 720-frame benchmark | no | 12 帧人工工具效果 review |
| Story Understanding | Core + Enhancer | M2 workflow | unreviewed | OCR Fact→Story run，零 event | yes，可人工兜底 | 同片段人工 Brief 对比 |
| Strategy / Hook | Core | M1 | unreviewed | Candidate/Gate 2 contracts and UI | yes，可人工兜底 | 3 候选人工选择 |
| Creative Timeline | Core | M3 | useful_with_revision | 30.27s Preview + Candidate v3 | yes，基础已具备 | 自动声画锚定 + held-out 盲测 |
| TTS / Voice | Core | M4 slice | useful | 7 WAV + committed VoiceAsset/VoiceTakeSet | no | 第二素材重复验证 |
| Conform / Mix | Core | M4 slice | useful | Alignment/ConformReport/MixedAudio + canonical MP4 | no | 第二素材重复验证 |
| Subtitle / ASS | Core | M4 slice | useful | committed ASSArtifact + libass 实片 | no | 字体跨环境验证 |
| Final Render / QC | Core | M4 slice | useful | `outputs/first_usable_cut_v2/canonical_e11.mp4` + execution/QC refs | no | 第二素材一键复跑 |
| Human Release | Core | M1 boundary | unreviewed | Gate 3 contract/API | yes | 对首个候选执行一次 |
| Confidence / L2+ | Scale | M0/M1 | deferred | contracts only | no | First Cut 后再评估 |
| Online Feedback | Scale | M0 | deferred | design only | no | 有真实发布后再开始 |

## 3. 当前 Blocker

按 First Usable Cut 排序：

First Usable Cut blocker 已全部关闭。进入“个人可重复使用”前仍有四项边界：

1. 单份配置入口已验证，但上游选题必须以整剧为单位。当前整剧 Story/Strategy 已由 Agent 完成内部候选生产审查，下一步直接生成跨集剪辑蓝图和主片候选。
2. IndexTTS 连续合成稳定性和 Docker 字体环境仍需重复验证。
3. 当前素材 RightsGrant 为 internal/manual-test，禁止把本次结果当作 Release Gate 3 或公开发布授权。
4. Candidate v3 的效果主要来自 Codex 导演配置；自动声画锚定、防提前剧透、TTS 后重排和角色/人工覆盖溯源尚未通过 held-out 验证。

以下不是 First Usable Cut blocker：

- E06 所有 Provider 完成 production admission
- 完整跨集身份与 Story Gold Corpus
- L2/L3 自动化
- 大规模并发和在线反馈

它们仍是未来生产规模化或质量提升任务，但不能抢占当前主线。

## 4. 三个产品检查点

### Checkpoint A — Parts Visible

必须能单独打开：

- 四句 TTS WAV
- Conformed Timeline diff
- Narration + original audio mix
- ASS 文件和字幕预览

通过条件：产品负责人知道每一步输入、输出和失败原因。

当前状态：**通过**。七个 WAV、VoiceTakeSet/VoiceAsset、Alignment、ConformReport、MixedAudio、ASS 和 manifest 均可独立追踪；canonical refs 见 `outputs/first_usable_cut_v2/canonical_acceptance.json`。

### Checkpoint B — Full Cut Visible

必须得到完整 30 秒 MP4，并验证：

- 四个画面段完整
- 解说可听且不被原声掩盖
- 字幕实际存在并同步
- 时长与 Timeline 一致
- QC 报告与实际文件一致

当前状态：**通过**。v2 产品证明获 `useful`；首次 canonical 输出因容器缺 CJK 字体产生乱码，机器 QC 未能识别该视觉错误。修复 run `da464df7-3c93-4a38-acde-fed53191acec` 已显式挂载 `Heiti SC`、对长句按 12 字换行，TechnicalQCReport passed；七个 narration cue 逐段抽帧正常，项目负责人整片复核结论为“目前可接受”。

### Checkpoint C — Product Decision

产品负责人分别评价：

- 剧情是否准确
- Hook 是否有吸引力
- 节奏是否值得继续
- 声音是否可接受
- 字幕是否可读
- 相比人工流程是否节省时间

结论只允许：useful、useful_with_revision、reject。没有人工结论，不进入下一个大模块。

当前决策：v1 = `useful_with_revision`；v2 = `useful`。通过项：声音、原声/解说比例、字幕、七段解说后的剧情表达与信息密度。First Usable Cut 的产品效果检查点已关闭；这不自动关闭 canonical Artifact 与正式 E11 qualification。

## 5. 下一执行批次

只做一个纵向批次：`Director Decision Provenance → Visual–Narration Anchor → TTS Reflow/Cache → held-out 跨集候选`。

明确不在本批次扩展：

- 新 Provider
- 新 Schema，除非现有 Contract 无法表达修复
- Confidence/L2+
- 在线指标
- 多租户和额外基础设施

## 6. 周报格式

以后项目进展只需回答：

1. 本周新增了哪个可打开的产物？
2. 产品负责人认为 useful、revise 还是 reject？
3. First Usable Cut 关闭了哪个 blocker？
4. 下周唯一可演示目标是什么？

工程测试和提交记录作为附件证据，不再作为进度主体。

详细规则：`product/PRODUCT_CONTROL_SYSTEM.md`。
验证卡：`product/MODULE_VALIDATION_CARDS.md`。
